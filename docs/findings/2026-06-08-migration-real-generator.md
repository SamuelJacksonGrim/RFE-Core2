# Migration on the real generator — does the field reconstitute real diversity?

- **Date:** 2026-06-08
- **Substrate:** live full stack (loop intact, NO governor), real generator (not mocked).
- **Probe:** `tests/diagnostic/migration_real_generator_probe.py` (seeds 0/1/2)
- **Status:** active — re-verifies the keystone migration result on the real generator
  after lock #1 was found resolved.
- **Depends on:** 2026-06-07-attractor-migration.md (the RIGID result this re-tests),
  2026-06-07-reconstruction-ablation.md (the reflective loop as the lock),
  2026-06-08-generator-diversity-remeasure.md (lock #1 resolved → real diversity exists).

## Question
The keystone RIGID migration result was measured by **mocking** an orthogonal new
regime B into the field. Lock #1 is resolved — the live generator emits real
directional diversity — so the honest test is: does the field still reconstitute
**real** generator diversity, or did the orthogonal mock overstate the lock?

## Pre-declared signatures
- RIGID: migration < 0.10 across seeds → the loop reconstitutes real diversity too;
  the mock did not overstate; Fix 2 is needed AND live.
- MIGRATES: migration > 0.50 → field adapts to real diversity on its own → rescope.
- PARTIAL: 0.10–0.50 → real diversity moves the field somewhat → rescope.
- CONFOUNDED (per seed): cos(A_dir, B_dir) > 0.70 (generator can't present two distinct
  regimes this init) → skip that seed.

**Method:** per seed, search the vocab for the MOST-SEPARATED real token pair
(tokA→A_dir, tokB→B_dir); establish regime A on tokA (multi-source, HHI<0.70, loop
intact), switch to tokB; migration = disp(novel B) − disp(continue-A control); attractor
center = unit(field.field); `field.inject` instrumented for what lands.

## Result (observed)
| seed | cos(A_dir, B_dir) | disp(control) | disp(novel B) | migration | landed cos·A / cos·B |
|-----:|------------------:|--------------:|--------------:|----------:|----------------------|
| 0 | −0.023 | 0.002 | 0.005 | **+0.002** | 0.329 / 0.186 |
| 1 | −0.097 | 0.003 | 0.006 | **+0.003** | 0.528 / 0.210 |
| 2 | −0.145 | 0.003 | 0.004 | **+0.001** | 0.408 / 0.436 |

**Mean migration = +0.002 (3/3 non-confounded).** The most-separated real token pairs
are cos −0.02 to −0.15 — essentially orthogonal, as novel as the mock's B — so the real
generator readily presents a genuinely distinct B regime (not confounded). Under that
real B, what lands is more aligned with the **established** regime A (cos·A 0.33–0.53)
than with the incoming B (0.19–0.44), even though the generator emits B at cos·B≈1.

## Interpretation
**RIGID confirmed on the real generator.** The reflective loop reconstitutes REAL
generator diversity exactly as it reconstituted the orthogonal mock — the field does
not migrate (+0.002, vs +0.008 for the mock; if anything more rigid). The mock did
**not** overstate the lock; the keystone result stands on real input. The
attractor-migration finding's "necessary-not-sufficient / mock is best-case" caveat is
now discharged on the migration side: real, near-orthogonal generator regimes move the
field no more than the mock did.

**Consequence for Fix 2:** it is **needed and LIVE, not dormant.** The earlier dormancy
argument rested on the (now-falsified) 1-D-generator premise; with real diversity
arriving and being reconstituted, a governor would actually fire. So Fix 2 proceeds —
built live, with the cost-probe rails exercised against the real generator and a
liveness guard so a future refactor can't silently neuter it.

## Threats / confounds
- Runs: 3 seeds, dim 64, single horizon (warmup 150 / phase 400). Effect is stark and
  consistent (all ≈ 0), so robust, but not a wide sweep.
- Single-token regimes (tokA / tokB) give the cleanest, most-separated real directions —
  best case for migration. A multi-token real "regime" would be *less* separated
  (averaging), so no more migratory; single-token is the favourable bound.
- Loop intact, no governor — this re-verifies the EXISTING system (the baseline the
  governor must change), not the fix.
- The probe asserts nothing about whether the governor *will* unlock migration — only
  that the lock is real on real input. That is the governor's job to demonstrate next.

## Open / next
1. **Build Fix 2 live** (governor: gnov W=10/T≈0.65/≥2-source primary, #1 confirmation,
   rails manip-rate + attractor-count + gain floor 0.45) — re-verify the cost-probe
   band/cliff and the migration-unlock on the **real** generator, not the mock.
2. **Liveness guard:** assert the trigger fires on the real-diversity counterfactual so
   a future change can't silently render Fix 2 inert.
3. Multi-seed/dim breadth on this re-verification once the governor exists.
