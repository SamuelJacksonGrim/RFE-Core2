# Is field coherence (Cm) identifying, or a saturated angular statistic?

- **Date:** 2026-06-15 · **Status:** superseded — refined by `2026-06-15-identifiability-suite`
- **Substrate:** isolated `ResonanceField` (dim 128), aligned vs orthogonal injection · **Probe:** `tools/ignition/cm_check.py`
- **Depends on:** `2026-06-12-secondlocker-field-map`, `2026-06-06-read-side-boundary`, `2026-06-15-cii-ignition-decomposition`

**Verdict:** Cm is **weakly identifying, operationally non-identifying**. A structural swing of **0.54** (mean
pairwise cosine: aligned 0.544 → orthogonal 0.009) maps to a Cm swing of only **0.12** (0.997 → 0.873); Cm's
floor is **~0.87** even for maximally-orthogonal input (field and history-mean are built from the same
injections → correlated by construction). Usable range ≈ [0.87, 1.0]. RFE's live injections stay aligned
(generator common-mode), so the field sits at Cm ≈ 0.97–1.0 and **never reaches Cm's discriminating range** —
part of the SECOND-LOCKER flatness is a sensor sitting in its blind spot.

**Refinement (why superseded):** the fuller change-vs-geometry battery (`identifiability-suite`) showed Cm *does*
track drift (→0.767 under rotation), so "saturated blind echo" was too strong — **Cm pins because the locked
field is genuinely static (no drift to report), not because the sensor is intrinsically blind.** The operational
pin stands; the mechanism is corrected. Consequence for CII: **metastability is the lone ignition term carrying
real signal**; I and Cm are geometric echoes in RFE's operating regime.

*Consolidated 2026-08-05 — the measured swing, the floor, and the refinement preserved. Full history in git.*
