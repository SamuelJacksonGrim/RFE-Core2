#!/bin/bash
# Short PR probe. No mouth. Same rows as the fraction-1.0 smoke.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2-phasec
export PYTHONUNBUFFERED=1
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
TRAIN=/mnt/c/Users/spamw/rfe/scratch/completion/s3/phasec_mix__phasec_smoke_r100s0_train.jsonl
HOLD=/mnt/c/Users/spamw/rfe/scratch/completion/s3/phasec_recur_holdout.jsonl
"$PY" -m tools.completion.train \
  --dim 128 --epochs 15 --seed 0 --batch-size 128 \
  --lr 0.01 --weight-decay 0 --rhythm-weight 0 --cond-scale 0 \
  --encoder rope --tag _phasec_prefix15_r100s0 \
  --train-rows "$TRAIN" --hold-rows "$HOLD"
