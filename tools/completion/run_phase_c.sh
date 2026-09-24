#!/bin/bash
# Phase C on the Windows worktree, WSL CUDA interpreter.
# No clock changes, no exclusive mode, no --gpu max.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2-phasec
export PYTHONUNBUFFERED=1
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
mkdir -p docs/findings/logs/2026-09-23-phase-c
exec "$PY" -m tools.completion.phase_c_curve "$@"
