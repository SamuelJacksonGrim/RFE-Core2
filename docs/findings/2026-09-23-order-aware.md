# Order-aware encoder: the binding is real, the bag mouth is not

- **Date:** 2026-09-23
- **Branch:** `experiment/order-aware`, cut from `experiment/completion-objective` (`a92afc2`), in worktree `C:\Users\spamw\rfe\RFE-Core2-order`. The main checkout was left on `experiment/completion-objective`. Not merged, not pushed.
- **Corpus:** live v1.3.0, read only, from the main checkout. Ordered rows derived into `rfe/scratch/order/` (10,158 train, 1,585 holdout). Glue stays in the line and is never a target. The held-out content word is replaced by `<BLANK>` at its own index. Nothing was sorted.
- **Loss:** the completion loss with rhythm weight 0 and no rhythm code. Adam, lr `1e-2`, no weight decay, 40 epochs, seed 0, batch 128. Same recipe as the embedding run that filled dimensions.
- **Status:** measured. **Do not promote.** Production `Generator.forward` and `RecursiveAttention` were not edited. `CONFIG["dim"]` stays 128.

## Question

Completion made the bag legible (recall@8 0.61, median rank 2) and stopped there. Mean-pool cannot say which token was where, and adding a position vector and then summing does not fix it: the positional part depends on length, not on order. Does an order-sensitive pool lift the mouth past that ceiling, or does it only buy a fact the current mouth cannot say?

## Design

A separate module, `tools/order/encoder.py`. Not a `Generator`. The production mean-pool and the production stack are untouched.

The completion finding is why this is not a trained transformer as the whole encoder. Training that stack under this loss returns participation to ~4. A 1-layer pre-LN transformer was still run, as the option on the table, and it does the same thing in a milder form. It is not the readout the result is about.

The readout that is order-sensitive by construction is a fixed Rademacher gate, one sign pattern per position, seed 0, not a parameter:

```
h = L2( mean_i( e_i * g_i ) )          # gated
h = L2( unit(mean e) + unit(mean e*g) ) # parallel
```

`mean(e_i + p_i)` was rejected. It is still a bag. Sinusoidal gates were rejected too: the position-0 sinusoid is 0 on every even axis, which deletes half of the first token before the pool. Signs flip coordinates and do not zero them. Swapping two tokens changes the sum on every axis where the signs differ, and training cannot turn the gate off.

`parallel` renormalizes each term before the add. A learned scale can erase a residual. A unit vector cannot. This is the single-vector version of "keep the bag and add order," which is what the field can actually consume. The field takes one vector.

`mean` is the paired control: same rows, same recipe, plain mean of embeddings. The published completion checkpoints (frozen stack, mean-pool, recall@8 0.61 / 0.64) are the other control. They were loaded read-only and never shown a `<BLANK>`.

Every readout returns one unit-norm vector of the training width. Measured norm is 1.0 on the nose, min and max, at 128 and 256.

## Corpus, and why completion is a weak test of order

Live lines are length 2–4 (train 5,626 / 1,747 / 1,154). There is no long stem. The order contrast that actually occurs is which side of a short line the hole is on: `[abstain, <BLANK>]` and `[<BLANK>, abstain]` are the same bag and different questions.

| | train | holdout |
|---|---|---|
| rows | 10,158 | 1,585 |
| peaked rows | 8,935 | 1,582 |
| multisets with more than one order | 945 | 15 |
| of which the target distribution differs | 945 | 15 |
| rows in those groups | 1,906 | 30 |
| holdout rows whose multiset conflicts in train | — | 9 |

Checked against the distributions, not the raw counts. All 945 train groups differ in the set of target words, not only in how many times a word was seen. A mean-pool encoder is handed one vector and two answers on 1,906 rows, about a fifth of the file. That is why its train peaked top-1 sits at 0.52 instead of the 0.93 the sorted-bag run reported. The sorted run had collapsed those orders into one row.

The holdout does not contain the contrast. Exact contexts seen in train were dropped (1,719). Nine holdout rows remain in a train conflict. A completion number on that slice is an anecdote. Order has to be scored on the lines themselves.

## What was trained

Surface vocab 709, content vocab 690, including `<PAD>` and `<BLANK>` inside the encoder only. Pad row stayed at 0. GPU: WSL venv, torch 2.13.0+cu130, RTX 5070 Ti. No `--gpu max`. Ports not touched. Other completion trains were not killed. Checkpoints are new files in the worktree, `data/checkpoints/order_encoder_{readout}_{dim}.pt`. The live names were not written. The main checkout has none of them.

`attn` is one pre-LN layer, 4 heads, feed-forward 4×, dropout 0, sinusoidal positions added, then a mean pool. `attn_parallel` is that pool unit-added to the unit bag. Dropout is 0 so a short corpus is not being asked to learn through noise.

## Table

Same mouth as the completion finding: frozen encoder, fresh `TokenDecoder`, hidden 256, BCE, 20 epochs, seed 42, recall@8, median rank of the true tokens. It reproduces the published completion field vector (participation 35.151 / 63.509, recall@8 0.612 / 0.640, median rank 2 / 2, exact-bag@8 0.313 / 0.343).

Order is two numbers. Reverse-cosine is the architecture test: a bag is 1, and the published frozen stack is 0.9996. Slot top-1 is a fresh linear probe per position, fit on the train lines, scored on the holdout lines, argmax over the whole 709-word surface. In-line accuracy restricts that argmax to the tokens in the line. The bag oracle, which is handed the true set of tokens and only a position prior, scores in-line **0.459**. Positional unigram, which ignores the line, is 0.005. Mean-pool landing on the oracle is the "provably cannot" result. Beating the oracle is the order result.

Completion peaked top-1 is the co-trained head. The fresh linear probe agrees. Chance is `1/690 = 0.0014`. The rhythm unigram on these rows, which ignores the context, is peaked top-1 **0.0126** and CE **5.05**. Uniform CE is `ln(690) ≈ 6.54`.

| readout | dim | PR | eff. rank | recall@8 | median rank | exact bag@8 | reverse cos | slot top-1 | slot in-line | completion peaked train / hold | rhythm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| published mean-pool | 128 | 35.2 | 15.0 | **0.612** | **2** | **0.313** | 1.00 | 0.39 | 0.42 | — | 0.995 |
| published mean-pool | 256 | 63.5 | 25.4 | **0.640** | **2** | **0.343** | 1.00 | 0.39 | 0.42 | — | 0.995 |
| mean, these rows | 128 | 52.1 | 17.5 | 0.576 | 2 | 0.279 | 1.00 | 0.43 | 0.44 | 0.521 / 0.011 | 0.996 |
| mean, these rows | 256 | 66.4 | 21.4 | 0.672 | 2 | 0.410 | 1.00 | 0.43 | 0.44 | 0.550 / 0.011 | 0.996 |
| gated | 128 | **72.1** | **29.9** | 0.302 | 10 | 0.061 | **0.27** | **0.94** | **0.98** | **0.985 / 0.007** | 0.992 |
| gated | 256 | **114.6** | **42.0** | 0.291 | 11 | 0.060 | **0.24** | **0.96** | **0.98** | **0.995 / 0.010** | 0.992 |
| parallel | 128 | 60.3 | 28.7 | 0.393 | 6 | 0.109 | 0.49 | 0.91 | 0.96 | 0.981 / 0.009 | 0.997 |
| parallel | 256 | 98.4 | 44.8 | 0.366 | 7 | 0.092 | 0.46 | 0.95 | 0.97 | 0.997 / 0.013 | 0.995 |
| attn | 128 | 13.6 | 7.6 | 0.558 | 2 | 0.208 | 1.00 | 0.31 | 0.42 | 0.167 / 0.012 | 0.990 |
| attn | 256 | 11.5 | 6.6 | 0.531 | 2 | 0.191 | 1.00 | 0.29 | 0.41 | 0.163 / 0.012 | 0.991 |
| attn + bag | 128 | 62.2 | 4.2 | 0.370 | 7 | 0.096 | 1.00 | 0.43 | 0.43 | 0.655 / 0.010 | 0.983 |
| attn + bag | 256 | 74.7 | 3.7 | 0.498 | 3 | 0.190 | 1.00 | 0.42 | 0.43 | 0.644 / 0.011 | 0.995 |

Zero quiet dimensions and zero dead dimensions on every arm, including the ones whose effective rank collapsed. That is not evidence the space is being used. Effective rank and the centroid matrix are.

Gated and parallel have no cosine above 0.99 under reversal (fraction 0). The published stack has fraction 0.999. At init, before any training, gated reverse-cosine was −0.25 and the one-layer transformer was already 0.996. The transformer was not order-sensitive and the loss did not make it so. A toy of eight reversed pairs with opposite labels does fit under that layer (loss 0.003), so the layer can represent order when every row demands it. This corpus does not demand it on the rows that survive into the holdout, and the layer takes the low-rank basin instead.

The bag/order alignment on the parallel arms is negative: mean cosine **−0.35** at 128 and **−0.38** at 256. The order term is not a small decoration of the bag. Adding the two unit vectors rotates the field vector off the direction the bag mouth reads.

`attn + bag` is the trap in the participation column. PR looks filled (62, 75) and effective rank is ~4. Within-centroid cosine is ~0.71 and the worst centroid pair is **+0.91**. The cones closed. The bag term inflates the participation ratio. It does not keep a legible cloud, and the reverse-cosine says the attention term never carried order.

## What the three questions actually answered

**(a) Held-out completion.** No. Every arm is at the rhythm unigram or worse. Gated, which solves the training set (peaked top-1 0.985 at 128, 0.995 at 256; word CE 0.80 / 0.57), is the worst on the holdout (0.007 / 0.010, CE 8.07 / 8.78, both past uniform). The nine-row conflict slice is 0 for gated. The pairs that order distinguishes occur once. A vector that can store them stores them, and does not transfer. This is the same split result as the completion finding, sharper here because the train number finally moves and the holdout number still does not.

**(b) Order.** Yes, for the gated pool, and only for that family. A linear probe reads the token at a position out of 709 words at 0.94 (128) and 0.96 (256) on holdout lines. Restricted to the line's own tokens it is 0.98. The bag oracle is 0.46. Mean-pool, the published stack, and both attention arms sit on the oracle. The binding survives training. It is not an init artifact: the probe is fit after epoch 40, and train slot top-1 is 1.00 with holdout 0.94, which is generalization across lines, not a memorized line.

Position 3 is the thin one (190 holdout lines). Gated linear in-line there is 0.75 at 128 and 0.77 at 256, still well above the oracle. Positions 0 and 1, which are almost every line, are 0.997 and above.

**(c) Participation and the mouth.** They come apart.

Participation of the gated pool is higher than the published field vector and higher than the paired mean (72 vs 52 vs 35 at 128; 115 vs 66 vs 64 at 256). Effective rank moves with it (30 and 42). Rhythm stays at 0.99. The cones do not shut (off-diagonal mean 0.20 at 128, 0.30 at 256). The space got fuller, not smaller.

The mouth did not. Recall@8 goes from 0.61 to 0.30, median rank from 2 to 10, exact-bag@8 from 0.31 to 0.06. The parallel blend, which was supposed to keep the bag, goes to 0.39 / rank 6. Width does not buy the bag back: gated at 256 is 0.29 / rank 11. The signs that make order readable are a superposition the bag decoder does not undo. The slot probe can undo them because it is a different head for each position. `TokenDecoder` is one head for the set.

The paired mean is the control for "maybe any encoder trained on these rows beats 0.61." It does not, at 128 (0.576). At 256 it does (0.672), and that gain belongs to a bare mean of embeddings, not to order. Order is the arm that loses the bag.

## Verdict

**Order is in the vector. It does not lift this mouth. It is not worth replacing the production readout now.**

- The mean-pool ceiling on order is real. Reverse-cosine 1.00, slot top-1 0.39, in-line stuck on the bag oracle at 0.46. The published completion stack does not leak a usable order through its frozen positions.
- A position-gated sum clears that ceiling on the lines we have. Holdout slot top-1 0.94–0.96, in-line 0.98, reverse-cosine 0.27. Participation goes up, not down. Rhythm holds.
- The current mouth is a bag reader. On the gated vector it falls from 0.61 / rank 2 to 0.30 / rank 10. Folding the gated term into the same unit vector (the only shape the field injection consumes) still costs the bag, because the two terms point opposite ways. One vector is not both facts.
- Held-out word prediction does not move. Do not describe the gated checkpoint as a model that can finish a new line. It can finish a training line whose order the bag could not represent. Those lines do not recur in the holdout.
- A 1-layer transformer plus a mean pool does not learn order under this loss, and it walks back toward a low-rank cloud. Adding the bag next to it hides the collapse inside a flattering participation ratio and closes the cones (worst pair +0.91). That option is the one to reject.

Nothing here is promoted. The live corpus and the live 128 checkpoint are byte-identical to the hashes at the start of the branch (`rhythm_train` `f5d60859…`, `rhythm_holdout` `61c93de1…`, `generator_weights_5rhythm.pt` `71c646fb…`).

## NOTES

For the gate.

**What does the order-aware output look like?** One vector, L2 norm 1.0 at every row, dim 128 or 256, float32. Cosine and additive injection can take it. The math is the field's math. The object is not a `Generator` state dict: no ecology, no address space, no symbol registry, and `<BLANK>` is not a live token. Loading it as `generator_weights_5rhythm.pt` would not parse, and it should not be asked to. The published completion checkpoints were not modified.

**Replace the production readout, or keep a parallel head?** Neither, as a change to `h`.

Replacing the pool with the gated sum is what makes order readable, and it is what breaks the bag mouth (0.61 → 0.30). The parallel blend was the test of "keep both in the one vector the field stores." The order term is anti-aligned with the bag (cosine −0.35), the mouth drops to 0.39, and rank goes from 2 to 6. A mix inside `h` spends the direction the current decoder reads.

The shape that matches the evidence is a second vector, not a mix. Leave the production mean-pool completion vector as the field vector. If a later mouth is a sequence reader rather than a bag reader, the gated pool is already a unit-norm vector of the right width, and a linear head per position reads it at 0.94 on holdout lines of length 2–4. That mouth does not exist in this stack. Building the gated vector into `Generator.forward` before that reader exists would make the mouth we have worse and give nothing in the loop a way to say the order it had stored.

Mean-pool plus the completion objective is the right production readout for now. Order is a later head.
