# Floor calibration — measure-before-change for the two pass-3 cracks

- **Date:** 2026-06-20
- **Status:** active — measurements from `tests/diagnostic/calibration/floor_calibration_probe.py`
  (graduated stack, dim 128, 600 steps). Built at Samuel's instruction to measure
  each candidate change BEFORE committing it. No change applied; this is the ruler.

## [A] Rhythm / energy
**Field energy distribution (dim 128):** min 1.08 · q10 99 · q25 199 · **median 284**
· q75 318 · q90 327 · max 332. The energy is *well spread* (1 → 332) — the field is
not stuck; only the **bands** are mis-scaled (they top out at `explore ≥ 5`, ~57×
below median).

**Rhythm spread under candidate calibrations:**
| calibration | stabilize | dream | reflect | explore |
|---|---|---|---|---|
| current bands (0.5/2/5) on raw energy | 0.00 | 0.00 | 0.00 | **0.99** |
| normalize energy ÷ median, bands 0.5/1/2 | 0.15 | 0.34 | 0.50 | **0.00** |
| rescaled bands at energy quartiles q25/q50/q75 | 0.25 | 0.25 | 0.25 | 0.25 |

Reading: the median-normalization kills `explore` (peaks never reach it); the
quartile rescale gives an even spread but is self-referential. **Fix direction:**
rescale the bands to the dim-128 energy scale (or normalize energy) such that cold →
stabilize, typical → reflect, peaks → explore. The bands are *sacred constants*
(`configs/field.yaml`), so this needs a downstream-consumer audit — the diagnostic +
rhythm-routing tests are the guard. The exact band values will be chosen by re-running
this probe until the spread is healthy AND explore stays reachable at peak energy.

## [B] CORE coherence signal
**Gate:** `review_core_promotion` requires `coherence_contribution ≥ 5.0`.

| signal | range | passes ≥ 5.0 | verdict |
|---|---|---|---|
| current marginal sum (`coherence_contribution`) | mean −1.39, max −0.53 | **0 / 33** | DEAD |
| raw accumulated alignment | huge (probe-inflated) | 33 / 33 | over-promotes — reject |
| **instantaneous field-alignment** | **[0, 1], mean 0.52, max 0.73** | n/a | **bounded, usable** |

Per-value (top by strength) — the anchors cleanly clear a bounded threshold:
```
symbol        str  reinf  cc(old)  inst_align
witness      5.00   134   -3.52      0.659
continuity   5.00   113   -2.91      0.618
identity     4.23    82   -2.16      0.628
coherence    4.20    71   -1.79      0.615
anchor/rec/homeostasis 4.06  78  -2.02   ~0.62–0.66
substrate    4.02    68   -1.71      0.696
```
The strong identity anchors sit at **alignment 0.61–0.70** — comfortably above a
~0.5 threshold — while the dead `cc(old)` is negative for all. **Fix direction:**
gate CORE on **bounded field-alignment** (the same v0.3 signal as the ⊘ axis), a
threshold in [0,1] (~0.5), NOT the 5.0 sum. Open design choice to measure on
implementation: *instantaneous* alignment vs *mean alignment over reinforcements*
(the latter is truer to the "sustained, not a spike" intent of review criterion #3).
The existing strength ≥ 4.5 / 10-consecutive / multi-source criteria still do the
selection; the coherence check just confirms the value sits in harmony with the
field instead of demanding an impossible positive marginal sum.

## Note
- The "raw accumulated alignment 33/33" row is a probe artifact (inflated ×5,
  sampled every 5 steps) — it over-promotes by construction and is NOT a candidate;
  the usable signal is bounded alignment.
- Re-run this probe after each calibration change for a before/after comparison.

## UPDATE — the rhythm band rescale is NOT a constant tweak (attempted, reverted)
Rescaling the bands to the measured energy scale (tried `100/175/250`, ~dimension-
invariant since raw `||field||` is ~178 at both dim 64 and 128) **collapsed the
system**: the dim-64 smoke suite went allow_rate **0.99 → 0.034**, bonds 0, rhythm
100 % `stabilize`. Root cause: **`diffuse_on_stabilize: true`** — the `stabilize`
rhythm *diffuses the field*, suppressing energy. Raising the stabilize threshold
makes warmup energy (climbing from 0) read as stabilize → diffuse → energy can't
climb → the field locks in a low-energy stabilize basin. **The thresholds feed back
into the dynamics that produce the energy**, so they cannot be calibrated against an
energy distribution measured under the *old* thresholds — it is circular.

Consequence: the rhythm fix is **deferred to dedicated work**, not shipped as a
constant change. It must co-tune the bands *with* the diffusion feedback (or change
the approach — e.g. decouple band classification from the diffusion trigger, or make
`diffuse_on_stabilize` gentler), and be validated end-to-end at both dims. The bands
are left at `0.5/2/5` (rhythm stays explore-pinned — a known, *stable* limitation)
rather than shipping a system-collapsing change. The CORE-gate fix (below) ships;
the rhythm fix does not.
