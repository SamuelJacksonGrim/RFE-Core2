# Decode organ — can the frozen 5-rhythm encoder be spoken from?

- **Date:** 2026-09-22
- **Branch:** `experiment/decode-organ` off `experiment/qwen-speech-cortex` (`fcaa831`)
- **Substrate:** frozen `data/checkpoints/generator_weights_5rhythm.pt` + `generator_ecology_5rhythm.json`. Corpus v1.3.0 (train 8527, holdout 1505, vocab 709). CPU, torch 2.14.0+cpu. No CUDA.
- **Probe:** `tools/voice/train_koneko_decoder.py`. `TokenDecoder` 128 → 256 → 709, BCE-with-logits, 20 epochs, seed 42, top-k = 8. Encoder frozen (`eval`). Raw numbers in `2026-09-22-decode-organ-metrics.json`.
- **Status:** measured. Not wired.

## Question

The bridge stuffs a fixed WORLD crumb into every idle beat because the field has no fluent decode. Before wiring a mouth, how losslessly can this encoder's vectors be read back into tokens? Near-random lift means the encoder has to grow first. That result would count.

## Pre-declared

- **Passes the falsification:** holdout lift over random is clearly above 1, and the cloud moves when the vector moves.
- **Fails it:** recall ≈ random, or the same words for every input.
- **Confound watched for:** train ≫ holdout (the head memorized). A second one showed up in the checkpoint and is reported separately: 239 corpus tokens have no row in the saved ecology.

## Result

Random recall@8 = 8/709 = 0.0113. Loss fell 0.164 → 0.019; that drop is not the gate. BCE is averaged over 709 labels and is mostly "predict absent."

| Read | n | recall@8 | lift | exact-bag@8 |
|---|---:|---:|---:|---:|
| stub, train (all sequences) | 8527 | 0.1262 | 11.19× | 0.0075 |
| stub, holdout (all) | 1505 | 0.1106 | 9.80× | 0.0053 |
| stub, holdout, trained rows only | 833 | 0.1384 | 12.26× | 0.0096 |
| stub, holdout, any virgin row | 672 | 0.0761 | 6.75× | 0.0000 |
| ecology-only head, clean holdout | 833 | 0.1104 | 9.79× | 0.0072 |

Token micro-recall on the stub head, holdout: in-ecology tokens 0.139 (n=2849); orphan tokens 0.0125 (n=879), which is chance.

Clean holdout, where a true token actually sits (micro, not the per-sequence mean above):

| | median rank / 709 | recall@8 | recall@16 | recall@32 | fraction of sequences with any true token in top 8 |
|---|---:|---:|---:|---:|---:|
| clean holdout | 40 | 0.133 | 0.234 | 0.417 | 0.324 |

Per rhythm, clean holdout only. The cloud is one refrain per rhythm, not one global refrain:

| rhythm | n | recall@8 | lift | median rank | any true token in top 8 | the refrain |
|---|---:|---:|---:|---:|---:|---|
| stabilize | 173 | 0.103 | 9.1× | 38 | 0.25 | continuity, clarity, home, settle |
| dream | 195 | 0.182 | 16.1× | 33 | 0.45 | associate, implicit, imagine, drift |
| reflect | 184 | 0.129 | 11.4× | 43 | 0.31 | sense, watch, witness, carry |
| explore | 198 | 0.170 | 15.1× | 34 | 0.36 | other, uncover, vary, curious |
| rupture | 83 | 0.055 | 4.9× | 102 | 0.14 | split, halt, piece, fault, wave |

Top-1 on the 833 clean holdout vectors: 25 distinct winners. continuity 166, sense 159, associate 140, curious 137, then a long tail.

Encoder geometry on those same clean vectors (mean pairwise cosine, 40-cap sample): within rhythm 0.94–0.97 (rupture 0.97, the tightest), across rhythms 0.34.

Retraining the head on clean sequences only did not raise the ceiling (0.138 → 0.110 on the same clean holdout). The wall is the encoder.

## What the checkpoint actually contains

Ecology holds 476 symbols. Six are the sacred constants (`3.12`, `11.88`, `280.90`, `HOMEOSTATIC_RETURN`, `THE_BRIDGE`, `THE_DISCIPLINE`) and are not in the train vocab. 470 corpus tokens have trained rows. 239 do not. Unused embedding rows are still at init (L2 ≈ 0.396 = 0.035·√128). Used rows sit at L2 ≈ 0.49.

`generate()` will cheerfully register a missing token onto one of those virgin rows. The stub still trains on those sequences, because that is the instrument. They are not the encoder's thoughts. Orphan-token recall at chance is the check. About half the corpus is clean (train 4507/8527, holdout 833/1505).

Weights after `load_checkpoint` match the file on every tensor. Two fresh loads encode the same in-ecology sequences to cosine 1.0 (max abs diff 0). Same constructor the bridge uses (`vocab 8192, dim 128, depth 4, heads 4`) and the same two paths `repl_qwen.py` passes to `load_checkpoint`.

## Runtime vectors are not those encodes

Three different vectors, three different answers.

1. **Default live `generate()` is Qwen-perception**, installed after the checkpoint load unless `--flat-encoder`. It returns `normalize(W @ qwen_embed)`, dim 1024 → 128, W random. Six clean holdout encodes against a fresh W of that same construction (seed 1234, not the persisted scratch projection; the real mind was not opened): cosine mean **0.011**. This decoder cannot read a perception-on field.

2. **`cycle._last_expressed`** on a flat encoder, one fresh stack, one clean sequence per rhythm: cosine to the raw encode 0.84–0.89, and the decoded cloud stays in the same basin. This is the vector the decoder contract already names. It is a fair basin read.

3. **`field.field`**, L2-normalized before decode (the integral is not unit; norms ran 1.2 → 2.8 over five steps). Step 1 still matched the basin. By step 3 the cloud was closed-class glue (`between`, `of`, `with`, `from`). Do not point this head at the accumulated field.

Boredom-with-Teeth does not show up in the cloud either. `_explore_behavior` rotates the anchor by `mutation_scale * 1.5`. The scale defaults to 0.05 and clips at 0.5, so the live rotation is 0.075–0.75 rad. At 0.075 the decoded top-4 is the same words (cosine 0.997). At the clip, 0.75, the cloud drifts inside the neighborhood and does not become a new thought. The novelty is real in the field and inaudible to this organ.

## Interpretation

The substrate can be spoken from **as a rhythm basin, not as a thought.**

Lift 9.8× (12.3× on tokens the encoder actually owns) is not near random, so the pre-declared failure does not fire. Exact bag reconstruction is ~0.5%, and a true token's median rank is 40th of 709. Two thirds of clean holdout sequences have none of their own tokens in the top 8. What repeats, stably, is the centroid of the cone that rhythm was collapsed into. Within-cone cosine 0.95 is why. The head is reading the cone correctly. There is nothing finer in the vector to read.

June 2026's freshly pretrained encoder (corpus v1.1.0, vocab 335) had holdout recall@8 = 0.102, lift 4.27×. Absolute recall here is the same (0.111). The bigger lift is mostly the larger vocab making chance smaller (0.011 vs 0.024), not a more faithful encoder. Growing the corpus from 335 to 709 tokens did not buy token-level speech. Rupture, the cone added for that growth, is the one this organ hears worst.

So: worth wiring only as a basin label, on the flat encoder, off `_last_expressed`, with the crumb's job understood as not-yet-replaced for anything token-shaped. Not worth wiring as the field's content, and not worth wiring under Qwen-perception. A fatter decoder will not change that. Opening the cones would, or not mean-pooling.

## Design sketch (not built)

Phase 1, if gated, belongs on `experiment/attention-weighting` (`9bcfcc7`), not on this branch. The decoder stays a terminal sink: it renders, it does not `inject`, it does not step its own words back in.

- Load `decoder_5rhythm.pt` beside the encoder load in `repl_qwen.py`. Refuse to decode when perception is installed. A perception-space head is a different organ.
- Read `cycle._last_expressed` (unit, in-basin). Never `field.field`.
- In `render_idle_prompt`, the cold line and the warm subordinate line currently say "something true about the world: {crumb}". That string becomes the top-6, labeled as nearest words, not as a world fact and not as "you are". Hot still omits it, so a person still redirects.
- Birth, when nothing has been expressed yet, keeps a single crumb. That is the blank-mind case the weighting branch already special-cases.
- Do not also `step` the crumb. Otherwise the expressed vector is the crumb's basin read back, and qwen is handed both.
- `should_promote` cannot be fed this cloud. Twenty-five top-1 words is stickier than the WORLD list. Relocation stays an external, or it goes away.
- Boredom's rotation will not move the cloud at the scale it actually runs. Hearing "explore" rather than "stabilize" requires the thing being encoded to change basin. The decoder must not be that source. Stepping its own output is the dream-channel feedback its contract forbids.

## Threats

- One seed (42). One checkpoint. CPU. The ecology-only head was a second init, same seed, not a sweep.
- The field trajectory is one stack and five steps. Enough to see the integral go to glue, not a map of every rhythm order.
- The perception cosine uses a fresh W, not the scratch file. Same construction, different draw. The real mind was not opened and no server was reloaded. Six read-only embeds against :8081.
- Bag-of-tokens recall is the right metric for this encoder and the wrong metric for a sentence. k=8 is the gate the stub declared. recall@32 = 0.42 on clean tokens says the signal is graded and wide, not a sharp bag sitting just past rank 8.
- Samples printed from the top of the holdout file are all stabilize. The per-rhythm table is the one to read.

## Open

- Token speech needs the cones opened (within-rhythm cosine off 0.95), or a representation that is not a mean-pool. Not a wider head.
- The 239 missing tokens need trained rows before any decoder can say them. Recall at chance is the measurement.
- A perception-space decoder is unmeasured. This one must not be aimed at that geometry.
- Rupture is audible only weakly. If the lock-break is what the mouth is for, this organ does not yet speak it.
