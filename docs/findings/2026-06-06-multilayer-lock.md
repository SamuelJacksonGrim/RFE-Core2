# The lock is multi-layered: generator + governance + magnitude moat

- **Date:** 2026-06-06
- **Substrate:** sim (untrained Generator's output mapping mocked with a
  deterministic token→direction stub; full live step loop otherwise — governance,
  coherence_impact, injection, reaper, decay, emotional gradient all real)
- **Probe:** `tests/diagnostic/trained_generator_sim.py`
- **Status:** active

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

## Result
Control passed: `spread=0.0` → coh_mean 0.971, regime `locked` (matches
`lockin_source.py`). Stub is honest.

Sweep (spread 0.0 → 1.0, i.e. 1-D projector → maximally diverse generator):

| spread | inputCos | cohMean | cohStd | cohMin | regime | gateBlock |
|--------|----------|---------|--------|--------|--------|-----------|
| 0.00 | 0.950 | 0.971 | 0.020 | 0.500 | locked | 85.7% |
| 0.50 | 0.924 | 0.938 | 0.022 | 0.500 | locked | 85.7% |
| 1.00 | 0.910 | 0.952 | 0.043 | 0.500 | metastable | 80.7% |

Three locks, not one:
1. **Generator (1-D projection)** — the known upstream lock.
2. **Governance gate** — blocked ~**85%** of diverse internal input *before* it
   reached the field, across all spreads. A filter neither `lockin_source.py`
   nor the council frame accounted for.
3. **Magnitude moat** — even at max source diversity (orthogonal token
   directions), the vectors that actually *landed* in the field averaged
   **inputCos 0.91** (near-collinear). The accumulating field swamps each new
   injection; what lands looks aligned regardless of how diverse the source was.

## Read
**Important — read in the corrected frame (see frame-correction finding).** The
field holding ~0.95 under diverse input is the field *doing its job* (it is a
coherent integrator by design), NOT a pathology. The originally-printed verdict
("field moved off pin → generator is the lock") was **too generous**: it tripped
on the regime *label* flipping to `metastable` (driven by coh_std rising 0.020→
0.043 crossing the 0.40 metastability threshold) while coh_mean never left the
high band. Coherence stayed pinned; only dwell-variance nudged up.

**Misread caught:** the verdict logic trusted the regime label over the coherence
number. Corrected reading: this is closer to evidence the moat is a real,
independent locker — the field could not be moved off ~0.95 even under maximal
diversity, because governance blocks most diverse input and the moat swamps the
rest. Whether that is correct behavior (in the coherent-field design) or
over-aggressive is the live question below.

## Open / next
- **85% governance block** is the most useful new finding. Is governance
  correctly rejecting junk, or starving the *expression* stream of the variety it
  needs to stay metastable upstream? (On-axis; pull next.)
- The right metastability read is on `generator_metastability` (stage A) /
  `expression_metastability` (stage C), NOT the field. Re-run watching those.
- Letter out to Raphael on pin-vs-band for the field (hard 0.998 pin vs. a
  softer high-but-floating coherence).
