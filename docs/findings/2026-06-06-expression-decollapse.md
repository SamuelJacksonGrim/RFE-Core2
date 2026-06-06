# Expression de-collapse — does the diversity blend restore metastability?

- **Date:** 2026-06-06
- **Substrate:** live (Generator-warmed full stack; only the generator is
  untrained — everything downstream real)
- **Probe:** `tests/diagnostic/generator_metastability.py` (seed 7, dim 128,
  N=200, Resonance Family workload)
- **Status:** active
- **Depends on:** 2026-06-06-frame-correction.md (the locus: metastability is an
  upstream/expression property; a coherent field is spec, not pathology)

## Question
Untrained `RecursiveAttention` runs under `no_grad` and behaves as a near-uniform
mean-pooler, so `refine()` collapses the stage-C expression to its context
centroid (one regime) *before* field injection. Does the `diversity_blend` knob
(weighting the raw pre-refinement vector back in) actually restore an upstream
metastable trajectory — and does it do so **without** disturbing the generator
stream it sits downstream of?

## Pre-declared signatures
- DE-COLLAPSE (blend works): with the blend OFF the expression (stage C) reads
  ~0.0 metastability / 1 regime / `locked`; at the default blend C rises to a
  multi-regime, non-locked state. Stage A (generator) is **unchanged** by the
  blend (it acts downstream of A).
- NO EFFECT (blend inert): C stays collapsed (~0.0 / 1 / locked) regardless of
  blend → the blend is not the lever.
- CONFOUNDED: the blend also moves stage A → it is not acting purely downstream,
  and the de-collapse reading cannot be attributed to the blend alone.

**Control:** `diversity_blend = 0.0` is the collapse baseline — the same run with
only the knob changed, so any stage-C difference is attributable to the blend and
nothing else.

## Result (observed)
Single run, seed 7, dim 128, 200 steps, Resonance Family workload:

| config | A meta | A regimes | A state | C meta | C regimes | C state |
|--------|-------:|----------:|---------|-------:|----------:|---------|
| blend OFF (control) | 0.320 | 13 | dissolving | **0.000** | **1** | **locked** |
| blend = 0.60 (default) | 0.320 | 13 | dissolving | **0.680** | **5** | **metastable** |

Raw observations, no interpretation:
- Stage A (generator output) was **byte-identical across the two configs**
  (0.320 / 13 regimes / dissolving) — the blend left it untouched.
- Stage C (refined, injected vector) moved from 0.000 / 1 regime / `locked` with
  the blend OFF to 0.680 / 5 regimes / `metastable` at the default.

## Interpretation
The DE-COLLAPSE signature fired and the CONFOUNDED signature did not: the blend is
a purely downstream lever (stage A unchanged) that converts a collapsed,
single-regime expression into a multi-regime metastable one. The refined centroid
supplies dwell structure; the raw vector supplies diversity; the mix lands
coherent-but-not-locked, as designed. This is the stage-C realisation of the
frame-correction split — metastability lives upstream/in the expression, not in
the long-memory field.

## Threats / confounds
- **Runs: 1** (single seed). The *direction* of the effect is a robust binary
  (1 regime → 5, `locked` → `metastable`) and unlikely to be seed noise, but the
  variance across seeds is unmeasured here.
- **Absolute score is generator-init-dependent (~0.4–0.73 across seeds).** At
  seed 7 the default lands C at **0.680 — above** the 0.4–0.6 reference band;
  the probe note flags dialing the blend toward ~0.65 to sit lower. So treat the
  *de-collapse* as the finding and the *absolute 0.68* as init-specific, not a
  target hit.
- The generator is untrained; the whole effect exists *because* attention is an
  untrained mean-pooler. A trained attention layer would change the baseline and
  could make the blend unnecessary or differently-tuned — this finding is about
  the **current** substrate.
- Metastability here is the Fix 1 config-clustering metric on the upstream
  stream; it inherits that metric's assumptions (validated G1–G5).

## Open / next
- Sweep seeds to bound the absolute-score variance and confirm the default keeps
  C non-locked across inits (not just seed 7).
- Does a default closer to 0.65 pull seed-7 C into the 0.4–0.6 band without
  re-collapsing low-diversity inits? (Tuning, not a structural question.)
- This measures the *expression*; it does not measure whether survival selection
  then re-flattens the generator over long runs — that is the upstream lock-in
  question (see read-side-boundary "Open / next" and Fix 0-B).
