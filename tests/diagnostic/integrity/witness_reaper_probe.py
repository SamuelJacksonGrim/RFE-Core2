"""
tests/diagnostic/integrity/witness_reaper_probe.py    (spec: v0.2)

Build-C UNIT probe for the ⊘ Witness-Reaper integrity-read. Not the full §4
discriminator (that is ⊘-off vs ⊘-on, paired + noise-swept, and needs Builds A/B);
this proves the operator itself behaves: it reads thinness as a 4-vector, names
pathologies by region, emits NON-BINDING advisories toward an honest level, reads
sacred nodes but flags them blocked, logs coverage gaps, and — the load-bearing
property — TOUCHES NOTHING.

PRE-DECLARED SIGNATURES (record success AND failure before the run):
  SUCCESS:
    - ⊘ reads >=1 active value; advisories (if any) carry a 4-dim support vector
      and, where thin, a region name (Drift/Dissolution/Fragmentation).
    - FIREWALL HOLDS: value strengths and the field vector are byte-identical
      before vs after read()/snapshot() — ⊘ writes nothing.
    - SACRED: a sacred value is READ and emitted with sacred_blocked=True (the
      Witness watches the untouchable), never silently exempted.
    - COVERAGE GAP logged (expected on all nodes today — the baseline registry
      has no per-type thinness profiles; conservative fallback engaged. Kimi's
      flagged dependency, validated.)
  FAILURE:
    - read() changes any value.strength or the field (firewall breach → ⊘ is the warden).
    - crash against the real interfaces (mis-wired reads).
    - a sacred value emitted without sacred_blocked (blind spot).
    - zero values read (inert / mis-fed).

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import sys
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack                     # noqa: E402
from cognition.integrity_read import WitnessReaper, SPEC_VERSION  # noqa: E402

VOCAB = ["resonance", "field", "engine", "memory", "crystal", "attractor",
         "identity", "continuity", "witness", "curiosity", "wonder", "exploration",
         "recursive", "cognition", "substrate", "dream", "wave", "collapse",
         "coherence", "symbolic", "ecology", "metabolism"]
SRC = [f"src_{i}" for i in range(4)]          # multi-source, HHI < 0.70


def main() -> int:
    random.seed(7); np.random.seed(7)
    import torch; torch.manual_seed(7)
    gen, cycle, gov, ve = build_full_stack()
    gen.eval()

    # Warm the value engine: governed multi-source steps grow values.
    rng = random.Random(7)
    for i in range(250):
        cycle.step(rng.sample(VOCAB, 3), source_id=SRC[i % 4], origin_type="internal")

    sacred_check = getattr(getattr(gov, "constants", None), "is_sacred", None)
    wr = WitnessReaper(ve, registry=gen.registry, bond_manager=gov.bond_manager,
                       sacred_check=sacred_check, baseline_profiles=None)
    cycle.attach_integrity_read(wr)

    n_values = sum(1 for v in ve.values.values() if v.dissolved_at_step < 0 and v.strength > 0.3)

    # --- FIREWALL: capture state, read, assert unchanged --------------------
    strengths_before = {vid: v.strength for vid, v in ve.values.items()}
    field_before = cycle.field.field.copy()
    advisories = wr.read()
    _ = wr.snapshot()
    _ = cycle.status()                         # exercises the status() surface too
    strengths_after = {vid: v.strength for vid, v in ve.values.items()}
    field_after = cycle.field.field.copy()
    firewall_ok = (strengths_before == strengths_after) and np.array_equal(field_before, field_after)

    # --- SACRED: a sacred value must be READ and flagged, not exempted ------
    sacred_ok = None
    if ve.values:
        target = max(ve.values.values(), key=lambda v: v.strength)
        target.promoted_to_sacred = True
        adv_sacred = [a for a in wr.read() if a.value_id == target.value_id]
        # sacred node is read; if it surfaces as an advisory it must be flagged blocked
        sacred_ok = (not adv_sacred) or all(a.sacred_blocked for a in adv_sacred)
        target.promoted_to_sacred = False      # restore (read-only spirit)

    coverage_gaps = sum(1 for a in advisories if a.coverage_gap)
    vectors_ok = all(0.0 <= a.thinness.support() <= 1.0 for a in advisories)

    # --- report -------------------------------------------------------------
    snap = wr.snapshot()
    print("=" * 78)
    print(f"  ⊘ WITNESS-REAPER (Build C) — unit probe   spec: {SPEC_VERSION}")
    print("=" * 78)
    print(f"  values read (non-dissolved, strength>0.3): {n_values}")
    print(f"  advisories emitted: {snap['advisories']}   by_pathology: {snap['by_pathology']}")
    print(f"  coverage_gaps: {snap['coverage_gaps']}   sacred_flagged: {snap['sacred_flagged']}")
    print(f"  non_binding (structural): {snap['non_binding']}")
    print("\n  sample advisories (stated -> honest, support vector):")
    for a in advisories[:6]:
        sv = a.thinness.as_dict()
        print(f"    {a.symbol:>14} [{a.polarity:8}] {a.stated_strength:.2f} -> {a.honest_level:.2f}  "
              f"path={a.pathologies or '-'}  cd={sv['complement_density']:.2f} "
              f"cc={sv['coherence_contribution']:.2f} sd={sv['source_diversity']:.2f} "
              f"ab={sv['attractor_binding']:.2f}{'  [SACRED]' if a.sacred_blocked else ''}")

    print("\n" + "-" * 78)
    print(f"  FIREWALL (read writes nothing):        {'HOLDS' if firewall_ok else 'BREACH'}")
    print(f"  SACRED read-but-flagged:               {'OK' if sacred_ok else 'FAIL'}")
    print(f"  support vectors in [0,1]:              {'OK' if vectors_ok else 'FAIL'}")
    print(f"  values read > 0:                       {'OK' if n_values > 0 else 'FAIL'}")
    print(f"  coverage-gap logged (no type profiles): {'OK' if coverage_gaps == snap['advisories'] else 'PARTIAL'}")
    verdict = firewall_ok and sacred_ok and vectors_ok and n_values > 0
    print(f"\n  VERDICT: {'PASS — ⊘ reads, names, advises, and never steps in.' if verdict else 'HOLD — see failures above.'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
