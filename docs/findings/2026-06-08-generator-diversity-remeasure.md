# Generator diversity re-measured — is lock #1 (1-D projector) still standing?

- **Date:** 2026-06-08
- **Substrate:** live untrained generator (`agents/generator.py`), no field/loop.
- **Probe:** `tests/diagnostic/generator_diversity_probe.py`
- **Status:** active — corrects a doc-vs-live-code staleness surfaced while assessing
  Fix 2's dormancy.
- **Depends on:** 2026-06-06-multilayer-lock.md (which lists generator-1-D as lock #1),
  the `sqrt(d_model)` scale fix (ROADMAP shipped item) and `run_contrastive_bootstrap.py`.

## Question
multilayer-lock and ROADMAP list "generator 1-D projection (cos ~0.998)" as a
*standing* lock (lock #1). But the `sqrt(d_model)` + init-std scale fix shipped after
that finding. Does the live untrained generator still collapse everything to one
direction, or does it emit diversity now? This decides whether Fix 2 is dormant (no
novelty can arrive) or live (novelty arrives and the loop reconstitutes it).

## Pre-declared signatures
- RESOLVED: mean pairwise cosine of generator outputs ≪ 0.9 across inits → emits
  diversity; lock #1 resolved.
- STANDING: mean ≈ 0.99 → still a 1-D projector.
- CONTROL: the stub `spread=0.0` baseline reads cos ≈ 0.998; the live generator must
  differ from it for "resolved" to hold.

## Result (observed)
Live untrained generator, dim 64, 30 diverse sequences, 6 seeded inits:

| seed | mean pairwise cos | range |
|-----:|------------------:|-------|
| 0 | 0.497 | [−0.05, 0.81] |
| 1 | 0.534 | [−0.11, 0.85] |
| 2 | 0.587 | [+0.01, 0.89] |
| 3 | 0.551 | [+0.04, 0.91] |
| 4 | **0.364** | [−0.23, 0.75] |
| 5 | 0.685 | [+0.38, 0.90] |

**Across inits: mean 0.536, sd 0.097, range 0.36–0.69.** None is ≈ 0.998. (An earlier
*unseeded* run hit a more collinear init at 0.855 — outside this seeded band — which
is itself the lesson: the generator's weights are torch-random, so diversity is
**init-dependent**, a distribution not a single value.) Control: the stub `spread=0.0`
baseline is cos 0.998 — the live generator does not match it.

## Interpretation
**RESOLVED. Lock #1 (generator as 1-D projector, cos ~0.998) no longer holds on the
current substrate** — the `sqrt(d_model)` + init-std scale fix removed the
positional-dominance collinearity, and the live untrained generator emits genuine
directional diversity (mean pairwise cos ~0.54 at dim 64, init-dependent 0.36–0.69;
≈0.39 at dim ≥ 256). `run_contrastive_bootstrap.py`'s own note already said as much
("the untrained generator already emits diverse vectors ~0.62; contrastive is a later
refinement, not a rescue").

**This is a doc-vs-live-code staleness, not a new dynamical finding.** The earlier
"generator 1-D" reading was *correct at the time* (pre-scale-fix); it was not updated
when the fix shipped, so multilayer-lock / ROADMAP currently contradict the
shipped-scale-fix notes elsewhere in the same docs. The consistency pass (#35) could
not catch it because it only shows up when you *run the generator*.

**Consequences for the arc:**
- The `spread=0.0` (cos 0.998) baseline in `trained_generator_sim` / multilayer-lock no
  longer matches the live generator — that control reproduced a bug that is now fixed.
- **Fix 2 is NOT dormant.** Its trigger's `gnov` signal reads real novelty now, so a
  governor would be *live*, not inert. The "safe because inert" justification is void.
- The keystone RIGID migration result (2026-06-07-attractor-migration) was measured by
  *mocking* diversity into the field. It must be re-verified on the real, diverse
  generator before Fix 2 is built (next probe).

## Threats / confounds
- Runs: 6 seeded inits at dim 64 (+ an unseeded outlier at 0.855, + dim sweep showing
  ~0.39 at dim ≥ 256). The *distribution* is characterised; no single canonical number.
- This measures the generator in isolation (no field). What matters downstream is
  whether that diversity *survives the field/loop* — which is the migration re-run, not
  this probe.
- Untrained generator: diversity is from random init, not learned structure. Training
  would sharpen it (refinement, not rescue), but it is already non-collinear untrained.

## Open / next
1. **Reconcile the docs** (append-and-supersede): mark lock #1 RESOLVED in
   multilayer-lock and ROADMAP; note the `spread=0.0` baseline mismatch. (This PR.)
2. **Re-run the migration probe with the REAL generator** (not the B-mock): does the
   field still reconstitute genuine generator diversity? RIGID → the loop eats real
   diversity too, Fix 2 is needed and live; MIGRATES → the lock was partly the mock,
   rescope. This is the next [SAM CHECKPOINT].
3. Training stays downstream — a refinement, not a rescue; it does not jump ahead of #2.
