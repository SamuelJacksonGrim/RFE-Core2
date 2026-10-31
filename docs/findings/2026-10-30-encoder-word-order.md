# Why does the corpus encoder ignore word order, and what does it take to get order into the sentence vector?

- **Date:** 2026-10-30
- **Substrate:** live Generator (dim 256, 4 heads), trained by the corpus driver `corpus\scripts\train_v2.py`
  (outside this repo) on Samuel's corpus rows; outside eval sets never trained on.
- **Probe:** `corpus\scripts\order_probe.py` (masked-head order sensitivity), `corpus\outside-eval\score_encoder.py`
  (BLiMP, PAWS, SNLI, MNLI, HANS...), `corpus\outside-eval\readout_probe.py`, `oc_diag.py`, `oc_crowd.py` (Grok);
  Generator change on branch `encoder-position-balance` (commit 941eea3).
- **Status:** active (full-scale confirmation of part 2 pending: run 1c)
- **Depends on:** `2026-09-23-completion-production` (the embedding residual and the detached transformer input)

## Question

Encoder run 1 (full corpus, 160M rows, 2026-10-28) scored near chance on the word-order tests: perm_delta 0 at every
eval, PAWS AUC 0.475, HANS non-entailment 0.04. The working belief was that order needs more scale or RoPE. What is
actually stopping it, and can the sentence vector (the field vector this repo consumes) be taught order without losing
meaning?

## Part 1: order at the token level

### Pre-declared (in `run_posbal_ab.ps1`, before the run)
- SUCCESS: with `position_balance`, shuffle and near deltas and perm_delta clearly above control (shuffle delta >=
  0.05 CE); holdout and masked CE no worse than control by more than slice noise (~0.02).
- FAILURE: order deltas about equal to control, or CE worse beyond noise.

### Result (observed)
Run 1 checkpoint, masked head on 4,000 ordered holdout windows: CE 6.8926 as written; +0.0001 with the words next to
the blank swapped; +0.0007 with every word shuffled. Mean norm of the sqrt(dim)-scaled token embeddings 1524.6 against
the sinusoidal PE's 11.31 (~135x).

Slice A/B, rows-ab-soft, 6M rows, seed 0, identical except the flag:

| | control | position_balance |
|---|---|---|
| shuffle delta (CE) | +0.010 | **+1.895** |
| near delta (CE) | +0.002 | **+1.136** |
| perm_delta | 0.0003 | **0.212** |
| masked CE | 7.502 | **6.782** |
| holdout CE | 7.426 | 7.410 |
| BLiMP syntax | 0.483 | **0.532** |
| PAWS AUC | 0.4745 | 0.4753 |

Full corpus, run 1b = run 1 + the flag (160M rows): holdout 6.833 (run 1 6.922), masked CE 5.297 (6.507), masked
top-1 0.173 (0.085), perm_delta 0.302 (0.000), shuffle delta +2.967 (+0.0007), BLiMP 0.587 (0.572), SNLI 0.639
(0.632), PAWS 0.476 (0.475), BLiMP semantics 0.579 (0.621).

### Interpretation
The embedding table trains at a fast LR with no weight decay; its rows grow far past init and swamp the fixed
sinusoidal signal they're added to, so after norm-first LayerNorm the position share is ~1% and the transformer sees a
bag. `Generator.position_balance` scales each token embedding to the PE norm before the add (default off; run 1
reproduces exactly with it off). The belief that order needed more scale was wrong: it was never visible.

## Part 2: order in the sentence vector

### Observation that framed it
With order fixed per token, PAWS did not move. Grok's readout study (posbal-B checkpoint) found no readout recovers it
without training: pooled token states move ~2% under a full shuffle; reweighting the residual mix changes PAWS by
0.0005.

### The misread (recorded on purpose)
I (Claude) then guessed the embedding residual was the limit: the output is `u + s_orth` with u (the order-blind
embedding mean) ~60% of the energy and locked at cosine >= 1/sqrt(2). An order-contrastive objective (SimCSE dropout
positives + interior-shuffle hard negatives, on the mixed vector, table protected by the detach) at weights 0.1 and
0.3 then failed its pre-declared lines: interior cosine 0.9985 / 0.9984 (bar: 0.02 below control), loss stuck at 0.93
for both weights. Grok's diagnosis (`oc_diag.json`) overturned the guess: the mix can express order. 0.93 was a tie
between the dropout positive and the hard negatives; the order gradient was ~1% of the masked gradient, so the step
never moved; trained alone for 2,000 steps on the same checkpoint, interior cosine went 0.998 -> 0.515. The failure was
optimization pressure, not representational capacity. (Raphael, GPT, reviewing with Samuel, reached the same reading:
change the objective's share before the architecture.)

### Result (observed), slice, 6M rows, seed 0, control = same settings with the objective off

| arm | interior cos | other-sentence cos | PAWS | SNLI | MNLI | holdout CE |
|---|---|---|---|---|---|---|
| control | ~0.998 | ~0.068 | 0.4753 | 0.6184 | 0.5436 | 7.4102 |
| fixed w = 2 | 0.618 | 0.106 | 0.5186 | 0.6025 | 0.5284 | 7.4141 |
| fixed w = 6 | 0.554 | 0.106 | 0.5264 | 0.6018 | 0.5264 | 7.4191 |
| balanced F = 0.1 | 0.905 | 0.147 | 0.4800 | 0.6125 | 0.5389 | 7.4050 |
| balanced F = 0.2 | 0.748 | 0.111 | 0.5016 | 0.6120 | 0.5265 | 7.4077 |
| balanced F = 0.4 | 0.613 | 0.082 | 0.5097 | 0.6012 | 0.5239 | 7.4090 |

(Balanced = the order gradient scaled each step to F times the masked gradient. The control logs no order numbers; its
cosines are from readout_probe / oc_crowd on the identical checkpoint.) The word table never receives order gradient
(the detach); the other-sentence rise comes from the transformer vector s no longer pointing every sentence the same way
(unit-s other cosine 0.86 -> 0.10), not from the table.

### Interpretation
Order enters the sentence vector in a clean dose-response, and PAWS clears chance for the first time in the project.
It costs NLI: about 0.6 SNLI points at F = 0.2, ~1.6 at the stronger settings, and 1.5-2 MNLI points. No arm met every
pre-declared success line (F = 0.2 misses the other-sentence line, +0.04 against +0.02). It's a real trade, small but
not free.

### Which mechanism (2026-10-31; Raphael's three-way split)
Raphael (GPT) separated three possible causes: direct gradient conflict, representational competition in the shared
transformer, and projection interference. Grok measured gradient alignment against the frozen SNLI/MNLI probes' own
loss (`corpus\outside-eval\grad_align.json`): ~0 at the untrained control; at F = 0.2, mildly opposed in the shared
transformer (order vs SNLI -0.10, vs MNLI -0.17) and ~0 in the projection, where only 6% of the order gradient's
energy sat but ~60% of the NLI gradient's. Then the test: a separate structural head (`--order-struct`, a second
128-dim projection trained only by the order loss; the field vector's projection gets no order gradient).

Slice, 6M rows, two seeds (seed 0 / seed 1), each against its own control:

| vector | dims | PAWS | SNLI | MNLI |
|---|---|---|---|---|
| control field (Matryoshka prefix) | 128 | 0.475 / 0.476 | 0.589 / 0.598 | 0.531 / 0.532 |
| head arm, field prefix | 128 | 0.475 / 0.476 | 0.590 / 0.598 | 0.533 / 0.532 |
| control field | 256 | 0.475 / 0.476 | 0.618 / 0.625 | 0.544 / 0.541 |
| head arm, field | 256 | 0.476 / 0.477 | 0.621 / 0.624 | 0.545 / 0.545 |
| head arm, field prefix + head | 128 + 128 | 0.524 / 0.528 | 0.611 / 0.611 | 0.537 / 0.540 |
| head arm, field + head | 256 + 128 | 0.524 / 0.527 | 0.634 / 0.632 | 0.551 / 0.547 |
| head arm, head alone | 128 | 0.536 / 0.536 | 0.528 / 0.525 | 0.463 / 0.450 |

Interpretation: projection interference. Mild direct conflict exists in the shared transformer but costs nothing once
the order updates are off the semantic projection: the field vector is unchanged on both seeds. Representational
competition isn't supported: the shared transformer carries both. Word order now lives in the head; combined with the
field it beats the same-width field on PAWS (+0.05) and, at 128 + 128 vs 128 or 256 + 128 vs 256, on SNLI and MNLI too.
At equal total width (128 + 128 vs 256) it trades ~1 SNLI point for the PAWS gain. A note on my own first read of
these numbers: the initial "combined" comparison set a 128 + 128 vector against the 256-dim control and looked like a
small SNLI cost; scoring the fair controls (`--vectors field128,combined384`) showed the dip was the halved semantic
width. Wider vectors also hand the linear NLI probe more features, which flatters the 384-dim row.

## Threats / confounds
- One seed per arm on a 5% slice; SNLI/MNLI differences under ~0.01 are inside plausible noise.
- PAWS coverage rule drops pairs with shared OOV words (13,239 of 16,000 scored).
- The control's sentence-order numbers come from a separate probe on the same weights, not its training log.
- Slices answer method questions; the size of the trade at full scale is unmeasured.

## Open / next
- Which vector RFE-Core2 consumes (field only, field + head, at what width) is the architect's call; the head lives
  in the corpus driver (`corpus\scripts\struct_head.py`), and adopting it means a second projection in Generator.
- Full-scale run 1c (run 1b + `--order-contrast-balance 0.2 --order-struct`) started 2026-10-31; then the decode test.
