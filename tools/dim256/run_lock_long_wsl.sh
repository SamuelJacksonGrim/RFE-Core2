#!/bin/bash
# Long control, rupture arm (loop forced), and mixed-traffic DDM sweep.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1

W256=data/checkpoints/generator_weights_5rhythm_256.pt
E256=data/checkpoints/generator_ecology_5rhythm_256.json
W128=data/checkpoints/generator_weights_5rhythm.pt
E128=data/checkpoints/generator_ecology_5rhythm.json

echo "=== 5000-step control 256 seed 11 ==="
"$PY" -m tools.dim256.lock_gate --dim 256 --weights "$W256" --ecology "$E256" \
  --steps 5000 --seeds 11 --sample 250 --traffic convergent --tag lock_5000

echo "=== 5000-step control 128 seed 11 ==="
"$PY" -m tools.dim256.lock_gate --dim 128 --weights "$W128" --ecology "$E128" \
  --steps 5000 --seeds 11 --sample 250 --traffic convergent --tag lock_5000

echo "=== rupture arm 256 ==="
"$PY" -m tools.dim256.lock_gate --dim 256 --weights "$W256" --ecology "$E256" \
  --steps 250 --seeds 11,23 --sample 25 --traffic convergent --rupture --tag lock_rupture

echo "=== rupture arm 128 ==="
"$PY" -m tools.dim256.lock_gate --dim 128 --weights "$W128" --ecology "$E128" \
  --steps 250 --seeds 11,23 --sample 25 --traffic convergent --rupture --tag lock_rupture

echo "=== mixed DDM 256 ==="
"$PY" -m tools.dim256.lock_gate --dim 256 --weights "$W256" --ecology "$E256" \
  --steps 400 --seeds 11 --sample 50 --traffic mixed --tag ddm_mixed

echo "=== mixed DDM 128 ==="
"$PY" -m tools.dim256.lock_gate --dim 128 --weights "$W128" --ecology "$E128" \
  --steps 400 --seeds 11 --sample 50 --traffic mixed --tag ddm_mixed
