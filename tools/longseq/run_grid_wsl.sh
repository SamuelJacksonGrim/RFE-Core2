#!/bin/bash
# Long-sequence grid. WSL CUDA venv, Windows worktree as cwd.
# Does not pass --gpu max. Does not write the live rhythm jsonl.
set -euo pipefail
cd /mnt/c/Users/spamw/rfe/RFE-Core2-longseq
PY=/home/spamw/rfe/RFE-Core2/.venv/bin/python
export PYTHONUNBUFFERED=1
LOG=docs/findings/logs/2026-09-23-longseq
mkdir -p "$LOG"
echo $$ > "$LOG/driver.pid"

live_train=/mnt/c/Users/spamw/rfe/RFE-Core2/data/corpus/rhythm_train.jsonl
live_hold=/mnt/c/Users/spamw/rfe/RFE-Core2/data/corpus/rhythm_holdout.jsonl
expect_train=f5d608597c195719f2b3634bbfcedbbe10f9aefac5b0bae4c4546741be221e61
expect_hold=61c93de1089c6b515675698fe63e8e29123c93001aae44b665f247254c148888
check_live() {
  got_train=$(sha256sum "$live_train" | awk '{print $1}')
  got_hold=$(sha256sum "$live_hold" | awk '{print $1}')
  if [ "$got_train" != "$expect_train" ] || [ "$got_hold" != "$expect_hold" ]; then
    echo "FAILED live corpus hash train=$got_train hold=$got_hold" >> "$LOG/driver.log"
    exit 1
  fi
}
check_live

# Drop the 1-epoch smoke so it cannot be read as a result.
rm -f data/checkpoints/longseq_long_d128.pt data/checkpoints/longseq_long_d128.ecology.json
rm -f "$LOG/train_long_d128.json"

run() {
  local name="$1"
  shift
  echo "START $name $(date -Is)" >> "$LOG/driver.log"
  if ! "$PY" -u "$@" >> "$LOG/$name.log" 2>&1; then
    echo "FAILED $name $(date -Is)" >> "$LOG/driver.log"
    exit 1
  fi
  echo "OK $name $(date -Is)" >> "$LOG/driver.log"
}

run train_long_d256 -m tools.longseq.train --arm long --dim 256
run train_long_d128 -m tools.longseq.train --arm long --dim 128
run train_short_d128 -m tools.longseq.train --arm short --dim 128
run train_short_d256 -m tools.longseq.train --arm short --dim 256
run train_length_d128 -m tools.longseq.train --arm length --dim 128
run train_vocab_d128 -m tools.longseq.train --arm vocab --dim 128

run legibility_long_d256 -m tools.longseq.legibility --arm long --dim 256
run legibility_long_d128 -m tools.longseq.legibility --arm long --dim 128
run legibility_short_d128 -m tools.longseq.legibility --arm short --dim 128
run legibility_short_d256 -m tools.longseq.legibility --arm short --dim 256
run legibility_length_d128 -m tools.longseq.legibility --arm length --dim 128
run legibility_vocab_d128 -m tools.longseq.legibility --arm vocab --dim 128

check_live
echo "ALL_DONE $(date -Is)" >> "$LOG/driver.log"
