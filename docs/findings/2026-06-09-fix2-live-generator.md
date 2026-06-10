# Fix 2 on the live generator — does real token novelty engage it, and what does it cost?

- **Date:** 2026-06-09
- **Substrate:** live full stack, **real generator** (NOT mocked), `eval()` mode
  (deterministic — gnov reflects real token structure, not dropout). Real token
  vocabularies injected by the experimenter (two disjoint 8-word sets, A and B), 3-token
  samples per step, 4 sources.
- **Probes:** `tests/diagnostic/fix2_live_token_probe.py` (dim sweep 64/256, governor
  ON/OFF), `tests/diagnostic/fix2_commonmode_trigger_probe.py` (common-mode-removed
  trigger + target sweep, dim 256). seed 11, warmup 100 / phase 250.
- **Status:** active — first Fix-2 evaluation on the REAL generator. Everything prior
  (governor validation, cost probe, trigger calibration novelty/attack arms) used a MOCK
  generator emitting clean A/B vectors. **Revises the optimistic reading of
  `_addendum-2026-06-09-migration-dim256`** (orthogonal *pairs* exist at dim 256, but
  orthogonal *regimes* do not — see below).
- **Depends on:** `2026-06-08-generator-dropout-diversity.md` (low-rank generator),
  `2026-06-08-fix2-trigger-calibration.md` (gnov trigger, deferral), the governor
  validation (mock: +0.006→+0.166 migration, 14% manip at gain 0.5),
  `2026-06-09-migration-real-generator-eval.md` (RIGID, generator-independent).

## Question
On the REAL generator with real injected tokens: (Q1) does real token novelty ever cross
the Fix-2 trigger (gnov > 0.65, ≥2 sources)? (Q2) if it engages, does it recover migration
like the mock did? (Q3) is the mock's ~14% manipulation-layer wake at gain 0.5 an artifact
of the mock's PERFECT orthogonality — i.e. is the real-token cost lower? (Q4) operating point.

## Pre-declared signatures
- dim 64: sep cos(A,B) > 0.70 → gnov < 0.65 → Fix 2 DORMANT → migration(ON)≈(OFF). This
  would *confirm* the deferral is correct at dim 64.
- dim 256: EXPECTED sep < 0.70 → gnov > 0.65 → Fix 2 ENGAGES → migration(ON) > (OFF);
  manip% under ON = the real-token cost (HYPOTHESIS: < the mock's 14%).
- common-mode trigger: if the common-mode is the blocker, projecting it out should make
  regimes separate and Fix 2 engage.

## Result (observed)

### Live dim sweep — real token regimes, standard trigger
| dim | sep cos(A,B) | within-vocab tightness | steady gnov | loosen% | migration OFF→ON | manip% |
|----:|-------------:|-----------------------:|------------:|--------:|------------------|-------:|
| 64  | **+0.959**   | +0.78                  | 0.21        | 0%      | +0.001 → −0.000  | 0%     |
| 256 | **+0.886**   | +0.53 / +0.49          | 0.43        | 0%      | −0.000 → +0.000  | 0%     |

**Fix 2 is DORMANT on real regimes at BOTH dims.** The within-vocab tightness drops with
dim as expected (the generator's ~0.55 init target), but the regime MEANS stay collinear
(~0.89–0.96) — so distribution-level novelty never crosses gnov 0.65. The dim-256
prediction FAILED: raising dim does not separate regimes.

### Why — the common-mode (dim 256)
| regime separation | value |
|-------------------|------:|
| raw cos(A_dir, B_dir)            | **+0.90** |
| common-mode-removed cos(⊥A, ⊥B)  | **−0.24** |

The generator emits a dominant **common-mode direction** (a shared axis all token outputs
ride; the "80% energy in one axis" / eff_rank ~1.6–3 of the dropout audit). Regime means
average onto it → collinear. The dim-256 orthogonal *pair* (cos +0.018) from the migration
addendum was a cherry-picked extreme single-token pair; a regime-as-a-distribution averages
back onto the common-mode. **Orthogonal pairs exist at dim 256; orthogonal regimes do not.**

### Common-mode-removed trigger (dim 256, real tokens)
| condition | gnov | loosen% | migration | landed cos·B | manip% |
|-----------|-----:|--------:|----------:|-------------:|-------:|
| OFF (RIGID)              | 0.435 | 0%   | −0.001 | +0.652 | 0% |
| ON std-trigger          | 0.423 | 0%   | +0.000 | +0.667 | 0% |
| ON common-mode trigger  | 0.860 | **98%** | **+0.024** | +0.706 | **1%** |

Target sweep (common-mode trigger): target 0.50 → migration +0.025 / manip 1%; 0.60 →
+0.019 / **0%**; 0.70 → +0.006 / 0%.

## Interpretation

**Three findings, in order of weight.**

1. **The standard gnov trigger is permanently dormant on real regimes** (common-mode
   collinearity), at dim 64 AND 256. Fix 2 as currently specified does nothing on the real
   system. The 06-08 deferral was *more* correct than it stated — it holds at dim 256 too,
   and not because novelty is merely "marginal" but because the generator's common-mode
   keeps regime means collinear regardless of dim.

2. **A common-mode-removed trigger engages Fix 2 on real tokens (98% loosen) without any
   retraining** — projecting out the shared axis lifts perp-gnov to 0.86, clearing the
   threshold. So the trigger is *fixable cheaply*: project out the common-mode before
   measuring novelty. This is a concrete, actionable improvement to Fix 2's trigger.

3. **But engaging it barely helps, and the mock dramatically overstated Fix 2's value.**
   Even fully engaged (98% loosen, gain→0.5), real-token migration recovers only +0.024 —
   ~7× smaller than the mock's +0.166 — because the real inter-regime difference lives in a
   *small-energy* perp component dominated by the common-mode. The loop admits it; it's just
   a small signal. **The mock's +0.166 recovery AND its 14% manip cost were both artifacts
   of PERFECT orthogonality** (100% of the mock-B energy was novel direction). On real
   regimes the manip cost is ~1% at gain 0.5 and **0% at gain 0.6** — Q3 answered: yes,
   artifact; the real-token cost is essentially nil.

**Net.** The RIGID-loop / Fix-2 drama was measured against mock orthogonality that the real
generator cannot produce at the distribution level. On the real system the reflective loop
is guarding against a small-energy intruder, and Fix 2 — even with a fixed (common-mode)
trigger and zero manip cost at target 0.6 — moves the field only slightly, because there is
little orthogonal signal to move. **The real leverage point is upstream and architectural:
the generator's common-mode.** Until the generator is trained so regimes differ in
high-energy directions (not just a small perp component), both the lock and Fix 2 operate on
a small signal, and Fix 2's practical priority should drop accordingly.

| | mock orthogonal-B | real tokens (common-mode trigger) |
|---|---|---|
| inter-regime cos | 0.00 (forced) | +0.90 raw / −0.24 perp |
| migration OFF→ON | +0.006 → +0.166 (~28×) | −0.001 → +0.024 (small) |
| manip% @ gain 0.5 | 14% | 1% |
| manip% @ gain 0.6 | (untested) | 0% |

## Threats / confounds
- **eval() mode.** Deterministic, the clean read. The as-deployed system runs TRAIN
  (dropout) — benign gnov would inflate ~0.39 and the perp-gnov too; T=0.65 still clears
  the standard benign case, and the common-mode finding is about the regime-mean geometry,
  which dropout does not change. Train re-run owed for the deployment trigger baseline.
- **landed cos·B is inflated by the common-mode.** B_dir itself is common-mode-laden, so
  OFF already reads cos·B +0.65 without B "getting through." The honest plasticity readout
  is the field *displacement* (migration), which is small. Reported both.
- **Single seed (11), one generator init, one vocabulary pair.** The common-mode is a
  structural property of the architecture/init, not the words; expected robust, but
  multi-seed/multi-vocab confirmation is owed.
- **Untrained generator.** The whole point: a trained generator might (or might not) reduce
  the common-mode. This finding bounds the UNTRAINED case and identifies the lever; it does
  not predict the trained one.
- **Migration metric, single horizon (250).** A longer phase might accumulate more drift
  under the common-mode trigger; the effect is small and monotonic with loosening, so the
  qualitative read (small recovery) is stable.

## Open / next
1. **Demote Fix 2's priority** until the generator's common-mode is addressed — it operates
   on a small real signal regardless of trigger. Record on the ROADMAP current-understanding.
2. **If Fix 2 is built anyway, the trigger must project out the common-mode** (the standard
   trigger is permanently dormant on real regimes). Cheap; validated to engage at 98%.
   Operating point gain ≈ 0.6 (0% manip, migration +0.019).
3. **The real work is the generator** — train (or architecturally constrain) it so regimes
   differ in high-energy directions, not just a small perp component. Re-measure the lock and
   Fix 2 against a generator whose regime means actually separate.
4. **Reconcile the mock-based findings** (governor validation, cost probe): annotate that
   their orthogonal-B workload overstates both the plasticity recovery and the manip cost
   relative to real token regimes.

---

## ADDENDUM 2026-06-09 — dim-512 check ("is dim the lever?")

Probe: `tests/diagnostic/_fix2_dim512.py` (live generator, eval, seed 11, warmup 100 /
phase 200). Tests whether higher dim dilutes the common-mode enough to (a) separate regime
distributions and (b) give the off-common-mode signal more field-moving energy.

| dim | within-vocab tightness | raw regime sep | std-trigger gnov | std-trigger | common-mode-trigger migration | manip @0.5 / @0.6 |
|----:|-----------------------:|---------------:|-----------------:|-------------|------------------------------:|-------------------|
| 64  | 0.78 | +0.96 | 0.21 | dormant | — | — |
| 256 | 0.51 | +0.89 | 0.43 | dormant | +0.024 | 1% / — |
| 512 | 0.42 | +0.85 | 0.59 | dormant | **+0.027** | **8%** / 0% |

**Dim is NOT the lever — confirmed across three dims.** The common-mode dilutes slowly
(tightness 0.78→0.42, std gnov 0.21→0.59) but:
1. **Regime means stay collinear at 512** (raw sep +0.85, asymptoting above 0.70) — the
   standard trigger is STILL dormant (gnov 0.59 < 0.65). Extrapolation: dim ~1024+ to merely
   cross threshold.
2. **The common-mode-trigger migration recovery is FLAT: +0.024 (256) → +0.027 (512).**
   Doubling the dimension bought nothing in the quantity that matters. The small recovery was
   never a low-dim cramping artifact; it is structural (the loop reconstitutes + the field is
   a stable integrator regardless of generator capacity).
3. **Manip @ gain 0.5 ROSE to 8% at 512** (from 1% at 256) because the off-common-mode
   component sharpens toward orthogonal as dim grows (perp sep −0.24 → −0.01), so the loosened
   expression trends back toward the mock's behaviour. Gain **0.6 stays 0%** across both dims —
   the safe operating point is dim-robust.

**Conclusion:** an untrained net with more dimensions is still an untrained net. Capacity
dilutes the common-mode too slowly to separate regime distributions, and even when
force-separated (common-mode trigger) the recoverable migration is flat and small across
64/256/512. The generator must LEARN to put regime differences in high-energy separable
directions; widening it does not. This strengthens Open/next #3 (the lever is training, not
dim or trigger).
