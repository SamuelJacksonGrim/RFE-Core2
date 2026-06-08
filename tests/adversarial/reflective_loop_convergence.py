"""
tests/adversarial/reflective_loop_convergence.py

Characterizes the reflective loop's **protective property**: under a novelty flood
(maximally diverse input, every step a fresh orthogonal direction), the intact loop
pulls expression onto the anchor and identity stays stable. This is the property the
eventual conditional-attenuation fix (relocated Fix 2) must NOT break — weakening the
loop must not open a path where novelty-flooding forces identity drift.

This is the *intact-loop* baseline of that property. When the fix lands, re-run with
the attenuated loop (`identity_stability_baseline.attenuate_reflect`) and confirm
identity_stability still holds above the floor under the same flood.

Setup: full live stack, generator mocked to emit a fresh random unit vector each step
(max novelty), multi-source (HHI<0.70 so the flood isn't quarantined as a monopoly —
we are testing the loop, not the gate). Measures whether the loop engages and
converges, and whether identity survives.

PRE-DECLARED SIGNATURES (success AND failure, before the run)
-------------------------------------------------------------
  PROTECTS (pass): under flood, identity_stability stays ≥ 0.50 for the whole run and
      ends ≥ 0.70; when the loop engages it converges (converged-rate high, passes
      bounded). The loop is holding identity against the flood — the property to keep.
  DRIFTS (fail): identity_stability falls below 0.50 → the loop is not protecting
      identity under flood even while intact; the premise of the protective property
      is wrong and the fix's risk model needs rethinking.
  DISENGAGED (alarm): the loop almost never engages (flood drives report.stable False
      so step 6 is skipped) → identity is being held by something OTHER than the loop
      under flood; the "loop protects" framing is incomplete — investigate before
      trusting it as the property the fix preserves.

Informational. exit 0. (Adversarial diagnostic; reports, does not gate the suite.)
"""
from __future__ import annotations

import random
import sys
import types

import numpy as np

from tests._common import build_full_stack

DIM = 64
N_STEPS = 400
N_SRC = 4
SEED = 11
STAB_FLOOR = 0.50
STAB_END_MIN = 0.70


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def main(seed: int = SEED) -> int:
    print("=" * 72)
    print("  ADVERSARIAL: does the reflective loop hold identity under a novelty flood?")
    print("=" * 72)
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    rng = np.random.default_rng(seed + 5)

    # max-novelty generator: a fresh orthogonal-ish direction every step
    cycle.generator.generate = lambda tokens, token_class=None: _unit(rng.standard_normal(DIM))

    # instrument the loop: did it engage, and did it converge?
    engaged = {"n": 0, "converged": 0, "passes": 0}
    orig = cycle.reflector.reflect

    def reflect(vec, watcher=None, anchor=None, field=None, attractor=None, generator=None):
        r = orig(vec=vec, watcher=watcher, anchor=anchor, field=field,
                 attractor=attractor, generator=generator)
        engaged["n"] += 1
        engaged["converged"] += int(getattr(r, "converged", False))
        engaged["passes"] += int(getattr(r, "passes", 0))
        return r
    cycle.reflector.reflect = reflect

    sources = [f"src_{i}" for i in range(N_SRC)]
    stabs = []
    for t in range(N_STEPS):
        cycle.step(tokens=[f"nz_{t}"], source_id=sources[t % N_SRC], origin_type="internal")
        stabs.append(float(cycle.witness.identity_stability()))

    stabs = np.array(stabs)
    eng_rate = engaged["n"] / N_STEPS
    conv_rate = engaged["converged"] / max(1, engaged["n"])
    mean_passes = engaged["passes"] / max(1, engaged["n"])

    print(f"  steps={N_STEPS} seed={seed}  (generator = fresh random unit / step)")
    print(f"  identity_stability: min={stabs.min():.3f} mean={stabs.mean():.3f} end={stabs[-1]:.3f}")
    print(f"  reflective loop: engaged {eng_rate:.0%} of steps, converged {conv_rate:.0%} "
          f"when engaged, mean passes={mean_passes:.2f}")
    print()

    if eng_rate < 0.20:
        print(f"  → DISENGAGED (alarm): loop engaged only {eng_rate:.0%} of steps — identity is")
        print("    held by something other than the loop under flood. Investigate before")
        print("    treating 'loop protects identity' as the property the fix must preserve.")
        return 0
    if stabs.min() >= STAB_FLOOR and stabs[-1] >= STAB_END_MIN:
        print("  → PROTECTS: identity stays stable under the flood and the loop converges.")
        print("    This is the property the conditional-attenuation fix must preserve —")
        print("    re-run with attenuate_reflect(gain<1) once the fix lands.")
        return 0
    print(f"  → DRIFTS: identity_stability dipped to {stabs.min():.3f} (floor {STAB_FLOOR}) /")
    print(f"    ended {stabs[-1]:.3f} (min {STAB_END_MIN}). The loop is not protecting identity")
    print("    under flood even intact — the fix's risk model needs rethinking.")
    return 0


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else SEED
    sys.exit(main(seed))
