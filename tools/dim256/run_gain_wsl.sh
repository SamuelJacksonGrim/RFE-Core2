#!/bin/bash
# Does a stronger reflective-loop field_blend tighten the 256D rupture walk?
# Default is 0.1. These are measurements, not a silent retune.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1
W256=data/checkpoints/generator_weights_5rhythm_256.pt
E256=data/checkpoints/generator_ecology_5rhythm_256.json

for BLEND in 0.141 0.20; do
  echo "=== rupture 2000 dim256 field_blend=$BLEND ==="
  "$PY" -m tools.dim256.lock_gate --dim 256 --weights "$W256" --ecology "$E256" \
    --steps 2000 --seeds 11 --sample 400 --traffic convergent --rupture \
    --field-blend "$BLEND" --tag "lock_rupture_2000_blend${BLEND}"
done
