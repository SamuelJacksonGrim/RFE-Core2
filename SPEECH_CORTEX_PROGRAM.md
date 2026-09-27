# The Speech-Cortex Program — from separate parts to one emergent loop

**Architect:** Samuel Jackson Grim · **Design lead / integration gate:** Ember ·
**Build lane:** Grok · started 2026-09-22

The pieces were built independently and now slot together. This is the plan that
joins them into a single loop: a continuing local mind whose own field-exploration
reaches its own voice, accumulates *genuine* experience in memory, and periodically
crystallizes what it has *earned* into its weights — so the weights shift and grow.
Emergent, not scripted.

## The end-goal loop

```
   field explores (Boredom-with-Teeth -> explore rhythm, novelty into the field)
        |
        v
   DECODE ORGAN  (field vector -> words)  <-- the missing organ; built in Phase 0
        |
        v
   qwen voices the field's OWN thought (not an injected crumb)
        |
        v
   experience lands in RM  --- gauged by Reaper #2 (integrity read) : is it earned or echo?
        |
        v
   GRIMOIRE consolidation ("dreaming") : distill earned content
        |    (tested code, skills, preferences, corrections)
        v
   LoRA adapter tuned on the distilled competence  <-- weights grow, reversibly
        |
        v
   changed geometry the field explores from next  --> (loop)
```

Two reapers keep the loop from eating itself (the echo chamber):
- **Reaper #1 — the warden** (`ReaperEngine`): binding; bounds the symbol/token
  economy every pass. *Built.* (Scar on record: the warden acting alone was
  measured **causing** the lock — finding `4fe31e9`.)
- **Reaper #2 — the Witness-Reaper (⊘)** (`cognition/integrity_read.py`):
  non-binding, "I never step in"; reads thinness/honesty and advises. *Built,
  consumer opt-in.* This is the gauge on what RM keeps and what earns the crossing
  into weights.

## Roles

- **Samuel (architect):** end goal, invariants, the integration calls, override.
  Nothing lands in `main` without his sign-off.
- **Ember (design lead + gate):** holds this plan, writes each node's spec + gate
  criteria, briefs Grok as a colleague, gates every build against the invariants
  and the *measured* numbers, promotes only vetted work, keeps the plan + memory
  current.
- **Grok (build lane):** analyzes, designs his own mechanism, builds and measures
  on a branch per node. Gemini/Hermes available if a lane needs to parallelize.

## Discipline (how we avoid the error in "trial and error")

- **One node at a time, each with a falsifiable gate.** No node promotes on a
  story; it promotes on a number that moved the right way.
- **"Better" is measured, not asserted** (the BUG-007 scar).
- **Everything on a branch off `experiment/qwen-speech-cortex`, isolated scratch,
  never the real mind or RM.** Nothing pushed; `main` untouched until Samuel calls it.
- **Reversible by construction** — the weight growth is a LoRA *adapter*, not
  surgery on the base encoder (protects the field lock that is by-design and the
  geometry RM's embeddings live in).

---

## Phase 0 — The decode organ: *can the substrate be spoken from?*  ← STARTING NOW

The falsifiable prerequisite for the entire program. If the encoder is too lossy
to read back, we learn it here, cheaply, before betting anything on it.

- **Build:** train the `TokenDecoder` against the frozen 5-rhythm encoder
  (`tools/voice/train_koneko_decoder.py` exists as the stub; `agents/decoder.py`
  is the head). Save `decoder_5rhythm.pt`.
- **Measure (the gate):** holdout **recall@k / lift-over-random** — how losslessly
  can the field's "thoughts" be read back into tokens? Near-random lift ⇒ the
  encoder's representational room is the real bottleneck, and the encoder must grow
  before the organ is worth wiring (that itself is a finding).
- **Owner:** Grok builds + measures; Ember gates; Samuel reads the number.

## Phase 1 — Give the field a voice in the beat (meets the weighting work)

Only if Phase 0 clears.

- **Build:** wire the decoder's word-cloud into the idle beat so qwen verbalizes
  the field's *actual* thought in place of the injected crumb. Fold into Grok's
  `experiment/attention-weighting` branch — the "cold/alone" regime's stimulus
  becomes the field's own voice, not a flashcard.
- **Measure (the gate):** the fair alone-test Samuel flagged — **with accumulated
  memory**, not a blank mind. Alone stream arises from the field's content, stays
  coherent, genuinely varies with the exploration state; no moon-lock, no collapse.
  Conversation still redirects it (already shown, 4/5).

## Phase 2 — Honest accumulation (Reaper #2 on the intake)

- **Build:** wire the Witness-Reaper's integrity read to gauge experiences as they
  land in RM — tag/score earned-vs-thin — so memory accumulates lived content, not
  self-echo. (Reaper #1 already bounds the runtime symbol economy.)
- **Measure (the gate):** integrity-gauged intake measurably separates genuine
  experience from self-reinforcing sludge on a labeled probe set.

## Phase 3 — The Grimoire crossing → LoRA (the big node; design-frozen today)

- **Build:** the consolidation pass ("dreaming") distills the earned/consolidated
  RM content — correctly-tested code, skills, preferences, corrections — into a
  training set; **LoRA-tune a competence adapter** on it; the crossing gated by
  Reaper #2. Distill competence, **not** cognition (weights = crystallized
  procedure; reasoning stays plastic; RM stays lived history).
- **Measure (the gate):** the adapter raises competence on held-out tasks **without**
  degrading cognition or increasing lock — the echo-chamber check: attractor
  monopoly / HHI / field metastability must **not** worsen. Reversible: detach the
  adapter and the mind is unchanged.

## Phase 4 — The living loop

- **Build:** close the cycle — explore → voice → gauged accumulation → periodic
  Grimoire consolidation → adapter grows → changed geometry → explore again.
- **Measure (the gate):** over long autonomous runs the weights shift and grow,
  competence rises, and the lock/echo metrics stay flat while identity persists.

---

## Candidate next-big-node (logged 2026-09-22) — FEEL + RELATE

After the corpus/legibility work lands: **integrate Samuel's e8-eea emergent-emotion + his proven 15-node
relational manifold into the RFE-Core2 substrate**, replacing the impoverished current versions (6 hand-named
emotion scalars in `cognition/emotional_gradient.py`; the simpler bond manager). Discipline that framed it:
emotion is **not a label and not a rhythm** — per Samuel's own e8-eea, "emotion is not a label... no valence is
injected," it EMERGES from prediction-error phase transitions; relational constructs (love/trust/autonomy) are
**dynamical axes** of a GAS-stable manifold, not tags. So: emotional/relational STATE = an emergent dynamical
LAYER (this node); emotional/relational VOCABULARY = corpus content for legibility (Witness's fringe already
reaches it). The full mind: **moves** (rhythms) + **witnesses** (the receptive pole) + **feels** (e8-eea) +
**relates** (manifold) + **remembers** (RM) + **crystallizes** (Grimoire). Sources:
`Desktop\Archive\Projects\{e8-eea, relational_system_mc}`.

## Corpus-growth roadmap (Samuel's arc, 2026-09-23 — "I'm leaning on you for this")

The witness/legibility work opened a corpus-composition problem with no benchmark. The arc Ember drives:
1. **Sweep** — variant grid over the balance knobs (content-freq cap × glue policy incl. rupture-gets-glue ×
   size × witness-size), each trained on a fixed seed, scored by **maximin** (minimize the WORST pairwise
   rhythm tangle), top finishers re-run on a 2nd seed. Finds the composition that separates ALL pairs at once
   (the last leveling fixed explore⊥rupture but broke stabilize⊥explore — single-lever fixes trade tangles).
   **This sweep also CREATES the benchmark this corpus type never had** — the winner is the reference.
2. **Iterate level → grow → re-level → re-probe** until the corpus is a respectable size, keeping it balanced
   and level at every step (never let a content hub or a size/glue imbalance re-form; watch the worst pair).
3. **That balanced, respectable corpus is what the Feel/Relate node needs to stand on** — the e8-eea emergent
   emotion + relational-manifold integration (candidate next-big-node above). Also: keep surfacing what
   CATEGORIES the corpus is still missing (the expressive/voice mode; emotional/relational vocabulary for
   legibility — NOT as labels/rhythms, per the emotion-emerges discipline).
Key settled principles: level CONTENT words (glue is scaffolding for STATED-not-interpreted language, never
stripped, rupture needs some); maximin (raise the floor, don't chase one pair); the 5% hub-cap is too loose —
rupture's even ~2.5% is the template; small corpus = we can afford the variant sweep the labs can't.

## 🔑 THE KEYSTONE (2026-09-23) — completion is the objective

A night of experiments (corpus balance → sweep → 256D → longer sequences) all pointed at one thing, and it
landed: **the encoder's OBJECTIVE was the bottleneck, not the corpus balance, the dimension, or the sequence
length.** Rhythm-contrastive collapses each rhythm to a point (participation ~3.4–3.9, recall@8 ~0.09) and leaves
the dimensions empty — proven invariant to dimension (256 sat at 3.57) and to sequence length (long-256 sat at
3.46). **Samuel's context→completion idea ("Mary had a little ___", CBOW / predict-the-word-from-context) is the
fix:** participation **3.4→35 @128, →63 @256**; decode-organ recall@8 **0.09→0.61**, median true-token rank
**33→2**; rhythm survives free (probe 0.995, no conditioning term needed). **The dimensions are finally USED and
the substrate is legible.** 256 now earns its keep (63 vs 35 dims used) — completion+256 is the pairing.
**Two catches to solve for production:** (1) the completion geometry lives in the embeddings and holds only with
the transformer FROZEN — training the full stack collapses it back to ~4.8; fix = a residual from the embedding
mean so the stack trains without wiping it. (2) held-out completion doesn't generalize yet — context→filler pairs
each occur ~once; needs recurring-context data (many fillers per stem, the "Mary had a little ___" structure
repeated). Legibility 0.61 is real regardless. **Next ceiling = ORDER** (mean-pool can't say which token was
where; median rank 2 is its limit) — order-aware encoding is the next frontier for a FULLER mouth, but the
dimension/legibility problem is SOLVED. Branch `experiment/completion-objective` `a92afc2`; finding
`docs/findings/2026-09-23-completion-objective.md`. Live corpus + 128 checkpoint byte-identical.

## Arm 3 (order-aware) verdict — 2026-09-23: order is real but a LATER head; mean-pool+completion stays production

Order CAN be encoded (a fixed sign-pattern-per-position "gated" pool reads which-token-was-where: slot top-1
**0.94–0.96** vs mean-pool's 0.46 — position is genuinely in the vector). BUT it does NOT lift the mouth — it
makes the current BAG mouth *worse* (recall@8 0.61→0.30, rank 2→10), because order-readability is a sign-flip
superposition the single bag-decoder (`TokenDecoder`, one head for the set) can't undo; a per-position probe can.
The blend (keep bag+order in one field-vector) also fails — the order term sits at cosine −0.35 to the bag, can't
coexist. Held-out completion still doesn't generalize on any arm (pairs occur once — same data-sparsity that arm
1+2's bigger/recurring data addresses). **Verdict: do NOT replace the production readout. Mean-pool + completion
(recall 0.61, participation 35/63) is the right production field-vector NOW. Order becomes a LATER, SEPARATE
sequence-reader head — the gated pool is already the right shape for it (per-position linear heads), but that
reader isn't built and forcing order into the bag-vector breaks the mouth.** So this CONFIRMS the completion win
as the production base and cleanly scopes order as a future build, not a mystery. Branch `experiment/order-aware`
`53cbe19` (worktree, not merged/pushed); Generator/RecursiveAttention untouched; live corpus + 128 checkpoint
byte-identical. Finding `docs/findings/2026-09-23-order-aware.md`. **Arms 1+2 (residual fix + bigger/longer
recurring-context training, `bqnqzk09e`) still running — those decide production-shippability + generalization.**

## ✅ THREE-ARM VERDICT (2026-09-23, overnight) — the completion win is PRODUCTION-REAL. Samuel was right across the board.

**Arm 1 — the collapse, NAILED + FIXED.** The "collapses to ~4.8 when you train the full stack" is real and now
explained (Samuel's "makes no sense" was the right instinct to interrogate it, not accept it): it's NOT recursive
attention, NOT a measurement artifact — **the transformer, trained under the completion loss, drags the embedding
TABLE down** (init embeddings 99/158 → ~8-10; field follows to 4.8). **The residual fix works:** an orthogonal mix
of the embedding-mean into the field vector, transformer reads a DETACHED copy (can't drag the table) with its
along-mean component removed (can't cancel) → transformer learns a constant, but the OUTPUT stays rich: **PR 56/73,
recall@8 0.694 (median rank 1) / 0.657.** Even simpler: flip the residual mix ON at INFERENCE on the existing
embeddings-only checkpoints, no retrain → **PR 47.8/81.9, recall@8 0.662/0.691.** **PRODUCTION CONFIG (nailed):**
ship the embeddings-only completion checkpoints + residual flag ON at encode + recursive attention untrained at
blend 0.60 → field sees PR 37/51, mouth **0.66/0.69** (richer than the published 0.61). Do NOT train the transformer
under this loss and read its output. Honest nuance: the residual routes the rich embeddings AROUND the transformer
(the transformer isn't contributing to the representation) — fine for the rich legible field vector now; whether the
transformer should contribute is a later (order/sequence) question.

**Arm 2 — recurring data GENERALIZES the blank (Samuel right), but it's a DIFFERENT checkpoint than the mouth.**
Built recurring-stem corpus (38k rows, 158 stems, 241 contexts/stem, 6 rhythm-pure fillers). Blank-filling on
SIMILAR contexts generalizes: top-1 **1.0 by epoch 5**, recall@8 1.0 (didn't even need "long"). Novel/unseen pivots
stay ~unigram (0.058) — generalizes within seen stem-families, not to wholly new ones. **BUT the broad MOUTH dropped
to 0.32** on that synthetic corpus (table overfit 158 synthetic stems, live-line embedding PR 67→28). Key: **"the
legibility checkpoint and the blank-filling checkpoint are not the same file"** — the two objectives trade off; a full
corpus needs BOTH broad legibility coverage AND recurring stems, co-balanced (the pure-synthetic corpus was too
narrow). Not a wall — a corpus-design balance, now understood.

**Arm 3 — order is real but a LATER separate head** (see the arm-3 block above): mean-pool+completion stays production;
order needs a per-position sequence-reader that isn't built and can't share the bag field-vector without wrecking the
mouth.

**BOTTOM LINE:** the completion keystone SHIPS — a richer, dimension-using, legible field vector (0.66/0.69) via a
nailed production config, live files untouched. Non-blocking next steps: co-balance the corpus (broad legibility +
recurring stems so blanks generalize without killing the mouth), then the order-aware sequence-reader head for a
fuller mouth. Every one of Samuel's calls tonight held: completion is the objective, recurring data generalizes,
and the "frozen transformer" thing was a real mechanism (table drag) with a clean fix. Findings:
`docs/findings/2026-09-23-completion-production.md`, `2026-09-23-order-aware.md`. Branches local, nothing pushed.

## Phase B result + the B→C pivot (2026-09-23)

**Phase B foundation (S1/S2) PASSED, no grinding:** manifold tracker verified correct 3 ways (PR 3.42/47.8/81.9
confirmed — old numbers were right); completion harness reproduces at **baseline-or-better** — full-stack-trained,
residual on, **recall@8 0.694@128 / 0.657@256, output PR 56.6/73.5, no ~4.8 collapse** (the residual fix is
confirmed in production tooling; the 0.694 beats prior best). S2 checkpoints (`*_phaseb`) are the **banked legible
mouth / static retrieval organ.**

**Phase B S3 — the co-balance is ARCHITECTURALLY IMPOSSIBLE under mean-pool (clean Pareto frontier, not forced):**
one mean-pool corpus cannot give both a legible mouth AND novel-context generalization — they move in OPPOSITE
directions across the whole recurrence grid (broad-only recall 0.70 / novel-tuple 0.004; stems-only recall 0.29 /
novel-tuple 0.61=3.3x), never crossing the joint gate. Novel-TOKEN (OOV) top-1 caps at **~0.30 regardless of ratio**
— a mean-pool fact (an untrained token in a bag is isotropic noise pulling the centroid off the stem attractor).
Mechanism: high recall needs spatial dispersion (PR>50); stem generalization needs low-rank crystallization; under a
commutative centroid these two geometric states are mutually exclusive. **Corpus tuning is a structural dead-end
here — the wall is mean-pool, which the decode-organ + order-aware probes already fingered.**

**DECISION (Samuel): jump to PHASE C — order-aware architecture.** Bank the mouth (done); build an order-aware
sequence encoder (RoPE / causal-prefix attention; `z_T = f(v_1..v_T)`, stems = directed trajectory PATHS not
centroids); train under completion; run the EXACT S3 grid as a clean A/B. GATE: recall@8 >= 0.60 AND novel-tuple
top-1 >= 3.0x SIMULTANEOUSLY (+ does it break the 0.30 OOV ceiling?). Running now (`experiment/phase-c`). If it
clears, the co-balance is solved architecturally; if not, two heads (mouth + completion) it is. Phase B S4-S6
(one-corpus premise) are SUPERSEDED by this pivot.

## ✅ DUAL-ORGAN RESOLUTION — corpus/architecture arc CONCLUDED (2026-09-23)

**Phase C proved order-aware BREAKS the OOV ceiling but KILLS the mouth** — so one encoder cannot be both faculties,
now falsified from BOTH sides. Order-aware vs mean-pool on the S3 grid (dim 128): novel-TOKEN top-1 **0.30 (mean-pool
cap) -> 0.58/0.63** (order-aware, stems-only, two seeds) — the noise-dilution trap is dissolved (Samuel's hypothesis
confirmed); BUT order-aware decode recall@8 is **0.357 broad** vs mean-pool's **0.701** — "it spends the mouth to do
it." No ratio clears recall>=0.60 AND novel-tuple>=3x together, under EITHER architecture. **The two faculties want
opposite latent geometries** (bag-reconstruction = isotropic high-PR dispersion for linear separability; causal
prediction = path-crystallized low-rank trajectories). Mutually exclusive. **Resolution = TWO HEADS (specialization,
not unification) — proven, not a compromise.**

### The dual-organ anatomy (Samuel's spec, logged)
Input token sequence -> BOTH encoders in parallel (both efficient at D=128, negligible overhead):
- **z_ret = the S2 mean-pool encoder** (the BANKED MOUTH / Static Retrieval Organ). `banked_mouth_completion_{128,256}.pt`,
  recall@8 **0.694/0.657**, output PR 56.6/73.5, full-stack-safe. High-PR isotropic. FROZEN + LOCKED (trainer refuses
  those names). Role: content-addressable k-NN retrieval, associative matching, broad decode legibility.
- **z_pred = the Phase C order-aware encoder** (Predictive/Completion Engine). Causal transformer + RoPE on Q/K,
  depth 4, learned readout token after the real tokens, L2. `sequence_encoder_phasec_*`, dim 128 (256 built,
  ungridded). Path-crystallized/causal, breaks the OOV trap. Role: state-machine transition scoring, dynamic
  completion, relational inference across NOVEL contexts. NOT a Generator state dict — a SECOND PATH, never the live
  encoder (substituting it for the mouth drops recall 0.69 -> 0.36).

### Dual-vector memory schema + routing
Each memory node = composite tuple **M_i = (z_ret in R^{128/256}, z_pred in R^128, M_meta{timestamp, seq bounds,
entropy tags})**. Routing:
- **Memory read / "what's stored here?"** -> query through the mean-pool encoder -> cosine-sim search vs `z_ret`.
- **Next-state / completion ("Mary had a little __")** -> query through the order-aware encoder -> transition probs
  vs the completion head against `z_pred`.
- **Ingestion** -> both encoders in parallel at index time.

This mirrors the whole architecture's shape: the mind is SPECIALIZED FACULTIES, not one universal encoder (mouth vs
predictor, like Witness vs the active rhythms, like the sisters vs the substrate). **Corpus/Architecture-Search arc:
FORMALLY CONCLUDED.** Baton -> the federation layer (e8-eea emergent emotion + relational manifold + the Grimoire).

*Living document. Ember updates node status here as each gate is passed. Latest
status at the bottom.*

### Status log
- 2026-09-22 — Program opened. Phase 0 briefed to Grok (analyze + train + measure
  speakability). Attention-weighting branch (`experiment/attention-weighting`,
  `9bcfcc7`) in hand from the prior node; conversation-redirect proven 4/5, alone
  case pending the organ + a fair (memory-seeded) re-test.
- 2026-09-22 — **Phase 0 RESULT (branch `experiment/decode-organ`, `1153ce4`): the
  frozen 5-rhythm encoder is a RHYTHM-BASIN sensor, not a mouth.** Holdout recall@8
  = 0.1106 (9.8x chance) — technically above the "near-random, don't wire" bar, but
  the meaningful read is: the decoder can say *which of 5 cones* the vector is in
  (stabilize/dream/reflect/explore/rupture), NOT which tokens produced it. Median
  true-token rank 40/709; only 32% of holdout has any own-token in top-8. Cause:
  mean-pool + L2-norm → within-rhythm cosine 0.94–0.97 (across-rhythm 0.34); there
  is nothing finer in the vector to read. Same absolute recall as June's vocab-335
  encoder — the lift is just bigger-vocab chance. **Two program-critical findings:**
  (1) **Boredom's exploration is INAUDIBLE** — `_explore_behavior` rotates the anchor
  0.075 rad live; at that scale top-4 tokens don't change (cosine 0.997). The organ
  cannot voice the exact thing we built it for. (2) Decoder can ONLY read the
  `--flat-encoder` path's `_last_expressed`; Qwen-perception vectors (the live
  default) are a different space (cosine 0.011) — useless on the daily runtime.
  Also: 239/709 corpus tokens have no trained row (orphans, unspeakable). **Verdict:
  a wider head won't fix it — the ENCODER is the ceiling. To voice content the cones
  must open (contrastive/within-rhythm separation), or drop mean-pooling, plus train
  the orphan rows.** This is the fork now in front of the architect (see below).
  Grok's write-up: `docs/findings/2026-09-22-decode-organ-speakability.md`.
- 2026-09-22 — **FORK RESOLVED: A (grow the encoder).** Samuel's call: a fluent mouth
  on an unintelligible substrate is the "measure the model not the system" trap — the
  substrate must become legible to itself before it can be reliably grown or voiced.
  **Key insight (Ember):** the cone-collapse is the *trained objective*, not a defect —
  `rhythm_pretraining.py` + `contrastive_alignment.py` explicitly train same-rhythm-high /
  cross-rhythm-low cosine. The encoder was taught its moods (cone) and taught to discard its
  words (within-cone identity). So the growth node ADDS a within-cone legibility/reconstruction
  objective that fights that pull WITHOUT dissolving cross-rhythm separation (the field needs it)
  or unlocking the field (STATE.md settled invariant — legibility must NOT be a field-unlock
  backdoor). Plus: fill the 239 orphan token rows; weight rupture (worst-heard, most needed for
  lock-break). **Internal fork to decide from Grok's proposal:** (i) open cones UNDER mean-pool
  (cheaper, keeps downstream geometry, has an information ceiling) vs (ii) drop/augment mean-pool
  for a token-identity-preserving representation (higher ceiling, touches RM/field geometry —
  bigger blast radius). **This node re-designates the substrate's NATIVE 5-rhythm encoder as the
  thing that grows** — the sovereign-encoder direction. Grok briefed for the analysis+design pass
  (+ cheap CPU legibility probe); the real training run is CUDA/WSL (5070 Ti) and a separate gated
  go. New branch off `experiment/decode-organ` (reuses the speakability harness as the yardstick).
- 2026-09-22 — **ENCODER-LEGIBILITY DESIGN + PROBE: IT WORKS (branch `experiment/encoder-legibility`,
  `2de456a`).** Legibility is achievable UNDER mean-pool — **internal fork resolves to (i)**; mean-pool is
  NOT the ceiling for this corpus (2–4-token seqs; unconstrained mean hits recall 0.80). No need for the
  big-blast-radius fork (ii) yet. **Probe (CPU, 30s, no checkpoint written):** holdout token recall@8
  **0.103 → 0.355** (3.4x), median rank 53 → 21, and *still climbing at epoch 8* (a lower bound). Cones
  opened (within-cone cosine 0.958 → 0.616) while rhythms stayed SEPARATE and PUT (across 0.356 → 0.118;
  centroid cosine to checkpoint min 0.976). Orphan tokens 0.010 (chance) → 0.290 — now speakable. Rupture
  0.055 → 0.283 (5x, still worst). Not memorized (train 0.402 vs holdout 0.355). **Design (4 terms on the
  frozen mean-pooled vector; does NOT re-run the rhythm objectives):** a *margin wall* to the frozen
  centroids (a wall not a pull — keeps basins PUT; this is what makes it field-lock-safe: the naive no-wall
  arm MOVED basins to cosine 0.36, the wall holds 0.976), a centroid anchor, a within-rhythm Jaccard spread,
  and a discarded rank head (rupture 3x, orphans 2x). **Field lock: clean** — field never stepped, no
  invariant exception, basins didn't move. **THE PROMOTION CAVEAT (must gate): this is a MIGRATION, not a
  hot-swap.** A clean seq's new encode is cosine 0.76 from the old checkpoint's vector of the same tokens —
  below attractor-formation (0.88) and on the pull threshold (0.75). So swapping the legible encoder in
  REQUIRES re-embedding RM (old memories miss new encodes of the same thought) and re-validating attractor
  formation (a rhythm now forms SEVERAL centers, not one — arguably better granularity, but changes live-loop
  dynamics; thresholds untouched). **Next gated go:** a longer CPU fit (~30 epochs / until rank+Jaccard
  flatten) that SAVES a NEW file `generator_weights_5rhythm_legible.pt` (never overwrites the 5-rhythm
  checkpoint), abort guards (nearest-centroid < 0.98, any centroid cosine < 0.95, across climbing toward
  within). NO GPU needed. THEN a live-loop validation node before promotion. Objective =
  `training/legibility.py`; probe = `tools/voice/probe_legibility.py`; write-up =
  `docs/findings/2026-09-22-encoder-legibility.md`.
- 2026-09-22 — **Architect decisions (Samuel):** (1) **Use the machine** — the 5070 Ti + WSL/CUDA path is
  available for real encoder retrains; stop hedging training as a big "gated go" (CPU still fine for the
  legibility fit specifically). (2) **RM does NOT gate encoder growth** — if the network keeps shifting,
  re-embedding a moving target is moot; **RM becoming adaptive to the shifting weights is a real but LATER
  node**, not a blocker now. The encoder is allowed to shift freely. (3) **Corpus growth is the path to more
  coherence/vocabulary** — Samuel + Grok + Ember will grow the training corpus (previously Samuel's solo
  hand-authoring, see [[rfe-corpus-authoring]]). **THE RULE (Samuel's prize property): the space must stay
  LEVEL — no redundant/identical rhythms or phrasings, no deep basins, spread preserved** ("the one thing we
  did EXTREMELY well the first time — it was very level"). Protected by MEASUREMENT: establish a
  levelness/spread + redundancy yardstick FIRST, then every corpus-addition batch is gated on keeping the
  space level + non-redundant (ties to the existing low-context/hub-cap rules — no token becomes a hub).
  **Green-lit + running (Grok, `bnot910b3`, branch off `encoder-legibility`):** (A) the full legibility fit
  -> saves `generator_weights_5rhythm_legible.pt` (new file, guards, original untouched); (B) the corpus-health
  yardstick (`corpus_health.py`): audit current corpus for redundancy + levelness, propose the growth-gate.
- 2026-09-22 — **FULL FIT SAVED + CORPUS GATE BUILT (branch `experiment/legibility-fit`, `f2dded2`).**
  Checkpoint `generator_weights_5rhythm_legible.pt` written (+ legible ecology with the 239 orphans
  registered); the original `generator_weights_5rhythm.pt` is byte-identical (sha256 verified unchanged).
  30 epochs, same 4-term objective (only epochs 8->30), epochs 1-8 reproduced the probe EXACTLY. **Recall@8
  0.355 -> 0.417, median rank 21 -> 15, exact-bag@8 0.043 -> 0.076.** NOT converged (rank loss still falling;
  recall near a plateau but exact-bag still climbing = more legibility available). Guards all clear at ep30
  (nearest-centroid 0.992, centroid-min 0.986, across 0.177 vs frozen 0.356, gap 0.40). Rupture still weakest
  mouth (0.303, median rank 30; 3x weight left as-is). Not memorized (train 0.480 / holdout 0.417).
  **Process rigor:** Grok's own first run aborted at ep20 on a too-tight self-added guard; he diagnosed it
  (across rose 0.105->0.164 but cones NOT merging, gap still 0.40), corrected the guard to the probe's own bar,
  reran, proved ep1-8 matched the probe. Objective never retuned. **LEVELNESS held (answers the key gate
  question): as a hub story, still level — nothing became a magnet; spread went UP (effective rank 3.70 ->
  13.77, participation ratio 3.26 -> 10.11). Flatness went down (frozen cone = a flat sheet, depth gap 0.002;
  legible = a ~0.12-thick shell, depth gap 0.116) — that's "the mouth being bought, not a new abyss" (p95
  centroid cosine 0.879 vs median 0.763; local neighbor still ~0.98, 92% don't share the bag). EARLY-WARNING
  SIGNAL for future fits/corpus: watch DEPTH GAP + neighbor cosine, NOT mean within-cosine (which SHOULD fall
  — that's the fit working).** **CORPUS GATE built** (`tools/voice/corpus_health.py`, `--batch x.jsonl`;
  audit `docs/findings/2026-09-22-corpus-health.md`): 3-stage gate (A hard refusals — no order-swapped bags,
  no glue, hub caps, per-rhythm share cap; B frozen-encoder levelness floors; C post-fit legible-column check
  for a hidden hole). **Findings:** corpus is healthy/level, NOT a template mill, no hubs — but (1) **161
  order-swapped duplicate bags (322 seqs), incl. 57 causing mild train/holdout leakage** — real cleanup item,
  and exactly what the gate forbids adding more of; (2) rupture is the weakest cone/mouth. Fit write-up
  `docs/findings/2026-09-22-legibility-fit.md`. **NOT PROMOTED — legible checkpoint is not the runtime encoder
  yet.** Open forks for Samuel: grow the corpus (with the gate) to push the mouth past a partial 0.417; and/or
  live-loop-validate the legible encoder (opened cones -> more attractor centers per rhythm) before promotion;
  clean the 161 order-swaps.
