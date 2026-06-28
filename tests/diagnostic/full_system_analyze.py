"""
tests/diagnostic/full_system_analyze.py — analyze a full_system_run output dir.

Reads run_<arm>_<seed>.jsonl + summary.json from an output dir, produces plots/
(PNG) and an aggregate.json (per-arm statistics averaged across seeds). Pairs
with tests/diagnostic/full_system_run.py. Informational (exit 0).

Usage:
  python -m tests.diagnostic.full_system_analyze --out docs/findings/logs/2026-06-28-full-system-run
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _load_runs(out_dir: str):
    """Return {(arm, seed): [rows...]} from the jsonl traces."""
    runs = {}
    for path in sorted(glob.glob(os.path.join(out_dir, "run_*.jsonl"))):
        base = os.path.basename(path)[len("run_"):-len(".jsonl")]
        arm, _, seed = base.rpartition("_")
        rows = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        runs[(arm, int(seed))] = rows
    return runs


def _series(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]


def _arms(runs):
    out = defaultdict(list)
    for (arm, seed) in runs:
        out[arm].append(seed)
    return out


def _mean_trajectory(runs, arm, key, n):
    """Mean over seeds of a per-step series, truncated to n."""
    mats = []
    for (a, s), rows in runs.items():
        if a != arm:
            continue
        ser = [r.get(key) for r in rows[:n]]
        ser = [x if isinstance(x, (int, float)) else np.nan for x in ser]
        if len(ser) < n:
            ser += [np.nan] * (n - len(ser))
        mats.append(ser)
    if not mats:
        return None
    return np.nanmean(np.array(mats, dtype=float), axis=0)


def plot_trajectories(runs, out_dir):
    arms = sorted(_arms(runs))
    n = min(len(rows) for rows in runs.values())
    pdir = os.path.join(out_dir, "plots")
    os.makedirs(pdir, exist_ok=True)

    specs = [
        ("coherence",        "Coherence C",          "coherence_trajectory.png"),
        ("field_energy",     "Field energy ||f||",   "field_energy_trajectory.png"),
        ("dilation_factor",  "Dilation factor",      "dilation_trajectory.png"),
        ("emo_arousal",      "Arousal",              "arousal_trajectory.png"),
        ("emo_valence",      "Valence",              "valence_trajectory.png"),
    ]
    for key, label, fname in specs:
        plt.figure(figsize=(9, 4))
        for arm in arms:
            traj = _mean_trajectory(runs, arm, key, n)
            if traj is not None:
                plt.plot(traj, label=f"{arm}", linewidth=1.1)
        plt.title(f"{label} over steps (mean across seeds)")
        plt.xlabel("step"); plt.ylabel(label); plt.legend(); plt.grid(alpha=0.3)
        plt.tight_layout(); plt.savefig(os.path.join(pdir, fname), dpi=110); plt.close()

    # metastability stage A (generator) vs stage C (expression), per arm
    plt.figure(figsize=(9, 4))
    for arm in arms:
        for key, style in (("meta_gen", "--"), ("meta_expr", "-")):
            traj = _mean_trajectory(runs, arm, key, n)
            if traj is not None:
                plt.plot(traj, style, label=f"{arm} {key}", linewidth=1.0)
    plt.title("Metastability: stage A (generator, --) vs stage C (expression, —)")
    plt.xlabel("step"); plt.ylabel("metastability"); plt.legend(fontsize=8); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(pdir, "metastability_AvsC.png"), dpi=110); plt.close()

    # rhythm distribution (fraction) per arm
    plt.figure(figsize=(8, 4))
    rhythm_order = ["stabilize", "dream", "reflect", "explore"]
    width = 0.8 / max(1, len(arms))
    for i, arm in enumerate(arms):
        counts = Counter()
        total = 0
        for (a, s), rows in runs.items():
            if a != arm:
                continue
            for r in rows:
                counts[r.get("rhythm")] += 1; total += 1
        fracs = [counts.get(rh, 0) / total if total else 0 for rh in rhythm_order]
        x = np.arange(len(rhythm_order)) + i * width
        plt.bar(x, fracs, width=width, label=arm)
    plt.xticks(np.arange(len(rhythm_order)) + width * (len(arms) - 1) / 2, rhythm_order)
    plt.title("Rhythm distribution (fraction of steps)")
    plt.ylabel("fraction"); plt.legend(); plt.grid(alpha=0.3, axis="y")
    plt.tight_layout(); plt.savefig(os.path.join(pdir, "rhythm_distribution.png"), dpi=110); plt.close()

    return pdir


def aggregate(runs, out_dir):
    """Per-arm stats averaged across seeds."""
    agg = {}
    for arm in sorted(_arms(runs)):
        seeds = sorted(_arms(runs)[arm])
        per_seed = []
        for s in seeds:
            rows = runs[(arm, s)]
            rh = Counter(r.get("rhythm") for r in rows)
            tot = sum(rh.values())
            per_seed.append({
                "seed": s,
                "coherence_mean": statistics.fmean(_series(rows, "coherence")) if _series(rows, "coherence") else None,
                "energy_mean":    statistics.fmean(_series(rows, "field_energy")) if _series(rows, "field_energy") else None,
                "dilation_mean":  statistics.fmean(_series(rows, "dilation_factor")) if _series(rows, "dilation_factor") else None,
                "meta_gen_mean":  statistics.fmean(_series(rows, "meta_gen")) if _series(rows, "meta_gen") else None,
                "meta_expr_mean": statistics.fmean(_series(rows, "meta_expr")) if _series(rows, "meta_expr") else None,
                "explore_frac":   rh.get("explore", 0) / tot if tot else None,
                "dream_frac":     rh.get("dream", 0) / tot if tot else None,
                "crystals_final": rows[-1].get("crystals") if rows else None,
                "attractors_final": rows[-1].get("attractors") if rows else None,
            })

        def _avg(field):
            xs = [d[field] for d in per_seed if d[field] is not None]
            return {"mean": statistics.fmean(xs), "stdev": statistics.pstdev(xs) if len(xs) > 1 else 0.0} if xs else None

        agg[arm] = {
            "seeds": seeds,
            "coherence": _avg("coherence_mean"),
            "field_energy": _avg("energy_mean"),
            "dilation": _avg("dilation_mean"),
            "metastability_gen": _avg("meta_gen_mean"),
            "metastability_expr": _avg("meta_expr_mean"),
            "explore_frac": _avg("explore_frac"),
            "dream_frac": _avg("dream_frac"),
            "per_seed": per_seed,
        }
    with open(os.path.join(out_dir, "aggregate.json"), "w") as f:
        json.dump(agg, f, indent=2, default=float)
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    runs = _load_runs(args.out)
    if not runs:
        print(f"No run_*.jsonl found in {args.out}")
        return 1
    print(f"Loaded {len(runs)} runs: {sorted(runs)}")
    pdir = plot_trajectories(runs, args.out)
    agg = aggregate(runs, args.out)
    print(f"Plots → {pdir}")
    print("Aggregate (per arm):")
    for arm, a in agg.items():
        print(f"  {arm}: coherence={a['coherence']}, explore_frac={a['explore_frac']}, "
              f"dream_frac={a['dream_frac']}, meta_expr={a['metastability_expr']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
