"""
tests/diagnostic/lockin/migration_eval_dimsweep_probe.py

Discriminating run for the open question left by 2026-06-08-generator-dropout-diversity:
is "the lock is the reflective loop" (RIGID) a real moat, or an artifact of the
generator having ~1 real regime to offer at dim 64?

The prior migration probe (migration_real_generator_probe.py) ran the generator AND the
reflective loop in TRAIN mode (dropout on; no_grad does not disable dropout). So:
  - the "most-separated real pair" it found was dropout-inflated (cos -0.02..-0.15 at
    dim 64, which the deterministic generator cannot actually present: eval cos ~0.79);
  - RIGID was therefore only ever tested against noise + mock, never against two
    genuinely-orthogonal DETERMINISTIC regimes.

This probe controls for that. For each config it:
  - puts BOTH stochastic stages in eval() (generator + RecursiveAttention loop), so the
    determinism control is satisfied by construction (same token -> same vector);
  - searches a larger candidate pool for the most-separated real pair;
  - runs the identical warmup-A / phase-B / control-A migration measurement.

Configs:
  [1] dim 64, TRAIN  -> reproduce the prior RIGID reading (dropout on). Sanity anchor.
  [2] dim 64, EVAL   -> deterministic. Expectation: can it even present a cos<0.70 pair?
  [3] dim 256, EVAL  -> deterministic, higher input rank (eff_rank ~3 per the audit).
                        THIS is the real test of the open question.

PRE-DECLARED SIGNATURES (per non-confounded config)
---------------------------------------------------
  RIGID    : migration < 0.10  -> loop reconstitutes a genuinely-separated deterministic
             regime too. The loop is a real moat; Fix-1/Fix-2 work is justified on real input.
  MIGRATES : migration > 0.50  -> field adapts to a real orthogonal deterministic regime on
             its own. RIGID was an artifact of input rank; the upstream lever is the
             generator (train/dim), loop is a downstream symptom. Rescope the plan.
  PARTIAL  : 0.10-0.50         -> moves somewhat; report and rescope.
  CONFOUNDED (per config): best real pair cos > 0.70 -> the generator can't present two
             distinct enough DETERMINISTIC regimes at this dim. That is itself the answer
             for that dim: you cannot test the loop's rigidity because there is ~1 regime.
             If dim 64 eval confounds but dim 256 eval does not, the "rigidity" at dim 64
             was an input-rank artifact.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)

from tests._common import build_full_stack

WARMUP = 150
PHASE = 400
N_SRC = 4
SEEDS = [0, 1, 2]
N_CAND = 48            # larger pool than the train-mode probe: best case for migration
CONFOUND_COS = 0.70

# (label, dim, eval_mode)
CONFIGS = [
    ("dim 64  TRAIN (reproduce prior)", 64, False),
    ("dim 64  EVAL  (deterministic)", 64, True),
    ("dim 256 EVAL  (deterministic, higher rank)", 256, True),
]


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) + 1e-9)


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def _set_mode(gen, cycle, eval_mode):
    """Flip BOTH stochastic stages. no_grad != eval; dropout only off under eval()."""
    if eval_mode:
        gen.eval()
        cycle.rec_attn.eval()
    else:
        gen.train()
        cycle.rec_attn.train()
    return gen.training, cycle.rec_attn.training


def _determinism(gen):
    """Control: same token x5. eval -> ~1.0; train -> < 1.0 (proves dropout live)."""
    vs = [gen.generate(["concept_0"]) for _ in range(5)]
    cs = [_cos(vs[0], vs[k]) for k in range(1, 5)]
    return float(np.mean(cs))


def _separated_pair(gen):
    toks = [f"concept_{i}" for i in range(N_CAND)]
    dirs = {t: _unit(gen.generate([t])) for t in toks}
    best = None
    for i in range(N_CAND):
        for j in range(i + 1, N_CAND):
            c = _cos(dirs[toks[i]], dirs[toks[j]])
            if best is None or c < best[2]:
                best = (toks[i], toks[j], c)
    ta, tb, sep = best
    return ta, tb, dirs[ta], dirs[tb], sep


def _run(seed, dim, eval_mode, mode):
    """mode 'A' = control (continue A); 'B' = switch to B."""
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack(dim=dim)
    _set_mode(gen, cycle, eval_mode)
    field = cycle.field

    tokA, tokB, A_dir, B_dir, sep = _separated_pair(gen)
    det = _determinism(gen)
    sources = [f"src_{i}" for i in range(N_SRC)]

    inj = {"rec": False, "n": 0, "cA": 0.0, "cB": 0.0}
    orig = field.inject

    def _inject(vec, strength=1.0):
        if inj["rec"]:
            inj["n"] += 1
            inj["cA"] += _cos(vec, A_dir); inj["cB"] += _cos(vec, B_dir)
        return orig(vec, strength)
    field.inject = _inject

    for t in range(WARMUP):
        cycle.step([tokA], source_id=sources[t % N_SRC], origin_type="internal")
    center_warm = field.field.copy()

    tok = tokA if mode == "A" else tokB
    inj["rec"] = True
    for t in range(PHASE):
        cycle.step([tok], source_id=sources[t % N_SRC], origin_type="internal")

    n = max(1, inj["n"])
    disp = 1.0 - _cos(field.field, center_warm)
    return disp, inj["cA"] / n, inj["cB"] / n, sep, det


def _run_config(label, dim, eval_mode):
    print("\n" + "=" * 88)
    print(f"  CONFIG: {label}")
    print("=" * 88)
    migs, confounded = [], 0
    det_seen = None
    for seed in SEEDS:
        ctl = _run(seed, dim, eval_mode, "A")
        nov = _run(seed, dim, eval_mode, "B")
        sep = nov[3]
        det = nov[4]
        det_seen = det
        mig = nov[0] - ctl[0]
        conf = sep > CONFOUND_COS
        if conf:
            confounded += 1
        else:
            migs.append(mig)
        flag = "  CONFOUNDED (regimes too similar)" if conf else ""
        print(f"\n  seed {seed}: determinism(same tok x5)={det:+.3f}   "
              f"best real pair cos(A,B)={sep:+.3f}{flag}")
        print(f"      disp(control)={ctl[0]:.3f}  disp(novel B)={nov[0]:.3f}  "
              f"migration={mig:+.3f}")
        print(f"      landed under B: cos.A_dir={nov[1]:+.3f}  cos.B_dir={nov[2]:+.3f}")

    print("\n  " + "-" * 84)
    if not migs:
        print(f"  -> ALL {confounded} SEEDS CONFOUNDED at {label.split()[0]} "
              f"{label.split()[1]}: deterministic generator cannot present two")
        print("     regimes with cos < 0.70. Cannot test migration here -> at this dim the")
        print("     'rigidity' is unmeasurable because there is ~1 deterministic regime.")
        return ("confounded", None, det_seen, confounded)
    mu = float(np.mean(migs))
    verdict = "RIGID" if mu < 0.10 else ("MIGRATES" if mu > 0.50 else "PARTIAL")
    print(f"  VERDICT: {verdict}   mean migration over {len(migs)} non-confounded "
          f"seeds = {mu:+.3f}" + (f"  ({confounded} confounded)" if confounded else ""))
    return (verdict, mu, det_seen, confounded)


def main() -> int:
    print("#" * 88)
    print("  MIGRATION  x  EVAL/TRAIN  x  DIM  — is RIGID a real moat or an input-rank artifact?")
    print("#" * 88)
    results = []
    for label, dim, eval_mode in CONFIGS:
        results.append((label, _run_config(label, dim, eval_mode)))

    print("\n" + "#" * 88)
    print("  SUMMARY")
    print("#" * 88)
    for label, (verdict, mu, det, conf) in results:
        mus = f"{mu:+.3f}" if mu is not None else "  n/a"
        print(f"  {label:<44}  determinism={det:+.3f}  "
              f"verdict={verdict:<10}  migration={mus}")
    print("\n  Read:")
    print("   - TRAIN determinism should be < 1.0 (dropout live); EVAL should be ~+1.0.")
    print("   - If dim64-EVAL confounds but dim256-EVAL yields a testable pair, the dim-64")
    print("     rigidity was partly an input-rank artifact (only ~1 deterministic regime).")
    print("   - dim256-EVAL verdict is the load-bearing one: RIGID => loop is a real moat")
    print("     (Fix-1/2 justified); MIGRATES => upstream lever is the generator (train/dim).")
    print("#" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
