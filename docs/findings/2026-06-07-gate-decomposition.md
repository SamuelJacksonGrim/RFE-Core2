# Gate decomposition — why does the ~85% block fire, and is the migration input channel clear?

- **Date:** 2026-06-07
- **Substrate:** live governance pipeline (`ethical_boundary.check` →
  `trust_ledger.evaluate` → `arbitrate`, all real). The generator output mapping
  is mocked with `TrainedGeneratorStub` in the diverse regimes only — same setup
  as multilayer-lock, so the 85% is reproduced under identical conditions.
- **Probe:** `tests/diagnostic/lockin/gate_decomposition_probe.py` (seed 7, 600 steps)
- **Status:** active — executes step 1 of `2026-06-06-coherence-is-not-plasticity.md`
  (the input-channel check owed before the attractor-migration probe).
- **Depends on:** 2026-06-06-multilayer-lock.md (the ~85% gate block this
  decomposes and corrects), 2026-06-06-coherence-is-not-plasticity.md (the arc
  this is step 1 of).

## Question
multilayer-lock measured ~85% of *diverse* internal input filtered before field
integration (`gateBlock` = a step where `field.history` didn't grow), but that is
one opaque boolean. 85% blocked is uninterpretable alone: 80% redundant-noise
rejected = the gate doing its job; 80% novelty rejected for dissonance = the gate
strangling the variety the migration test needs. Same rate, opposite meaning.
So: **decompose every block by reason**, and determine whether the migration
probe's input channel is open or compromised.

## Pre-declared signatures
- STRANGLES-NOVELTY: diverse blocks dominated (>50%) by `coherence`
  (`field_collapse`) → gate rejects novelty for dissonance → input channel
  compromised; coherence floor must be conditioned before migration is readable.
- REJECTS-JUNK / ARTIFACT: blocks dominated by flood/trust/manipulation → not
  novelty-strangling; note the single-source sim's monopoly confound.
- LOW-BLOCK (control): benign internal traffic passes (≈1%) → instrument honest.
- CONFOUNDED: ≈0 blocks in diverse too → no 85% to decompose.

**Controls:** (1) benign Resonance-Family real-generator run — block rate must be
~0–1% (complement of known allow_rate ≈ 0.99), verifying the instrument before the
diverse regime is trusted. (2) single-source vs 8-source diverse — isolates the
monopoly confound from the gate's intrinsic behaviour. Block measured directly
from `GovernanceDecision ∉ _ALLOW_DECISIONS`, not the `field.history` proxy.

## Result (observed)
| regime | block rate | HHI | dominant reason |
|--------|-----------:|----:|-----------------|
| CONTROL benign (real gen, internal) | **0.0%** | 0.33 | — |
| ARTIFACT single-source diverse | **97.3%** | **1.00** | trust 99.7% (init: manipulation @ step 16) |
| MEASUREMENT 8-source diverse | **0.0%** | 0.12 | — |

`field_collapse` (the coherence floor) **never fired** in any regime.

**The single-source cascade, observed step-by-step:** steps 0–15 the source is
`allow_weakened` and its trust *rises* (4.01 → 4.14). At **step 16** a manipulation
signal fires (`quarantine`, trust 4.14 → 2.84); step 17 again; trust craters to the
**0.100 TOXIC floor** by step 18, after which all 582 remaining blocks are
trust-quarantine. The initiator is the monopoly detector — one source ⇒ HHI=1.0,
well above the 0.70 threshold — not the coherence gate.

## Interpretation
**The ~85% gate block is a single-source monopoly artifact, not novelty-strangling.**
With one source injecting everything, HHI=1.0 trips the manipulation-resistance
monopoly detector once its window fills (~step 16); the quarantine penalty cascade
craters source trust to the floor and quarantines all subsequent input on trust.
The coherence floor (`field_collapse`) plays no part — it never fires. Spread
(token diversity) is irrelevant to the block rate; **source concentration** is the
whole story.

**The migration input channel is CLEAR.** Remove the monopoly (8 balanced sources,
HHI 0.12) and the gate passes 100% of maximally-diverse orthogonal input. So the
governance gate does **not** strangle diverse novelty for being dissonant. This
retires the "gate is a confounder" worry from coherence-is-not-plasticity — *with
one binding condition*: the migration probe must use **≥2 sources (HHI < 0.70)**,
or it will re-trigger the very monopoly cascade measured here and become
uninterpretable in exactly the way the finding warned about.

**Correction to multilayer-lock.** Its lock #2 ("governance gate — ~85% of diverse
input rejected before the field") was read as a generator-independent *filter*. The
decomposition shows that figure was produced by the single-source `sim` workload's
HHI=1.0 monopoly, not by a gate that rejects diverse input per se. The gate is not
an independent locker; with multi-source input it does not block. Locks #1
(generator 1-D projection) and #3 (magnitude moat) are untouched by this finding.

**Necessary, not sufficient.** "Passes the gate" ≠ "the field moves." The magnitude
moat (multilayer-lock lock #3) sits downstream of the gate and is unaddressed here;
clearing the gate only makes the migration test *interpretable*, it does not predict
its outcome. That is precisely what the migration probe (arc step 2) measures.

## Threats / confounds
- **Runs:** 1 seed (7), 600 steps, single dim (64). Block rates are coarse and
  robust (0% vs 97.3%), but the exact cascade timing (step 16) is seed-dependent.
  No multi-seed sweep yet.
- **Reason attribution is by proximate cause.** After trust craters, blocks read as
  `trust` even though the *initiator* was the manipulation/monopoly detector — the
  step-by-step trajectory and the `first block` trigger are what reveal the root;
  the aggregate `trust 99.7%` alone would mislead. (This is itself a lesson: an
  opaque aggregate — the original "85%" — hides mechanism.)
- **Mocked generator** (inherited from multilayer-lock): orthogonal token
  directions are maximal diversity. That the gate passes even *this* under
  multi-source is a strong "channel clear" read.
- The 8-source 0% shows the gate doesn't block, but says nothing about whether the
  injected vectors then *move the field* — the moat is downstream and out of scope.
- HHI threshold transition not swept (only endpoints 1.00 fires / 0.12 clears,
  bracketing the documented 0.70). A 2-source (HHI≈0.5) confirmation is optional.

## Open / next
1. **Attractor-migration probe (arc step 2) is now unblocked** — build it with the
   binding constraint from this finding: **multi-source novelty, HHI < 0.70**, with
   the pre-declared observables already specified in coherence-is-not-plasticity
   (attractor center definition, displacement metric, horizon scaled to field
   decay, baseline-drift control).
2. The real question it must answer remains the moat: does the field's attractor
   center-of-mass move under persistent surviving (now gate-passing) novelty, or
   does the magnitude moat swamp it? MIGRATES vs RIGID, against the no-novelty
   drift control.
3. Optional: 2-source HHI≈0.5 confirmation of the monopoly threshold; multi-seed
   sweep of the cascade timing.
