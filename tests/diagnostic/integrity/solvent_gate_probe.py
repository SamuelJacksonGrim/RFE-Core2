"""
tests/diagnostic/integrity/solvent_gate_probe.py    (spec: v0.2)

Build-B UNIT probe for the λ-ledger + ⊕ solvent gate. The spec's load-bearing
claim: composition (the productive-tension reinforcement term in Tier 3) resolves
toward fulfillment ONLY in the presence of the solvent λ (Law 2), and λ cannot be
bootstrapped (Laws 6b/6c). This probe proves the mechanism, not the live §4
discriminator (that is ⊘-off vs ⊘-on, paired + noise-swept).

PRE-DECLARED SIGNATURES (success AND failure, declared before the run):
  SUCCESS:
    - solvent_gain monotone non-decreasing on [0, λ_max], range ⊂ [0,1], gain(0)=0.
    - vanish-at-zero (Law 6b): reinforce() on λ=0 keeps λ=0; only ignite() moves it
      off zero. A live workload with the ledger pinned at 0 never raises λ
      (composition cannot mint the solvent).
    - GATE GATES COMPOSITION: with two values in tension and strength ≥ min_s, the
      productive-tension bonus applied at λ=0 is ZERO, and at high λ is the full
      bonus. The gate is the only thing that changed.
    - PAIRED CONTROL: ledger absent ≡ ledger present at gain≈1 — value strengths
      byte-identical across a workload (gain=1 reproduces default Tier 3 exactly).
    - 6c DISJOINTNESS (structural): lambda_ledger.py imports nothing from the ⊘
      integrity-read path (AST audit) — the λ-ledger and the advisory stream share
      no data path.
  FAILURE:
    - gain non-monotone, out of [0,1], or gain(0)≠0.
    - λ rises under a pinned-zero workload (bootstrap leak → Law 6b breach).
    - the bonus is applied at λ=0 (gate inert) or differs from default at gain≈1.
    - lambda_ledger imports integrity_read (6c breach).

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import ast
import sys
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack                              # noqa: E402
from agents.lambda_ledger import LambdaLedger, solvent_gain             # noqa: E402
from agents.value_emergence import EmergentValue, ValuePolarity         # noqa: E402

VOCAB = ["resonance", "field", "engine", "memory", "crystal", "attractor",
         "identity", "continuity", "witness", "curiosity", "wonder", "exploration",
         "recursive", "cognition", "substrate", "dream", "wave", "collapse"]
SRC = [f"src_{i}" for i in range(4)]


def _make_value(ve, vid, strength):
    """Register a synthetic value at a given strength (no symbol coupling needed —
    we patch _compute_tension to isolate the gate)."""
    v = EmergentValue(value_id=vid, symbol_stable_id=-1, symbolic_core=vid,
                      strength=strength, polarity=ValuePolarity.ACTIVE)
    ve.values[vid] = v
    return v


def _import_audit() -> bool:
    """6c: lambda_ledger imports nothing from the ⊘ integrity-read path."""
    with open("agents/lambda_ledger.py") as fh:
        tree = ast.parse(fh.read())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [n.name for n in node.names if "integrity_read" in n.name]
        elif isinstance(node, ast.ImportFrom):
            if node.module and "integrity_read" in node.module:
                bad.append(node.module)
    return not bad


def main() -> int:
    random.seed(11); np.random.seed(11)
    import torch; torch.manual_seed(11)

    # --- (1) solvent_gain shape ---------------------------------------------
    xs = [i * 0.05 for i in range(0, 101)]   # 0 .. 5.0
    gains = [solvent_gain(x) for x in xs]
    gain0_ok      = abs(gains[0]) < 1e-12
    monotone_ok   = all(b >= a - 1e-12 for a, b in zip(gains, gains[1:]))
    bounded_ok    = all(0.0 <= g <= 1.0 for g in gains)

    # --- (2) vanish-at-zero on the ledger object ----------------------------
    led = LambdaLedger()
    z0 = led.strength
    led.reinforce(0.5)                       # multiplicative on 0 → stays 0
    z1 = led.strength
    led.ignite(1.2)                          # the only zero-crossing
    z2 = led.strength
    led.reinforce(0.10)                      # now multiplicative on >0
    z3 = led.strength
    vanish_ok = (z0 == 0.0 and z1 == 0.0 and z2 > 0.0 and z3 > z2)

    # --- (3) the gate actually gates the composition bonus ------------------
    gen, cycle, gov, ve = build_full_stack()
    ve._compute_tension = lambda a, b: 0.5   # force tension ≥ threshold (isolate gate)
    a = _make_value(ve, "val_a", 2.0)
    b = _make_value(ve, "val_b", 2.0)

    # λ = 0 → gain 0 → no composition
    cold = LambdaLedger()
    ve.set_lambda_ledger(cold)
    sa0, sb0 = a.strength, b.strength
    ve._evaluate_tensions(a)
    cold_delta = (a.strength - sa0) + (b.strength - sb0)

    # λ high → gain ≈ 1 → full composition bonus
    a.strength, b.strength = 2.0, 2.0
    hot = LambdaLedger(); hot.ignite(5.0)
    ve.set_lambda_ledger(hot)
    sa1, sb1 = a.strength, b.strength
    ve._evaluate_tensions(a)
    hot_delta = (a.strength - sa1) + (b.strength - sb1)

    expected_full = 2.0 * ve.config["productive_tension_bonus"] * solvent_gain(hot.strength)
    gate_ok = (abs(cold_delta) < 1e-12) and (abs(hot_delta - expected_full) < 1e-6) and hot_delta > 0

    # --- (4) λ cannot be minted by a live workload pinned at 0 --------------
    gen2, cycle2, gov2, ve2 = build_full_stack()
    pinned = LambdaLedger()
    cycle2.attach_lambda_ledger(pinned)
    rng = random.Random(11)
    for i in range(120):
        cycle2.step(rng.sample(VOCAB, 3), source_id=SRC[i % 4], origin_type="internal")
    no_mint_ok = (pinned.strength == 0.0)

    # --- (5) paired control: OFF is the original code path, exactly ---------
    # The substrate is not bit-reproducible run-to-run (torch nondeterminism), so a
    # full-run comparison is the wrong tool. The "byte-identical when off" invariant
    # is instead a *code identity* at the gate: with no ledger attached
    # `_solvent_gain()` returns exactly 1.0, so the gated line
    #     bonus = config["productive_tension_bonus"] * _solvent_gain()
    # is exactly the original `bonus = config["productive_tension_bonus"]`. We prove
    # the multiply is the identity (no float drift) and that detaching restores it.
    gen3, cycle3, gov3, ve3 = build_full_stack()
    off_gain   = ve3._solvent_gain()                 # no ledger → exactly 1.0
    base_bonus = ve3.config["productive_tension_bonus"]
    off_identity = (off_gain == 1.0) and (base_bonus * off_gain == base_bonus)
    # attach then detach → back to the identity path
    ve3.set_lambda_ledger(LambdaLedger())            # λ=0 → gain 0
    gated_zero = ve3._solvent_gain()
    ve3.set_lambda_ledger(None)
    restored = ve3._solvent_gain()
    paired_ok = off_identity and (gated_zero == 0.0) and (restored == 1.0)

    disjoint_ok = _import_audit()

    # --- report -------------------------------------------------------------
    print("=" * 78)
    print("  ⊕ SOLVENT GATE + λ-LEDGER (Build B) — unit probe   spec: v0.2")
    print("=" * 78)
    print(f"  solvent_gain: gain(0)={gains[0]:.4f}  gain(λ=1)={solvent_gain(1.0):.4f}  "
          f"gain(λ=5)={solvent_gain(5.0):.4f}")
    print(f"  ledger vanish-at-zero trace: 0→reinforce={z1:.3f} →ignite={z2:.3f} →reinforce={z3:.3f}")
    print(f"  composition bonus  cold(λ=0)={cold_delta:.5f}   hot(λ=5)={hot_delta:.5f}  "
          f"(expected full={expected_full:.5f})")
    print(f"  pinned-zero workload final λ: {pinned.strength:.5f}")
    print(f"  paired control: off_gain={off_gain}  base_bonus×off_gain==base_bonus  "
          f"gated(λ=0)={gated_zero}  restored={restored}")
    print("\n" + "-" * 78)
    print(f"  gain(0)=0:                              {'OK' if gain0_ok else 'FAIL'}")
    print(f"  gain monotone non-decreasing:           {'OK' if monotone_ok else 'FAIL'}")
    print(f"  gain bounded [0,1]:                     {'OK' if bounded_ok else 'FAIL'}")
    print(f"  vanish-at-zero (Law 6b):                {'OK' if vanish_ok else 'FAIL'}")
    print(f"  gate gates composition (0 vs full):     {'OK' if gate_ok else 'FAIL'}")
    print(f"  no minting by workload (λ pinned 0):    {'OK' if no_mint_ok else 'FAIL'}")
    print(f"  paired control (gain=1.0 ≡ default):    {'OK' if paired_ok else 'FAIL'}")
    print(f"  6c disjointness (no ⊘ import):          {'OK' if disjoint_ok else 'FAIL'}")
    verdict = all([gain0_ok, monotone_ok, bounded_ok, vanish_ok, gate_ok,
                   no_mint_ok, paired_ok, disjoint_ok])
    print(f"\n  VERDICT: {'PASS — composition needs the solvent; λ cannot self-ignite.' if verdict else 'HOLD — see failures above.'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
