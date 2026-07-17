"""
tests/integration/bond_ddm_invariants.py

Hard-invariant gate for the bond-formation accumulator lever
(agents/bond_accumulator.py + the RelationalBondManager ddm_formation path).

This is the pass/fail CI companion to the informational probes
(tests/diagnostic/calibration/bond_ddm_*). It locks down only the contracts
that must never move, on synthetic feedback streams (no substrate, <1 s):

  1. OFF is the default and OFF is classic — a default-constructed manager
     has no accumulator, consumes no RNG, and forms a bond by exactly the
     classic rule (interactions >= 20, quality disjunction, crystal >= 1).
  2. ACCEPT is the only path that commits — with the lever ON, negative and
     pure-noise streams never form a bond, however many interactions and
     crystals accumulate.
  3. Structural preconditions still gate — an ACCEPT crossing without the
     crystal footprint holds at the bound instead of committing; the bond
     forms only once the footprint exists.
  4. The asymmetry is wired — symmetric-magnitude negative evidence reaches
     its (nearer) bound many times faster than positive evidence reaches
     the accept bound.
  5. The diffusion is real — sigma = 0 is rejected at construction, and
     different seeds produce different trajectories (not a deterministic
     ramp).
  6. The field never sees V — structural check: the substrate does not
     import the accumulator, and the accumulator does not import the
     substrate. The only crossing is the discrete commitment inside
     RelationalBondManager.

Usage:
    python -m tests.integration.bond_ddm_invariants
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from agents.bond_accumulator import AccumulatorOutcome, BondFormationAccumulator
from agents.relational_bond_manager import RelationalBondManager
from agents.trust_ledger import GovernanceFeedback

REPO = Path(__file__).resolve().parents[2]

PASS = []
FAIL = []


def check(name: str, ok: bool, detail: str = ""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail else ""))


def feedback(source_id: str, decision: str, alignment: float = 0.98,
             satisfaction: float = 0.0) -> GovernanceFeedback:
    trust_impact = {"allow": 0.10, "allow_weakened": 0.01, "monitor": -0.05,
                    "quarantine": -0.50, "reject": -0.30, "sacred_shield": -1.00}[decision]
    return GovernanceFeedback(
        source_id       = source_id,
        stable_ids      = [],
        decision        = decision,
        coherence_delta = 0.0,
        timestamp       = time.time(),
        outcome_metrics = {
            "coherence_delta":        0.0,
            "trust_impact":           trust_impact,
            "emotional_satisfaction": satisfaction,
            "surprise":               0.0,
            "field_alignment":        alignment,
        },
    )


# ---------------------------------------------------------------------------
# 1. OFF default + classic formation unchanged
# ---------------------------------------------------------------------------

def test_off_is_default_and_classic():
    print("\n[1] OFF is the default; classic formation rule intact")
    bm = RelationalBondManager()
    check("default manager has no accumulator", bm._ddm is None)

    bm.notify_crystal("src")                       # crystal precondition
    formed_at = None
    for i in range(1, 31):
        bm.receive_feedback(feedback("src", "allow"))
        if formed_at is None and bm.get_bond("src") is not None:
            formed_at = i
    check("classic path forms at exactly the interaction threshold",
          formed_at == bm.formation_interaction_threshold,
          f"formed at interaction {formed_at}")


# ---------------------------------------------------------------------------
# 2. ACCEPT is the only committing path
# ---------------------------------------------------------------------------

def test_accept_only_commits():
    print("\n[2] ON: only an ACCEPT crossing commits")
    # Negative stream: rejects, plenty of interactions + crystals
    bm = RelationalBondManager(ddm_formation=True, ddm_config={"seed": 11})
    bm.notify_crystal("hostile")
    for _ in range(200):
        bm.receive_feedback(feedback("hostile", "reject", alignment=0.98))
    check("sustained negative stream never bonds", bm.get_bond("hostile") is None)
    st = bm._ddm.state("hostile")
    check("negative stream is ACTIVELY rejected (a decision, not a timeout)",
          st is not None and st["outcomes"].get("reject_active", 0) > 0
          and st["outcomes"].get("accept", 0) == 0,
          f"outcomes={st['outcomes'] if st else None}")

    # Pure-noise stream: zero alignment, zero evidence
    bm2 = RelationalBondManager(ddm_formation=True, ddm_config={"seed": 12})
    bm2.notify_crystal("noise")
    for _ in range(1200):
        bm2.receive_feedback(feedback("noise", "allow", alignment=0.0))
    st2 = bm2._ddm.state("noise")
    check("pure-noise stream never bonds (times out, no spurious accept)",
          bm2.get_bond("noise") is None
          and st2 is not None and st2["outcomes"].get("accept", 0) == 0
          and st2["outcomes"].get("reject_timeout", 0) > 0,
          f"outcomes={st2['outcomes'] if st2 else None}")

    # Genuine stream: clean allows at live alignment
    bm3 = RelationalBondManager(ddm_formation=True, ddm_config={"seed": 13})
    bm3.notify_crystal("genuine")
    formed_at = None
    for i in range(1, 121):
        bm3.receive_feedback(feedback("genuine", "allow", alignment=0.98))
        if formed_at is None and bm3.get_bond("genuine") is not None:
            formed_at = i
    check("genuine sustained stream bonds", formed_at is not None,
          f"formed at interaction {formed_at}")
    check("no bond before the accumulator's minimum decision time "
          "(>= interaction threshold — temporal depth preserved)",
          formed_at is not None and formed_at >= bm3.formation_interaction_threshold,
          f"formed at {formed_at}, threshold {bm3.formation_interaction_threshold}")


# ---------------------------------------------------------------------------
# 3. Structural preconditions still gate at commit time
# ---------------------------------------------------------------------------

def test_preconditions_hold_at_bound():
    print("\n[3] ON: crystal footprint still gates; crossing holds at bound")
    bm = RelationalBondManager(ddm_formation=True, ddm_config={"seed": 21})
    for _ in range(120):                      # plenty to cross B_accept
        bm.receive_feedback(feedback("early", "allow", alignment=0.98))
    st = bm._ddm.state("early")
    check("no bond without the crystal footprint", bm.get_bond("early") is None)
    check("V held at the accept bound while the footprint lags",
          st is not None and abs(st["V"] - bm._ddm.b_accept) < 1e-9,
          f"V={st['V'] if st else None}")
    bm.notify_crystal("early")
    bm.receive_feedback(feedback("early", "allow", alignment=0.98))
    check("bond commits on the next crossing once the footprint exists",
          bm.get_bond("early") is not None)


# ---------------------------------------------------------------------------
# 4. Asymmetry is wired
# ---------------------------------------------------------------------------

def test_asymmetry_wired():
    print("\n[4] Asymmetry: denial is many times faster than earning")
    acc = BondFormationAccumulator(seed=31)
    accept_steps = reject_steps = None
    for i in range(1, 1001):
        if acc.observe("earn", "allow", 1.0) is AccumulatorOutcome.ACCEPT:
            accept_steps = i
            break
    for i in range(1, 1001):
        if acc.observe("deny", "quarantine", 1.0) is AccumulatorOutcome.REJECT_ACTIVE:
            reject_steps = i
            break
    ok = (accept_steps is not None and reject_steps is not None
          and reject_steps * 10 <= accept_steps)
    check("reject bound reached >= 10x faster than accept bound", ok,
          f"accept={accept_steps} steps, reject={reject_steps} steps")

    # Control: asymmetry unwired (ratio 1) collapses the timing gap to the
    # bound geometry alone — proves the measured gap above is the drift lever.
    ctl = BondFormationAccumulator(seed=31, trust_asymmetry=1.0)
    c_accept = c_reject = None
    for i in range(1, 4001):
        if ctl.observe("earn", "allow", 1.0) is AccumulatorOutcome.ACCEPT:
            c_accept = i
            break
    for i in range(1, 4001):
        if (ctl.observe("deny", "reject", 1.0)
                in (AccumulatorOutcome.REJECT_ACTIVE, AccumulatorOutcome.REJECT_TIMEOUT)):
            c_reject = i
            break
    check("asymmetry=1 control collapses the gap (drift lever is causal)",
          c_accept is not None and c_reject is not None
          and c_reject * 10 > c_accept,
          f"control accept={c_accept}, reject={c_reject}")


# ---------------------------------------------------------------------------
# 5. The diffusion is real
# ---------------------------------------------------------------------------

def test_noise_real():
    print("\n[5] Diffusion is real (no ramp in accumulator costume)")
    try:
        BondFormationAccumulator(sigma=0.0)
        check("sigma=0 rejected at construction", False)
    except ValueError:
        check("sigma=0 rejected at construction", True)

    a, b = BondFormationAccumulator(seed=1), BondFormationAccumulator(seed=2)
    for _ in range(15):
        a.observe("s", "allow", 0.5)
        b.observe("s", "allow", 0.5)
    check("different seeds produce different trajectories",
          a.trace("s") != b.trace("s"))

    a2, b2 = BondFormationAccumulator(seed=7), BondFormationAccumulator(seed=7)
    for _ in range(15):
        a2.observe("s", "allow", 0.5)
        b2.observe("s", "allow", 0.5)
    check("same seed reproduces exactly (determinism discipline)",
          a2.trace("s") == b2.trace("s"))


# ---------------------------------------------------------------------------
# 6. The field never sees V (structural)
# ---------------------------------------------------------------------------

def test_severity_economy_synced():
    print("\n[7] Severity economy: negative evidence mirrors the trust penalties")
    # bond_accumulator cannot import _TRUST_IMPACT (circular via
    # relational_bond_manager), so this gate is what enforces the shared
    # economy the accumulator's comment promises.
    from agents.bond_accumulator import _NEGATIVE_EVIDENCE
    from agents.selfhood_governance import GovernanceDecision, _TRUST_IMPACT
    mismatches = {
        dec: (_NEGATIVE_EVIDENCE[dec], _TRUST_IMPACT[GovernanceDecision(dec)])
        for dec in _NEGATIVE_EVIDENCE
        if abs(_NEGATIVE_EVIDENCE[dec] - _TRUST_IMPACT[GovernanceDecision(dec)]) > 1e-9
    }
    check("blocking-decision evidence equals the trust-penalty magnitudes",
          not mismatches, f"mismatches={mismatches}" if mismatches else
          "reject/quarantine/sacred_shield aligned")


def test_field_isolation():
    print("\n[6] Field isolation: the substrate and the accumulator never import "
          "each other")
    import ast

    def imports_of(path: Path) -> set:
        tree = ast.parse(path.read_text())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
        return mods

    field_imports = imports_of(REPO / "substrate" / "resonance_field.py")
    acc_imports   = imports_of(REPO / "agents" / "bond_accumulator.py")
    check("resonance_field.py does not import the accumulator",
          not any("bond_accumulator" in m for m in field_imports),
          f"imports={sorted(field_imports)}")
    check("bond_accumulator.py does not import the substrate",
          not any(m.startswith("substrate") for m in acc_imports),
          f"imports={sorted(acc_imports)}")


# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("  BOND DDM — HARD INVARIANTS GATE")
    print("=" * 70)
    test_off_is_default_and_classic()
    test_accept_only_commits()
    test_preconditions_hold_at_bound()
    test_asymmetry_wired()
    test_noise_real()
    test_severity_economy_synced()
    test_field_isolation()
    print("\n" + "=" * 70)
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print(f"    ✗ {f}")
    print("=" * 70)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
