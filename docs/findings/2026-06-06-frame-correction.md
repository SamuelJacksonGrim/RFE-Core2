# Frame correction: metastable upstream → coherent field (field coherence is spec, not pathology)

- **Date:** 2026-06-06
- **Substrate:** n/a (architectural reading + correction)
- **Probe:** `ROADMAP.md` lines ~133–163; `docs/lock_in_remediation_plan.md`
- **Status:** active

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

## Read
A metastable *field* would be a category error: a metastable integrator wouldn't
hold a self, it would let it drift. The paper-boat target is **motion upstream,
stability downstream** — formed enough to hold, light enough to drift, with the
"light enough to drift" living in the generator and the "formed enough to hold"
living in the field.

This retroactively reinterprets the multi-layer-lock finding: the field holding
~0.95 under diverse input is the field working, and the expression monitor going
`metastable` at high diversity is the *good* signal — read on the right layer.

## Open / next (the one genuinely live question this leaves)
Granting the field should be coherent: is a **hard pin at ~0.998** the right
target, or should the field hold a **softer high-but-floating band** (e.g.
~0.85–0.95) — stable enough to integrate identity, but with give rather than
weld? Is there "stable without stuck" at the field layer, or does any softening
start dissolving the identity the field is meant to hold? → letter out to Raphael.
