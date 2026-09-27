# Banked mouth — S2 completion encoder

Phase C does not retrain this model and does not load it. It is the verified
legible mouth / static retrieval organ from Phase B slice S2. Later sequence
checkpoints use new filenames (`sequence_encoder_phasec_*`). The names below
are refused by `tools/completion/live_guard.py`.

Recipe: residual completion, full stack, lr 0.01, weight decay 0, rhythm
weight 0, cond scale 0, batch 128, 40 epochs, seed 0, tag `_phaseb`.
Measured on the live holdout: recall@8 **0.6936** at dim 128 (median rank 1)
and **0.6573** at dim 256 (median rank 1). Output participation **56.581** /
**73.531**. Full-stack output, not a collapsed stack (stack-only participation
0.612 / 0.729 is the stripped direction, recorded in `s2_summary.json`).

Copies live next to the originals under `data/checkpoints/`. Checkpoints are
gitignored. The hashes are the record. A copy was also placed in the
`experiment/phase-c` worktree so that tree does not need to write the originals.

| role | file | sha256 |
|---|---|---|
| mouth 128 | `generator_weights_completion_128_phaseb.pt` | `db82166f830952c92e291a7dc91e135b3f17ead802640ef0489cdd48dba46f57` |
| mouth 128 copy | `banked_mouth_completion_128.pt` | same |
| ecology 128 | `generator_ecology_completion_128_phaseb.json` | `28cf991862bcbdcb9347f5a7db43af094a61ccb531f2140917c16e43877bf1d4` |
| ecology 128 copy | `banked_mouth_ecology_128.json` | same |
| head 128 | `completion_head_128_phaseb.pt` | `9006e3946a5c0a24ed897cfbc3dc3c4b6e51b0cef74ceede5f1edfa96767081a` |
| head 128 copy | `banked_mouth_head_128.pt` | same |
| mouth 256 | `generator_weights_completion_256_phaseb.pt` | `fdd1da4d2882f285100b27513d3f7fd602e6e6c4b1dde6854c7e31eb98673f40` |
| mouth 256 copy | `banked_mouth_completion_256.pt` | same |
| ecology 256 | `generator_ecology_completion_256_phaseb.json` | `4b3071abd930627c5904417c749df59be70a0ea65731af9b658f8e7e7cb8cad7` |
| ecology 256 copy | `banked_mouth_ecology_256.json` | same |
| head 256 | `completion_head_256_phaseb.pt` | `aaa057e9a59f50e41a4d618a198d130f08ac9dc1731e336f9d2053e5805d31ce` |
| head 256 copy | `banked_mouth_head_256.pt` | same |

Numbers: `docs/findings/logs/2026-09-23-phase-b/s2_summary.json`.
