"""
tests/diagnostic/full_system_run.py — full-system instrumented run (capture + summarize).

Boots the FULLY composed engine via loop.recursion1188.build_engine (exercising the
configs/*.yaml load path), drives multi-source steps, and records the whole
observable state to disk for offline analysis / tuning. Informational (exit 0);
not a CI gate.

Paired design for attributable differences:
  arm "levers_on"  — default CONFIG (corpus pretrain + novelty attenuation ON)
  arm "levers_off" — graduated levers OFF (pretrain off, novelty off); dim 128,
                     eval-mode still on. The pre-graduation baseline.
Each arm runs over several seeds.

Outputs (per --out dir):
  manifest.md                      run config, seeds, versions, commit sha, env
  run_<arm>_<seed>.jsonl           per-step rich trace
  status_<arm>_<seed>.json         periodic full status() snapshots
  governance_<arm>_<seed>.json     end-of-run governance audit (decision histogram)
  summary.json                     aggregated per-arm/seed statistics

Usage:
  python -m tests.diagnostic.full_system_run \
      --steps 1000 --seeds 42,7,11 --arms levers_on,levers_off \
      --out docs/findings/logs/2026-06-28-full-system-run
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import Counter

import numpy as np

from loop.recursion1188 import CONFIG, SOURCES, SOURCE_WEIGHTS, build_engine


ARMS = {
    "levers_on":  {},  # default CONFIG
    "levers_off": {"pretrain_on_corpus": False, "reflect_novelty_attenuation": False},
    # Experimental: current default + generator common-mode projection. Compared
    # against `levers_on` to decide whether common-mode projection earns default-on.
    "common_mode": {"project_common_mode": True},
}


def _val(obj, name, default=None):
    """Read attr `name`, calling it if it's a method/callable (handles the
    property-vs-method split across emotion accessors). Never raises."""
    try:
        v = getattr(obj, name)
        return v() if callable(v) else v
    except Exception:
        return default


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _step_row(step_i: int, source_id: str, state, cycle) -> dict:
    """Cheap, always-available per-step metrics: StepState + emotion + subjective time
    + upstream metastability (stage A generator / stage C expression)."""
    row = state.as_dict()
    row["source_id"] = source_id
    e = cycle.emotion
    for name in ("curiosity", "wonder", "joy", "tension", "boredom", "stability",
                 "arousal", "valence", "field_decay_rate", "attractor_pull",
                 "crystal_pressure"):
        row[f"emo_{name}"] = _val(e, name)
    row["dilation_factor"] = _val(cycle.stream, "dilation_factor")
    row["subjective_time"] = _val(cycle.stream, "subjective_time")
    for tag, mon in (("meta_gen", cycle.generator_metastability),
                     ("meta_expr", cycle.expression_metastability)):
        if mon is not None:
            snap = mon.snapshot() or {}
            row[tag] = snap.get("metastability", snap.get("score"))
            row[f"{tag}_regimes"] = snap.get("n_regimes")
    return row


def _governance_audit(cycle) -> dict:
    """End-of-run decision histogram + trust/bond/HHI summary, defensively."""
    out = {}
    gov = getattr(cycle, "governance", None)
    if gov is None:
        return out
    try:
        out["status"] = gov.status()
    except Exception as exc:
        out["status_error"] = str(exc)
    # Decision histogram + gate-firing counts from the bounded audit log
    # (SelfhoodGovernance._audit_log: List[dict], capped at 512 — so this is the
    # last <=512 decisions of the run).
    log = getattr(gov, "_audit_log", None)
    if isinstance(log, list) and log:
        decs = Counter(str(e.get("decision")) for e in log if isinstance(e, dict))
        gates = Counter()
        for e in log:
            for g in (e.get("gates_fired") or []):
                gates[str(g)] += 1
        out["decision_histogram"] = dict(decs)
        out["decisions_in_log"] = len(log)
        out["gates_fired_histogram"] = dict(gates)
    return out


def run_arm(arm: str, seed: int, steps: int, status_every: int, out_dir: str) -> dict:
    overrides = ARMS[arm]
    cfg = {**CONFIG, **overrides}

    _seed_all(seed)
    t_boot = time.perf_counter()
    generator, cycle, governance, value_engine = build_engine(cfg)
    boot_s = time.perf_counter() - t_boot

    sids = list(SOURCES.keys())
    weights = [SOURCE_WEIGHTS[s] for s in sids]
    src_rng = random.Random(seed)

    run_path = os.path.join(out_dir, f"run_{arm}_{seed}.jsonl")
    status_path = os.path.join(out_dir, f"status_{arm}_{seed}.json")
    snapshots = []

    rhythms, decisions_seen = Counter(), 0
    coh, energy, dil, meta_gen, meta_expr = [], [], [], [], []
    dreams = 0
    t0 = time.perf_counter()
    with open(run_path, "w") as f:
        for i in range(steps):
            source_id = src_rng.choices(sids, weights=weights)[0]
            tokens = src_rng.choice(SOURCES[source_id])
            state = cycle.step(tokens, source_id=source_id, origin_type="internal")
            row = _step_row(i, source_id, state, cycle)
            f.write(json.dumps(row, default=float) + "\n")

            rhythms[row.get("rhythm")] += 1
            if row.get("rhythm") == "dream":
                dreams += 1
            if row.get("coherence") is not None:
                coh.append(row["coherence"])
            if row.get("field_energy") is not None:
                energy.append(row["field_energy"])
            if row.get("dilation_factor") is not None:
                dil.append(row["dilation_factor"])
            if row.get("meta_gen") is not None:
                meta_gen.append(row["meta_gen"])
            if row.get("meta_expr") is not None:
                meta_expr.append(row["meta_expr"])

            if status_every and (i % status_every == 0 or i == steps - 1):
                try:
                    snap = cycle.status()
                    snap["_step_index"] = i
                    snapshots.append(snap)
                except Exception as exc:
                    snapshots.append({"_step_index": i, "error": str(exc)})
    wall_s = time.perf_counter() - t0

    with open(status_path, "w") as f:
        json.dump(snapshots, f, indent=2, default=float)

    gov_audit = _governance_audit(cycle)
    with open(os.path.join(out_dir, f"governance_{arm}_{seed}.json"), "w") as f:
        json.dump(gov_audit, f, indent=2, default=float)

    final = snapshots[-1] if snapshots else {}

    def _ms(xs):
        return {"mean": statistics.fmean(xs), "stdev": (statistics.pstdev(xs) if len(xs) > 1 else 0.0),
                "min": min(xs), "max": max(xs)} if xs else None

    return {
        "arm": arm, "seed": seed, "steps": steps,
        "boot_s": round(boot_s, 2), "wall_s": round(wall_s, 2),
        "rhythm_histogram": dict(rhythms),
        "dreams_fired": dreams,
        "coherence": _ms(coh), "field_energy": _ms(energy),
        "dilation_factor": _ms(dil),
        "metastability_gen": _ms(meta_gen), "metastability_expr": _ms(meta_expr),
        "final_crystals": final.get("crystals"),
        "final_attractors": final.get("attractors"),
        "final_bonds": (final.get("governance", {}).get("bonds", {}) if isinstance(final.get("governance"), dict) else {}),
        "final_hhi": (final.get("governance", {}).get("dependency", {}).get("hhi")
                      if isinstance(final.get("governance"), dict) else None),
        "final_values": final.get("values"),
        "decision_histogram": gov_audit.get("decision_histogram"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--seeds", type=str, default="42,7,11")
    ap.add_argument("--arms", type=str, default="levers_on,levers_off")
    ap.add_argument("--status-every", type=int, default=25)
    ap.add_argument("--out", type=str,
                    default="docs/findings/logs/full-system-run")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    arms = [a for a in args.arms.split(",") if a.strip() in ARMS]
    os.makedirs(args.out, exist_ok=True)

    # manifest
    try:
        import torch
        torch_v = torch.__version__
    except Exception:
        torch_v = "n/a"
    manifest = [
        "# Full-system run — manifest",
        "",
        f"- Date (UTC): {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"- Commit: `{_git_sha()}`",
        f"- Python: {platform.python_version()} | numpy {np.__version__} | torch {torch_v}",
        f"- Platform: {platform.platform()}",
        f"- Steps: {args.steps} | seeds: {seeds} | arms: {arms} | status_every: {args.status_every}",
        "",
        "Arms:",
        "- `levers_on`  — default CONFIG (corpus pretrain + novelty attenuation ON)",
        "- `levers_off` — graduated levers OFF (pretrain off, novelty off); dim 128, eval on",
        "",
        f"Input: weighted multi-source round-robin over {list(SOURCES.keys())} "
        f"(weights {SOURCE_WEIGHTS}), origin_type='internal'.",
    ]
    with open(os.path.join(args.out, "manifest.md"), "w") as f:
        f.write("\n".join(manifest) + "\n")

    results = []
    for arm in arms:
        for seed in seeds:
            print(f"[run] arm={arm} seed={seed} steps={args.steps} ...", flush=True)
            res = run_arm(arm, seed, args.steps, args.status_every, args.out)
            results.append(res)
            print(f"  done boot={res['boot_s']}s wall={res['wall_s']}s "
                  f"rhythm={res['rhythm_histogram']} dreams={res['dreams_fired']} "
                  f"coh={res['coherence']['mean'] if res['coherence'] else None:.4} "
                  f"meta_expr={res['metastability_expr']['mean'] if res['metastability_expr'] else None}",
                  flush=True)

    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(results, f, indent=2, default=float)
    print(f"[done] {len(results)} runs → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
