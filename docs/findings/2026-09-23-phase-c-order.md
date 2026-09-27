# Phase C — order-aware co-balance

- **Date:** 2026-09-23
- **Branch:** `experiment/phase-c`, cut from `experiment/phase-b` (`f0aac11`), worktree `C:\Users\spamw\rfe\RFE-Core2-phasec`. Not merged, not pushed.
- **Status:** measured. The joint gate does **not** clear. The mean-pool OOV ceiling **does** break. Do not promote. `Generator.forward` was not edited.

## What was banked

The S2 mouth stays the retrieval organ. Copies sit beside the originals as `banked_mouth_completion_{128,256}.pt` (and the matching ecology and head). Names are refused by `tools/completion/live_guard.py`. Hashes and the S2 numbers (recall@8 0.6936 / 0.6573, output PR 56.581 / 73.531) are in `docs/findings/logs/2026-09-23-phase-c/banked_mouth.md`. Phase C wrote `sequence_encoder_phasec_*` only.

## Why this encoder

Mean-pool cannot co-balance. S3 already showed the two numbers moving apart across the whole ratio grid, and novel-token top-1 stuck near 0.30. An untrained token in a bag is isotropic noise inside the centroid.

The previous order probe (`experiment/order-aware`) is not this encoder. A sign gate can store position, and a one-layer transformer plus a mean pool does not: reverse-cosine stayed 1, because the pool throws the trajectory away. Phase C does not mean-pool.

The readout is a causal transformer with RoPE on queries and keys, depth 4, 4 heads, dropout 0.1, width 128 or 256. A learned readout token is appended after the real tokens. Pads sit to its right and are masked, and the readout's rotary position is the true length, so padding does not move it. The field vector is L2-normalized. RoPE is how position enters the attention logits. The causal readout is the aggregation, so the result is the end of a trajectory rather than a centroid. Both are required. RoPE followed by a mean would be the arm that already failed.

Recurring stems are stored as sorted bags, so alphabetical position is not the variable slot. Those rows are presented as `[kernel_0, kernel_1, vary]`. The set of tokens is unchanged, so a mean pool of the same row is still the S3 control. Broad rows and live mouth lines keep their authored order.

## The anchor, and why it is not the S2 mean

An unanchored readout, same loss and lr 0.01, is the collapse the completion finding already named. On stems only, 15 epochs: output participation 5.2, train top-1 0.19, novel-tuple top-1 0.18 and falling. The table was being dragged down with it (embedding participation 98 → 23).

The S2 residual would stop that collapse by mixing the full embedding mean back in. That mean is the dilution this experiment is here to get out of. An orthogonal add cannot cancel a component that already sits inside the anchor.

The residual that applies is the mean of every real token except the last. On a role-ordered stem that is the kernel, and the partner — trained or OOV — is not in it. A one-token row keeps its only token. The stack reads a detached copy of the embeddings and is added orthogonal to that prefix, which is the S2 protection with a different vector. Embeddings train through the prefix only. The slot token's embedding gets no gradient.

At stems-only, epoch 80, seed 0: output participation **45.4**, embedding participation **76.1**, stack-only participation **7.6**. The RoPE stack is still the low-rank basin. The prefix anchor is what stays legible as a cloud. Swapping the two kernel tokens leaves the vector almost unchanged (swap cosine 0.93–1.00), because that anchor is a mean of those two. Reversing the row, which pulls the slot into the anchor, moves it (reverse cosine 0.51–0.67). Output norm is 1.0 at every grid point, minimum and maximum.

## The grid

Same fractions as the published S3 frontier, including 0.70. Same generator, same mix, same metrics, dim 128, 80 epochs, lr 0.01, weight decay 0, rhythm weight 0, cond scale 0, seed 0. The unigram bar is still 0.1852, so 3× is **0.5556**. Recall is the phase-0 mouth on the live holdout, full line, glue included.

| Recur fraction | Mean-pool tuple | Mean-pool OOV | Mean-pool recall@8 | Order tuple | Order OOV | Order recall@8 | Order PR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.004 | 0.003 | **0.701** | 0.004 | 0.003 | 0.357 | 40.6 |
| 0.20 | 0.178 | 0.104 | **0.706** | 0.339 | **0.345** | 0.342 | 47.2 |
| 0.40 | 0.278 | 0.106 | **0.659** | 0.433 | **0.407** | 0.328 | 47.8 |
| 0.60 | 0.369 | 0.167 | **0.614** | 0.439 | **0.434** | 0.286 | 55.5 |
| 0.70 | 0.443 | 0.205 | 0.571 | 0.474 | **0.458** | 0.295 | 51.4 |
| 0.80 | 0.500 | 0.208 | 0.535 | 0.489 | **0.469** | 0.242 | 51.5 |
| 1.00 | **0.611** | 0.298 | 0.293 | **0.613** | **0.576** | 0.138 | 45.4 |

Seed 1 at stems only: tuple **0.613** (3.31×), OOV **0.629**, recall **0.152**, unseen-kernel 0.019. Same miss, and the OOV number is higher, not a seed accident.

Unseen kernels stay near 0.02–0.05 on the whole grid. The model is not inventing a pair it never trained.

Content-only mouth (glue stripped, not the gate) peaks at **0.429** on broad data and is 0.205 / 0.199 at stems only. Glue is a slice of the mouth loss. It is not the loss.

## Verdict

**The joint gate does not clear.** No ratio has recall@8 ≥ 0.60 and novel-tuple top-1 ≥ 3× the unigram at the same time. The best maximin point is recur fraction 0.20 (tuple 0.339 = 1.91×, recall 0.342). Mean-pool's best joint was fraction 0.80 (tuple 0.500, recall 0.535). Order-aware moves that point the other way because the mouth never gets near 0.60, including on broad data alone, where mean-pool scores 0.70 and this encoder scores 0.36.

**The OOV ceiling does break.** Mean-pool novel-token top-1 never rose above 0.298. This encoder is past 0.30 from recur fraction 0.20 up, and at stems only it is 0.576 / 0.629. That is the slot result: an untrained partner is not inside the anchor, so it does not pull the kernel off its direction. Tuple top-1 at stems only matches mean-pool (0.613 vs 0.611, both 3.3×). The gain is the OOV slice, not a better kernel memorizer.

The two numbers still move apart. Fixing the blank's noise-dilution spends the mouth. One vector is still not both faculties. The banked S2 checkpoint remains the retrieval organ. This encoder is a blank reader.

Dim 256 is the same module and returns a unit vector (tested). It was not swept. S2's width gap on the mouth was 0.69 vs 0.66. A second width is not a reason to expect 0.36 to become 0.60.

## NOTES

For the gate.

**Judgment calls.** Causal RoPE plus a readout token, not the sign gate and not attention-then-mean. Role order on recur rows only. The unanchored stack was measured for 15 epochs and rejected before the grid. The prefix anchor is the residual that does not put the slot back into the centroid. Dropout 0.1 and depth 4 match the S2 stack. lr stayed 0.01.

**Field shape.** One float32 vector, dim 128 on the grid, L2 norm 1.0 on every scored row (min and max). Dim 256 constructs and normalizes the same way. It is not a `Generator` state dict: no ecology, no address space. The sidecar JSON says not to load it into the live mind. `embedding_residual` on this checkpoint means the prefix anchor, not the S2 full-bag mean.

**What integration would take, if anyone still wanted the blank reader.** Do not replace `Generator.forward`. Keep the banked mouth as the field vector the current decoder reads. A second path would role-order a stem, run this encoder, and hand the unit vector to a completion head. The field can store that vector beside the mean-pool vector. It should not be asked to be the mouth. On this grid, substituting it for the mouth drops recall@8 from 0.69 to at best 0.36.

Live corpus hashes are the Phase B ones (`rhythm_train` `f5d60859…`, `rhythm_holdout` `61c93de1…`). The worktree checkout had arrived with CRLF; those two worktree copies were rewritten to LF so the hash matched. The main checkout was not modified. Nothing was merged and nothing was pushed.
