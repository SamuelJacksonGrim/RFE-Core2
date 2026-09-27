#!/bin/bash
# Run a completion-experiment module on the Windows checkout with the WSL CUDA
# interpreter. No clock changes, no exclusive mode, no --gpu max.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1
exec "$PY" "$@"
