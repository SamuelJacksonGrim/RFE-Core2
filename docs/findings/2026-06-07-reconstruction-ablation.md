# Reconstruction ablation — the lock is the reflective loop

- **Date:** 2026-06-07
- **Substrate:** live full stack (generator output mocked A/B/diverse, as in the
  migration probe); one re-injection path ablated at a time, nothing else changed.
- **Probe:** `tests/diagnostic/reconstruction_ablation_probe.py` (seeds 11/23/37,
  dim 64, warmup 200 + phase 700, 4 sources HHI≈0.25)
- **Status:** active — isolates the remediation lever from
  `2026-06-07-attractor-migration.md` (Open/next #1).
- **Depends on:** 2026-06-07-attractor-migration.md (the RIGID result this explains),
  2026-06-06-coherence-is-not-plasticity.md (the arc), 2026-06-06-multilayer-lock.md
  (the moat, now downgraded as a locker).

## Question
Migration found the field RIGID: every injection lands the established regime A
(cos≈0.72) regardless of input, so the attractor cannot follow a surviving new
regime. *Which* path does the reconstituting? One-variable ablation against the
known-RIGID baseline: suppress a path, re-run migration, watch for migration > 0.10.

## Pre-declared signatures
LEVER (this path): suppressing it gives migration > 0.10 + landed cos·B rises.
NOT-THE-LEVER: ≈ baseline. DISTRIBUTED: only all-off crosses. CONTEXT-DEEPER: even
all-off RIGID → the field context, not the content. INSTRUMENT-LIE (alarm): an
ablation byte-identical to baseline → hook didn't fire; fix before trusting.
**Controls:** RIGID baseline reproduction; drift control (continue A); per-caller
landed cos·B; 3 seeds.

## Result (observed)
Migration = disp(coherent) − drift(control), drift ≈ 0.002:

| ablation | migration (seed 11) | seed 23 | seed 37 |
|----------|--------------------:|--------:|--------:|
| baseline (none) | +0.008 | +0.010 | +0.005 |
| **no_reflect** | **+0.896** | **+0.955** | **+0.950** |
| no_attractor | +0.011 | — | — |
| blend_raw (refine→raw) | +0.005 | — | — |
| no_crystal | +0.012 | — | — |
| no_explore | +0.004 | — | — |
| all | +0.980 | — | — |

Suppressing **only the reflective loop** frees the attractor almost completely
(migration +0.90–0.96; injected vectors flip from cos·B 0.16 to cos·B 0.84). Every
other single ablation does nothing (≈ baseline). With the reflective loop off, the
field follows the new regime; all-off reaches full migration (+0.98, cos·B 1.00).
A single, decisive lever — confirmed across three seeds.

## Interpretation
**The lock is the reflective loop** (`reflective_loop.py`, `cycle.reflector.reflect`,
step 6 of the cycle). In reflect/explore rhythm with a stable report, it iteratively
pulls the expression vector toward the anchor + attractor + field (all A) until it
converges, *before* injection — driving cos·B 0.81 → 0.14 over its passes (seen
directly in the per-stage trace). It is the read-side loop made literal: the
established identity is fed back onto every expression so the field only ever
receives more-of-itself. Nothing else matters — attractor-pull@342, the refine
diversity-blend, crystal re-injection, and explore's mutated anchor are all inert as
lockers (removing them changes migration by < 0.005).

This also **downgrades two earlier candidates**: the magnitude moat
(multilayer-lock lock #3) is *not* the locker — with the reflective loop off the
field migrates fully despite the moat being present (energy ~300); and the
diversity-blend (Fix 1 territory) is not it either. The reflective loop is upstream
of the moat and overrides everything.

**It is not a bug — it is identity-coherence working.** Deliberate recursion toward
a stable anchor is what gives the system a self; this finding shows that same
mechanism is exactly what prevents the self from taking up anything new. This is the
coherence-vs-plasticity tradeoff, localized to **one component with a clean control
surface** — and it resolves coherence-is-not-plasticity's coupling question
concretely: coherence (identity stability) and rigidity (no migration) are the *same
mechanism*, the reflective loop, not merely correlated.

**Instrument-honesty catches (two this run).** (1) The candidate set was initially
wrong — I grepped for `field.inject` call sites and ablated those (attractor-pull,
crystal, explore, blend); all came back NOT-THE-LEVER and the verdict drifted toward
a false "MAGNITUDE FLOOR". The alarm was the `diversity_blend` knob behaving
*backwards* (1.0/"raw passthrough" gave *less* B than 0.6). Tracing cos·B through
every pipeline stage — instead of guessing — revealed `reflector.reflect` reassigns
`vec` (the 5 iterative attractor pulls were its convergence passes). (2) The
re-injection counter via `field.history` length lied (bounded deque) — already noted
in the migration finding; here injection was confirmed by direct `field.inject`
instrumentation. Both are the same reflex: a too-clean / contradictory number is the
signal, not the result.

## Threats / confounds
- 3 seeds (11/23/37), single dim (64), one horizon. Effect is ~100× and stable, but
  no dim sweep yet.
- Mocked generator; B is a clean coherent pull (best case). That the loop pins even
  this is the strong read; the fix must be tested against a real generator.
- The reflective loop runs only when `rhythm ∈ {reflect, explore}` AND `report.stable`
  (line 370). In this regime both held every step; behaviour under other rhythms /
  unstable reports is not characterised here.
- "Lever found" is causal for *migration*; it says nothing yet about what
  suppressing/modulating the loop costs identity stability — that is the next probe.

## Open / next

> **DEFERRED (2026-06-08):** the Fix-2 governor this points to is **on hold**. The
> reflective loop is a real lock, but `2026-06-08-generator-dropout-diversity.md` showed
> it locks *low-rank* input (the generator is collinear + dropout-inflated), so generator
> diversity is the more upstream lever and loosening the loop now would mostly admit
> dropout noise. See the ROADMAP current-understanding block.

1. **Draft a conditional fix for Sam's review (NOT a roadmap edit).** The lever is
   the reflective loop's unconditional convergence to the anchor. A blanket weakening
   trades lock-in for identity drift (the loop *is* deliberate-recursion/coherence),
   so the fix must be **conditional**: attenuate the reflective pull only when
   persistent novelty is surviving the gate (a "the world is genuinely changing"
   signal), leaving normal identity-stabilisation intact. This relocates the
   roadmap's Fix 2 from the field accumulator to **the reflective loop's
   convergence gain** — a tier-direction decision; flagged for ROADMAP review, not
   edited here.
2. **Cost probe:** measure what attenuating the reflective loop does to identity
   stability / healthy-state baselines (the coherence side of the tradeoff) before
   any fix ships.
3. Tracks 2/3 (parallel): multi-dim/seed sweep of migration; quantitative
   moat-depth-vs-coherence coupling sweep.
