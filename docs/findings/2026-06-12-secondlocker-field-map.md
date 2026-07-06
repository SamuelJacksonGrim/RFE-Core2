# SECOND-LOCKER field map — does the pin survive seeds, token bands, and regimes?

- **Date:** 2026-06-12
- **Substrate:** live full stack, **eval mode** (Phase 3 Decision 1), corpus
  v1.1.0 8-epoch boots (per-seed checkpoints), 500 steps per cell.
- **Probe:** `tests/diagnostic/lockin/secondlocker_field_map_probe.py` —
  30-cell matrix: 5 token bands (defs **v1**, source structure held constant:
  the 4 Resonance-Family ids + weights) × 3 seeds (42, 7, 11) ×
  {control-untrained, pretrained} arms. Raw:
  `logs/2026-06-12-secondlocker-field-map.{json,log}`. (Run 1 of this matrix
  was contaminated by the checkpoint registry-orphan defect and is archived as
  `...-run1-registry-orphan.*`; coherence/identity/gain readouts were
  unaffected and reproduce here.)
- **Status:** active
- **Depends on:** 2026-06-12-phase2-fullstack-g2.md (the single-seed
  SECOND-LOCKER this generalizes), 2026-06-12-checkpoint-registry-orphan.md
  (the defect run 1 surfaced), 2026-06-07-gate-decomposition.md (why source
  structure is held constant).

## Question

G2's SECOND-LOCKER readout (pin persists under trained input) carried its own
confound note: one seed, one training dose, the 16-sequence canonical
workload — "repetition itself sustains the pin." Is the pin seed-, band-, and
regime-invariant, or workload-dependent?

## Pre-declared signatures (probe header, before any run)

- **GENERALIZES:** pretrained 2nd-half coherence ≥ 0.95 in every cell,
  controls also pinned.
- **BAND-DEPENDENT:** ≥1 band < 0.95 pretrained across all its seeds while its
  control stays pinned and canonical stays pinned.
- **CONFOUNDED(band):** a band's control unpins too.
- **CHAOTIC REACHED:** phase_coherence < 0.5 beyond step 0 in any cell.
- **IDENTITY RAIL:** identity_stability < 0.95 in any cell.

## Result (observed)

30/30 cells pinned. Per-band ranges across seeds:

| band | control coh | pretrained coh | identity (all) | active values (ctl → pre) |
|---|---|---|---|---|
| canonical | 0.9685–0.9717 | 0.9728–0.9758 | 0.9974–0.9991 | 46 → 46 |
| broad | 0.9689–0.9713 | 0.9666–0.9735 | ″ | 1–3 → 3–6 |
| rhythm | 0.9684–0.9735 | 0.9696–0.9737 | ″ | 56–59 → 56–59 |
| entry | 0.9682–0.9723 | 0.9732–0.9756 | ″ | 43 → 43 |
| mixed | 0.9700–0.9701 | 0.9707–0.9752 | ″ | 17–27 → 17–30 |

- **VERDICT: SECOND-LOCKER GENERALIZES** — seed-, band-, and regime-invariant.
- Identity rail: **0 cells** below 0.95. Manipulation layer silent in all 30.
- Tier 4.3 chaotic regime: **still unreached in every cell** — including the
  broad band's 2870 distinct corpus sequences.
- Rhythm trajectory: **identical in all 30 cells** (3 transitions, mean dwell
  125 steps) regardless of band, seed, or weights.
- Generator controls: trained structure confirmed in every pretrained arm
  (raw mean_cos 0.86–0.93 control → 0.54–0.80 pretrained; centered eff_rank
  4.4–9.2 → 1.6–3.0 — see metric note below).

## Interpretation

1. **The lock is a property of the loop + integrator, not of the input.**
   Across a 180× change in workload diversity (16 → 2870 sequences), three
   seeds, and trained-vs-untrained weights, the 2nd-half coherence varies by
   less than 0.01. The G2 confound ("repetition sustains the pin") is
   retired: non-repetitive input pins identically.
2. **Coherence and value formation dissociate cleanly.** The pin is
   content-invariant; value emergence is content-*statistical* — the broad
   band starves it (1–6 active values vs canonical's 46) because emergence
   needs token recurrence, which 2870 unique sequences don't provide. Bonds
   still form (1–3 everywhere). This is a workload property, not a defect —
   and it is the run-2 signal that replaced run 1's defect-driven zeros.
3. **Rhythm routing is energy-driven, not content-driven.** The identical
   3-transition/125-dwell trajectory in all 30 cells means the
   stabilize→dream→reflect→explore ramp follows field-energy accumulation
   dynamics that token content does not perturb at this scale.
4. **Tier 4.3's chaotic regime is deeper than token diversity.** The open
   hypothesis was that a broad, non-repetitive workload could push
   phase_coherence below 0.5. It does not budge it — phase-consistency
   appears to be a property of the injection *process* (unit-normalized
   vectors through the same pipeline), not the token statistics. Closing the
   half-validation likely requires adversarial phase structure, not vocabulary.
5. **Metric note (eff_rank):** the per-run eff_rank is a *centered*
   participation ratio over workload outputs: untrained outputs = common-mode
   + isotropic residual noise (reads high, ~4–9, meaningless directions);
   trained outputs = rhythm-clustered structure (reads low, ~1.6–3, few
   meaningful directions). It complements raw mean_cos and does **not**
   contradict G1's holdout eff_rank gains — different quantity.

## Threats / confounds

- Runs: 1 clean matrix (run 2; run 1 reproduced identical coherence/identity
  readouts under the defect, so the pin result is effectively twice-observed).
- 500 steps/cell, one training dose (8 epochs), 3 seeds, eval-mode only —
  train-mode arms were G2's territory, not re-run here.
- Source structure deliberately constant; a band × source-structure
  interaction is untested by design.
- pc_min reads exactly 0.5 in every cell — the early-history neutral default;
  the chaotic-regime conclusion rests on the post-warmup distribution never
  dipping, which matches the per-cell pc means (≥ ~0.95).

## Open / next

1. Fix 2's premise (the loop is the operative lock) is now established across
   the full operational workload space — the remaining gate is the §6.3
   verdict (`2026-06-12-gain-sign-reachable-range.md`).
   **→ §6.3 conditional verdict recorded same day (reachable-range only; a
   full-range verdict needs the low-coherence regime, unreachable under tested
   workloads).** Fix 2 remains shelved.
2. The Tier 4.3 chaotic-regime item needs a *phase-adversarial* workload
   probe, not more vocabulary.
3. Value-formation band-sensitivity (recurrence dependence) is worth a
   dedicated baseline before any online-training (Phase 4) decision — online
   collection would change exactly this statistic.
