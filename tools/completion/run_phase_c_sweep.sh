#!/bin/bash
# Full phase-C frontier. Dim 128, 80 epochs, the published S3 fractions.
# No clock changes, no exclusive mode, no --gpu max.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2-phasec
export PYTHONUNBUFFERED=1
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
mkdir -p docs/findings/logs/2026-09-23-phase-c
"$PY" -m tools.completion.phase_c_curve --sweep --epochs 80 --dim 128 --seed 0 \
  > docs/findings/logs/2026-09-23-phase-c/sweep.log 2>&1
