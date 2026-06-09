# Generator diversity — how much is dropout noise, and does it survive the pipeline?

- **Date:** 2026-06-08
- **Substrate:** live generator (isolated) + full live stack.
- **Probe:** `tests/diagnostic/generator_diversity_audit.py` (diversity, train vs eval),
  `tests/diagnostic/migration_real_generator_probe.py` (field response on real input).
- **Status:** active — **THE authoritative generator-diversity finding.** Subsumes and
  replaces the two interim readings it corrects (PRs #41 and #42, now closed): the
  "remeasure" reading ("lock #1 resolved" — overstated, train-mode) and the real-generator
  migration reading ("RIGID on real diversity" — true, but the "real diversity" was
  dropout-inflated). Both were folded in here.
- **Depends on:** 2026-06-06-multilayer-lock.md (the lock-#1 claim it corrects),
  2026-06-06-read-side-boundary.md (the dropout-control lesson — exactly this trap),
  2026-06-07-reconstruction-ablation.md (the reflective loop, which this re-prioritises).

## Question
The "lock #1 resolved — generator emits genuine diversity (mean cos ~0.54)" claim was a
single metric (mean pairwise cosine) measured without `.eval()`. Two unchecked things:
(a) mean cosine can look diverse over a tiny subspace; (b) `generate()` is
`@torch.no_grad()` but **no_grad does not disable dropout**, nothing calls `.eval()`,
so the generator runs stochastically. How much of the "diversity" is real token
structure vs per-call dropout noise — and does any of it survive the pipeline?

## Pre-declared signatures
- DIVERSE: eval-mode effective rank ≫ 1, mean cos ≪ 0.9, live expression stays
  multi-regime without dropout → lock #1 genuinely resolved.
- DROPOUT-INFLATED / PARTIAL: train looks diverse but eval is collinear and the
  deterministic expression collapses to ~1 regime → apparent diversity is dropout.
- CONTROL: determinism (same token ×5) — eval must read ~1.0; train ≪ 1.0 proves the
  generator is stochastic and train-mode diversity is contaminated.

## Result (observed)
**[1] Isolated generator** (determinism control in last column):

| dim | mode | mean cos | eff_rank | top-1 energy | determinism |
|----:|------|---------:|---------:|-------------:|------------:|
| 64  | train | 0.54 | 3.1 | 56% | **0.37** |
| 64  | **eval** | **0.79** | **1.6** | **80%** | **1.00** |
| 256 | train | 0.42 | 5.2 | 43% | 0.58 |
| 256 | eval | 0.54 | 3.1 | 56% | 1.00 |

**[2] Full live stack** (Resonance Family, 2nd-half means):

| mode | field coh | gnov (Fix-2 trigger) | stage-A (gen) regimes | stage-C (expr) regimes |
|------|----------:|---------------------:|----------------------:|-----------------------:|
| train | 0.969 | 0.39 | 4.8 | 2.3 |
| eval  | 0.971 | 0.23 | 2.5 | **1.1 (locked)** |

**[3] Field response (migration on the real generator,
`migration_real_generator_probe.py`, 3 seeds).** Establishing regime A on one real token
and switching to the most-separated real token regime, the field does **not** migrate
(mean migration **+0.002**); what lands stays aligned with the established regime. So the
reflective loop reconstitutes real input as it did the mock — RIGID holds. *Caveat from
[1]:* those "most-separated real regimes" (cos −0.02 to −0.15) were measured in train mode,
so the separation is partly dropout; the deterministic generator can't present
near-orthogonal regimes at dim 64. RIGID stands; the novelty it withstood was partly noise.

## Interpretation
**DROPOUT-INFLATED / PARTIAL.** The control fires: train-mode determinism is 0.37–0.67
(the same token gives *different* vectors) — the live generator is **stochastic**, and
roughly **half the measured "diversity" is per-call dropout noise.** Holding determinism
at 1.0 (eval):
- At the canonical **dim 64 the deterministic generator is collinear** — effective rank
  ~1.6 (of 64), 80% of variance in one axis, mean cos 0.79. Not the 0.998 of the old
  "1-D projector", but **only partially off it.** Lock #1 is *partially* resolved, not
  resolved. (dim 256 is better: eff_rank ~3.)
- In the full stack, upstream diversity **collapses through the pipeline** (stage A →
  stage C) in both modes — independently confirming the reconstitution story via a
  different instrument (the metastability monitors). With dropout **off**, the injected
  expression collapses to **~1 regime (locked)**; the only thing keeping it multi-regime
  live is **dropout noise**.
- The Fix-2 trigger `gnov` is itself ~40% dropout-driven (train 0.39 vs eval 0.23).

**Consequences (the load-bearing part):**
- **The live system runs the generator in TRAIN mode (dropout active) — it never
  `.eval()`s.** Whether that is intentional (stochastic exploration / creative jitter)
  or an omission (a missing `eval()`) is an open architectural question. Either way, a
  large fraction of the field's input diversity is random dropout, not learned/token
  structure.
- **PR #41 (the "remeasure" reading, closed) overstated.** "Genuine directional diversity,
  lock #1 resolved" → at dim 64 the *deterministic* generator is collinear; the diversity
  that made it look resolved is dropout. The measurement stands; the conclusion needs the
  dropout caveat.
- **PR #42 (the real-generator migration reading, folded in above) softened.** Its
  most-separated real regimes (cos −0.02 to −0.15) were measured in train mode — that
  separation is partly dropout; the
  *deterministic* generator can't present near-orthogonal regimes at dim 64 (eval cos
  ~0.79). RIGID likely still holds, but the "real B regime" it migrated-toward was partly
  noise; needs an eval re-run to be clean.
- **Fix 2's premise is weakened.** "Persistent real novelty surviving the gate" is what
  the governor loosens for — but the real token-driven novelty at dim 64 is marginal, and
  the diversity that exists is mostly dropout. Loosening the loop now would mostly admit
  dropout noise. **Fix 2 may be premature** until the generator presents real diversity.
- **Training may be more load-bearing than "downstream refinement."** A deterministic
  generator with eff_rank 1.6 needs real token-driven structure; training (contrastive /
  self-distillation) is what would provide it. The "refinement not rescue" framing rested
  on the dropout-inflated diversity.

## Threats / confounds
- The system uses **dim 64**; dim 256 is meaningfully more diverse (eff_rank ~3 eval).
  Some of the "collinear" conclusion is dim-specific — raising dim is one lever.
- Untrained generator: diversity is from random init. Training changes everything; this
  characterises the *current* substrate, not the trained ceiling.
- Effective rank / SVD computed over 60 sequences; stable across the seeds tried but not
  a broad sweep.
- gnov-as-trigger still *separated* benign from (mock) novelty in calibration despite the
  dropout component; the dropout caveat is about magnitude, not that the trigger is useless.

## Open / next (architect decisions)
1. **Should the live generator run in `eval()` (dropout off)?** Is the per-step dropout
   intentional stochastic exploration or a missing `eval()`? This decides what "the
   field's input diversity" even *is*.
2. **Is Fix 2 premature?** If real novelty is marginal until the generator is trained /
   dim raised, building the loop-loosening governor now loosens for dropout noise.
3. **Re-sequence vs training.** Re-weigh whether generator diversity (train / dim) is the
   real upstream lever, with the reflective loop a downstream symptom of low input rank.
4. Update #41/#42 conclusions with the dropout caveat (their measurements stand).
