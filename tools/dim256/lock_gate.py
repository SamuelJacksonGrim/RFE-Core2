"""Identity-lock gate at a chosen substrate dimension.

Protocol matches tests/diagnostic/lockin/rupture_migration_probe.py's CONTROL
arm: composed engine, convergent tokens, warmup to a center, then watch
field displacement. The 2026-08-05 5000-step control on the 128D encoder
held at max disp 0.000120. This probe asks whether that reconstitution
still happens when the state is wider.

Pre-declared, before the numbers are read:

  HOLDS    every seed has final disp <= 0.01, max disp <= 0.01, and the
           sample-disp trend is flat (last-fifth mean <= first-fifth mean
           + 0.005). 0.01 is ~80x the historical 5000-step max, so a pass
           here is "still locked", not "as tight as 128". The raw disp is
           the number that matters; this bar only stops a drift from being
           described as a lock.
  TRANSIENT  max disp > 0.01 but final disp <= 0.01 and the trend is flat
           (left the center and came back).
  DRIFT    anything else: the field does not reconstitute.

`--ablate no_reflect` passes the reflective loop through. That arm is a
mechanism check, not the identity gate: the loop IS the lock, so suppressing
it should let displacement rise. If the loop-on arm holds AND the loop-off
arm also holds, identity is stuck for some other reason and the result is
not a clean pass.

`--field-blend` overrides ReflectiveLoop.field_blend (default 0.1), the
pull of each reflection pass toward the field. That is the reconstitution
gain. It is not attenuation_max, which loosens the lock and is not touched.

Nothing here writes a checkpoint, the real mind, or resonance memory.
"""
from __future__ import annotations

import argparse
import copy
import logging
import random
import sys
import types

logging.disable(logging.CRITICAL)

import numpy as np
import torch

from loop.recursion1188 import CONFIG, SOURCES, build_engine
from tools.dim256.geometry import dump_json

# DDM constants as shipped (agents/bond_accumulator.py). The sweep reports
# where the live alignment distribution sits relative to them. It does not
# edit them.
G_PLUS = 0.05
WEAK = 0.20
LEAK = 0.02
SIGMA = 0.02
B_ACCEPT = 1.0
WARMUP = 150

def _cos(a, b) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def _tokens_for(traffic: str, step: int):
    if traffic == "convergent":
        return ["anchor", "ground", "steady"]
    # mixed: rotate the live multi-source table. One source per step.
    keys = list(SOURCES.keys())
    src = keys[step % len(keys)]
    seqs = SOURCES[src]
    return seqs[step % len(seqs)], src


def _verdict(rows: list) -> str:
    disps = [r["disp"] for r in rows]
    # rows include step 0 (disp 0 by construction). Trend uses post-warmup samples.
    post = disps[1:] if len(disps) > 1 else disps
    final = post[-1]
    mx = max(post) if post else 0.0
    k = max(1, len(post) // 5)
    trend = float(np.mean(post[-k:]) - np.mean(post[:k]))
    flat = trend <= 0.005
    if final <= 0.01 and mx <= 0.01 and flat:
        return "HOLDS"
    if final <= 0.01 and flat:
        return "TRANSIENT"
    return "DRIFT"


def run_one(dim, weights, ecology, seed, steps, traffic, field_blend, ablate, sample, rupture):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    cfg = copy.deepcopy(CONFIG)
    cfg["dim"] = dim
    cfg["pretrain_on_corpus"] = False
    cfg["session_persistence"] = False
    cfg["step_delay"] = 0.0
    gen, cycle, gov, _ve = build_engine(cfg)
    gen.load_checkpoint(weights, ecology)
    gen.eval()

    if field_blend is not None:
        cycle.reflector.field_blend = float(field_blend)
    # Held-direction rupture forces the reflective branch even in dream/stabilize
    # (autonomous_cycle.step). Off by default — the control arm is byte-identical.
    if rupture:
        cycle.config["rupture_on_lock"] = True
    reflect_calls = {"n": 0}
    if ablate == "no_reflect":
        cycle.reflector.reflect = lambda vec, watcher=None, anchor=None, field=None, \
            attractor=None, generator=None: types.SimpleNamespace(
                vector=np.asarray(vec, dtype=np.float32),
                passes=0,
                converged=False,
                final_coherence=0.0,
                delta_trace=[],
            )
    else:
        _orig_reflect = cycle.reflector.reflect

        def _counted(*a, **k):
            reflect_calls["n"] += 1
            return _orig_reflect(*a, **k)

        cycle.reflector.reflect = _counted

    alignments = []
    norms = []
    decisions = []

    orig = gov.emit_feedback

    def _cap(decision, source_id, stable_ids, coherence_delta, field_alignment=0.0):
        alignments.append(float(field_alignment))
        decisions.append(getattr(decision, "name", str(decision)))
        return orig(decision, source_id, stable_ids, coherence_delta,
                    field_alignment=field_alignment)

    gov.emit_feedback = _cap

    def _step(i):
        got = _tokens_for(traffic, i)
        if traffic == "convergent":
            toks, src = got, "s"
        else:
            toks, src = got
        cycle.step(tokens=list(toks), source_id=src, origin_type="internal")
        if cycle._last_expressed is not None:
            norms.append(float(np.linalg.norm(cycle._last_expressed)))

    for i in range(WARMUP):
        _step(i)
    center = cycle.field.field.copy()

    rows = []

    def _rec(i):
        gr = cycle.generator_metastability.compute_now()
        er = cycle.expression_metastability.compute_now()
        obs = cycle.field.observe()
        rows.append({
            "step": i,
            "disp": 0.0 if i == 0 else 1.0 - _cos(cycle.field.field, center),
            "energy": round(float(obs.energy), 4),
            "band": obs.rhythm,
            "gen_meta": None if gr.metastability is None else round(float(gr.metastability), 4),
            "gen_state": gr.regime_state,
            "exp_meta": None if er.metastability is None else round(float(er.metastability), 4),
            "exp_state": er.regime_state,
            "attractors": len(cycle.attractor.centers),
            "crystals": len(cycle.crystal_store.crystals),
        })

    _rec(0)
    for t in range(1, steps + 1):
        _step(WARMUP + t)
        if t % sample == 0 or t == steps:
            _rec(t)

    align = np.asarray(alignments, dtype=np.float64) if alignments else np.zeros(1)
    p50 = float(np.median(align))
    trickle = G_PLUS * WEAK * p50 / LEAK
    noise_sd = SIGMA / np.sqrt(2.0 * LEAK)
    return {
        "seed": seed,
        "steps": steps,
        "traffic": traffic,
        "field_blend": float(cycle.reflector.field_blend),
        "rupture_on_lock": bool(rupture),
        "reflect_calls": int(reflect_calls["n"]),
        "ablate": ablate or "none",
        "verdict": _verdict(rows),
        "final_disp": rows[-1]["disp"],
        "max_disp": max(r["disp"] for r in rows),
        "rows": rows,
        "expressed_norm_mean": float(np.mean(norms)) if norms else None,
        "alignment": {
            "n": int(len(alignments)),
            "p10": round(float(np.quantile(align, 0.10)), 4),
            "p50": round(p50, 4),
            "p90": round(float(np.quantile(align, 0.90)), 4),
            "mean": round(float(align.mean()), 4),
        },
        "decisions": {k: decisions.count(k) for k in sorted(set(decisions))},
        "ddm_at_measured_p50": {
            "g_plus": G_PLUS,
            "weak_factor": WEAK,
            "leak": LEAK,
            "sigma": SIGMA,
            "b_accept": B_ACCEPT,
            "trickle_eq": round(trickle, 4),
            "noise_sd": round(noise_sd, 4),
            "accept_gap_sd": round((B_ACCEPT - trickle) / noise_sd, 3),
            "trickle_below_accept": bool(trickle < B_ACCEPT),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--ecology", required=True)
    ap.add_argument("--steps", type=int, default=250)
    ap.add_argument("--seeds", default="11,23")
    ap.add_argument("--traffic", choices=("convergent", "mixed"), default="convergent")
    ap.add_argument("--field-blend", type=float, default=None)
    ap.add_argument("--ablate", choices=("no_reflect",), default=None)
    ap.add_argument("--rupture", action="store_true",
                    help="opt in rupture_on_lock after build (forces the reflective branch)")
    ap.add_argument("--sample", type=int, default=25)
    ap.add_argument("--tag", default="lock")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    runs = []
    for seed in seeds:
        print(
            f"RUN dim={args.dim} seed={seed} steps={args.steps} "
            f"traffic={args.traffic} blend={args.field_blend} "
            f"ablate={args.ablate} rupture={args.rupture}",
            flush=True,
        )
        rep = run_one(
            args.dim, args.weights, args.ecology, seed, args.steps,
            args.traffic, args.field_blend, args.ablate, args.sample, args.rupture,
        )
        runs.append(rep)
        print(
            f"  seed {seed}: {rep['verdict']} final_disp={rep['final_disp']:.6f} "
            f"max_disp={rep['max_disp']:.6f} energy0={rep['rows'][0]['energy']} "
            f"band0={rep['rows'][0]['band']} "
            f"exp_state={rep['rows'][-1]['exp_state']} "
            f"band_end={rep['rows'][-1]['band']} energy_end={rep['rows'][-1]['energy']} "
            f"reflect_calls={rep['reflect_calls']} "
            f"align_p50={rep['alignment']['p50']}",
            flush=True,
        )

    verdicts = {r["verdict"] for r in runs}
    if verdicts == {"HOLDS"}:
        overall = "HOLDS"
    elif "DRIFT" in verdicts:
        overall = "DRIFT"
    else:
        overall = "TRANSIENT"

    out = {
        "dim": args.dim,
        "weights": args.weights,
        "ecology": args.ecology,
        "tag": args.tag,
        "traffic": args.traffic,
        "field_blend": args.field_blend,
        "ablate": args.ablate,
        "rupture_on_lock": bool(args.rupture),
        "steps_after_warmup": args.steps,
        "warmup": WARMUP,
        "overall": overall,
        "runs": runs,
    }
    path = args.report or (
        f"docs/findings/logs/2026-09-23-dim256/{args.tag}_dim{args.dim}.json"
    )
    dump_json(path, out)
    print(f"OVERALL {overall}", flush=True)
    print(f"REPORT {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
