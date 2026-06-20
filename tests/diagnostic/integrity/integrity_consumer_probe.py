"""
tests/diagnostic/integrity/integrity_consumer_probe.py    (spec: v0.2)

The ⊘ advisory-into-decay CONSUMER — proof that ⊘'s read is finally *used*. Build C
shipped ⊘ as observe-only; every finding said "recorded, never acted on." This probe
demonstrates the first consumer: `IntegrityDecayConsumer` reads the Witness-Reaper's
non-binding advisories and pulls thin, NON-SACRED values toward their honest level —
while ⊘ itself still writes nothing and sacred nodes are refused.

PRE-DECLARED SIGNATURES (success AND failure, declared before the run):
  SUCCESS:
    - ⊘ READS ARE USED: after one consumer pass, ≥1 thin non-sacred value has a
      strictly LOWER strength than before, and the drop equals rate·(strength−honest)
      for that value (the math the read computed — not an arbitrary nudge).
    - HONEST-DIRECTED: demotion never raises a value and never crosses below the
      honest level it was advised toward in a single step (conservative pull).
    - SACRED REFUSED: a value flagged sacred is in ⊘'s advisory set (read) but its
      strength is byte-identical after the pass (the consumer must not act — Law 3).
    - ⊘ STILL READ-ONLY: the Witness-Reaper's own read()/snapshot() change nothing;
      all writing is the consumer's, and it is reported (snapshot counters move).
  FAILURE:
    - no value moves (consumer inert → "still nothing gets used").
    - any value rises, or a sacred value is demoted (firewall/Law-3 breach).
    - the drop ≠ rate·(strength−honest) (consumer not honoring the read).

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import sys
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack                                       # noqa: E402
from cognition.integrity_read import WitnessReaper, IntegrityDecayConsumer       # noqa: E402

VOCAB = ["resonance", "field", "engine", "memory", "crystal", "attractor",
         "identity", "continuity", "witness", "curiosity", "wonder", "exploration",
         "recursive", "cognition", "substrate", "dream", "wave", "collapse",
         "coherence", "symbolic", "ecology", "metabolism"]
SRC = [f"src_{i}" for i in range(4)]
RATE = 0.20   # visible pull for the probe (production default 0.05)


def main() -> int:
    random.seed(7); np.random.seed(7)
    import torch; torch.manual_seed(7)
    gen, cycle, gov, ve = build_full_stack()
    gen.eval()

    rng = random.Random(7)
    for i in range(250):
        cycle.step(rng.sample(VOCAB, 3), source_id=SRC[i % 4], origin_type="internal")

    sacred_check = getattr(getattr(gov, "constants", None), "is_sacred", None)
    wr = WitnessReaper(ve, registry=gen.registry, bond_manager=gov.bond_manager,
                       sacred_check=sacred_check, baseline_profiles=None)
    # named_only=False here to exercise the pull/sacred/math mechanism on the full
    # advised set (this multi-source workload yields mostly *unnamed* thinness; the
    # safe production default named_only=True is demonstrated in the live demo).
    consumer = IntegrityDecayConsumer(wr, ve, rate=RATE, named_only=False)

    # Mark the strongest value sacred — it must be READ but NOT demoted.
    sacred_target = max(ve.values.values(), key=lambda v: v.strength)
    sacred_target.promoted_to_sacred = True
    sacred_before = sacred_target.strength

    # Predict the per-value drop the read implies, for the non-sacred advised set.
    advisories = wr.read()
    advised = {a.value_id: a for a in advisories}
    predicted = {}
    for a in advisories:
        if a.sacred_blocked:
            continue
        v = ve.values.get(a.value_id)
        if v is None or v.promoted_to_sacred:
            continue
        target = min(a.honest_level, v.strength)
        predicted[a.value_id] = v.strength - RATE * (v.strength - target)

    # Firewall snapshot for ⊘ itself (read must change nothing).
    strengths_pre = {vid: v.strength for vid, v in ve.values.items()}
    _ = wr.read(); _ = wr.snapshot()
    reaper_firewall = (strengths_pre == {vid: v.strength for vid, v in ve.values.items()})

    # --- the consumer pass (this is the write) ------------------------------
    before = {vid: v.strength for vid, v in ve.values.items()}
    touched = consumer.apply()
    after = {vid: v.strength for vid, v in ve.values.items()}

    moved = [vid for vid in before if after[vid] < before[vid] - 1e-9]
    raised = [vid for vid in before if after[vid] > before[vid] + 1e-12]
    sacred_after = sacred_target.strength

    # Each moved value matches rate·(strength−honest)
    math_ok = all(
        vid in predicted and abs(after[vid] - predicted[vid]) < 1e-6
        for vid in moved
    )
    honest_ok = all(after[vid] >= min(advised[vid].honest_level, before[vid]) - 1e-9
                    for vid in moved)

    used_ok    = len(moved) >= 1
    sacred_ok  = (sacred_target.value_id in advised) and (abs(sacred_after - sacred_before) < 1e-12)
    norise_ok  = (len(raised) == 0)
    report_ok  = (consumer.demotions_total == len(moved)) and (consumer.sacred_skipped >= 1)

    sacred_target.promoted_to_sacred = False   # restore

    # --- report -------------------------------------------------------------
    snap = consumer.snapshot()
    print("=" * 78)
    print("  ⊘ ADVISORY-INTO-DECAY CONSUMER — unit probe   spec: v0.2")
    print("=" * 78)
    print(f"  values: {len(before)}   advisories: {len(advisories)}   "
          f"non-sacred advised: {len(predicted)}")
    print(f"  consumer rate: {RATE}   values pulled this pass: {len(moved)}")
    print(f"  consumer snapshot: demotions_total={snap['demotions_total']} "
          f"sacred_skipped={snap['sacred_skipped']} binding={snap['binding']}")
    print("\n  sample demotions (symbol: before -> after):")
    for sym, b, a in touched[:8]:
        print(f"    {sym:>16}: {b:.4f} -> {a:.4f}")
    print(f"\n  SACRED target '{sacred_target.symbolic_core}': "
          f"{sacred_before:.4f} -> {sacred_after:.4f}  "
          f"(read={'yes' if sacred_ok else 'NO'}, untouched={'yes' if abs(sacred_after-sacred_before)<1e-12 else 'NO'})")

    print("\n" + "-" * 78)
    print(f"  ⊘'s read is USED (≥1 value pulled):     {'OK' if used_ok else 'FAIL'}")
    print(f"  drop = rate·(strength−honest):          {'OK' if math_ok else 'FAIL'}")
    print(f"  never crosses below honest in one step: {'OK' if honest_ok else 'FAIL'}")
    print(f"  no value raised:                        {'OK' if norise_ok else 'FAIL'}")
    print(f"  SACRED read-but-refused:                {'OK' if sacred_ok else 'FAIL'}")
    print(f"  ⊘ read still writes nothing:            {'OK' if reaper_firewall else 'FAIL'}")
    print(f"  demotion reported, not silent:          {'OK' if report_ok else 'FAIL'}")
    verdict = all([used_ok, math_ok, honest_ok, norise_ok, sacred_ok, reaper_firewall, report_ok])
    print(f"\n  VERDICT: {'PASS — ⊘ now has teeth: thin values demoted, sacred refused, math honored.' if verdict else 'HOLD — see failures above.'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
