# Completion: the collapse is the transformer, and a recurring stem does generalize

- **Date:** 2026-09-23
- **Branch:** `experiment/completion-objective`, on top of `a92afc2`. Not merged, not pushed.
- **Corpus:** live v1.3.0, read only. The recurring-stem file is a second pair under `rfe/scratch/completion/` (`completion_recur_*.jsonl`). It does not replace `completion_train.jsonl`.
- **Status:** measured. **Do not promote.** Production `CONFIG["dim"]` stays 128. The live 128 checkpoint was not written.

## What the last run actually measured

Participation in `2026-09-23-completion-objective.md` is the post-transformer field vector: `Generator.forward`, L2-normalized, on the 1,505 live holdout lines. It is not the embedding table, and it is not the vector after `RecursiveAttention`. The instrument matches that note. A fresh init at dim 128 scores field participation **21.186**, the same epoch-0 number as the collapsed arm.

`RecursiveAttention` is not inside `Generator`. The completion trainer never constructed one. Production runs it untrained, under `refine()`, with `diversity_blend` 0.60, after `generate()` and a 0.15 attractor pull. The attractor is not in the numbers below. The attention measurements are in `eval()`, so dropout is off; the live cycle currently leaves the module in `train()`, which would put dropout noise on top of the same map.

## Where it collapses

Both points, every config. "Stack" is `Generator.forward` with the residual flag off. "Emb" is the masked mean of the sqrt(dim)-scaled token embeddings, before position.

| encoder | dim | emb PR | field PR | field eff | residual at inference, PR / eff |
|---|---|---|---|---|---|
| init | 128 | 98.7 | 21.2 | 1.4 | 82.2 / 5.2 |
| init | 256 | 158.1 | 41.4 | 2.2 | 115.4 / 7.9 |
| contrastive, frozen live | 128 | 30.0 | 3.42 | 1.85 | 11.7 / 4.5 |
| completion, full stack (the 4.8 arm) | 128 | **9.8** | **4.77** | 2.54 | 7.8 / 4.4 |
| completion, full stack, 20 epochs | 256 | **8.2** | **4.37** | 2.66 | — |
| completion, embeddings only | 128 | **66.9** | **35.15** | 15.03 | **47.8 / 19.3** |
| completion, embeddings only | 256 | **115.0** | **63.51** | 25.43 | **81.9 / 31.9** |
| completion, stack trained, residual on | 128 | 57.3 | stack 0.61 | stack eff 1.0 | **output 56.6 / 26.3** |
| completion, stack trained, residual on | 256 | 74.1 | stack 0.73 | stack eff 1.0 | **output 73.5 / 31.7** |

The 256 full-stack arm is the same recipe as the 128 collapse (lr `1e-2`, no weight decay, rhythm weight 0). By epoch 5 the field is already at 2.0 and the embedding mean at 7.8. Epoch 20 settles at 4.37 / 8.2. Same basin as 128. Not a width artifact and not an early stop.

Cosine between the field and the embedding mean on the collapsed arm is about 0, not −1. The transformer is not cancelling a rich table. The table itself was dragged down, from 99 at init to 9.8. Turning the residual on after the fact cannot restore it: there is nothing rich left to mix. Contrastive is the other shape. There the table is still at 30 and the field is at 3.4, so that collapse really is the stack erasing a richer table. The completion collapse is both points.

## Recursive attention

It is not the module that learned the basin. Keeping it frozen is what the collapsed run already did.

What it does to a vector that is already rich, untrained, production blend, live-holdout order:

| input | dim | blend 0, stream | blend 0.60, stream | blend 0.60, no history | blend 1 (passthrough) |
|---|---|---|---|---|---|
| emb-only field | 128 | PR 6.0 | **25.0 / eff 8.0** | 31.7 / 13.4 | 35.15 / 15.03 |
| emb-only field | 256 | PR 7.9 | **37.3 / eff 10.9** | 57.2 / 23.4 | 63.51 / 25.43 |
| emb-only, residual mixed in | 128 | PR 9.1 | **37.2 / eff 9.2** | 41.5 / 16.8 | 47.8 / 19.3 |
| emb-only, residual mixed in | 256 | PR 9.6 | **50.9 / eff 14.4** | 69.9 / 31.3 | 81.9 / 31.9 |
| residual-trained output | 128 | PR 8.2 | **34.9 / eff 15.5** | — | 56.6 / 26.3 |
| residual-trained output | 256 | PR 8.6 | **41.8 / eff 14.6** | — | 73.5 / 31.7 |

Blend 0 is the untrained pooler with the raw vector weighted out, and it does collapse the rich cloud to a handful of directions. Blend 0.60 does not. Streaming history is a tax (35 → 25, 64 → 37 on the published field). Clearing history before each line gives most of the cloud back, so the tax is the rolling mean, not a pointwise rewrite. The field, which consumes `refine()` at 0.60, sees a discounted rich vector. It does not see the four-direction basin.

## The residual

The flag is `Generator.embedding_residual`, default off, not in the state dict. Off, `forward` is the old path; a self-check rounds-trips the flag and gets the original tensor back. On, the field vector is

```
h = normalize(u + (s - proj_u s))
```

`u` is the unit embedding mean. `s` is the unit post-transformer vector. The transformer reads a detached copy of the embeddings, so its collapse cannot backprop into the table, and the projection removes its component along `u`, so it cannot cancel. The lock is `u · h >= 1/sqrt(2)`. Measured cosine on the trained residual outputs is 0.77.

Trained 40 epochs, both widths, same step size as the run that filled dimensions. The stack participation falls to ~1 by epoch 5 and stays there (256 spends most of the run at 0). The output does not follow it. It tracks the embedding mean and is still rising at epoch 40:

| epoch | 128 output PR | 128 emb PR | 128 stack PR | 256 output PR | 256 stack PR |
|---|---|---|---|---|---|
| 0 | 82.2 | 98.7 | 21.2 | 115.4 | 41.4 |
| 5 | 13.5 | 14.1 | 0.94 | 20.3 | 0.0 |
| 20 | 44.7 | 45.9 | 0.71 | 58.9 | 0.04 |
| 40 | 56.6 | 57.3 | 0.61 | 73.5 | 0.73 |

The early dip is the table reorganizing, not a return to the basin. The stack is a dead direction the mix strips off. It is not a learned encoder. Train mode top-1 on the old one-shot corpus only reached 0.50 / 0.53, and holdout top-1 stayed at 0.011. The residual saves the geometry. It does not, by itself, create a completion the model has not been given a chance to learn.

Mouth on that output, phase-0 protocol: recall@8 **0.694** at 128 (median rank **1**) and **0.657** at 256 (median rank 1).

Mixing the residual in at inference, on the existing embeddings-only checkpoints, no retrain:

| | 128 | 256 |
|---|---|---|
| field, residual off (the published win) | PR 35.2, eff 15.0, recall@8 0.612, rank 2 | PR 63.5, eff 25.4, recall@8 0.640, rank 2 |
| same weights, residual on | PR **47.8**, eff **19.3**, recall@8 **0.662**, rank 2 | PR **81.9**, eff **31.9**, recall@8 **0.691**, rank 2 |

## Production config

Speech and the phase-0 mouth read `generate` / `encode_batch`, before the attractor and before recursive attention. The field injects the refined vector.

The config that keeps a rich vector at both of those points, and the better mouth at 256:

1. Train token embeddings only. Leave the transformer, the position codes, and both projections at init. Rhythm weight 0. This is the existing `generator_weights_completion_{128,256}_emb.pt`.
2. Set `generator.embedding_residual = True` before encode. The flag is not stored in the checkpoint. Forgetting it ships the published vector, which is already rich (35 / 63, mouth 0.61 / 0.64). Setting it is a strict improvement of those same weights.
3. Leave `RecursiveAttention` untrained at `diversity_blend` 0.60. Do not train it. Blend 0 would throw the rich vector away.

Do not train the transformer under this loss and then read its output. At both widths that is participation ~4.4–4.8, and the table falls with it. Training it behind the residual keeps the output rich only because the transformer is ignored. At a matched 40 epochs the 256 mouth is worse that way (0.657 against 0.691), and the module's own participation is under 1.

This is not wired into the cycle or the speech cortex on this branch. The live loop still loads `generator_weights_5rhythm.pt`.

## Recurring stems

The old holdout failed because a context was paired with one filler, once. The new file gives each stem the same filler distribution in 241 contexts.

Built only from rhythm-pure live content words (41 ambiguous words dropped). Per rhythm: 16 fillers, up to 32 pivots, the rest partners. A stem's target is one mode (count 11) and five other fillers (count 2). Entropy floor **1.458** nats. Glue is stored as a scaffold (`the … of a`) and is not in the context. Pooling a glue frame was the gluepad arm; it collapsed. Rhythms are the row's rhythm, and every filler is from that rhythm.

| | train | similar holdout | seen (copies) | novel pivots |
|---|---|---|---|---|
| rows | 38,078 | 6,952 | 2,000 | 240 |
| stems | 158 | the same pivots | the same contexts | pivots never in train |
| contexts / stem | 241 exactly | new partner tuples | — | — |

Context length in train: 158 bare pivots, 3,160 pairs, 34,760 triples. The rhythm-unigram baseline on the similar split is mode top-1 **0.063**, support recall@8 **0.506**, CE **2.776**. The old 0.011 figure is the unigram on a file of ~567 distinct one-hot targets. It is not the bar on this file. 0.063 is.

Recipe: embeddings only, transformer frozen, lr `1e-2`, no weight decay, rhythm weight 0, 100 epochs, seed 0, both widths. The curve is the co-trained head. A fresh linear probe at epoch 100 agrees with it.

| epoch | 128 similar top-1 | 128 field PR | 128 emb PR | 256 similar top-1 | 256 field PR | 256 emb PR |
|---|---|---|---|---|---|---|
| 0 | 0.000 | 21.2 | 98.7 | 0.003 | 41.4 | 158.1 |
| 5 | **1.0** | 15.3 | 19.2 | **1.0** | 18.4 | 24.0 |
| 20 | 1.0 | 16.7 | 24.0 | 1.0 | 20.0 | 30.3 |
| 40 | 1.0 | 16.9 | 27.0 | 1.0 | 20.3 | 34.8 |
| 100 | 1.0 | 16.6 | 27.6 | 1.0 | 20.0 | 35.9 |

Similar-split frozen probe at epoch 100, both widths: mode top-1 **1.0**, support recall@8 **1.0**, CE **1.46** (the floor). Seen copies: the same. Novel pivots: mode top-1 **0.058** (128) and **0.038** (256), CE 3.37 and 3.18, worse than the unigram. The model is sure, and wrong, on a stem it has never had. That is the negative control, and it held.

It is not still climbing. Completion was done by epoch 5. The next 95 epochs moved field participation by about one point. Word CE sat on the floor from epoch 5 (1.52 → 1.51; floor 1.46).

The mouth did not hold. Phase-0 recall@8 on the live holdout is **0.322** at 128 (median rank 10) and **0.326** at 256 (median rank 10). Residual-at-inference does not repair it: **0.319** and **0.327**, ranks 11 and 10. The table itself is less legible for live lines (embedding participation 67 → 28 at 128, 115 → 36 at 256; field eff 15 → 8.4 and 25 → 8.9). It is not a return to the contrastive mouth. 0.32 is still about 28× chance, against 0.09. Rhythm survived: holdout probe **0.964** and **0.963**.

Post-RA at blend 0.60 on these field vectors: participation 14.5 (128) and 15.6 (256). The expression is thinner than the live-line completion model and still not the four-direction basin.

## Verdict

The collapse is a property of training the transformer under this loss. It is not a measurement artifact, and it is not `RecursiveAttention`. Both the embedding mean and the field go to the low-rank basin, at 128 and at 256. Freezing recursive attention does not prevent it, because it was never in the graph. A residual the transformer cannot cancel does prevent it from reaching the output: the output stays rich while the transformer goes to a point. The production reading of that fact is to not train the transformer. Train the embeddings, and mix the embedding mean back in at the generator output. That is the vector speech reads, and on the checkpoints that already exist it raises the mouth from 0.612 / 0.640 to 0.662 / 0.691. The field, downstream of untrained recursive attention at blend 0.60, then sees participation 37 / 51 rather than 25 / 37. Still rich. Not the full generator vector.

Recurring stems are the generalization. Same pivot, new partners, mode top-1 1.0 against a unigram of 0.063, at both widths, by epoch 5, confirmed by a fresh probe, and absent on a pivot the model has never seen. Longer than that is not buying completion. It also does not keep the mouth. The synthetic distribution spends the dimensions the live lines were using. The legibility checkpoint and the blank-filling checkpoint are not the same file.

Nothing promoted. After the runs, `rhythm_train` is `f5d60859…`, `rhythm_holdout` is `61c93de1…`, `generator_weights_5rhythm.pt` is `71c646fb…`.

## NOTES

For the gate.

**Is the win production-ready after the collapse is nailed?** The representation is, under a config, and the config is not "train the whole stack." The stack is the thing that collapses, and it collapses the table with it. The shipped reading is the embeddings-only checkpoint with the residual flag on at encode time, recursive attention left untrained at blend 0.60. Mouth 0.66 / 0.69, median rank 2, field participation after attention 37 / 51. The flag is code, not a weight. This branch does not turn it on in the live cycle. I would not call the transformer a trained encoder in this objective: given the residual, it learns a constant.

**Is bigger / longer the answer to generalization?** Yes for the blank, and it did not need to be long. A stem that recurs with a real filler distribution is solved on new partner contexts (top-1 1.0, recall@8 1.0, CE on the entropy floor) and unsolved on a stem that never occurred. The curve is flat from epoch 5 to epoch 100. No, for the mouth. Recall@8 falls from 0.61 to 0.32 because the table is fit to 158 synthetic stems rather than to the live lines. Scale of this kind does not carry both wins. Keep the live-line completion checkpoint for legibility. Treat the recurring-stem result as the evidence that the blank failed for lack of repetition, not for lack of width.
