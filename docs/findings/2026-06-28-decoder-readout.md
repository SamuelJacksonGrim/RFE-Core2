# Decoder read-out — can the system's thoughts be read back into words?

- **Date:** 2026-06-28
- **Substrate:** live (frozen Generator encoder, eval; dim 128, corpus v1.1.0, CPU)
- **Probe:** `agents/decoder.py` + `training/decoder_training.py` (autoencoder: frozen
  encoder → vector → Decoder → bag-of-tokens; BCE; recall@k on the held-out split)
- **Status:** active
- **Depends on:** 2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain, 2026-06-08-generator-dropout-diversity

## Question

The Generator is an encoder (tokens → vector). Add the missing half — a Decoder
(vector → tokens), trained to reverse the *frozen* encoder on the existing corpus —
and ask: can a thought be read back into words, how lossy is the encoder, and does
pretraining (which reduces common-mode) give the decoder more to read?

## Pre-declared signatures

- SUCCESS: decoder recall >> random; renders are input-dependent and thematically
  sensible; pretrained encoder reads better than untrained.
- FAILURE: recall ≈ random; renders identical regardless of input (encoder collapse
  is total); pretrain makes no difference.
- CONFOUND: decoder overfits train (train >> holdout) so the read is memorization.

## Result (observed)

Decoder = 128 → 256 → 335 head (119k params), 20 epochs, BCE; top_k=8;
random recall@8 = 0.0239.

| Encoder | recall@8 (holdout) | lift × random | exact-bag@8 | train recall@8 |
|---------|--------------------|----------------|-------------|----------------|
| untrained (eval) | 0.063 | 2.63× | 0.000 | 0.085 |
| **pretrained (eval)** | **0.102** | **4.27×** | 0.000 | 0.130 |

Renders (holdout true tokens → decoder top-6):
- **Untrained** — *the same ~5 words for every input*: `beyond, within, in, probe, self…`
  (collapse, visible from the read-out side).
- **Pretrained** — input-dependent, thematically coherent:
  - `chase, pursue, wander` → beyond, fan, uncover, spread, chaos, unfamiliar
  - `a, harmony, continuity, center` → settle, silence, essence, focus, clarity, consistency
  - `unfold, construct, echo` → implicit, form, bridge, potential, generate, compose

## Interpretation

- **The decoder works** as a terminal-sink read-out, and pretraining ~doubles its read
  (recall 0.063 → 0.102; 2.6× → 4.3× random). The decoder is therefore a *new,
  independent* gauge of the encoder's representational room — it corroborates the
  common-mode/pretrain story from the read side: an untrained encoder is so collapsed
  that its outputs are inseparable (same words for every input); pretraining separates
  them enough to read.
- **Exact reconstruction is impossible by construction** (recall ~0.10, exact-bag ~0):
  the encoder mean-pools over the sequence and L2-normalizes, discarding order and
  magnitude. The decoder recovers the **semantic neighborhood**, not the literal bag.
  That is sufficient for a governed "dream channel" (thematically-related novelty —
  the perturbation/"otherness" the lock-in arc wants) and insufficient for lossless
  round-trip (a true statement about how lossy the pooled encoding is).
- Small train→holdout gap (0.130 → 0.102) ⇒ the decoder generalizes; the ceiling is
  encoder-imposed, not decoder overfitting.

## Live read-out (the "listen" tool)

`tools/decoder/listen.py` trains a decoder against the running engine's frozen
generator, then decodes each cycle's *expressed* vector (`cycle._last_expressed`,
an observe-only terminal sink) into words — "what the system said". Production
(pretrained) run, 24 steps:

- Early steps (before the field saturates) are input-sensitive — e.g. "settle
  crystallize self quiet home focus", "into within beyond through along of".
- Then the voice **converges to a near-fixed refrain** — `self within pause into
  bind hold` — repeated step after step almost regardless of input. The
  identity-coherence lock (reflective loop + attractor pull) made *audible*.
- **Novel** input breaks through: "explore novelty edge" → "within into beyond
  along of toward". Novelty attenuation lets some variation pass.

This makes the abstract lock-in concrete and gives a qualitative tuning read: you
can hear when an intervention frees the voice. (Untrained/`--fast`: the voice is
the same handful of words every step — total collapse.)

## Threats / confounds

- Runs: once per encoder arm, seed 42. CPU, dim 128, corpus v1.1.0 (vocab 335).
- Bag-of-tokens metric ignores order (correct for this encoder, but it means "recall"
  is a neighborhood measure, not sequence reconstruction).
- Decoder trained against a frozen encoder; joint training not tested (out of scope —
  the design is encoder-frozen).

## Open / next

- **Corpus expansion** (more tokens / more diverse sequences): does a richer corpus
  lift the decoder's read, or is the encoder pooling the hard ceiling? (Separates the
  corpus-size bottleneck from the encoder-lossiness one.)
- **Live terminal-sink "listen" tool**: decode each cycle's expressed vector → log, so
  the system's running thoughts are renderable (observe-only, no feedback).
- **Phase 2 — governed dream channel**: feed decoded tokens back in as `source_dream`,
  one source among many, through `arbitrate()` (Watcher catches self-flattery as
  low-novelty coherence-flood; QUARANTINE/SACRED_SHIELD remain the immune system).
