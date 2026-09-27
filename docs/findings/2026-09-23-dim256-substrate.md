# Dim 256: the identity lock holds, the payoff does not

- **Date:** 2026-09-23
- **Branch:** `experiment/dim256`, cut from `experiment/qwen-speech-cortex` (`fcaa831`). Not merged, not pushed.
- **Substrate:** corpus v1.3.0 (5 rhythms, train 8527, holdout 1505, vocab 709). Fresh contrastive pretrain via `training/rhythm_pretraining.py` (`RhythmPretrainer`, 20 epochs, seed 0, batch 8). Architecture otherwise the live one: vocab 8192, depth 4, heads 4, ff_mult 4. GPU: WSL venv `~/rfe/RFE-Core2/.venv`, torch 2.13.0+cu130, RTX 5070 Ti. Checkpoints written on the Windows checkout. No `--gpu max`. Ports :8080 / :8081 / :1234 not touched. Real mind (`~/.rfe-speech-cortex*`) and the real resonance-memory store not touched.
- **Status:** measured. **Do not promote.** Production `CONFIG["dim"]` stays 128.

## Question

Does doubling the field from 128 to 256 keep the identity lock, and does it lift the separability floor and the decode-organ mouth? Samuel's 2026-08-07 note (`docs/2026-08-07-256dim-proposition.md`) names both ceilings and the risk: at 256 the reflective loop has a larger state to snap back across, and if that reconstitution fails, 256 does not ship.

The 6-rhythm / witness corpus is **not** in this run. Dimension is the only intended variable. That corpus folds in only after 256 is validated.

## Touch-point map (the change surface — not flipped)

These are field dimension. A real bump has to move them together. This branch does **not** change their defaults. The experiment passes `dim` explicitly and loads a new checkpoint.

| Surface | Where | What 128 means |
|---|---|---|
| Composition default | `loop/recursion1188.py` `CONFIG["dim"]` | What `build_engine` actually builds |
| YAML mirror | `configs/recursion.yaml` `generator.dim`, `configs/field.yaml` `field.dim` and `watcher.dim` | Overridden by CONFIG when built through `build_engine` (`dim` is dropped from the YAML section). Still the number a hand-built field would read |
| Constructors | `Generator`, `ResonanceField`, `VectorSpace`, `TemporalStream` (the `dim` arg, not `maxlen`), `Watcher`, `Witness`, `RecursiveAttention`, `PredictiveEcho`, `AutonomousCycle`, `TokenDecoder` (`dim`, not `hidden`) | Defaults. Callers that pass `dim` ignore them |
| Speech-cortex entry | `tools/voice/repl_qwen.py` `build_full_stack(..., dim=128)` plus `generator_weights_5rhythm.pt` | Live mouth. Field restore already skips a vector whose shape doesn't match |
| JL perception | `tools/voice/qwen_perception.py` `PROJ_DIM = 128`, `W` is `(128, 1024)`, scale `1/sqrt(128)` | 1024→128. A persisted `perception_W.npy` is shape-checked; a 256 code path must not overwrite the real mind's `W` |
| Decoder boot | `tools/voice/train_koneko_decoder.py`, `training/decoder_training.py --dim` | Frozen-encoder mouth |
| Probes pinned to the live runtime | `lockin_source.py`, `generator_metastability.py`, `metastability_validation.py`, `all_levers_composition_probe.py`, `two_operator_live_demo.py`, `bonded_adversarial_probe.py`, the voice A/B scripts | `DIM = 128` |
| Bootstrap | `training/run_contrastive_bootstrap.py`, `tools/ignition/cm_check.py` | Separate from the 5-rhythm checkpoint |

Not field dimension, left alone: `max_len=128`, metastability `window=128`, `TemporalStream.maxlen`, visualization caps, `TokenDecoder` hidden width 256, field `history_len` 256.

Resonance memory does not hardcode 128. It stores whatever vector the caller writes (`tools/voice/repl_qwen.py` `RMClient`). A 256 encoder cannot read 128 memories. That re-embed is a later node. It was not done.

Two calibrations that are not a dim constant but were tuned on 128 distributions:

- Asymmetric DDM (`agents/bond_accumulator.py`): `g_plus=0.05`, `trust_asymmetry=60`, `leak=0.02`, `sigma=0.02`, `b_accept=1.0`, `b_reject=-0.5`, `weak_evidence_factor=0.20`. Evidence is `max(0, cos)` of a unit vector, so the scale stays in `[0, 1]` if L2 normalization holds.
- Reflective-loop reconstitution gain: `ReflectiveLoop.field_blend=0.1` (the per-pass pull toward the field). `attractor_blend` is stored and not what `reflect()` applies; `attractor.pull_blend` is 0.15. `attenuation_max=0.30` is the loosening ceiling. It was not touched. Raising it would weaken the lock, which is the opposite of this gate.

Rhythm energy bands (`stabilize 5 / dream 150 / reflect 300`) were measured at dim 64 and 128 and agree. They are not a dim constant. They were not retuned. See the energy note below.

## What was trained

`tools/dim256/train_5rhythm.py`. Corpus tokens are registered before AdamW binds, so a resize cannot orphan the embedding. The live reaper does not run during this offline pass. The live 128 files were refused by name.

| File | sha256 | bytes |
|---|---|---|
| `data/checkpoints/generator_weights_5rhythm.pt` (untouched) | `71c646fb36d40e3b20cb03d1aa02f51c7a139ab4250aa701694fad8ef2482361` | 7720565 |
| `data/checkpoints/generator_ecology_5rhythm.json` (untouched) | `d74c829c078e22b76423cdf1b5b02a2032e02b1b8ae142b85f51d19e7d27d600` | 288050 |
| `data/checkpoints/generator_weights_5rhythm_256.pt` | `4496d18edd0c8eddef8e450f939e3e690aba91f758562475345380af2b6b989a` | 22234549 |
| `data/checkpoints/generator_ecology_5rhythm_256.json` | `1a5c57f13267cd883b3458531f825bb330f87ef61d6e99b762ba7e1234bbc331` | 429272 |
| `data/checkpoints/generator_weights_5rhythm_128paired.pt` | `8b83bd237bedcb5c2baaf34f972cdee3a1ec8c308a5ea2fc1d03135b30272e89` | 7721205 |
| `data/checkpoints/generator_ecology_5rhythm_128paired.json` | `9ce1da8bcba9f286116852cfe037c19b5a6336a24b236ca51ebd7018f2dd42b7` | 429272 |
| `data/checkpoints/decoder_5rhythm_256.pt` | `92d22459b9da08b059be4ba2f7d834bf7bf26c540f6acd37f4563d0fed934574` | 1005909 |

256D train loss: 1.754 → 0.544 over 20 epochs, still falling at the end. Train-set nearest-rhythm accuracy 0.994. Holdout encodings are unit-norm. Per-coordinate std is nowhere dead (0 quiet dims, 0 dims with std < 1e-3). Participation ratio of the holdout cloud is **3.57**. Effective rank on a 512-row cap is **1.72**. The new coordinates are not empty, and they are not new axes. The rhythm cloud still lives in about four directions, rotated across the ambient dim. The paired 128 run of the same recipe has participation **3.90** and effective rank **1.68**. Doubling the ambient dim did not unfold the manifold.

## Lock gate

Harness: `tools/dim256/lock_gate.py`. Same control as `rupture_migration_probe`: composed engine, checkpoint loaded, `pretrain_on_corpus` off, convergent tokens `anchor / ground / steady`, 150-step warmup, then displacement from that center. `disp = 1 - cos(field, center)`. The historical 128D bar is max disp **0.000120** over 5000 steps.

Pre-declared for the control arm, before the long run: HOLDS if final and max disp stay ≤ 0.01 and the sample trend is flat at the 0.005 level. 0.01 is deliberately loose next to 0.00012. The raw disp is the result. The rupture arm is judged against the probe's own migration bar (disp above control by 0.10), not against 0.01.

### Control — the 5000-step identity test

| | max disp | final disp | energy at end | band | `reflect()` calls |
|---|---|---|---|---|---|
| 256, seed 11, 5000 steps | **0.000129** | 0.000119 | 126.7 | dream | **0** |
| 128 frozen, same harness | **0.000109** | 0.000095 | 126.5 | dream | **0** |
| historical 128 (2026-08-05) | 0.000120 | | | | |

Short window (250 steps, seeds 11 and 23) matches: 256 max disp 8.4e-5 / 7.1e-5, 128 max disp 5.0e-5 / 6.9e-5. Expression regime `locked` throughout. Both climbs are the same slow creep, 256 about 1.2× wider, both far inside the historical number.

**The loop did not run.** `reflect()` is only called in reflect/explore, or when `rupture_on_lock` forces it. This workload equilibrates at energy ~127, inside the dream band (threshold 150), at both dimensions. The 5000-step control is the field integrator holding a near-constant injection. It is real, it matches 128, and it is not the loop-snap-back test the proposition was worried about.

### Rupture arm — the loop is actually on

`rupture_on_lock` forces the reflective branch. `reflect()` fired on 2135 of ~2150 steps in the 2000-step run. Default `field_blend=0.1`.

| steps | 256 disp | 128 disp |
|---|---|---|
| 250 (seed 11 / 23) | 0.0075 / 0.0057 | 0.0045 / 0.0039 |
| 2000 (seed 11) | 0.0055, 0.0094, 0.0112, 0.0127, **0.0140** | 0.0038, 0.0066, 0.0080, 0.0089, **0.0097** |

Both curves flatten. 256's asymptote is about 1.4× the 128 walk, cosine to the warmup center still **0.986**. The original probe calls migration only above control+0.10. This is not migration and not fragmentation. The field stays one regime. It is a wider bounded walk, and it was visible only because the loop was forced.

### Loop gain — scaled, and it got worse

Same 2000-step rupture arm, 256 only. `field_blend` is the reconstitution pull.

| field_blend | final disp |
|---|---|
| 0.10 (shipped default) | **0.0140** |
| 0.141 (×√2, the "scale with dim" guess) | **0.0554** |
| 0.20 (×2) | 0.0166 |

Not monotonic. The √2 step jumps early (0.039 by step 400) and settles near 0.055. Doubling settles slightly worse than the default. **Gain was not scaled in the checkpoint or the code.** The default is the tightest of the three. `attenuation_max` was not raised.

### DDM — measured, not retuned

Expressed vectors are unit length (mean norm 1.000) at both dims, so the cosine scale did not change.

| traffic | 256 align p50 (p10–p90) | 128 align p50 (p10–p90) | trickle eq at that p50 | accept gap |
|---|---|---|---|---|
| convergent, 5000 | 0.9968 | 0.9977 | ~0.50 | ~5.0 sd |
| mixed 4-source, 400 | 0.871 (0.785–0.983) | 0.829 (0.756–0.978) | 0.436 vs 0.414 | 5.6 vs 5.9 sd |

Trickle equilibrium is `g_plus * 0.20 * align / leak`. It stays near 0.4–0.5, and `b_accept` is 1.0. A single step still moves `V` by at most `g_plus` (0.05). Sharpening did not happen in the direction that would let trickle or a burst cross. Thresholds stay at the shipped constants.

Mixed traffic is not a lock failure. The input changes, so displacement from the warmup center is supposed to move (0.093 at 256, 0.086 at 128). Both runs end at energy ~300, one labeled explore (300.6) and one reflect (298.9). That is the existing knife at the reflect/explore threshold, not a 256 shift. Bands were not retuned. The full pinned-band equilibrium grid was not re-run; the unpinned convergent equilibrium matched across dims (126.7 vs 126.5), which is why.

## Payoff

Holdout centroid cosine. Worst pair = highest off-diagonal (most tangled). The +0.47 floor in the brief is the **6-rhythm witness sweep**. It is not this corpus and was not re-measured.

| encoder | worst pair | off-diag mean | best pair | within-centroid cos | participation |
|---|---|---|---|---|---|
| frozen live 128 | reflect–rupture **+0.691** | 0.544 | stabilize–explore +0.334 | 0.84–0.97 | 3.42 |
| paired 128, this recipe | stabilize–dream **+0.396** | 0.333 | reflect–rupture +0.223 | 0.985–0.997 | 3.90 |
| 256, this recipe | dream–reflect **+0.588** | 0.385 | stabilize–explore +0.267 | 0.990–0.995 | 3.57 |

Same recipe, same seed, same epoch budget: **128 separates better than 256.** The floor did not fall. Orthogonality was not free. The frozen checkpoint's +0.69 worst pair is a different training point (its cones are looser); it is the live baseline, and it is not the dim comparison.

The famous rupture⊥explore centroid of −0.096 is not what `generator_weights_5rhythm.pt` measures on this holdout (that pair is +0.405). That number belongs to the kimi run named in the 2026-08-05 finding. The kimi file is not in `data/checkpoints/` on this machine.

Decode-organ mouth, Phase 0 protocol (frozen encoder, fresh `TokenDecoder`, hidden 256, BCE, 20 epochs, seed 42, recall@8):

| encoder | holdout recall@8 | lift over chance | median true-token rank |
|---|---|---|---|
| frozen live 128 | **0.109** | 9.7× | 33 |
| paired 128, this recipe | 0.088 | 7.8× | 41 |
| 256, this recipe | 0.091 | 8.0× | 41 |

0.109 reproduces the Phase 0 yardstick (0.1106) on the frozen checkpoint. Against that live baseline, 256 is worse. Against the matched retrain, 256 and 128 are the same mouth. The extra conditioning rank was not used. The contrastive loss spent the capacity pulling each rhythm onto a point (within-cosine ~0.99 at both dims under this recipe). A wider linear map into a 4096-d LLM cannot recover token identity the encoder has already thrown away.

Loss was still falling at epoch 20, so a longer run would move both encoders. It would not, by itself, answer a different question than the one this matched pair already answered.

## Verdict

**The lock holds at 256. The payoff does not. Do not ship the bump.**

- Identity, on the 5000-step control, is as tight as 128 (0.000129 vs 0.000109, historical bar 0.000120). No gain change required for that.
- With the loop forced, the walk is wider (0.014 vs 0.010 at 2000 steps) and bounded. Not a break. Raising `field_blend` made it worse. Leave the gain at 0.1.
- DDM thresholds do not need a sweep-driven edit. Distributions stayed in the trickle-immune band.
- Separability got harder, not easier, once training budget is matched. Legibility did not gain room.
- Production dim, perception `W`, the live checkpoint, the real mind, and resonance memory stay as they are.

What would have to be true before folding the 6-rhythm corpus in, or before flipping `CONFIG["dim"]`: an objective that actually occupies the extra axes (this contrastive loss does not), a lock re-run on that checkpoint, and a new perception matrix that is not written over the live mind's `W`.

## Instruments

- `tools/dim256/train_5rhythm.py`, `readout.py`, `lock_gate.py`, `legibility.py`
- Logs: `docs/findings/logs/2026-09-23-dim256/`
- WSL launchers: `tools/dim256/run_*_wsl.sh` (cwd is the Windows repo; the CUDA interpreter is the WSL venv)
