# Completion objective: the dimensions fill, the stack erases them

- **Date:** 2026-09-23
- **Branch:** `experiment/completion-objective`, cut from `experiment/qwen-speech-cortex` (`fcaa831`). Not merged, not pushed.
- **Corpus:** live v1.3.0, read only. Completion rows derived into `rfe/scratch/completion/` (8,290 train, 2,064 holdout). `data/corpus/authoring/NOTES.md` is not in the tree; the glue rule used here is the one already settled (glue is scaffolding, never a target, never stripped from a live line).
- **Loss:** soft cross-entropy from the mean-pooled context onto the empirical distribution of the held-out content word. Rhythm loss weight **0** in the run that fills dimensions. See below for why the 0.15 term was dropped.
- **Status:** measured. **Do not promote.** The live 128 checkpoint was not written. Production `CONFIG["dim"]` stays 128.

## Question

The dim-256 contrastive run left participation at ~4 at both widths. The objective was the bottleneck. Samuel's redirect: stop clustering rhythm bags, and train context → completion, the way word2vec does, so the vector has to represent a distribution over words instead of a centroid. Rhythm stays a condition. Does that use the dimensions, and does the mouth move off 0.11?

## Loss

For a context `c` and an empirical distribution `p(w | c, rhythm)`:

```
h = encode(c)                                   # the field vector, already L2
loss = -sum_w p(w) log softmax(W h)(w)
```

This is CBOW with a full-vocabulary softmax. One-hot rows (a single held-out partner) are ordinary cross-entropy. A pivot with several partners is the "Mary had a little ___" row: one context, a distribution of fillers. A handful of centroids can realize only a handful of softmaxes. The completion matrix on the train rows has participation **467** and numerical rank **689** over 690 content words, so the target itself is not low-rank.

A rhythm term was designed and then measured out. Two forms were tried on the real encoder, 20–30 epochs, same step size as the run below:

| arm | what was added | live-holdout participation | holdout word CE |
|---|---|---|---|
| glue-padded context, rhythm CE 0.15, code scale 0.25 | scaffold was 4 of 5 tokens | 4.50 | 5.05 |
| content context, rhythm CE 0.15, code scale 0.25 | the code can solve a 5-way unigram by itself | 4.62 | 5.06 |
| content context, rhythm CE 0.15, code scale 0 | probe only, no shortcut | 4.60 | 5.07 |
| content context, rhythm weight 0, code scale 0, **stack trained** | pure CBOW through the transformer | 4.77 | 5.11 |
| same pure CBOW, **embeddings only, stack frozen** | the run in the table | **35.2** (128) / **63.5** (256) | 6.92 / 7.75 |

Chance word CE is `ln(690) ≈ 6.54`. The rhythm-unigram baseline (ignore the context, predict that rhythm's filler marginal) sits at CE **5.08** and peaked top-1 **0.011**. Every arm that *trained the stack* stopped in that neighborhood and at participation ~4, including the arm with no rhythm term at all. The rhythm CE is sufficient to cause the collapse and it is not necessary. The shared map takes the basin by itself.

The 0.15 rhythm weight was the "light conditioning term." At chance it is small next to the word loss (`0.15 * ln 5 ≈ 0.24` against `ln 690 ≈ 6.5`). It is also the easier problem, and it pins the cones by epoch 3, before a word gradient has anywhere to stand. It is not in the checkpoint below. Rhythm did not need it. See the probe column.

## Corpus

Leave-one-out on the live lines. The context is the other **content** words, sorted, so an order swap is one row. Glue is not a target and it is not padded in: a fixed glue frame was the first build, it made the scaffold four fifths of the pool, and it collapsed exactly like contrastive (archived as `*_gluepad`, participation 4.50). Glue stays in the live lines the mouth reads.

| | train | holdout |
|---|---|---|
| rows | 8,290 | 2,064 |
| context length 1 / 2 / 3 | 679 / 6,371 / 1,240 | — |
| peaked rows (one filler) | 6,684 | 1,587 |
| stems (one pivot, ≥3 fillers) | 599 | 302 |
| distinct peaked targets | 567 | 501 |
| cross-rhythm rows | 99 | — |
| mean target entropy | 0.28 nats | 0.26 nats |

Most contexts are two content words because most live lines are two to four tokens and one is held out. That is shorter than the 4–5 word window asked for. Padding to get the length was tested and it destroyed the gradient. 164 order-swapped train bags were counted once. 62 holdout content-bags that already occurred in train were dropped. Token overlap was kept.

46 content types occur in more than one rhythm, so the "same stem, rhythm changes the filler" case is real and small (99 rows). It is not the bulk of the file. The bulk is within-rhythm co-occurrence. The vocabulary is rhythm-pure, which is why a rhythm probe can score 0.99 with no rhythm loss.

## What was trained

Same architecture as the dim-256 run (vocab 8192, depth 4, heads 4, ff 4). Completion runs: Adam, lr `1e-2`, no weight decay, 40 epochs, seed 0, batch 128. **The transformer, the position codes, and both projections are frozen at init.** Only the token embedding and the softmax head train. 56 tensors frozen. GPU: WSL venv, torch 2.13.0+cu130, RTX 5070 Ti. No `--gpu max`. Ports not touched.

Checkpoints are new files. The live names were refused.

| file | role |
|---|---|
| `generator_weights_completion_128_emb.pt` | field vector, dim 128 |
| `generator_weights_completion_256_emb.pt` | field vector, dim 256 |
| `completion_head_{128,256}_emb.pt` | the softmax, not part of the field |
| `*_gluepad`, `*_rhythmce`, `*_noshortcut`, `*_cbow`, `*_cbowlr` | the collapsed arms, kept so the negative is reproducible |

Bare CBOW (mean of embeddings, no transformer, same loss, same 40 epochs, same lr) is the control that says the objective itself can fill a space. It is not a field checkpoint.

## Table

Same instrument as `docs/findings/2026-09-23-dim256-substrate.md`. Participation and effective rank are on the **live** holdout lines (1,505), not on the completion rows. The mouth is Phase 0: frozen encoder, fresh `TokenDecoder`, hidden 256, BCE, 20 epochs, seed 42, recall@8. It reproduces the published contrastive numbers (frozen participation 3.40 vs 3.42, paired 3.90 vs 3.90, dim-256 3.57 vs 3.57; paired recall@8 0.089 vs 0.088; dim-256 recall@8 0.091 vs 0.091; frozen median rank 33 vs 33).

Rhythm is a linear probe fit on the live train lines and scored on the live holdout. Completion top-1 is a fresh linear softmax on `encode(context)` — the held-out word is not in the input — scored on peaked rows. Chance top-1 is `1/690 = 0.0014`. The rhythm-unigram baseline, which ignores the context, is peaked top-1 **0.011** and CE **5.08**.

| encoder | dim | participation | eff. rank | recall@8 | median rank | exact bag@8 | completion top-1 (train / hold) | rhythm probe |
|---|---|---|---|---|---|---|---|---|
| contrastive, frozen live | 128 | 3.40 | 1.86 | 0.114 | 33 | 0.005 | 0.018 / 0.014 | 0.817 |
| contrastive, paired retrain | 128 | 3.90 | 1.68 | 0.089 | 41 | 0.005 | 0.017 / 0.011 | 0.987 |
| contrastive, this recipe | 256 | 3.57 | 1.72 | 0.091 | 41 | 0.008 | 0.016 / 0.018 | 0.987 |
| completion, embeddings only | 128 | **35.15** | **15.03** | **0.612** | **2** | **0.313** | 0.935 / 0.009 | **0.995** |
| completion, embeddings only | 256 | **63.51** | **25.43** | **0.640** | **2** | **0.343** | 0.999 / 0.007 | **0.995** |

Within-centroid cosine, which contrastive drives to ~0.99, falls to ~0.54 (128) and ~0.46 (256). Worst centroid pair: paired contrastive stabilize–dream **+0.40**; completion 128 dream–explore **+0.26**; completion 256 reflect–explore **+0.21**. Off-diagonal mean: 0.33 → 0.08 (128) and 0.11 (256). The cones opened and the centroids got further apart. Zero quiet dimensions, zero dead dimensions, at both widths.

Bare mean-of-embeddings, same loss, no transformer: participation **56.1** at 128 and **72.8** at 256. Effective rank 27.7 and 34.8. Train peaked top-1 0.56 / 0.59. Holdout peaked top-1 0.008 / 0.009. Rhythm probe 0.995 both. The frozen init stack passes a fraction of that geometry through to the field vector (35 of 56 at 128, 64 of 73 at 256). Dim 256 passes more of it.

Both completion curves were still rising at epoch 40 (128 participation 33.7 → 35.2 over the last five epochs; 256 60.7 → 63.5). The gap versus contrastive is not a question of stopping early. The collapsed full-stack arm had already flattened near 4.8 by epoch 30.

## What the two "accuracy" numbers are saying

They are different questions and they disagree.

The mouth reads the **full line**, tokens included. Recall@8 of 0.61 against 0.09 means the bag is in the vector. Median rank 2 means the true token is usually the top hit or the one next to it. Train recall 0.70 / 0.72 against holdout 0.61 / 0.64 is a gap, not a memorize-and-forget: the holdout lines were not the training pairs, and a fresh decoder still reads them. That is the legibility the contrastive encoder does not have, because it has already thrown the token away.

The completion head reads the **context with the answer removed**. On train it is solved (peaked top-1 0.93 at 128, 1.00 at 256). On holdout it is worse than the rhythm unigram (0.008 vs 0.011) and the CE is worse than uniform (6.9–7.8 vs 6.54). The head memorized pairings. Most pairings occur once, so there is nothing to generalize. A high-rank space can store 8,000 arbitrary maps and still be useless on the 2,000 it has not seen. Dimension use and held-out word prediction are not the same claim. This run supports the first and not the second.

## Verdict

**Yes, this is the objective the dim-256 result was missing. No, it is not a loss you can drop on the usual training loop.**

- Participation leaves ~4. At 128 it reaches 35; at 256 it reaches 64. Contrastive did the opposite: 256 was slightly worse (3.57 vs 3.90). Under this objective the extra width is used. Effective rank moves with it (1.7 → 15 → 25), so it is not one dominant axis with a noisier residual.
- The mouth moves off 0.11, to 0.61 and 0.64. Median rank 33 → 2. That is bag legibility, and it is real on the holdout.
- Rhythm is not destroyed. The probe is 0.995 at both widths, a point above the paired contrastive encoder (0.987), with the cones opened rather than tightened. No rhythm loss was required. The words already carry the rhythm.
- 256 pays off on the geometry and on how completely the training completions are stored (word CE 2.23 → 1.34, peaked top-1 0.93 → 1.00). It barely pays off on the mouth (0.612 → 0.640). Mean-pool bag readout is close to saturated once the tokens are distinct. More ambient dimensions do not recover order.
- Held-out completion does not work. Do not describe this checkpoint as a model that can fill in the blank on a new line.
- Training the transformer under the same loss returns participation to ~4.8. The objective fills dimensions only when the shared map is not allowed to erase them. The init stack, frozen, is a random filter that still passes most of a 256-d embedding geometry and less of a 128-d one. It is not a learned encoder in the usual sense.

Nothing here is promoted. The live corpus and the live 128 checkpoint are byte-identical to the hashes at the start of the branch (`rhythm_train` `f5d60859…`, `rhythm_holdout` `61c93de1…`, `generator_weights_5rhythm.pt` `71c646fb…`).

## NOTES

For the gate, the short version.

**Is context → completion the objective the evidence pointed at?** Yes. The contrastive cloud is a point per rhythm because that is what the loss asks for, and a point per rhythm is about four directions at any ambient width. A distribution over 690 words is not that object. The completion matrix is participation 467. A mean of embeddings trained to predict it reaches participation 56 at dim 128 and 73 at dim 256, and the field vector follows (35 and 64) when nothing is allowed to collapse it. The mouth going from 0.09 to 0.61 is the same fact read out as tokens. That is the pivot the 256D note named.

**How much rhythm conditioning was kept?** None in the run that works. Weight 0.15, with and without a 0.25 additive rhythm code, was enough to put the *trained* stack back at participation ~4.5 and word CE ~5.1, which is the rhythm-unigram solution. The code is an escape hatch: five rhythm vectors can implement five filler marginals and the context vector is then free to die. With the stack frozen, the rhythm loss was unnecessary. Holdout rhythm-probe accuracy is 0.995 with no rhythm term, because 644 of the 690 content types belong to one rhythm. The condition Samuel described — the same stem, a different filler distribution per rhythm — is in the file for the 46 cross-listed pivots (99 rows) and is not what the geometry is built on. I would not put the 0.15 term back on a stack that is allowed to train. If a later run trains the stack through a residual that cannot be erased, a rhythm probe at a much smaller weight can be remeasured. It is not load-bearing now.

**Is order the next ceiling?** For the mouth, yes, and it is a different ceiling from the one this experiment cleared. Mean-pool cannot say which token was where, and the readout is already at median rank 2, so another width will not buy order. Exact-bag@8 of 0.34 says a third of holdout lines are fully named and two thirds are not; some of that residue is the frozen random map blurring the sum, and some is the bag being unordered. Dropping mean-pool is how order would enter. It is not how dimensions would start being used — they are being used.

The ceiling in front of that one is smaller, and it is what blocked the naive training loop. The shared transformer, given this loss, walks into the same four-direction basin contrastive lives in, even with the rhythm term off and the step size raised to the one that works for a bare embedding. A residual from the embedding mean into the field vector, so the stack can move and cannot wipe the completion geometry, is the experiment I would run before an order-aware encoder. I did not run it.

**What not to conclude.** This is not a better contrastive encoder you can hot-swap. The transformer weights are the init. Held-out blanks are not predicted. The live loop, the live checkpoint, and dim 128 are unchanged.
