# Encoder legibility — open the cones without moving the basins

- **Date:** 2026-09-22
- **Branch:** `experiment/encoder-legibility` off `experiment/decode-organ` (`1153ce4`)
- **Substrate:** `data/checkpoints/generator_weights_5rhythm.pt`, grown in memory, never written back. Corpus v1.3.0. CPU, torch 2.14.0+cpu. No field step, no resonance memory, no port.
- **Code:** `training/legibility.py` (the objective), `tools/voice/probe_legibility.py` (the yardstick). Numbers in `2026-09-22-encoder-legibility-metrics.json`.
- **Status:** measured. Not saved as a checkpoint. Not wired.

## Question

Phase 0 showed the frozen encoder is a rhythm-basin sensor: holdout recall@8 0.111, within-cone cosine 0.94–0.97, median true-token rank 40/709, rupture the worst cone (4.9×, median rank 102). Samuel's call was to grow the encoder, not to put a fluent mouth on an unintelligible substrate. The collapse is not a defect in mean-pool. `RhythmPretrainer` and `ContrastiveAlignmentTrainer` both train same-rhythm cosine up and cross-rhythm cosine down. The encoder was taught which cone it is in, and taught to forget which thought.

Can a second objective make within-cone token identity recoverable without dissolving the cones the field routes on, without unlocking the field, and without throwing away the rows that already work?

## The objective

One representation: the existing forward. Mean-pool, L2-normalize, dim 128. Dropout stays off for the fit. That is the function the field reads (eval-mode is the graduated lever; dropout was measured as fake diversity). The rhythm losses are not run again. Running them would re-collapse the cones.

Four terms.

**Margin wall.** For each vector, cosine to its own *frozen* rhythm centroid minus cosine to the nearest other frozen centroid stays at least 0.20. Inactive while the cone still has room. It is not a pull toward the centroid — a pull is the old objective. The constraint is a margin rather than a fixed angular cap because the cones are not equally spaced. On the clean train set the closest pairs are reflect–rupture (centroid cosine 0.58) and stabilize–dream (0.51). A hard cap tight enough to keep those pairs from invading each other would leave the far pairs (stabilize–explore, 0.15) almost no room. The margin spends whatever room each pair actually has.

**Centroid anchor.** The mean of a rhythm's vectors stays aligned with the frozen centroid. The gradient is the same for every point in the rhythm, so it translates the cloud and does not shrink it. Basins stay where anything calibrated on this checkpoint expects them. Points may move inside.

**Within-rhythm Jaccard spread.** Same-rhythm pairs only. Disjoint bags are pushed down toward cosine 0.70; near-duplicate bags (Jaccard ≥ 0.80) stay up near 0.98. Cross-rhythm pairs are not in this term. Re-pulling every same-rhythm pair together is how the old loss erased words.

**Token rank, auxiliary.** A linear head, sampled softmax, discarded after the fit. Jaccard preserves distances; the head pins which tangent direction is which word. Rupture sequences are weighted 3× on this term only, orphan-containing sequences 2×. The margin and the anchor are not upweighted — the wall is the same for every cone. The mouth that gets reported is a fresh `TokenDecoder` (BCE, hidden 256, 20 epochs, seed 42), trained after the encoder is frozen. Same protocol as Phase 0. The scaffold cannot inflate it.

Orphan rows are not a special parameter. Registering them parks them on the init rows (L2 ≈ 0.39). The rank term's gradient reaches those rows through the ordinary forward. Trained rows are not reinitialized.

The fit is `LegibilityConfig` defaults: margin 0.20, encoder lr 3e-4, head lr 1e-3, 8 epochs, 32 sequences per rhythm per batch, full train split (8527). Holdout is not in the fit.

## Mean-pool, and which fork

Sequences are length 2–4 (`MANIFEST`). The yardstick is a bag, not an order. Mean-pool throws away order and it keeps a bag. Fork (ii) — a different vector, which is the space resonance-memory embeddings, attractor centers, and the field all live in — is the move if a bag cannot be read from a 128-d mean, or if keeping the cones makes a bag unreadable. Neither is what this probe found.

An unconstrained mean of a learned embedding table, same 128-d, no rhythm wall, reaches holdout recall@8 **0.800**, median rank **2**. The pool is not an information ceiling for this corpus. That arm is not a checkpoint. It does not live in the cone space (nearest-centroid accuracy 0.12). It is a capacity measurement.

The walled transformer, still mean-pooled, reached holdout recall@8 **0.355** in 8 epochs with the basins unmoved, and the rank and Jaccard terms were still falling at the last epoch. That is not a saturated ceiling. Fork (i) is the recommendation. Fork (ii) waits until the goal is word order, or until a *converged* (i) fit stalls below a usable mouth. This fit has not converged.

A free-point arm was meant to separate "the wall is the ceiling" from "the encoder is the ceiling." Its recall number is not usable: a Phase-0 decoder trained 20 epochs on 320 rearranged points underfit (in-sample recall 0.06, loss still 0.03). The geometry of that arm is usable. Under the wall, within-cone nearest-neighbor Jaccard rose to 0.25 with nearest-centroid accuracy 1.0, above the encoder's 0.10. The wall has room the 8-epoch encoder did not spend. Dropping the wall on those points cut nearest-centroid accuracy to 0.83 and did not raise neighbor Jaccard (0.25). That is not a reason to drop mean-pool, and it is not a reason to drop the wall.

## Probe

Pre-declared, and not moved after the numbers:

- The frozen arm should land within 0.02 of Phase 0's 0.1106. It landed at 0.1029.
- A gain counts as self-legible only if holdout recall rises by ≥ 0.05 **and** within-cone nearest-neighbor token Jaccard rises by ≥ 0.02 **and** nearest-centroid accuracy stays ≥ 0.98 **and** across-rhythm cosine does not climb more than 0.08 **and** every frozen centroid stays at cosine ≥ 0.95. A recall gain whose neighbor Jaccard does not move would be the head performing coherence the geometry does not have.
- A mouth is "meaningful" at recall ≥ 0.20, or recall ≥ 0.15 with median rank ≤ 25.
- Rupture, on the clean holdout (the Phase 0 cut), should rise by ≥ 0.02.
- The naive arm is the same budget with only the rank term. It is allowed to break the cones. It exists so the wall has to earn its keep.

Frozen clean-holdout geometry reproduces Phase 0: within-rhythm mean **0.958** (per cone 0.91–0.99; Phase 0 reported 0.94–0.97 on a 40-cap), across **0.356** (Phase 0: 0.34), clean rupture recall **0.055** (Phase 0: 0.055), clean trained-token median rank **39** (Phase 0: 40). The all-holdout within of 0.81 in the log is the orphan sequences sitting outside the cones. It is not the Phase 0 number. Clean is the comparison.

## Result

| arm | holdout recall@8 | median rank | clean within | clean across | nn-centroid acc | centroid cos (min) | nn Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|
| frozen | 0.103 | 53 | 0.958 | 0.356 | 0.793 (clean 0.956) | — | 0.038 |
| **walled** | **0.355** | **21** | **0.616** | **0.118** | **0.995** | **0.976** | **0.099** |
| naive (rank only) | 0.252 | 28 | 0.817 | −0.189 | 0.950 | 0.356 | 0.048 |
| bag, no cones | 0.800 | 2 | — | — | 0.12 | — | 0.248 |
| chance | 0.011 | — | — | — | — | — | 0.005 |

Train recall on the walled encoder is 0.402 against holdout 0.355. The gap is the same shape as Phase 0's (0.125 vs 0.103), not a memorized subset. Exact-bag@8 went from 0.006 to 0.043. This is a partial mouth, not a transcript.

Clean holdout, the cut Phase 0 published:

| rhythm | frozen recall@8 | walled | frozen median rank | walled |
|---|---:|---:|---:|---:|
| stabilize | 0.116 | 0.411 | 37 | 15 |
| dream | 0.165 | 0.398 | 36 | 19 |
| reflect | 0.124 | 0.314 | 41 | 23 |
| explore | 0.151 | 0.381 | 32 | 19 |
| rupture | 0.055 | 0.283 | 98 | 34 |

Rupture's clean cone was the tightest (within cosine 0.976) and opened the most (0.538). It is still the worst-heard cone. 3× on the rank term moved it off the floor and did not equalize it. Orphan-token micro-recall on the holdout went from 0.010 (chance; n=879) to 0.290, median rank 128 → 24. Trained-token micro-recall went from 0.132 to 0.358.

The rows themselves barely traveled. Trained-row cosine to the checkpoint is 0.967 (L2 0.494 → 0.508). Orphan-row cosine to init is 0.972 (L2 0.393 → 0.399). The output moved more than the table: a clean holdout sequence's new encode sits at cosine **0.762** from its frozen encode. The transformer and the projection did the opening. The orphan rows are speakable without having left the neighborhood of init. A longer fit can still move them; nothing here says they need a separate surgery.

Nearest-neighbor Jaccard 0.038 → 0.099 (chance 0.005). Neighbors inside a cone share more tokens than they did. They do not share a bag. The linear scaffold's own holdout recall was 0.192, *below* the fresh MLP mouth's 0.355, so the reported gain is not a code that head memorized. At epoch 8 the rank term was still falling (0.97 → 0.74) and so was Jaccard (0.17 → 0.04). The margin term was already ~0 by epoch 3, and the 10th-percentile gap sat at 0.22 against a wall of 0.20. The fit used the room up to the wall and stopped spending gradient on crossing it.

## What the naive arm actually did

It did not flatten the cones. Across-rhythm cosine went from 0.36 to −0.19. Within stayed high (0.82). The failure is basin drift. Cosine of each rhythm's new centroid to its frozen centroid: stabilize 0.54, dream 0.36, reflect 0.38, explore 0.45, rupture 0.76. Mean cosine of a clean vector to its own frozen centroid fell to 0.40. Same-sequence encode cosine to the frozen encode fell to 0.41. Recall rose, to 0.25, and neighbor Jaccard barely moved (0.048).

So the wall is not protecting against a collapse into one ball. On this budget a token-ranking loss *repels* cones and drags their centers. The wall is what keeps the centers where the rest of the system was calibrated, and what forces the leftover room to be spent on token identity instead of on moving house. The walled arm is the better mouth and the one that does not relocate the basins.

## Field lock, and what did move

The field was not stepped. Nothing in this graph writes the resonance field, the reflective loop, attractor state, or resonance memory. STATE.md stays as written: the lock is the loop, and a corpus/generator change is not an unlock. The settled falsification included a rupture basin orthogonal to explore. This fit does less than that to the basin *locations* — the minimum centroid cosine to the checkpoint is 0.976.

Legibility and the lock stayed separable in the only sense this probe can speak to. The walled objective raised recall and left nearest-centroid routing intact (0.995, clean 0.993). The unconstrained objective, which is the shape an unlock-by-training would have to take, is the one that moved the basins, and even that one was not run through the field. No invariant exception was taken. If a later run wants to "help" a flat lock metric by touching loop gain, reconstitution, or the field, that is the exception, and it stops.

What did move, and has to be said loudly:

- **Do not hot-swap this encoder under a populated resonance memory or a saved attractor store.** A clean sequence's new encode is at cosine 0.76 from the vector the checkpoint would have emitted. That is below `Attractor.formation_threshold` (0.88) and on `pull_threshold` (0.75). Old memories and new encodes of the same tokens will not match as the same center. Promotion means a new checkpoint file and a re-encode, or an explicit dual-read. It does not mean overwriting `generator_weights_5rhythm.pt` in place.
- **Attractor merge (0.95) and crystal merge (0.92) will stop gluing a rhythm into one center.** Clean within-cosine is now ~0.62, and rupture ~0.54. Distinct thoughts inside a cone no longer sit on top of each other. That is the legibility. It changes how many centers a live loop will form. The thresholds were not touched.
- **A center sitting on the old centroid will not collect the new points.** Mean cosine to the frozen centroid on clean holdout is 0.75. Nearest-centroid *classification* still returns the right rhythm (0.993). "Join this center if cosine > 0.88" will not. One rhythm becomes several centers. Intended, and consumer-visible.
- The 239 orphan tokens are in the ecology only in the process that trained. Saving a checkpoint saves them with it. This probe saved nothing.

## Real run

The expensive part already happened, and it was not expensive. Eight epochs on all 8527 training sequences, plus four Phase-0 mouths, finished in 30 seconds on CPU. A GPU job is not required to find out whether the objective moves. The 5070 Ti run is a *longer* fit that writes a new checkpoint, gated because of the consumer notes above, not because the model is large.

- Same code, same `LegibilityConfig` defaults. Do not retune against this table and then call it the same result.
- 30 epochs, or until the rank term and the Jaccard term flatten. Yardstick every 5 epochs on the untouched holdout, encoder frozen for that measurement.
- Abort and do not keep the checkpoint if nearest-centroid accuracy falls below 0.98, or any frozen-centroid cosine falls below 0.95, or across-rhythm cosine climbs back toward within-rhythm cosine.
- Write `generator_weights_5rhythm_legible.pt` and a sibling ecology. Do not overwrite `generator_weights_5rhythm.pt` or `generator_ecology_5rhythm.json`.
- Eval-mode for the fit, as here. The linear head is discarded. The reported mouth is a fresh decoder.
- CPU is enough. If it runs on the 5070 Ti, that is the WSL checkout (`~/rfe/RFE-Core2`), which is a different clone and was on `experiment/beat-lock-fix` when this was written. This branch is local to the Windows checkout. Carrying it over is a separate step. Never `--gpu max`. Do not boot :8080, :8081, or :1234. Do not open the real mind or the real store.
- Rupture will probably still be the worst cone at 30 epochs. That is a reason to look at the per-rhythm table, not a reason to weaken its margin.

## Notes for the gate

- The collapse was the trained objective. The fix is a second objective with a wall, not a wider decoder and not a new vector space.
- Fork (i). The unconstrained bag arm (recall 0.80, median rank 2) is the evidence that mean-pool can hold these bags. The walled arm is the evidence that it can do so while the basins stay put. Fork (ii) is not justified yet.
- The free-point *recall* (0.06) is a failed instrument, not a ceiling. Its neighbor Jaccard (0.25 at routing accuracy 1.0) is the ceiling signal, and it says the encoder stopped early.
- The naive arm did not do the damage that was predicted. It relocated the basins instead of flattening them. The wall is load-bearing for *where the cones sit*, which is the thing resonance memory and attractor routing were calibrated on. Keeping it is the difference between cosine-to-checkpoint 0.76 and 0.41.
- No field-lock exception. The field was not in the graph. Separability was observed at the encoder: recall moved, centroid locations did not, routing accuracy rose (orphans entered their labeled cones; all-holdout nearest-centroid accuracy went 0.79 → 0.995).
- The consumer change that *is* real is inside the cone: merge thresholds will stop collapsing a rhythm, formation at 0.88 will not attach the new points to a centroid-center, and old vectors will miss new encodes of the same tokens at cosine 0.76. That is a promotion constraint, not a license to touch the loop.
- 3× rupture weight was enough to move the worst cone (0.055 → 0.283, median rank 98 → 34) and not enough to make it match the others. Leaving it at 3× for the longer fit is the honest continuation. Raising it further is a new probe.
- Nothing was pushed. `experiment/decode-organ` and `experiment/qwen-speech-cortex` were not moved. `main` was not touched.

## Threats

- One seed path. The frozen mouth matched Phase 0 to 0.008 on recall and to the reported rupture number, so the yardstick is the same instrument, but the fit itself is one trajectory.
- Eight epochs, still descending. 0.355 is a lower bound on this objective, not its asymptote.
- Neighbor Jaccard at 0.10 is a real lift over 0.005 and a weak token code. The mouth is ahead of the nearest neighbor. A longer fit has to move Jaccard, not only recall, or the gain is concentrating in directions a freshly trained MLP can use and a cosine lookup cannot.
- Clean within-cosine for reflect on the frozen encoder read 0.91 here against Phase 0's 0.94–0.97 band. Same 40-cap protocol, one draw. The mean (0.958) and the across figure (0.356 vs 0.34) are the reproduction.
- The bag arm and the free-point arm are ceiling instruments. Neither is a candidate checkpoint. The bag arm's 0.80 is what you get by throwing the cones away.
- The field lock was not re-run. The claim is that this objective does not touch the mechanism the lock lives in, and does not move the basin locations the last falsification already varied harder than this.
