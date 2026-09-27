#!/bin/bash
# Train from the Windows checkout using the WSL CUDA venv.
# Checkpoints land in /mnt/c/.../data/checkpoints (the main repo).
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1
# Do not touch GPU clocks or exclusive mode. Just run the trainer.
exec "$PY" -m tools.dim256.train_5rhythm "$@"
