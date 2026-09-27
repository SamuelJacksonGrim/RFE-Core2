#!/bin/bash
# Does the rupture-forced reflective loop keep walking, or does it asymptote?
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1
W256=data/checkpoints/generator_weights_5rhythm_256.pt
E256=data/checkpoints/generator_ecology_5rhythm_256.json
W128=data/checkpoints/generator_weights_5rhythm.pt
E128=data/checkpoints/generator_ecology_5rhythm.json

echo "=== rupture 2000 256 ==="
"$PY" -m tools.dim256.lock_gate --dim 256 --weights "$W256" --ecology "$E256" \
  --steps 2000 --seeds 11 --sample 200 --traffic convergent --rupture --tag lock_rupture_2000

echo "=== rupture 2000 128 ==="
"$PY" -m tools.dim256.lock_gate --dim 128 --weights "$W128" --ecology "$E128" \
  --steps 2000 --seeds 11 --sample 200 --traffic convergent --rupture --tag lock_rupture_2000
