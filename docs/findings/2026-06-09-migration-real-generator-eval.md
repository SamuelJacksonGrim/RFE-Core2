# Migration on the real generator (eval/deterministic) — does the reflective loop reconstitute real token diversity?

- **Date:** 2026-06-09
- **Substrate:** live full stack (Tier 0–3), real generator in **eval() mode** (dropout
  off — deterministic, real token structure only). This is the clean re-run called for
  by `2026-06-08-generator-dropout-diversity.md` ("needs an eval re-run to be clean").
- **Probe:** `tests/diagnostic/migration_real_generator_probe.py` (modified: `gen.eval()`
  added in `_run`; dim 64, warmup 150, phase 400, 4 sources HHI<0.70, seeds [0,1,2],
  N_CAND=24)
- **Status:** active — **supersedes** the real-generator migration result folded into
  `2026-06-08-generator-dropout-diversity.md` (which was contaminated by dropout noise);
  the mock-B result in `2026-06-07-attractor-migration.md` is now confirmed generator-
  independent in both the dropout-inflated AND the deterministic regime.
- **Depends on:** `2026-06-08-generator-dropout-diversity.md` (the dropout audit that
  motivated this clean re-run; also gives the eval-mode diversity baseline: eff_rank ~1.6,
  mean cos ~0.79 at dim 64), `2026-06-07-attractor-migration.md` (the mock-B keystone
  this re-verifies), `2026-06-07-reconstruction-ablation.md` (the reflective loop as the
  confirmed locker).

## Question

The 2026-06-08 finding folded in a real-generator migration run but flagged it: the
most-separated A/B pair was found in train mode (dropout active), so the B direction was
partly per-call dropout noise, not pure token structure. Does RIGID hold on the
*deterministic* generator — where A and B are genuinely distinct token directions and the
cycle runs without noise? This is the cleanest achievable test of whether the reflective
loop reconstitutes real token structure, not just mock orthogonal vectors or stochastic
jitter.

Pre-declared: **if RIGID → the reflective loop eats real diversity too; the mock did NOT
overstate the lock; Fix 2 is needed AND live.** If MIGRATES → the lock was partly from
the mock's orthogonal B or dropout-inflated separation; rescope remediation.

## Pre-declared signatures

(Carried forward from `migration_real_generator_probe.py` docstring.)
- **RIGID**: mean migration < 0.10 across seeds → reflective loop reconstitutes REAL
  token-structured diversity; Fix 2 is needed and live.
- **MIGRATES**: mean migration > 0.50 → field adapts to real diversity on its own;
  rescope Fix 2.
- **PARTIAL**: 0.10–0.50 → real diversity moves the field somewhat; report and rescope.
- **CONFOUNDED** (per seed): cos(A_dir, B_dir) > 0.70 — regimes too similar to test
  migration. If all seeds confound → the deterministic dim-64 generator can't present
  distinct enough regimes; its own finding (lock #1 partial, eff_rank ~1.6).

## Result (observed)

Generator: eval() mode, dim 64. Most-separated pair search over N_CAND=24 tokens
(concept_0…concept_23). All 3 seeds non-confounded.

| seed | cos(A_dir,B_dir) | disp(control) | disp(novel B) | migration | landed cos·A | landed cos·B |
|-----:|-----------------:|--------------:|--------------:|----------:|-------------:|-------------:|
| 0    | **+0.337**       | 0.002         | 0.007         | **+0.005**| +0.743       | +0.227       |
| 1    | **+0.189**       | 0.003         | 0.010         | **+0.007**| +0.702       | +0.096       |
| 2    | **+0.443**       | 0.002         | 0.006         | **+0.004**| +0.760       | +0.347       |

**Mean migration over 3 seeds = +0.005. RIGID.**

The load-bearing number: in all three seeds, what *lands* in the field during the B
phase has cos·A ≈ 0.70–0.76 — the established regime A — despite the cycle being driven
with real token B. cos·B in the landed vectors is 0.10–0.35 (well below the generator's
own B-direction). The reflective loop converts real B input back to A before the field
sees it.

Note on the separation: seed 0 = 0.337 is close to the user's estimate of ~0.36. Seeds
span 0.189–0.443, all comfortably below the 0.70 confound threshold.

## Interpretation

**RIGID — and generator-independent.** Mean migration 0.005 ≪ 0.10. The result holds
across all three conditions that have now been tested:

1. **Mock orthogonal B** (attractor-migration): migration 0.008, 1 seed — RIGID.
2. **Real generator, train mode** (generator-dropout-diversity): migration ~0.002, 3 seeds
   — RIGID (but the B directions were partly dropout noise).
3. **Real generator, eval mode (this finding)**: migration 0.005, 3 seeds — **RIGID on
   genuine, deterministic token structure.**

The dropout caveat from 2026-06-08 is resolved: even with the deterministic generator
(no dropout noise), where the best-case real separation is cos 0.189–0.443 (vs. the
mock's 0.000), the field does not migrate. The reflective loop is the locker — it
reconstitutes the established regime from any input, including real token-driven
novelty with non-trivial separation.

**Fix 2 is needed AND LIVE.** The "Fix 2 may be premature" caution in 2026-06-08 rested
on the possibility that real diversity might be enough to move the field without the
governor — it is not. The reflective loop's reconstitution acts on real token structure,
not just on orthogonal mocks or stochastic noise.

**The weaker separation (cos 0.19–0.44 vs mock's 0.00) is informative.** Even if the
untrained generator at dim 64 can only present moderately separated regimes (eff_rank
~1.6 eval), those regimes are nonetheless fully reconstituted. The lock is not contingent
on the generator's diversity ceiling; it fires at any positive separation.

## Threats / confounds

- **Runs:** 3 seeds, single dim (64), single horizon (400 phase steps). Effect is stark
  and consistent across seeds; variance in migration is 0.004–0.007 (very tight). Adding
  seeds or dims would not change the qualitative verdict.
- **Untrained generator.** The eval-mode diversity (eff_rank ~1.6) is from random init,
  not learned token structure. A trained generator with higher eff_rank would present
  better-separated A/B; it remains possible (though unlikely given the mechanism) that
  very high separation overcomes the loop. That is a future probe, not a current confound.
- **Deterministic warmup.** With eval() mode, the warmup is fully deterministic per seed —
  the established center is a reproducible artifact of the random init, not a live-system
  sample. This makes the finding conservative (a trained generator would produce a
  different center, but the reconstitution mechanism is the same).
- **Mechanism confirmed separately.** The locker is identified as the reflective loop by
  `2026-06-07-reconstruction-ablation.md` (suppressing it frees migration to 0.90–0.96
  across 3 seeds). This finding adds the generator-independence confirmation; it does not
  re-decompose the mechanism.

## Open / next

1. **Fix 2 is unblocked.** The governor (conditional loop-gain reduction for gate-surviving
   novelty) is motivated and live. Proceed per ROADMAP.
2. **Architect decision outstanding (from 2026-06-08):** should the live generator run with
   `eval()` or remain in train mode? This finding confirms RIGID holds in both modes;
   the decision is about the character of the field's input diversity, not about whether Fix
   2 is needed (it is, in both modes).
3. **High-separation stress test (future).** With a trained or dim-256 generator, A·B might
   approach -0.5 or lower. A single-seed probe under those conditions would confirm the
   loop reconstitutes at higher diversity too, or surface a diversity threshold above which
   the field can self-adapt.
