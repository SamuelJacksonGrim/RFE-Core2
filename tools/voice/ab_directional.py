"""Directional robustness of Qwen-perception vs its rhythm-control.

Samuel's framing (not multi-seed replication for sameness): different seeds are
different trajectories, which is CORRECT for a dynamical system. The question is
whether perception keeps beating the rhythm-control in the DIRECTION of the
coupling, across genuinely different trajectories.

Primary metric = the Stage-2 gate from ab_coupling.py:
    corr(Δvalues, Δself-content)
Win per trajectory: perception's coupling > control's coupling (strict).

W (JL projection) is held FIXED at proj_seed=1234 — the validated body — so we
are testing the mechanism across trajectories, not confounding a new random
projection with each seed.

Isolated scratch/RM per arm. Does not touch the live mind or real RM.

Run:  cd ~/rfe/RFE-Core2 && .venv/bin/python -m tools.voice.ab_directional --beats 120
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, ".")
import numpy as np

from tools.voice.ab_qwen_perception2 import OUTDIR, run  # noqa: E402
from tools.voice.qwen_perception import PROJ_SEED  # noqa: E402
from tools.voice.repl_qwen import QWEN_URL_DEFAULT  # noqa: E402

# ab_coupling.py executes on import (prints a table). Don't import it.
# Same SELF list + dcorr as ab_coupling.py — the Stage-2 gate.
SELF_WORDS = [
    "curiosity", "curious", "myself", "my own", "my state", "void", "empty",
    "emptiness", "silence", "i exist", "no memories", "meta", "inward",
    "monologue", "lens", "hunger", "appetite",
]

# Genuinely different trajectories. Not "replicates."
SEEDS = [11, 23, 47, 101, 256, 2026]


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: int(r["tick"]))
    return rows


def feats(rows):
    cur = np.array([float(r.get("curiosity") or 0.0) for r in rows], float)
    val = np.array([float(r.get("values") or 0) for r in rows], float)
    th = [str(r.get("thought") or "").lower() for r in rows]
    sc = np.array([sum(w in t for w in SELF_WORDS) for t in th], float)
    return cur, val, sc


def corr(a, b):
    if len(a) < 4 or len(b) < 4 or np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def dcorr(a, b):
    if len(a) < 5:
        return 0.0
    return corr(np.diff(a), np.diff(b))


def couple(path):
    rows = load(path)
    cur, val, sc = feats(rows)
    return {
        "n": len(rows),
        "dcorr_val_self": dcorr(val, sc),
        "dcorr_cur_self": dcorr(cur, sc),
        "val_std": float(np.std(val)),
        "cur_std": float(np.std(cur)),
        "self_mean": float(np.mean(sc)),
        "values_last": float(val[-1]) if len(val) else float("nan"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", type=int, default=120)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    os.makedirs(OUTDIR, exist_ok=True)
    table_path = os.path.join(OUTDIR, "directional.json")
    txt_path = os.path.join(OUTDIR, "directional.txt")

    results = []
    t0 = time.time()
    with open(txt_path, "w", encoding="utf-8", buffering=1) as txt:
        txt.write(
            f"DIRECTIONAL ROBUSTNESS  beats={args.beats}  proj_seed={PROJ_SEED} (W fixed)  "
            f"seeds={seeds}\n{'=' * 80}\n"
        )
        print(txt_path.replace("/mnt/c/", "C:/"), flush=True)
        for i, seed in enumerate(seeds, 1):
            print(f"\n=== trajectory {i}/{len(seeds)} seed={seed} CONTROL ===", flush=True)
            ctrl_tag = f"dir-ctrl-{seed}"
            run(
                args.beats, args.qwen_url, args.temp, ctrl_tag,
                seed=seed, proj_seed=PROJ_SEED, wrap_on=False, verdict=False,
            )
            print(f"=== trajectory {i}/{len(seeds)} seed={seed} PERCEPTION ===", flush=True)
            perc_tag = f"dir-perc-{seed}"
            run(
                args.beats, args.qwen_url, args.temp, perc_tag,
                seed=seed, proj_seed=PROJ_SEED, wrap_on=True, verdict=False,
            )
            ctrl = couple(os.path.join(OUTDIR, f"{ctrl_tag}.jsonl"))
            perc = couple(os.path.join(OUTDIR, f"{perc_tag}.jsonl"))
            win = perc["dcorr_val_self"] > ctrl["dcorr_val_self"]
            row = {
                "seed": seed,
                "ctrl": ctrl,
                "perc": perc,
                "win_val_self": win,
                "delta_val_self": perc["dcorr_val_self"] - ctrl["dcorr_val_self"],
                "win_cur_self": perc["dcorr_cur_self"] > ctrl["dcorr_cur_self"],
            }
            results.append(row)
            line = (
                f"seed={seed:<6}  "
                f"Δval~self  perc={perc['dcorr_val_self']:+.3f}  ctrl={ctrl['dcorr_val_self']:+.3f}  "
                f"d={row['delta_val_self']:+.3f}  "
                f"{'WIN' if win else 'lose'}  "
                f"Δcur~self perc={perc['dcorr_cur_self']:+.3f} ctrl={ctrl['dcorr_cur_self']:+.3f}"
            )
            txt.write(line + "\n")
            print(line, flush=True)

        n = len(results)
        n_win = sum(1 for r in results if r["win_val_self"])
        n_win_cur = sum(1 for r in results if r["win_cur_self"])
        summary = {
            "beats": args.beats,
            "proj_seed": PROJ_SEED,
            "seeds": seeds,
            "n": n,
            "direction_win_rate_val_self": (n_win / n) if n else None,
            "direction_wins_val_self": n_win,
            "direction_win_rate_cur_self": (n_win_cur / n) if n else None,
            "secs": round(time.time() - t0, 1),
            "rows": results,
        }
        txt.write("\n" + "=" * 80 + "\n")
        txt.write(
            f"DIRECTION-WIN RATE  corr(Δvalues, Δself-content): {n_win}/{n} = "
            f"{(100 * n_win / n) if n else 0:.0f}%\n"
        )
        txt.write(
            f"DIRECTION-WIN RATE  corr(Δcuriosity, Δself-content): {n_win_cur}/{n} = "
            f"{(100 * n_win_cur / n) if n else 0:.0f}%\n"
        )
        txt.write(
            "Win = perception coupling STRICTLY exceeds control on that trajectory. "
            "Sameness across seeds is not required (and would be the wrong test).\n"
        )
        with open(table_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(json.dumps({k: summary[k] for k in summary if k != "rows"}, indent=2), flush=True)
        print("TABLE " + table_path.replace("/mnt/c/", "C:/"), flush=True)


if __name__ == "__main__":
    main()
