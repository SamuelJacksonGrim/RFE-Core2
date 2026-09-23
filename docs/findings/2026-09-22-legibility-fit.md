# Legibility fit — the checkpoint, and where it stopped

- **Date:** 2026-09-22
- **Branch:** `experiment/legibility-fit` off `experiment/encoder-legibility` (`2de456a`)
- **Substrate:** `data/checkpoints/generator_weights_5rhythm.pt` read, never written. New file `data/checkpoints/generator_weights_5rhythm_legible.pt` plus `generator_ecology_5rhythm_legible.json`. Corpus v1.3.0. CPU, torch 2.14.0+cpu. No field step, no resonance memory, no port.
- **Code:** `training/legibility.py` (unchanged losses; an optional `on_epoch` hook so a run can be scored and stopped), `tools/voice/fit_legible.py`. Numbers in `2026-09-22-legibility-fit-metrics.json`.
- **Status:** checkpoint saved. Not wired. Not converged.

## What was not changed

`LegibilityConfig` against the probe defaults differs in one field: `epochs` 8 → 30. Margin 0.20, τ 0.70 / 0.98, rupture ×3, orphan ×2, the four weights, both learning rates, 32 per rhythm, seed 42. Epochs 1–8 of the loss matched the probe history to a worst absolute difference of 0. The epoch-8 yardstick reproduced the published row (recall@8 0.3554, median rank 21, exact-bag@8 0.0432, clean within 0.6156, across 0.1178, centroid min 0.9759).

The hook restores the torch RNG around each yardstick. That is why the losses match a probe that had no mid-fit eval. The frozen Phase-0 mouth is run first, as the probe ran it, because that mouth is what seeds the rank term's negative samples.

## Guards

Abort, and do not keep a checkpoint, if nearest-centroid accuracy (all-holdout or clean) falls below 0.98, or any rhythm centroid's cosine to the frozen checkpoint falls below 0.95, or clean across exceeds frozen clean across + 0.08, or clean within − across falls below 0.10.

A tighter rule was tried on a first pass and was wrong. It treated a 0.05 rise in across off its early minimum as "climbing back toward within," and it fired at epoch 20 (across 0.164, within 0.587, frozen across 0.356). Nothing was saved. The cones were not merging. That rule is not in the run that produced the checkpoint. Across did keep drifting up, slowly, and it is in the curve below so it can be watched. At epoch 30 it is 0.177 against a frozen 0.356, and the gap to within is 0.40.

## Curve

Holdout mouth, fresh `TokenDecoder`, BCE, hidden 256, 20 epochs, seed 42. Within / across are the clean holdout (no orphan token), the Phase 0 cut. Centroid min is that holdout cloud's centroid against the frozen clean-train centroid.

| epoch | recall@8 | median rank | exact-bag@8 | clean within | clean across | nn-acc | centroid min | rupture | orphan | nn Jaccard |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 0.316 | 23 | 0.029 | 0.657 | 0.105 | 0.993 | 0.982 | 0.265 | 0.230 | 0.086 |
| 8 | 0.355 | 21 | 0.043 | 0.616 | 0.118 | 0.995 | 0.976 | 0.283 | 0.290 | 0.099 |
| 10 | 0.371 | 20 | 0.044 | 0.608 | 0.129 | 0.995 | 0.969 | 0.303 | 0.300 | 0.099 |
| 15 | 0.400 | 17 | 0.051 | 0.594 | 0.152 | 0.995 | 0.972 | 0.317 | 0.357 | 0.107 |
| 20 | 0.402 | 16 | 0.063 | 0.587 | 0.164 | 0.993 | 0.968 | 0.303 | 0.344 | 0.102 |
| 25 | 0.412 | 16 | 0.072 | 0.583 | 0.169 | 0.995 | 0.979 | 0.289 | 0.369 | 0.105 |
| 30 | 0.417 | 15 | 0.076 | 0.577 | 0.177 | 0.992 | 0.986 | 0.303 | 0.372 | 0.100 |

Rank loss: 0.741 at epoch 8, 0.487 at epoch 30, still falling about 0.007 per epoch. Jaccard loss: 0.044 → 0.019, and the last five epochs move it by 0.002. The flatten rule (rank drop < 0.005 and Jaccard drop < 0.001 for 3 epochs) did not trip. **Not converged.** The mouth is close to a plateau (0.412 → 0.417 from epoch 25 to 30). The rank term is not.

Train recall at epoch 30 is 0.480 against holdout 0.417. Same shape of gap as the probe (0.402 vs 0.355), not a memorized subset.

Clean holdout, epoch 30:

| rhythm | recall@8 | median rank | within cosine |
|---|---:|---:|---:|
| stabilize | 0.450 | 12 | 0.602 |
| dream | 0.406 | 17 | 0.604 |
| reflect | 0.414 | 14 | 0.583 |
| explore | 0.448 | 15 | 0.643 |
| rupture | 0.303 | 30 | 0.451 |

Rupture is still the worst mouth. It peaked at 0.317 on epoch 15 and sat at 0.303 from epoch 20 on. 3× was left at 3×. Raising it would be a new probe.

Centroid cosine to the frozen checkpoint at epoch 30: stabilize 0.995, dream 0.993, reflect 0.994, explore 0.989, rupture 0.986. The minimum dipped to 0.968 at epochs 10 and 20 and came back. The floor is 0.95. Clean nearest-centroid accuracy at epoch 30 is 0.988, all-holdout 0.992. Both cleared 0.98. The clean number is the one with less room.

## Against the probe row

| | recall@8 | median rank | exact-bag@8 | clean within | clean across | nn-acc | centroid min | rupture | orphan | nn Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| probe, epoch 8 | 0.355 | 21 | 0.043 | 0.616 | 0.118 | 0.995 | 0.976 | 0.283 | 0.290 | 0.099 |
| this fit, epoch 30 | 0.417 | 15 | 0.076 | 0.577 | 0.177 | 0.992 | 0.986 | 0.303 | 0.372 | 0.100 |

Neighbor Jaccard did not move. It peaked at 0.107 on epoch 15 and finished at 0.100. The probe's own threat was this one: a longer fit has to move Jaccard, not only recall, or the gain is sitting in directions a fresh MLP can use and a cosine lookup cannot. That is what happened. Recall rose 0.06. The decoder-free neighbor code did not.

A clean sequence's new encode sits at cosine 0.732 from the frozen encode of the same tokens (0.762 at the probe's epoch 8). Further from the checkpoint, still below formation (0.88) and now under the pull threshold (0.75). Trained-row cosine to the checkpoint is 0.938 (probe 0.967). Orphan-row cosine to init is 0.945 (probe 0.973). The rows traveled more and are still in the neighborhood. The ecology saved with the checkpoint has the 239 orphan tokens registered; the frozen ecology does not.

## The file

| file | sha256 | bytes | mtime |
|---|---|---:|---|
| `generator_weights_5rhythm.pt` | `71c646fb36d40e3b20cb03d1aa02f51c7a139ab4250aa701694fad8ef2482361` | 7720565 | 2026-09-22 15:13:41, unchanged |
| `generator_ecology_5rhythm.json` | `d74c829c078e22b76423cdf1b5b02a2032e02b1b8ae142b85f51d19e7d27d600` | 288050 | same mtime, unchanged |
| `generator_weights_5rhythm_legible.pt` | `c51598ec36d86ecca86275e1a64a69844f3885c232167b37f7c8f1a381efdaa4` | 7720245 | 2026-09-22 18:52:17 |
| `generator_ecology_5rhythm_legible.json` | `f64e55b00e1c4f86a2a0c9dd3954778b50082b1b1d55db831483f086791a7395` | 447127 | same minute |

`data/checkpoints/` is gitignored. The weights are on this machine, not in the commit. The frozen pair was hashed before the fit and after it. Same bytes, same mtime.

The saved ecology is the post-orphan-registration snapshot taken before any measurement encode, with the trained weights loaded back on top. `register()` during the fit bumps usage counts; those bumps were not what got written.

## Notes for the gate

- Same objective. The extra recall is more of the same fit, not a retune.
- Not converged. Stopping at 30 was the budget. Another 30 epochs would still be spending rank gradient. The yardstick says most of the mouth was in by epoch 20.
- The wall held. Across rose off its epoch-5 minimum and stayed far below the frozen across. Centroids finished closer to the checkpoint than the probe left them (min 0.986 vs 0.976).
- Do not hot-swap. Encode cosine to the frozen vector of the same tokens is 0.73, under `pull_threshold` 0.75. Worse than the probe's 0.76, same conclusion.
- Neighbor Jaccard at 0.10 is the number to believe about a cosine lookup. 0.417 is the number to believe about a trained MLP mouth. They are not the same fact.
- Rupture is still the worst cone, and its within-cosine opened the most (0.45). The levelness read of that opening is in `2026-09-22-corpus-health.md`. Short version: effective rank of the clean cloud went 3.7 → 13.8, nothing became a hub, and the flatness of the cone went from a depth gap of 0.002 to 0.12. Local neighbors are still cosine ~0.98.
- No field-lock exception. The field was not in the graph.
- Nothing was pushed. `experiment/encoder-legibility`, `experiment/decode-organ`, and `experiment/qwen-speech-cortex` were not moved. `main` was not touched.
