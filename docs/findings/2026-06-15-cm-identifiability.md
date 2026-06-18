# Is field coherence (Cm) identifying, or a saturated angular statistic?

- **Date:** 2026-06-15
- **Substrate:** isolated `ResonanceField` (dim 128), aligned vs orthogonal
  injection streams (no generator — tests the metric directly).
- **Probe:** `tools/ignition/cm_check.py`.
- **Status:** active — **refined by 2026-06-15-identifiability-suite.md**: the
  fuller change-vs-geometry battery shows Cm *does* track drift (→0.767 under
  rotation), so "saturated blind echo" was too strong. Cm pins in RFE because the
  locked field is genuinely static (no drift to report), not because the sensor is
  intrinsically blind. The operational pin stands; the mechanism is corrected.
- **Depends on:** 2026-06-12-secondlocker-field-map.md (the coherence pin),
  2026-06-06-read-side-boundary.md, 2026-06-15-cii-ignition-decomposition.md (Cm
  is an ignition term).

## Question
Prompted (GPT) by the CII work: `ResonanceField.internal_coherence` (= Cm) is
`(cos(field, mean-of-last-32-injections)+1)/2`. Does it read genuine internal
organization, or is it a saturated angular statistic — high because the field is
*built from* those injections, regardless of how diverse they are? Inject an
aligned stream vs an orthogonal stream; compare Cm to a full-range ground-truth
separability metric (mean pairwise cosine of recent injections).

## Pre-declared signatures
- GEOMETRY ECHO: Cm ≈ same for aligned and orthogonal while pairwise cosine
  swings fully → Cm non-identifying.
- VALID: Cm tracks the pairwise cosine across its range.
- COMPRESSED (middle): Cm moves but into a thin saturated band.

## Result (observed)
| regime | field Cm | mean pairwise cos (truth) | eff_rank |
|--------|---------:|--------------------------:|---------:|
| aligned | 0.997 | +0.544 | 26.4 |
| orthogonal | 0.873 | +0.009 | 31.0 |

COMPRESSED fired: a structural swing of 0.54 (pairwise cos) maps to a Cm swing of
0.12. Cm's **floor is ~0.87 even for maximally-orthogonal input** (field and
history-mean are both built from the same injections → correlated by
construction). Usable range ≈ [0.87, 1.0].

## Interpretation
Cm is **weakly identifying, operationally non-identifying.** It is *not* pure
geometry (GPT's strongest claim is too strong — it does drop 0.997→0.873), but
its information is squeezed into a thin top band, and it mostly measures "the
field tracks its own recent input average" (near-tautological). Crucially, RFE's
live injections — even after training — stay aligned (generator common-mode
dominance), so the field sits at Cm ≈ 0.97–1.0 and **never reaches Cm's
discriminating range.** That is exactly the SECOND-LOCKER flatness. So the
coherence pin is not (only) a field/loop lock — it is partly a **sensor sitting in
its blind spot because the generator keeps the system aligned.**

Consequence for CII: in RFE's operating regime, **I and Cm are saturated echoes;
metastability is the lone ignition term carrying real signal** — the one that
actually moved under training. The ignition index is, in practice, "1 signal + 2
geometric echoes," as GPT framed it.

## Threats / confounds
- Isolated field, synthetic injections (not generator output); but the live pin
  (Cm ≈ 0.99 even trained, train_ignite) corroborates the operating-regime claim.
- "aligned" here is pairwise cos 0.54 (0.08 noise in dim 128), not ~0.95; a
  tighter aligned stream would push Cm nearer 1.0 — widening the gap, not
  closing it.
- `I` (watcher composite) is *assumed* similarly saturated by association; not yet
  measured directly with an identifiability test of its own.

## Open / next
- Replace/augment Cm with a full-range read: mean pairwise cosine (or 1−it) of
  recent injections, or intra-window eff_rank, as the real "internal organization"
  signal for CII's I/Cm slots.
- Run the same identifiability test on `I` (watcher composite) directly.
- This is the read-side question GPT flagged, now with a number: confirm whether
  any field/witness scalar is identifying in RFE's operating regime, or whether
  metastability is the only honest observable.
