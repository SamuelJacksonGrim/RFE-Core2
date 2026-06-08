# Where is the lock? (generator / governance / magnitude moat)

- **Date:** 2026-06-06
- **Substrate:** sim (untrained Generator's output mapping mocked with a
  deterministic token→direction stub; full live step loop otherwise — governance,
  coherence_impact, injection, reaper, decay, emotional gradient all real)
- **Probe:** `tests/diagnostic/trained_generator_sim.py`
- **Status:** active
- **Depends on:** 2026-06-06-read-side-boundary.md (the survival-by-coherence
  mechanism), 2026-06-06-frame-correction.md (read this finding in the corrected
  frame: coherent field is spec, not pathology)

## Question
`lockin_source.py` proved the live lock is upstream: the untrained Generator maps
near-everything to ~one direction (cos ~0.998), so field input is effectively 1-D
regardless of tokens. It did NOT test whether the field dynamics can hold low
coherence *given* diverse input (it only tested a single novel injection). So:
if the generator stopped being a 1-D projector, would the field escape the pin?

## Pre-declared signatures
- GENERATOR-IS-THE-LOCK: under diverse input the field drops off the ~0.998 pin
  to a lower/variable band; monitor reads non-locked → training the generator
  unlocks it, no field-side fix needed for this lock.
- SECOND-LOCKER: field still pins ~0.99+ even under maximal diverse input →
  a generator-independent locker (the accumulate-decay magnitude moat).
- Control: `spread=0.0` (stub = 1-D projector) must reproduce the known lock,
  or the stub is dishonest and nothing downstream is trustworthy.

## Result (observed)
Control passed: `spread=0.0` → coh_mean 0.971, regime `locked` (matches
`lockin_source.py`). Stub is honest.

Sweep (spread 0.0 → 1.0, i.e. 1-D projector → maximally diverse generator):

| spread | inputCos | cohMean | cohStd | cohMin | regime | gateBlock |
|--------|----------|---------|--------|--------|--------|-----------|
| 0.00 | 0.950 | 0.971 | 0.020 | 0.500 | locked | 85.7% |
| 0.50 | 0.924 | 0.938 | 0.022 | 0.500 | locked | 85.7% |
| 1.00 | 0.910 | 0.952 | 0.043 | 0.500 | metastable | 80.7% |

Raw observations, no interpretation:
- Even at max source diversity (spread 1.0, orthogonal token directions), the
  vectors that actually *landed* in the field averaged inputCos **0.91**
  (near-collinear).
- coh_mean stayed in [0.94, 0.97] across the whole sweep; coh_min touched 0.500
  transiently every row; coh_std rose 0.020 → 0.043.
- The governance gate blocked ~**85%** of diverse internal input before field
  integration, across all spreads.
- The regime label flipped `locked` → `metastable` only at spread 1.0, when
  coh_std crossed the 0.40 metastability threshold.

## Interpretation
**Three locks, not one** — and read in the corrected frame (see
frame-correction): a coherent field is spec, not pathology.
1. **Generator (1-D projection)** — the known upstream lock.
2. **Governance gate** — ~85% of diverse input rejected *before* the field. A
   filter neither `lockin_source.py` nor the council frame accounted for.
3. **Magnitude moat** — the accumulating field swamps each new injection
   (inputCos 0.91 landing despite orthogonal sources); what reaches the field
   looks aligned regardless of source diversity.
   **→ DOWNGRADED (2026-06-07, `2026-06-07-reconstruction-ablation.md`): the moat is
   NOT the locker.** With the reflective loop ablated the field migrates fully to a
   new regime despite the moat being present. Lock #2 was earlier struck (gate
   decomposition: monopoly artifact); lock #3 (moat) is real context but surmountable.
   The actual lock is the **reflective loop**, downstream of all three.

The field holding ~0.95 under diverse input is the field *doing its job* (coherent
integrator by design), not a pathology. The strongest reading: the moat is a real,
generator-independent locker — the field couldn't be moved off ~0.95 even under
maximal diversity, because governance blocks most diverse input and the moat
swamps the rest.

**Misread caught:** the originally-printed verdict ("field moved off pin →
generator is the lock") was **too generous** — it trusted the regime *label*
(which flipped on a 0.020→0.043 dwell-variance nudge) over the coherence number
(which never left the high band). Corrected above.

## Threats / confounds
- Runs: 1 per spread point (5 points). Single seed; no repetition to check
  variance of the gate-block rate or the inputCos figure.
- **Mocked component:** the Generator's output mapping is a stub, not a trained
  generator. Random-orthogonal token directions are *maximal* diversity — more
  spread than a real trained generator (which clusters semantically). So
  "field still locked under max diversity" is a STRONG read; "field escaped"
  would have been weak (best case). The asymmetry is load-bearing.
- The 85% gate-block is observed but **undecomposed** — we don't yet know *why*
  each block fired (could be 80% junk + 5% novel, or the reverse; same rate,
  opposite meaning). Do not over-read the rate until decomposed (see Finding 4).

## Open / next
- **85% governance block** is the most useful new finding. Is governance
  correctly rejecting junk, or starving the *expression* stream of the variety it
  needs to stay metastable upstream? (On-axis; pull next.)
  **→ DECOMPOSED & CORRECTED (2026-06-07), see `2026-06-07-gate-decomposition.md`:**
  the 85% was a **single-source monopoly artifact** of this probe's `sim` workload
  (HHI=1.0 → manipulation detector → trust cascade), *not* the gate rejecting
  diverse input. `field_collapse` never fired; 8-source diverse input blocks at 0%.
  Lock #2 (governance gate) is **not** an independent locker — strike it. Locks #1
  (generator) and #3 (moat) stand.
- The right metastability read is on `generator_metastability` (stage A) /
  `expression_metastability` (stage C), NOT the field. Re-run watching those.
- Pin-vs-band for the field was put to Raphael → reframed; see Finding 4
  (coherence-vs-plasticity).
