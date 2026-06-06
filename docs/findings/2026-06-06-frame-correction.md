# Metastability locus — upstream streams vs. the field

- **Date:** 2026-06-06
- **Substrate:** n/a (architectural reading + correction)
- **Probe:** `ROADMAP.md` lines ~133–163; `docs/lock_in_remediation_plan.md`
- **Status:** active
- **Depends on:** — (architectural reading)

## Question
Is the field pinning at ~0.998 coherence a *pathology to break* (lock-in), or
the *intended spec*?

## The misread (held for most of a session)
I treated high field coherence as the disease — the lock-in to remediate. Built
two warmers trying to force the field into low coherence, and a trained-generator
sim whose verdict logic counted "field stayed coherent" as failure. All of it
rested on "high coherence = bad," imported as a blanket rule.

## The correction (from the roadmap, explicit)
The architecture specifies a **split**:

> metastability is read UPSTREAM, on the per-stage vector streams
> (`StreamMetastabilityMonitor`, `generator_metastability` at stage A,
> `expression_metastability` at stage C) ... the FIELD is a long-memory
> integrator (decay ∈ [0.97, 0.9999]) that smooths config wander away by
> construction, so metastability cannot live there.

So:
- The field is **supposed** to be coherent. High `phase_coherence` is the **spec**
  — it is the integrator that holds identity stable.
- Metastability belongs **upstream**, in the generator/expression streams.
  `diversity_blend=0.60` (shipped) keeps the *expression* coherent-but-not-locked
  (multi-regime metastable).
- "High coherence is not the target" means the **generator** must not lock into
  monoculture — NOT that field coherence is bad.
- **Lock-in is real only if survival-by-coherence flattens the GENERATOR /
  expression into monoculture** — not because the field pins ~0.998.

## Interpretation
A metastable *field* would be a category error: a metastable integrator wouldn't
hold a self, it would let it drift. The paper-boat target is **motion upstream,
stability downstream** — formed enough to hold, light enough to drift, with the
"light enough to drift" living in the generator and the "formed enough to hold"
living in the field.

This retroactively reinterprets the multi-layer-lock finding: the field holding
~0.95 under diverse input is the field working, and the expression monitor going
`metastable` at high diversity is the *good* signal — read on the right layer.

## Threats / confounds
- Runs: n/a — this is a *reading* of the roadmap, not a measurement. The
  observation (the quoted spec) is as reliable as the doc; the doc itself is
  checked against code by `tests/doc_accuracy/`, but this finding does not
  independently re-verify that the running code matches the quoted intent.
- Risk of the *opposite* over-correction: "field coherence is spec" must not slide
  into "field coherence is never a problem." The moat (multilayer-lock) shows
  coherence can still contribute to rigidity via a different mechanism — see
  Finding 4's coupling question. Spec ≠ immune.

## Open / next (the one genuinely live question this leaves)
Granting the field should be coherent: is a **hard pin at ~0.998** the right
target, or should the field hold a **softer high-but-floating band**? Reframed
and largely answered by Finding 4 (coherence-vs-plasticity): the coherence
*value* is likely the wrong variable — attractor *plasticity* is the thing to
measure, with the gate characterized first.
