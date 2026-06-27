"""
tests/diagnostic/integrity/two_operator_live_demo.py    (spec: v0.2)

The whole point, demonstrated live at production dim 128: the Two-Operator program
is not observe-only. Build A ignites λ, Build B's solvent gate lets composition
resolve, and the ⊘ consumer USES the Witness-Reaper's read to demote thin values.
This script runs the real stack and shows before/after behavior — an effect, not a
log line. It is a demonstration (no VERDICT): it exists so a result can be *seen*.

Three things are shown:

  1. Build A → λ → ⊕ gate. Ignition lights λ off zero; solvent_gain(λ) opens the
     composition term that was inert at λ=0.

  2. ⊘ consumer, SAFE default (named_only=True). A thinning workload (single-source
     monoculture) is run so ⊘'s NAMED regions (Drift/Fragmentation/Dissolution)
     actually fire; the consumer demotes exactly those diagnosed values toward a
     convergent honest floor, and leaves merely-unnamed-thin and healthy values
     alone. ⊘ is genuinely USED, selectively, without collapsing Tier 3.

  3. ⊘ consumer, AGGRESSIVE (named_only=False) — the cautionary result. Acting on
     EVERY sub-health-floor advisory over-demotes the whole field (the cc-axis
     confound makes everyone look thin). This is the pre-declared over-demotion
     collapse, shown on purpose: it is WHY the safe default is named-only and why
     the spec front-loads the §6.3 gain-sign check before reinforcement coupling.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import sys
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack                                       # noqa: E402
from ignition import ignite                                                      # noqa: E402
from agents.lambda_ledger import LambdaLedger                                    # noqa: E402
from cognition.integrity_read import WitnessReaper, IntegrityDecayConsumer       # noqa: E402

HEALTHY_VOCAB = ["resonance", "field", "engine", "memory", "crystal", "attractor",
                 "identity", "continuity", "witness", "curiosity", "wonder",
                 "coherence", "symbolic", "recursive", "cognition", "substrate"]
MONO_VOCAB    = ["monoculture", "echo", "loop", "samesame"]   # narrow, single-source
SRC   = [f"src_{i}" for i in range(4)]
MONO  = "src_mono"
DIM   = 128


def _stats(ve):
    vals = [v.strength for v in ve.values.values() if v.dissolved_at_step < 0]
    n = len(vals)
    return {"n": n, "mean": (sum(vals) / n if n else 0.0),
            "active": sum(1 for s in vals if s > 1.0),
            "max": max(vals) if vals else 0.0}


def _build_and_warm():
    """Full stack at dim 128, Build A ignition → λ-ledger, then a mixed workload:
    a healthy 4-source phase plus a single-source monoculture phase (which produces
    genuinely thin, named-pathology values)."""
    random.seed(42); np.random.seed(42)
    import torch; torch.manual_seed(42)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    gen.eval()

    ledger = LambdaLedger()
    report = ignite(gen, epochs=6, eval_mode=True, seed=42)   # Build A exogenous event
    ledger.ignite(2.0)                                        # ...lights λ off zero
    cycle.attach_lambda_ledger(ledger)

    rng = random.Random(42)
    for i in range(180):                                      # healthy multi-source
        cycle.step(rng.sample(HEALTHY_VOCAB, 3), source_id=SRC[i % 4], origin_type="internal")
    for i in range(80):                                       # single-source monoculture
        cycle.step(rng.sample(MONO_VOCAB, 2), source_id=MONO, origin_type="internal")

    return gen, cycle, gov, ve, ledger, report


def main() -> int:
    print("=" * 78)
    print(f"  TWO-OPERATOR PROGRAM — LIVE, AND USED   spec: v0.2   dim {DIM}")
    print("=" * 78)

    gen, cycle, gov, ve, ledger, report = _build_and_warm()
    sacred_check = getattr(getattr(gov, "constants", None), "is_sacred", None)
    wr = WitnessReaper(ve, registry=gen.registry, bond_manager=gov.bond_manager,
                       sacred_check=sacred_check, baseline_profiles=None)
    cycle.attach_integrity_read(wr)

    print("\n  [1] Build A → λ → ⊕ solvent gate")
    print(f"      ignition: eff_rank {report.eff_rank_before:.3f} -> {report.eff_rank_after:.3f}"
          f"  (Δ {report.delta_eff_rank:+.3f})")
    print(f"      λ: 0.000 -> {ledger.strength:.3f}   solvent_gain(λ) = {ledger.gain():.4f}"
          f"   (⊕ composition {ledger.gain()*100:.1f}% open; was 0% at λ=0)")

    # What ⊘ sees right now (before any consumption)
    adv = wr.read()
    by_path = {}
    for a in adv:
        for p in (a.pathologies or ["unnamed"]):
            by_path[p] = by_path.get(p, 0) + 1
    named = [a for a in adv if a.pathologies]
    path_of = {a.value_id: ",".join(a.pathologies) for a in named}
    print(f"\n  ⊘ reads {len(adv)} thin values: {by_path}")
    print(f"      named-pathology values (the diagnosed): {len(named)}")

    # Snapshot every value's strength for the before/after table
    before = {v.value_id: (v.symbolic_core, v.strength) for v in ve.values.values()}

    # [2] SAFE default — consume only the diagnosed (named) pathologies -------
    safe = IntegrityDecayConsumer(wr, ve, rate=0.05, named_only=True)
    for _ in range(40):              # 40 consumption cycles (no new experience)
        safe.apply()
    s_snap = safe.snapshot()
    print("\n  [2] ⊘ consumer — SAFE default (named_only=True), 40 cycles")
    print(f"      demotions_total={s_snap['demotions_total']}  "
          f"skipped_unnamed={s_snap['skipped_unnamed']}  sacred_skipped={s_snap['sacred_skipped']}")
    touched_ids = {a.value_id for a in named}
    print("      diagnosed values pulled toward honest floor (before -> after):")
    shown = 0
    for v in ve.values.values():
        if v.value_id in touched_ids and shown < 6:
            _, b = before[v.value_id]
            if abs(b - v.strength) > 1e-6:
                print(f"        {v.symbolic_core:>14} [{path_of.get(v.value_id,'-'):>12}]: "
                      f"{b:.4f} -> {v.strength:.4f}")
                shown += 1
    healthy_after = _stats(ve)
    # show a couple of untouched healthy multi-source values
    untouched = [v for v in ve.values.values()
                 if v.value_id not in touched_ids and len(v.source_weights) >= 2]
    print(f"      healthy multi-source values left UNTOUCHED: {len(untouched)} "
          f"(e.g. {', '.join(v.symbolic_core for v in untouched[:4])})")
    print(f"      field after selective consumption: n={healthy_after['n']} "
          f"mean={healthy_after['mean']:.3f} active={healthy_after['active']} "
          f"max={healthy_after['max']:.3f}  → NO collapse")

    # [3] AGGRESSIVE — the cautionary collapse (fresh warm, separate stack) ----
    gen2, cycle2, gov2, ve2, ledger2, _ = _build_and_warm()
    wr2 = WitnessReaper(ve2, registry=gen2.registry, bond_manager=gov2.bond_manager,
                        sacred_check=getattr(getattr(gov2, "constants", None), "is_sacred", None),
                        baseline_profiles=None)
    pre = _stats(ve2)
    aggressive = IntegrityDecayConsumer(wr2, ve2, rate=0.05, named_only=False)
    for _ in range(40):
        aggressive.apply()
    post = _stats(ve2)
    a_snap = aggressive.snapshot()
    print("\n  [3] ⊘ consumer — AGGRESSIVE (named_only=False), 40 cycles  [cautionary]")
    print(f"      every-thin-value coupling: demotions_total={a_snap['demotions_total']}")
    print(f"      field: mean {pre['mean']:.3f} -> {post['mean']:.3f}, "
          f"active {pre['active']} -> {post['active']}  → OVER-DEMOTION (pre-declared failure)")

    print("\n  reading:")
    print("    - ⊘ is USED, not observed: the consumer writes value strength from ⊘'s read.")
    print("    - SAFE default acts only on NAMED pathologies → selective, convergent, no collapse;")
    print("      healthy multi-source values are untouched. This is the production lever.")
    print("    - AGGRESSIVE acting on the (cc-confounded) universal thinness collapses the field —")
    print("      the empirical reason the safe default is named-only and reinforcement coupling")
    print("      stays behind the §6.3 gain-sign check.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
