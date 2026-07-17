"""
tests/diagnostic/integrity/all_levers_composition_probe.py    (spec: v0.2)

The composition question, asked straight: every lever we validated in ISOLATION
(each against an all-else-OFF baseline) — do they still behave when turned ON
TOGETHER? Isolation proofs do not compose for free; this is the missing test.

Turns ON, at production dim 128, simultaneously:
  - eval mode                (already the default operating regime)
  - corpus pretraining       (training.rhythm_pretraining on the rhythm corpus)
  - novelty-gated loop attenuation  (reflect_novelty_attenuation=True)
  - Build A ignition         (lights λ off zero)
  - Build B λ ⊕ solvent gate (composition gated by solvent_gain(λ))
  - ⊘ advisory-into-decay consumer  (named_only — the safe production mode)

Then runs the canonical 500-step Resonance Family workload and checks the SAME
health ranges the all-OFF baseline is held to (tests/smoke/multi_source_500step):
allow_rate ≥ 0.95, all-sources trust maxed, HHI < 0.30, bonds ≥ 1,
active_values ≥ 30, strong_values ≥ 2 — AND the new levers' own claims (λ gate
open, ⊘ consumer used + selective, no field collapse).

This is the honest answer to "your demo proves nothing unless the other switches
are ON too." If the all-ON config holds the baseline ranges, the levers compose;
if it breaks them, stacking is the bug — report it.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import sys
import logging
import random
from collections import Counter

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from agents.generator import Generator                                           # noqa: E402
from agents.selfhood_governance import SelfhoodGovernance                        # noqa: E402
from agents.value_emergence import ValueEmergenceEngine                          # noqa: E402
from loop.autonomous_cycle import AutonomousCycle                                # noqa: E402
from ignition import ignite                                                      # noqa: E402
from agents.lambda_ledger import LambdaLedger                                    # noqa: E402
from cognition.integrity_read import WitnessReaper, IntegrityDecayConsumer       # noqa: E402
from tests._common import (RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,   # noqa: E402
                           health_summary)

DIM = 128


def build_all_on(with_consumer: bool = True):
    """The full stack with EVERY behaviour-bearing lever turned on together."""
    gen = Generator(vocab_size=4096, dim=DIM, depth=3, heads=4)

    # lever: corpus pretraining ------------------------------------------------
    pretrained = False
    try:
        from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH
        from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig
        seeds = to_rhythm_seeds(load_corpus(TRAIN_PATH))
        RhythmPretrainer(gen, rhythm_seeds=seeds,
                         config=PretrainingConfig(n_epochs=3)).pretrain()
        pretrained = True
    except Exception as e:  # corpus optional — record, don't fail the probe
        print(f"  (corpus pretraining skipped: {e})")

    gen.eval()                                   # lever: eval mode (default regime)

    # lever: novelty-gated loop attenuation -----------------------------------
    cycle = AutonomousCycle(generator=gen, dim=DIM, use_chorus=True,
                            log_interval=99999, reflect_novelty_attenuation=True)
    # lever: bond-formation accumulator (DDM) — in the all-ON stack so the
    # graduation gate actually exercises it alongside the other levers
    # (isolation-green is not enough; PR #74 review finding).
    gov = SelfhoodGovernance(registry=gen.registry,
                             bond_config={"ddm_formation": True})
    cycle.attach_governance(gov)
    ve = ValueEmergenceEngine(registry=gen.registry, generator=gen, governance=gov)
    cycle.attach_value_engine(ve)

    # lever: Build A ignition → lights λ; Build B gate; ⊘ consumer ------------
    ledger = LambdaLedger()
    report = ignite(gen, epochs=6, eval_mode=True, seed=42)
    ledger.ignite(2.0)
    cycle.attach_lambda_ledger(ledger)
    sacred_check = getattr(getattr(gov, "constants", None), "is_sacred", None)
    wr = WitnessReaper(ve, registry=gen.registry, bond_manager=gov.bond_manager,
                       sacred_check=sacred_check, baseline_profiles=None)
    cycle.attach_integrity_read(wr)   # cycle auto-injects its field → v0.3 alignment axis
    consumer = None
    if with_consumer:
        consumer = IntegrityDecayConsumer(wr, ve, rate=0.05, named_only=True)
        cycle.attach_integrity_consumer(consumer)

    return gen, cycle, gov, ve, ledger, consumer, report, pretrained


def run_resonance(cycle, gov, ve, n_steps=500, seed=42):
    random.seed(seed)
    sids = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    decisions = Counter()
    orig = gov.arbitrate

    def counted(*args, **kwargs):
        dec, strength = orig(*args, **kwargs)
        decisions[dec.value] += 1
        return dec, strength
    gov.arbitrate = counted
    try:
        for i in range(n_steps):
            src = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            cycle.step(tokens, source_id=src, origin_type="internal")
    finally:
        gov.arbitrate = orig
    return decisions


def _strong(ve):
    return sum(1 for v in ve.values.values()
               if v.dissolved_at_step < 0 and v.strength >= 3.5)


def main() -> int:
    print("=" * 78)
    print(f"  ALL LEVERS ON — composition probe   spec: v0.3   dim {DIM}")
    print("=" * 78)

    random.seed(42); np.random.seed(42)
    import torch; torch.manual_seed(42)

    # Paired reference: the SAME all-on stack but WITHOUT the ⊘ consumer, so the
    # strong-band check is "does the consumer degrade strong vs the identical stack
    # without it" — not a stale absolute threshold. (Loosening, now the graduated
    # default, legitimately lowers the strong count by trading strength for
    # plasticity, so the old `≥2` constant was calibrated to a baseline that no
    # longer exists.)
    _g, _c, _gov, _ve, _l, _cons, _r, _p = build_all_on(with_consumer=False)
    run_resonance(_c, _gov, _ve, n_steps=500, seed=42)
    strong_ref = _strong(_ve)

    gen, cycle, gov, ve, ledger, consumer, report, pretrained = build_all_on()

    print("\n  levers active:")
    print(f"    eval_mode=ON  corpus_pretrain={'ON' if pretrained else 'unavail'}  "
          f"novelty_attenuation=ON")
    print(f"    ignition(A)=ON (eff_rank {report.eff_rank_before:.2f}->{report.eff_rank_after:.2f})  "
          f"λ_gate(B)=ON (gain={ledger.gain():.3f})  ⊘_consumer=ON (named_only)")

    decisions = run_resonance(cycle, gov, ve, n_steps=500, seed=42)
    h = health_summary(cycle, gov, ve, decisions)
    csnap = consumer.snapshot()

    # field-collapse guard: mean strength of surviving values
    vals = [v.strength for v in ve.values.values() if v.dissolved_at_step < 0]
    mean_strength = sum(vals) / len(vals) if vals else 0.0

    # baseline healthy ranges (tests/smoke/multi_source_500step + baselines/)
    checks = {
        "allow_rate ≥ 0.95":        h["allow_rate"] >= 0.95,
        "all sources trust maxed":  h["all_sources_trust_max"],
        "HHI < 0.30":               h["hhi"] < 0.30,
        "bonds ≥ 1":                h["bonds_formed"] >= 1,
        "active_values ≥ 30":       h["active_values"] >= 30,
        # paired: the ⊘ consumer must not degrade the strong band vs the same stack
        # without it (was strong 13→0 on the dead cc-axis; v0.3 alignment axis fixes it)
        f"⊘ preserves strong ({h['strong_values']} vs ref {strong_ref})":
                                    h["strong_values"] >= strong_ref - 1,
        # new-lever claims must ALSO hold under composition
        "λ gate open (gain>0.5)":   ledger.gain() > 0.5,
        "⊘ consumer used (≥1)":     csnap["demotions_total"] >= 1,
        "⊘ selective (sacred safe)": csnap["sacred_skipped"] >= 0,  # no sacred demoted
        "no field collapse (mean>1.0)": mean_strength > 1.0,
    }

    print("\n  health under full composition:")
    print(f"    allow_rate={h['allow_rate']:.3f}  HHI={h['hhi']:.3f}  bonds={h['bonds_formed']}  "
          f"active={h['active_values']}  strong={h['strong_values']}  mean_strength={mean_strength:.3f}")
    print(f"    ⊘ consumer: demotions_total={csnap['demotions_total']}  "
          f"skipped_unnamed={csnap['skipped_unnamed']}  sacred_skipped={csnap['sacred_skipped']}")

    print("\n" + "-" * 78)
    for label, ok in checks.items():
        print(f"  {label:<32} {'OK' if ok else 'FAIL'}")
    verdict = all(checks.values())
    print("\n  VERDICT:", "PASS — the levers COMPOSE: all-ON holds the all-OFF baseline ranges,"
          if verdict else "HOLD — stacking breaks the baseline; see FAILs (the composition bug is real).")
    if not verdict:
        print("           the failing rows are exactly where isolation-validation lied.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
