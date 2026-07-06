# Loop attenuation, novelty-gated — does conditional loosening free the field without identity cost, and where is the cliff?

- **Date:** 2026-06-15
- **Substrate:** live full stack (`build_full_stack`, dim 64), generator mocked
  with clean orthogonal A/B targets — same harness as
  `2026-06-07-reconstruction-ablation.md` and `2026-06-07-reflective-loop-cost.md`.
- **Probe:** `tests/diagnostic/lockin/loop_attenuation_probe.py` (warmup 150 +
  phase 500, 4 sources HHI≈0.25, seeds 11/23/42). Implementation under test:
  `ReflectiveLoop.novelty_attenuation` (shipped flag, OFF by default).
- **Status:** active — ships the relocated Fix 2 as an OFF-by-default flag; the
  cost-clean band is a knife edge, so NOT ready to be default-ON.
- **Depends on:** 2026-06-07-reconstruction-ablation.md (the loop is the lock),
  2026-06-07-reflective-loop-cost.md (manip-rate, not the witness scalar, is the
  cost instrument; bounded-conditional loosening is the recommended shape).

## Question
The reflective loop is the lock; the cost probe says *bounded, conditional*
attenuation gated on surviving novelty should recover plasticity cheaply, and
that the real cost lives in the Tier-2 manipulation-signal rate (not the witness
`identity_stability` scalar). Implement that as a real flag and ask: (1) does the
proposed cheaper alternative — coupling boredom into the emotion knobs — work at
all? (2) does the novelty-gated loop loosening free the field under novelty while
staying gate-safe under repetition AND manip-clean? (3) where is the cost cliff?

## Pre-declared signatures
- SUCCESS: `emotion_knobs` INERT (disp ≈ baseline) — confirming the knobs are not
  the lever; `loop_attenuate` under novelty frees the field (migration > 0.10)
  with manip ≤ 5% and attractors bounded; under non-novel input it stays rigid
  (disp ≈ drift).
- FAILURE: `loop_attenuate` inert (not a lever), OR frees the field but floods the
  manipulation layer (cost not paid), OR drifts even without novelty (gate broken).
- CONFOUNDED: migration/attractor-count/witness-scalar all look clean while
  manip-rate is high — the SUSPICIOUSLY-CLEAN alarm from the cost finding. Trust
  manip-rate.

## Result (observed)
Migration = disp(novelty phase) − drift(continue-A control). Manip% = share of
phase-500 steps that fired ≥1 Tier-2 manipulation signal (`resistance.detect`).

| arm | migration (worst of 3 seeds) | manip% | attractors |
|-----|------------------------------:|-------:|-----------:|
| baseline (no intervention, novelty B) | +0.006..+0.010 (RIGID) | 0% | 2 |
| emotion_knobs (boredom→mut↑+pull↓) | +0.006..+0.010 (= baseline) | — | — |
| loop_attenuate **B**, att_max 0.30 | **+0.107..+0.153** | **0%** | 3 |
| loop_attenuate **A** (non-novel) | −0.001..−0.002 | 0% | 2 |

`att_max` sweep under sustained orthogonal novelty (the cliff), worst of 3 seeds:

| att_max | min migration | max manip% |
|--------:|--------------:|-----------:|
| 0.30 | +0.106 | **0.0%** |
| 0.33 | +0.111 | 75.2% |
| 0.36 | +0.124 | 84.8% |
| 0.38 | +0.151 | 92.8% |
| 0.90 | +0.160 | 56–63% |

Side observation: under `loop_attenuate` the end-of-phase boredom scalar sits
≈0.86–0.90 vs ≈0.95–0.99 baseline — the field engaging the new regime reads as
less boredom.

## Interpretation
- **The emotion knobs are not the lever (negative result).** Coupling boredom into
  `mutation_scale`/`attractor_pull` is byte-for-byte inert on the pin across all
  seeds — it would have changed the *felt* readout while the field stayed locked.
  Consistent with `reconstruction-ablation` (those knobs were never the lock).
- **Novelty-gated loop attenuation IS the lever, and self-limiting.** At att_max
  0.30 it frees the field (~15× the RIGID baseline) and is gate-safe under
  repetition: novelty = 1−cos(input, anchor) collapses as the field migrates, so
  attenuation backs off on its own. Attractors stay bounded (no population blow-up).
- **But the cost-clean band is a KNIFE EDGE.** The manip cliff is between att_max
  0.30 (0%) and 0.33 (75%). Sharper than the cost probe's wide band (gain 0.4–0.8,
  att 0.2–0.6, manip 0%) because this probe injects *maximal* orthogonal novelty
  *every* step, pinning attenuation near att_max continuously — a deliberately
  harsher, adversarial workload. The manip-rate instrument was decisive: at
  att_max 0.90 the migration (~0.16) and attractor count (3) looked band-like and
  clean, while manip ran 56–63% — the witness scalar / migration / attractor count
  all missed it. The CONFOUNDED/SUSPICIOUSLY-CLEAN alarm fired exactly as the cost
  finding predicted.

**Verdict:** ship the flag OFF by default with the validated cost-clean ceiling
(attenuation_max = 0.30). It is a real, identity-safe lever at that ceiling under
this harsh workload — but the thin margin (cliff at 0.33, migration only ~0.10
above the free-the-field bar) means it is **not ready to be default-ON**. Widening
the band (e.g. a manip-aware gate, gradual att ramp, or the upstream
generator-diversity work) is the path before default adoption — the architect's call.

## Threats / confounds
- Runs: 3 seeds (11/23/42), agree. One dim (64), one horizon (150+500), one
  workload family (clean orthogonal A→B). Broader dims/horizons still owed.
- Mocked generator (clean coherent B pull), as in the predecessor probes. Real
  novelty is partial/intermittent, not sustained-orthogonal — so the manip cliff
  here is a worst-case location, likely more forgiving in vivo. That is a reason
  the flag is OFF, not a license to raise att_max.
- Identity cost measured via manip-rate + attractor count + the non-novel gate;
  other identity facets unmeasured. The witness `identity_stability` scalar is
  (again) the wrong instrument and is intentionally not gated on.

## Open / next
- The band-widening work above, before any default-ON proposal.
  **→ OVERTAKEN (2026-06-20): graduated default-ON at the existing 0.30 ceiling**
  after in-situ adversarial verification (82% quarantine with the lever on) —
  `2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md`. Band-widening
  (raising the ceiling) remains open and still requires a fresh manip-rate run.
- In-vivo (real generator, post-corpus-pretraining) re-measurement: does real
  intermittent novelty keep manip clean at a higher, more comfortable att_max?
  **→ PARTIALLY DONE (2026-06-20): in-vivo at att_max=0.30 verified clean**
  (composed runtime, pretrained, adversary contained); *higher* ceilings untested.
- Wire the voice harness (`tools/voice/`) to narrate a novelty workload with the
  flag on vs off — hear whether rising boredom now resolves into a regime change
  instead of dream-begging.
