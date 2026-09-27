#!/bin/bash
# One-epoch pipeline check. Distinct tag so it cannot be read as the 80-epoch frontier.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2-phasec
export PYTHONUNBUFFERED=1
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
mkdir -p docs/findings/logs/2026-09-23-phase-c
"$PY" -m tools.completion.phase_c_curve --fractions 1.0 --epochs 1 --dim 128 --tag-prefix _phasec_smoke \
  > docs/findings/logs/2026-09-23-phase-c/smoke.log 2>&1
