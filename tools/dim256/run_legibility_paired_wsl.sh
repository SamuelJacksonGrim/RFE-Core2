#!/bin/bash
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1
exec "$PY" -m tools.dim256.legibility --dim 128 \
  --weights data/checkpoints/generator_weights_5rhythm_128paired.pt \
  --ecology data/checkpoints/generator_ecology_5rhythm_128paired.json \
  --no-save \
  --report docs/findings/logs/2026-09-23-dim256/legibility_dim128paired.json
