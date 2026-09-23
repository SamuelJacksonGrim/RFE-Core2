#!/bin/bash
# Paired 128 retrain (same recipe as the 256 run) plus decode-organ legibility.
# Never writes the live 128D checkpoint names.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1

echo "=== paired 128 train ==="
"$PY" -m tools.dim256.train_5rhythm --dim 128 --epochs 20 --seed 0 \
  --weights data/checkpoints/generator_weights_5rhythm_128paired.pt \
  --ecology data/checkpoints/generator_ecology_5rhythm_128paired.json \
  --report docs/findings/logs/2026-09-23-dim256/train_dim128paired_s0.json

echo "=== legibility frozen 128 ==="
"$PY" -m tools.dim256.legibility --dim 128 \
  --weights data/checkpoints/generator_weights_5rhythm.pt \
  --ecology data/checkpoints/generator_ecology_5rhythm.json \
  --no-save \
  --report docs/findings/logs/2026-09-23-dim256/legibility_frozen128.json

echo "=== legibility 256 ==="
"$PY" -m tools.dim256.legibility --dim 256 \
  --weights data/checkpoints/generator_weights_5rhythm_256.pt \
  --ecology data/checkpoints/generator_ecology_5rhythm_256.json \
  --save data/checkpoints/decoder_5rhythm_256.pt \
  --report docs/findings/logs/2026-09-23-dim256/legibility_dim256.json
