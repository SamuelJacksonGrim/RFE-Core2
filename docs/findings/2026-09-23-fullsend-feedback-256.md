# Full-send at dim 256: participation 82 still settles to one field groove

- **Date:** 2026-09-23
- **Branch:** `experiment/full-send-feedback-256`, cut from `experiment/full-send-feedback` (`b08e067`). Not merged, not pushed.
- **Probe:** `tests/diagnostic/sidecar/fullsend_feedback_256_probe.py`. Raw summary: `logs/2026-09-23-fullsend-feedback-256/summary.json`.
- **Substrate:** baseline is a fresh dim-128 stack (the 5-rhythm weights do not load at 256). Full-send is a fresh dim-256 stack. Eval mode, canonical Resonance-Family band, seeds 42 / 7 / 11, 500 workload steps. CPU. No live mind, no RM, no ports.
- **Status:** measured. **Do not promote.** Does not change the 128 conclusion. Does not reopen the field-lock ruling.

## Question

The dim-128 full-send (`2026-09-23-fullsend-feedback.md`) put token feedback in front of a participation-47.8 field and both arms stayed RIGID. One groove, occupancy 1.0. The diagnosis was that `arbitrate()` collapses the cloud through a three-token door, so the shared coordinate system is the blocker, not the encoder. This is that run with one variable changed: the full-send encoder is the dim-256 completion field, participation 81.9. Does the richer field break the lock, or does the seam still bottleneck it?

## Which checkpoint, and why it is not `*_256_resid.pt`

The brief named `generator_weights_completion_256_resid.pt` and said the field participation is ~82. Those are different files. Measured on the live holdout, `Generator.forward`, before any cell, same instrument as the 128 probe:

| file | flag | holdout field PR | eff | what it is |
|---|---|---|---|---|
| `generator_weights_5rhythm.pt` | off | **3.423** | 1.85 | baseline, dim 128 |
| `generator_weights_completion_128_emb.pt` | on | **47.806** | 19.3 | the 128 full-send arm |
| `generator_weights_completion_256_emb.pt` | on | **81.917** | 31.85 | this arm |
| `generator_weights_completion_256_resid.pt` | on | **73.531** | 31.69 | named in the brief, not loaded |

The 128 arm was the embeddings-only checkpoint with `embedding_residual` set at encode. The flag is not in the state dict. The matching 256 file is `generator_weights_completion_256_emb.pt` with the flag on. That is the published 81.9 field, and it is the richest completion encoder on disk (mouth recall@8 0.691). The `*_256_resid.pt` file trained the transformer behind the residual. Its output is 73.5, its stack participation is ~0.7, and its mouth is worse (0.657). Loading it would have changed the training recipe as well as the width, and it would not have been the ~82 field the question names.

The probe aborts the full-send arm outside participation `[78, 88]`. 81.917 passed. 73.531 would not have. The resid file was measured and recorded. It was not loaded into a cell.

`completion_head_256_emb.pt` is the mouth. The 128 probe did not load a head, and neither does this. Hashed only (`244ef932…`). Nothing writes a 256-d vector through governance.

## What was actually on

Same seam as June and as the 128 probe. `LAESidecar` / `PLESidecar` offers re-enter as `cycle.step(..., source_id="lae_engine"|"ple_engine")`.

| | baseline | full-send |
|---|---|---|
| weights | `generator_weights_5rhythm.pt` | `generator_weights_completion_256_emb.pt` |
| stack dim | 128 | **256** |
| `embedding_residual` | off | **on** |
| holdout field participation | **3.423** | **81.917** |
| rupture_on_lock | off | on (fires: **0 / 0 / 0**) |
| novelty attenuation (`--free`) | off | on, ceiling left at **0.30** |
| boredom threshold | 0.50 | 0.25 |

Levers, same reasons as the 128 run. Rupture's trigger is a locked generator stream. This host's generator read `structureless` on the full-send arm and `metastable` on the baseline, never `locked`, so the lever was armed and never fired. Attenuation was in the path: the late rhythm is `reflect` on every cell. The ceiling was not raised. Boredom was already biting on the baseline (peak 0.97), so 0.50 was not a silent default. Not turned on: corpus pretrain, the dream channel, Fix 0-B.

## Gate

Unchanged from the 128 probe. Declared in the module before this run.

Boot center = field direction at the first step with workload index ≥ 50. Late window = workload index ≥ 200. One groove = every late field vector within cosine 0.90 of one medoid, and that medoid holds ≥ 15% of the window.

- **FRAGMENTED** — late identity mean < 0.95, or more than 2% of steps have identity < 0.90, or late coherence mean < 0.80.
- **METASTABLE** — not fragmented, and two or more grooves (or no groove holds 15% while three or more raw modes exist).
- **RIGID** — otherwise. `RESTATED` if that groove still sits on the boot center (cosine ≥ 0.90), else `NEW_GROOVE`.

## Result

Every cell is **RIGID / NEW_GROOVE**. Late occupancy is 1.0 and the raw mode count is 1 in all six cells. Identity never crossed under 0.95 (fraction below 0.90 is 0). No cell is fragmented. No cell hovers.

`NEW_GROOVE` means the settled reflect direction is not the step-50 vector. Step 50 is inside the dream transient. The late window is `reflect` only, on every seed, both arms. One post-boot rhythm transition: dream → reflect. Then the field sits.

| arm | seed | disp | cos to step 50 | id min | id late | coh late | grooves | attractors | crystals | gen regimes | expr regimes | LAE fires | rejects |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 42 | 0.141 | 0.859 | 0.973 | 0.999 | 0.966 | 1 | 2 | 1 | 4 | 4 | 426 | 28 |
| baseline | 7 | 0.145 | 0.855 | 0.972 | 0.999 | 0.965 | 1 | 3 | 3 | 4 | 4 | 388 | 36 |
| baseline | 11 | 0.129 | 0.871 | 0.971 | 0.999 | 0.969 | 1 | 3 | 2 | 5 | 4 | 395 | 24 |
| full-send 256 | 42 | 0.212 | 0.788 | 0.972 | 0.994 | 0.884 | 1 | 19 | 16 | 17 | 17 | 681 | 114 |
| full-send 256 | 7 | 0.213 | 0.787 | 0.976 | 0.995 | 0.889 | 1 | 19 | 16 | 16 | 16 | 865 | 88 |
| full-send 256 | 11 | 0.201 | 0.799 | 0.973 | 0.994 | 0.889 | 1 | 18 | 13 | 15 | 15 | 635 | 104 |

Groove occupancy is 1.0 in every cell. The 256 displacement spread across seeds is 0.012. The arm gap versus this run's baseline is the same direction on 3/3 seeds.

## 256 beside the 128 run

The 128 numbers are the published means from `2026-09-23-fullsend-feedback.md`. This process re-ran the baseline; it landed on the same verdict, mean displacement 0.138 against the published 0.140. The comparison column for the encoder is the published 128 full-send, not a re-fit.

| | baseline (128 run) | full-send 128 (PR 47.8) | full-send 256 (PR 81.9) |
|---|---|---|---|
| Verdict, 3/3 seeds | **RIGID** | **RIGID** | **RIGID** |
| Late field grooves | 1 (occupancy 1.0) | 1 (occupancy 1.0) | 1 (occupancy 1.0) |
| Displacement from step 50 | 0.140 | 0.233 | **0.209** |
| Cosine of that groove to step 50 | 0.860 | 0.767 | **0.791** |
| Identity min / late mean | 0.972 / 0.999 | 0.974 / 0.994 | **0.974 / 0.994** |
| Late coherence | 0.967 | 0.891 | **0.887** |
| Substrate attractors | 2.7 | 15.0 | **18.7** |
| Generator regimes | 4–5 | 16–17 | **15–17** |
| Expression regimes | 4 | 16–17 | **15–17** |
| Post-boot rhythm transitions | 1 (dream → reflect, then stay) | 1 (same) | 1 (same) |

Going from participation 48 to participation 82 did not open a second basin. It did not even move the field farther than the 128 full-send already had. Displacement is slightly smaller (0.209 vs 0.233) and the settled direction sits slightly closer to the dream snapshot (0.791 vs 0.767). Late coherence and late identity are the same to three digits (0.887 vs 0.891, 0.994 vs 0.994). Attractors are a little fuller (18–19 vs 11–18) and crystals are a little fuller (13–16 vs 6–12). Regime counts are the same band. That is the same richer cloud being integrated into the same kind of single field direction.

The stream monitor's label did change. On the 128 full-send the generator read `metastable` (mean score 0.418). Here it reads `structureless` (0.376 / 0.382 / 0.395), with expression equal to generator. That label is the stream's own alignment, not the field gate. The field gate's coherence stays at 0.89 and its mode count stays at 1. `structureless` is not FRAGMENTED.

## Verdict

**The richer field does not change the verdict. The seam is still the blocker.**

Participation 82 under the same three-token door (`liminal` / `paradox` plus a word or two, through `arbitrate()`) is still one reflect groove. Dimensionality was the variable that could have falsified the 128 diagnosis. It did not. A legible manifold, at the richest completion encoder on disk, does not become a second basin when the only write back into the cycle is a token.

What the encoder keeps changing, and only upstream, is the same thing the 128 run already showed. More stream regimes, a fuller attractor store, a settled direction farther from the dream snapshot than the collapsed encoder sits, lower late coherence, identity unmoved. Width from 128 to 256 does not add another step on that list.

## Honest scope

This isolates encoder dimension. It does not isolate a shared field write, because that write does not exist. The engines still feed tokens through governance. There is no 128-d write and no 256-d write.

It is also still a cold 500-step snapshot. E8-EEA emotion cannot emerge here, because nothing accumulates across a life of the mind. The manifold and the Grimoire are not in the loop. A null on this probe does not close the dynamic question or the federated question. It closes one question: encoder dimension alone, cold, does not break the single groove.

If this arm had gone METASTABLE, dimensionality would have mattered after all and the 128 null would have been a width artifact. It went RIGID. The shared coordinate system is the build, not a wider encoder.

## Does this reopen "the field lock is identity by design"?

No. Identity held (no step under 0.95, late mean 0.994, anchor gap 0.02–0.04) while the field occupied one groove. A METASTABLE field with identity held would have been the reason to reopen that ruling. The field did not hover. The ruling stands, now at participation 82 as well as at 48 and at 3.4.

## Threats

- The named `*_256_resid.pt` file was not the arm. Its participation is 73.5, not 82. A cell on that recipe was not run. It would have confounded width with a trained, collapsed transformer.
- The baseline stack is dim 128 and the full-send stack is dim 256. The field width is the encoder width. Witness, attractor, and the rest of the fresh stack are constructed at that dim because a 256-d vector does not fit a 128-d field. That is the variable, not a second one.
- This baseline re-run is not byte-identical to the published cells. Mean displacement 0.138 vs 0.140. Seed 11 moved the most (0.129 vs 0.141). Same verdict, same single reflect groove. The 128 full-send column in the comparison table is the published one.
- Step 50 is inside the dream transient. `NEW_GROOVE` is not a second late regime.
- Rupture never fired. Its trigger is `locked`. The full-send stream was `structureless`. This is not a test of held-direction rupture. Boredom peaked at 0.97 on the baseline and ~0.80 on the full-send, so the threshold change is not the contrast. The lever that actually differed, besides the encoder, is attenuation at 0.30.
- Feedback steps are extra cycles (executed length ~870–900 baseline, ~1100–1310 full-send). Late metrics are by workload index. The arm gap still confounds "richer vectors" with "more offers" (LAE fires ~400 vs ~730). That gap is the same shape as the 128 run, and it is small beside the missing second groove.
- PLE lattice attractors are not `cycle.attractor.centers`. The attractor column is the substrate store. PLE still caps near 5–6 validated findings and 6 active paradoxes.
- No GPU. Nothing on :1234, :8080, or :8081 was touched. Wall-clock coupled, one process, seeds paired.

## Notes

For the gate.

**Participation of the encoder as loaded: 81.917**, residual on, dim 256, embeddings-only checkpoint `generator_weights_completion_256_emb.pt`. The file named in the brief, `generator_weights_completion_256_resid.pt`, measured **73.531** and was not loaded. The completion head was not on the field path.

**Identity stayed coherent.** Minimum 0.971–0.976 is a boot dip. Late mean 0.994–0.995. Fraction of steps under 0.95 is zero. Not dissolution.

**This does not change "the seam is the blocker."** It confirms it at the richer field. Participation 82 produces the same single reflect groove as participation 48. The next build is a write of the field vector, not another encoder width.

Nothing was promoted. After the run the live guard still matches: `generator_weights_5rhythm.pt` `71c646fb36d40e3b20cb03d1aa02f51c7a139ab4250aa701694fad8ef2482361`. The 256 checkpoint was only read (`30fc80cb…`).
