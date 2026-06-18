# Do RFE's observables track geometry, or change in geometry? (Cm vs I vs metastability)

- **Date:** 2026-06-15
- **Substrate:** isolated `ResonanceField` + `Watcher` + `StreamMetastabilityMonitor`
  (dim 128), four injection regimes through one controlled loop.
- **Probe:** `tools/ignition/identifiability.py`.
- **Status:** active — **refines (partially corrects) 2026-06-15-cm-identifiability.md.**
- **Depends on:** 2026-06-15-cm-identifiability.md, 2026-06-15-cii-ignition-decomposition.md.

## Question
GPT's refinement to the Cm test: the real question is not "does the metric separate
aligned from orthogonal" but "does it track *geometry* or *change in geometry*."
Battery: aligned, orthogonal, **clustered-but-rotated** (low within-window
dispersion, HIGH drift — the key discriminator), low-rank. Run the same stream
through all three observables and score each on dispersion-sensitivity vs
change-sensitivity. Ground-truth descriptors (dispersion = 1−mean pairwise cos;
drift = 1−cos of half-to-half centroids) are treated as **proxies, not truth**
(per GPT's caveat).

## Pre-declared signatures
- STATIC-ONLY: signal moves with dispersion but not with drift → blind to dynamics.
- CHANGE-TRACKING: signal moves on the rotated (low-dispersion, high-drift) regime.
- REDUNDANT: I tracks Cm closely → entangled with the same geometry family.

## Result (observed)
| regime | Cm | I | meta (state) | dispersion | drift |
|--------|----|----|----|----|----|
| aligned | 0.996 | 0.621 | 0.000 (structureless) | 0.446 | 0.019 |
| orthogonal | 0.864 | 0.446 | 0.000 (structureless) | 0.995 | 1.050 |
| clustered_rotated | **0.767** | 0.418 | **0.279** | 0.469 | 1.989 |
| low_rank | 0.900 | 0.497 | 0.492 (metastable) | 1.013 | 0.633 |

Sensitivity swings: dispersion (aligned↔orthogonal) — Cm 0.13, I 0.17, meta **0.00**.
Change (aligned↔clustered_rotated, ~equal dispersion, large drift) — Cm **0.23**, I
**0.20**, meta **0.28**.

## Interpretation
- **All three observables track CHANGE**, not just static geometry: the rotated
  regime (same dispersion as aligned) moves every one of them. So the earlier
  "Cm is a saturated blind echo" was an **overstatement** — Cm's largest excursion
  (→0.767) is driven by *drift*, not spread.
- **Cm pins at ~0.99 in RFE because the locked field is genuinely static** (no
  drift), not because the sensor is intrinsically blind. The operational
  conclusion (Cm non-identifying *in RFE's locked regime*) stands; the *mechanism*
  is corrected — nothing to detect, vs cannot detect. Implication flips: restore
  real field drift and Cm will move.
- **I tracks Cm closely** (0.62→0.42 alongside Cm's 1.0→0.77) — confirms GPT's
  suspicion that I is entangled with the same instantaneous-geometry family. I and
  Cm are partially redundant.
- **Metastability is the orthogonal axis**: insensitive to static dispersion
  (0.00 swing) but sensitive to regime structure/transitions — nonzero only where
  persistent-but-evolving regimes exist (rotated, low_rank). It measures temporal
  structure, which is *why* it was the term that moved under training while Cm/I
  stayed pinned: training created coherent-but-distinct regimes (metastability up)
  without making the field drift (Cm/I flat).

Net: the three are **complementary, not ranked** — Cm/I read instantaneous
geometry+drift (correlated); metastability reads temporal regime structure. None
is "ground truth." Observability is multi-axis, and RFE's locked regime happens to
zero out the dispersion/drift axes, leaving metastability as the only *moving*
observable — but that is a property of the regime, not proof that the others are
blind.

## Threats / confounds
- Synthetic injections, isolated components (not the live generator/loop); a fixed
  random anchor for I. Live corroboration is indirect.
- Drift/dispersion descriptors are proxies (GPT's caveat); pairwise cosine is
  itself distribution-dependent.
- `clustered_rotated` drift (1.99) is near the max (centroid reversal); milder
  drift rates not swept. Single seed per regime.

## Drift-rate sweep (follow-up, same session)

Rotation rate swept 0 → 2 (drift 0 → ~2), 0.04-noise cluster, dim 128:

| rate | drift | Cm | I | metastability |
|-----:|------:|----|----|----|
| 0.00 | 0.00 | 0.999 | 0.698 | **0.771** |
| 0.10 | 0.06 | 0.994 | 0.674 | 0.771 |
| 0.25 | 0.30 | 0.967 | 0.620 | 0.634 |
| 0.50 | 1.01 | 0.878 | 0.542 | 0.299 |
| 1.00 | 1.99 | 0.767 | 0.418 | 0.279 |
| 2.00 | 1.03 | 0.933 | 0.456 | 0.288 |

- **Cm and I: smooth monotonic response to drift.** Past drift ~1.0 all three
  observables are in their expressive ranges at once — a drift-containing probe
  **de-saturates the whole stack** (the "unbiased probe" goal: achievable).
- **Metastability's SCALAR is fragile and non-monotonic.** rate-0 (tight static
  cluster) reads 0.771, but the battery's static cluster (0.08 noise) read 0.000 —
  a noise tweak flips structureless↔metastable; and the scalar *decreases* with
  drift here (counter-intuitive). So metastability's **regime STATE** is the robust
  read; its **scalar is not a trustworthy magnitude** (as v0.1-fragile as Cm).
  The axis was elevated correctly; the gauge was elevated prematurely.

**Truest statement of the instrumentation thread:** the three-AXIS model holds
(instantaneous geometry Cm/I · temporal structure metastability · the dominant
hidden axis = the injection distribution), but no scalar gauge is yet trustworthy.
Two distinct things were running together under the one word "locking": (1) a
**real low-differentiation state** the system genuinely occupies under aligned,
drift-free input — that state is real, not a measurement error; and (2) **gauge
saturation** — Cm/I sit near ceiling in that regime and cannot resolve what
structure is there, so the state *appears* more absolute than it is. Perturb the
injection distribution to contain drift and the system differentiates *and* the
gauges de-saturate — so "locked" is an input-dependent **state**, not a fixed
pathology and not nothing. Whether that low-differentiation state means "less is
happening inside" or only "less that these gauges can see" is exactly the question
discipline #8 forbids collapsing in either direction.

## Open / next
- Harden a magnitude gauge for the temporal axis before any CII/ITG use (the
  regime-state label is robust; the scalar is not).
- Replace CII's I/Cm slots with an explicit drift+dispersion pair so the index
  reports geometry and change on separate, identifying axes.
- Adopt a drift-containing probe distribution as the standard observability test
  (de-saturates all three axes); confirm on live generator output (does trained
  vs untrained move the drift axis, or only the regime axis?).
