#!/bin/bash
# Short identity-lock comparison. Does not write checkpoints.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1

echo "=== LOCK 256 convergent ==="
"$PY" -m tools.dim256.lock_gate --dim 256 \
  --weights data/checkpoints/generator_weights_5rhythm_256.pt \
  --ecology data/checkpoints/generator_ecology_5rhythm_256.json \
  --steps 250 --seeds 11,23 --traffic convergent --tag lock_short

echo "=== LOCK 128 convergent (frozen live encoder) ==="
"$PY" -m tools.dim256.lock_gate --dim 128 \
  --weights data/checkpoints/generator_weights_5rhythm.pt \
  --ecology data/checkpoints/generator_ecology_5rhythm.json \
  --steps 250 --seeds 11,23 --traffic convergent --tag lock_short
