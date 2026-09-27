# Phase B — Co-balanced Completion Corpus + Tooling (Kaizen roadmap)

**Owner of execution:** Grok (Kaizen loop, checks off as it goes). **Gate:** Ember. **Architect:** Samuel.
**Companion:** `SPEECH_CORTEX_PROGRAM.md` (the keystone finding). Work on a branch off
`experiment/completion-objective`; scratch/isolated; nothing promotes to the live corpus/mind/RM without
Ember's gate + Samuel's sign-off. Author `Samuel Jackson Grim <samgrim97@gmail.com>`, co-author
`Ember <emberkindled@gmail.com>`, never anthropic/Claude.

## How to run this roadmap (the Kaizen mechanic)
For each slice: **BUILD → MEASURE against the STANDARD → if below standard, ITERATE (adjust + re-measure) →
when the standard is met, CHECK THE BOX and record the measured numbers here → move to the next slice.**
Never check a box on a story — only on a number that met the standard. Re-run to confirm; don't trust a single
readout. Where slices are marked **[swarm]**, run independent lanes in parallel (git worktrees). **Hand off to
Ember** at each `GATE` marker (report the numbers); do not proceed past a FAILED standard without flagging it.
Keep this file updated (check boxes, paste numbers) and commit it each time you advance.
**Standard direction:** every standard that PRODUCES a result is **"baseline or better, never worse"** — a number
that BEATS the baseline PASSES (it's a win, not a deviation to flag; a frozen baseline that rejects an improvement
is the wrong gate). When a result beats a baseline, **the new number REPLACES the old as the reference** (the
benchmark ratchets up; we never keep grading against a stale floor).
**The Kaizen iterate-loop applies ONLY to the IMPROVEMENT slices (S3–S6)** — where you tune toward a quality bar.
**S1 and the reproduce-part of S2 are BUILD-RIGHT-AND-RUN-ONCE, not iterate-to-a-number.** Do NOT loop trying to
force a reading to equal an old published number — that wastes time and tokens chasing a target that was never
ground truth. Build the tool correctly, run it, verify it's internally consistent, record whatever it truthfully
reads, move on. A reading that differs from the prior number is a finding to explain, not a target to grind toward.

## North star (what "done" means for B)
One corpus + recipe such that a completion-trained encoder is SIMULTANEOUSLY:
- **Legible** — decode-organ recall@8 >= 0.66.
- **Generalizes** — held-out completion top-1 on NOVEL contexts >= 3x the rhythm-unigram baseline (not just
  memorized/similar contexts).
- **Healthy manifold** — participation ratio >= ~50 @128 / ~80 @256; effective rank high; no collapse toward 4;
  depth-gap in the level range (corpus-health gate).
- **6 rhythms incl witness separable** — rhythm probe >= 0.95, worst-pair centroid cosine minimized (maximin),
  witness holds its own basin.
- **Level** — no deep basin, no hub (the corpus-health `corpus_health.py` gate).
- **Production-real** — works with the embeddings+residual config; full-stack trainable WITHOUT collapse to ~4.8.

---

## S1 — Manifold-health tracker (instrument) [swarm]
- [x] BUILD `LatentManifoldTracker` (participation ratio, effective rank, spectral entropy, spectral anisotropy,
      condition number) per the data-pipeline strategy doc; GPU-cheap, no-grad, per-batch.
- **STANDARD (GATE — CORRECTNESS, not "match the old number"):** a FIXED checkpoint has ONE true PR, so the
      tracker must produce a **verifiably correct** reading — cross-checked by an independent computation (e.g. a
      direct covariance-eigenvalue calc), not merely "equals the previously-published number." The old numbers
      (frozen ~3.4, completion_128_emb ~47.8, completion_256_emb ~81.9) are PRIOR MEASUREMENTS by earlier runs, NOT
      ground truth. If the new tracker disagrees, DETERMINE WHICH IS RIGHT — and if the tracker is the accurate one
      (the checkpoint is richer than recorded, i.e. BETTER), the tracker is correct and the old number is updated.
      Only an internally-inconsistent / unverifiable reading fails.
- Measured: `PR_frozen=3.423  PR_c128=47.806  PR_c256=81.917  (cross-check method: numpy covariance eigvalsh vs torch.linalg.eigvalsh vs numpy SVD of the centered unit-norm cloud, same 1505 live-holdout lines; max |delta| 1.4e-14 vs torch, 8.0e-9 vs SVD; geometry.population agrees at 3 decimals. Roy-Vetterli effective rank 3.877 / 71.508 / 129.221, which is not eff_rank_512cap.)`

## S2 — Completion training harness + collator [swarm]
- [x] BUILD the completion collator (mask stem tokens with ignore_index -100, loss on filler tokens only) + the
      training loop with the residual fix baked in (orthogonal embedding-mean mix; transformer reads a detached
      copy so it can't drag the table down).
- **STANDARD (GATE — BASELINE OR BETTER):** reproduces the completion result on the current corpus at the baseline
      floor OR ABOVE — decode recall@8 **>= 0.61** (0.66–0.69 is the residual-config target; HIGHER passes, a higher
      number is a WIN not a deviation), PR **>= ~35/63** @128/256, AND the residual config trains the FULL stack
      without collapsing to ~4.8. Only a result WORSE than baseline fails.
- Measured: `recall@8=0.6936@128 / 0.6573@256  PR128=56.581  PR256=73.531  fullstack_PR=56.581/73.531 output (stack-only 0.612/0.729)`

## S3 — Entropy-gated recurring-stem generator (the co-balance problem)
- [ ] BUILD the generator: recurring context stems, many rhythm-appropriate fillers per stem, entropy floor
      **H(F) >= 2.5 bits** per stem; stem-filler extraction across the domains (relational-memory kernels =
      where the rhythms live; plus structural/logic patterns). Dedup order-invariant bags; glue as scaffolding.
- **STANDARD (GATE — the hard one):** a corpus from it yields a completion encoder where BOTH hold at once:
      held-out completion top-1 on NOVEL contexts >= 3x unigram, AND decode recall@8 >= 0.60. This is the
      "legibility checkpoint != blank-filling checkpoint" problem — **Kaizen-iterate the broad-coverage vs
      recurring-stem RATIO until both clear.** Report the ratio that worked.
- Measured: `FAIL — no ratio clears both. best joint broad:recur=0.25 (recur fraction 0.80, seed 0 / seed 1): novel_tuple=0.500/0.472 (unigram=0.185, 3x bar=0.556, single-token ceiling=0.374) recall@8=0.535/0.530. recur-only tuple=0.611 (3.30x) but recall@8=0.293. mouth stays >=0.60 only through recur fraction 0.60 (recall 0.614) where tuple=0.369 (1.99x). OOV-partner top-1 peaks at 0.298. Phase C (order-aware) did not close this box. See the progress log.`

## S4 — 6 rhythms + witness under completion [swarm the authoring]
- [ ] REDO the rhythm/witness structure under the COMPLETION objective (the old contrastive separability is
      superseded). Fold witness in as the 6th (its pulled receptive core). Rhythm carried as a conditioning
      signal, not a contrastive label.
- **STANDARD (GATE):** all 6 rhythms recoverable (rhythm probe >= 0.95); witness holds its own basin;
      worst-pair centroid cosine minimized (maximin, report it); levelness preserved (`corpus_health.py` passes:
      no deep basin, no hub, depth-gap in range).
- Measured: `rhythm_probe=___  witness_basin=___  worst_pair=___  levelness=pass/fail`

## S5 — The co-balanced composite corpus (integration)
- [ ] COMBINE broad-legibility coverage + S3 recurring stems + S4 6-rhythm/witness; level the content-word
      frequency (glue scaffolding, dedup), the whole thing under completion.
- **STANDARD (GATE — maximin):** the composite corpus's completion encoder clears EVERY north-star axis at once
      (legible >=0.66, generalizes >=3x, PR >=50/80, 6 rhythms separable+level). **Kaizen-iterate the composition
      until the WORST axis clears its bound.** No axis may regress to buy another.
- Measured: `recall@8=___  novel_top1=___  PR=___  rhythm_probe=___  worst_pair=___  levelness=___`

## S6 — Production encoder train (128 + 256) [GATE → HAND OFF to Ember + Samuel]
- [ ] TRAIN the final completion encoder on the composite corpus, residual config, at 128 AND 256; save new
      checkpoints (never overwrite existing).
- **STANDARD (GATE):** beats the current best (`completion_256_resid`) on the composite metric; production
      config (embeddings + residual, full-stack-safe) confirmed; no regression on any north-star axis.
- Measured: `best_axis_deltas=___`
- [ ] HAND OFF: report the full result to Ember; Ember gates against the invariants; **Samuel decides promotion**
      into the live corpus/encoder. This corpus is what the Feel/Relate (e8-eea + manifold) node stands on next.

---

## Invariants (every slice)
Scratch/branch only; NEVER touch the live corpus (`data/corpus/rhythm_{train,holdout}.jsonl`), the real mind
(`C:\Users\spamw\.rfe-speech-cortex*`), or the real RM until Samuel promotes. New checkpoints as new files.
Don't disturb :8080/:8081/:1234. Never `--gpu max` (GPU/WSL training is fine, chunked/long runs OK). Measure,
don't assert — re-run before believing a number. Flag anything uncertain rather than checking a box on a guess.

### Progress log (Grok appends: date, slice, result, next)
- (start)
- 2026-09-23 — S1 PASS. `LatentManifoldTracker` on the live holdout (n=1505), one encode per checkpoint. Frozen 5-rhythm residual off: PR 3.422698. completion_128_emb with residual on: PR 47.805656. completion_256_emb with residual on: PR 81.917393. Cross-check: the tracker's numpy covariance eigenvalues, an independent `torch.linalg.eigvalsh` of that covariance, and an SVD of the centered data matrix agree (max abs delta 1.4e-14 / 8.0e-9). `geometry.population` rounds to the same 3 decimals (3.423 / 47.806 / 81.917). Those are the old published figures at the precision they were written (3.4 / 47.8 / 81.9, and the production note's 47.806 / 81.917). No discrepancy to adjudicate. There is no separate data-pipeline strategy doc in the tree; PR is the covariance definition `population()` already used, effective rank is exp(spectral entropy) on the positive eigenvalues, anisotropy is `D * λ_max / sum(λ)`, condition number is `λ_max / λ_floor` with floor `1e-8 * λ_max`. Effective rank is not `eff_rank_512cap` (that older number is 1.848 / 19.305 / 31.85 on these same clouds). Log: `docs/findings/logs/2026-09-23-phase-b/s1_manifold.json`.
- 2026-09-23 — S2 PASS, one run, not retuned. Collator keeps the encoder input as the context only, writes `-100` on every stem position, and supervises one mode-filler slot. The loss is the existing per-row soft cross-entropy (not count-expanded hard labels). Self-check: target distribution matches `pack_targets` to 0, and with the residual flag on the transformer input does not require grad while an encoder parameter still receives grad. Recipe: lr 0.01, weight decay 0, rhythm weight 0, cond scale 0, batch 128, 40 epochs, seed 0, full stack, `--residual`, `--legibility`, tag `_phaseb`. Holdout decode recall@8 0.6936 (128, median rank 1) and 0.6573 (256, median rank 1). Output PR 56.581 / 73.531, confirmed by the tracker on the saved checkpoints (torch and SVD deltas < 1e-8). Above the floor of 0.61 and ~35/63, and the same curve as the prior residual measurement (epoch 0 → 5 → 20 → 40: 82.2/13.5/44.7/56.6 at 128 and 115.4/20.3/58.9/73.5 at 256). The transformer-only stack (residual forced off) is 0.612 / 0.729, the known stripped direction, not a field collapse to ~4.8. New files only: `data/checkpoints/*_phaseb*` (gitignored, same as the other checkpoints) and `train_dim{128,256}_phaseb_s0.json`. Live corpus hashes unchanged. Next: S3 is the Kaizen co-balance slice. Not started. Handing off here.
- 2026-09-23 — S3 FAIL, box left open. Generator `tools/voice/gen_recurring_stems.py`. Entropy floor 2.5 bits; every emitted stem is H=2.7569 (count pattern 5/4/4/3/3/3/2). 3,384 train stems, 24 observations each, 8–18 surface contexts per kernel, domains relational 1,584 / logic 915 / structural 885. Holdout: novel_tuple 540 (partner seen in other kernels, this bag never trained; one-token policy tops out at 0.374, under the 3x bar), novel OOV 929 (partner token absent from the stem train), unseen_kernel 160 (negative control). Rhythm-unigram on novel_tuple is 0.1852, so 3x is 0.5556. Glue is scaffold only. Mix is subsampled, not cloned: broad leave-one-out rows against those stems. Recipe matches S2 at dim 128, 80 epochs, residual, full stack. Curve (recur fraction → tuple top-1 / OOV top-1 / recall@8): 0.00 → 0.004 / 0.003 / 0.701; 0.20 → 0.178 / 0.104 / 0.706; 0.40 → 0.278 / 0.106 / 0.659; 0.60 → 0.369 / 0.167 / 0.614; 0.70 → 0.443 / 0.205 / 0.571; 0.80 → 0.500 / 0.208 / 0.535; 1.00 → 0.611 / 0.298 / 0.293. Seed 1 at 0.80: tuple 0.472, recall 0.530. A separate 100-epoch recur-only run peaked tuple top-1 at 0.650 (epoch 95) with unseen-kernel still ~0.03, so the tuple gain is the trained kernel plus a new partner, not a new pair and not one token. No point clears tuple >= 0.556 and recall >= 0.60 together. Best joint point is broad:recur 0.25. OOV partners never clear. One completion encoder on one mixed corpus does not carry both objectives; the mouth and the blank move in opposite directions. Logs: `docs/findings/logs/2026-09-23-phase-b/s3_frontier.json`, `s3_curve_dim128_e80.json`, `s3_build.json`. Live corpus hashes unchanged. Not starting S4. Handing off.
- 2026-09-23 — Phase C FAIL on the joint gate, OOV ceiling broken. Branch `experiment/phase-c`. S2 mouth banked (`banked_mouth_completion_{128,256}.pt`, recall@8 0.6936/0.6573). Encoder is a causal RoPE readout, unit-norm, anchored on the mean of every token except the last (the variable slot on role-ordered stems). An unanchored readout collapsed (PR ~5, train top-1 0.19 at epoch 15) and was not the grid. Same S3 fractions, dim 128, 80 epochs. Curve (recur fraction → tuple / OOV / recall@8): 0.00 → 0.004 / 0.003 / 0.357; 0.20 → 0.339 / 0.345 / 0.342; 0.40 → 0.433 / 0.407 / 0.328; 0.60 → 0.439 / 0.434 / 0.286; 0.70 → 0.474 / 0.458 / 0.295; 0.80 → 0.489 / 0.469 / 0.242; 1.00 → 0.613 / 0.576 / 0.138. Seed 1 at 1.00: tuple 0.613, OOV 0.629, recall 0.152. No point clears tuple >= 0.556 and recall >= 0.60. Mean-pool OOV never passed 0.298; this encoder passes 0.30 from fraction 0.20 up. The mouth never reaches 0.60, including broad-only. One vector is still not both faculties. Finding: `docs/findings/2026-09-23-phase-c-order.md`. Not starting S4.
