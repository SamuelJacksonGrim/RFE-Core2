#!/bin/bash
# Silent until the grid fails, the first cell finishes, or the driver exits.
set -euo pipefail
LOG=/mnt/c/Users/spamw/rfe/RFE-Core2-longseq/docs/findings/logs/2026-09-23-longseq/driver.log
PIDFILE=/mnt/c/Users/spamw/rfe/RFE-Core2-longseq/docs/findings/logs/2026-09-23-longseq/driver.pid
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  [ -f "$PIDFILE" ] && break
  sleep 5
done
if [ ! -f "$PIDFILE" ]; then
  echo "FAILED: longseq driver pid never appeared"
  exit 1
fi
PID=$(cat "$PIDFILE")
seen=0
while kill -0 "$PID" 2>/dev/null; do
  if [ -f "$LOG" ] && grep -q '^FAILED' "$LOG"; then
    echo "FAILED: longseq grid $(grep '^FAILED' "$LOG" | tail -1)"
    exit 1
  fi
  if [ "$seen" = 0 ] && [ -f "$LOG" ] && grep -q '^OK ' "$LOG"; then
    echo "ACTION_REQUIRED: first longseq cell finished: $(grep '^OK ' "$LOG" | head -1)"
    seen=1
  fi
  sleep 30
done
sleep 2
if [ -f "$LOG" ] && grep -q '^ALL_DONE' "$LOG"; then
  echo "DONE: longseq grid"
  exit 0
fi
if [ -f "$LOG" ] && grep -q '^FAILED' "$LOG"; then
  echo "FAILED: longseq grid $(grep '^FAILED' "$LOG" | tail -1)"
  exit 1
fi
echo "FAILED: longseq driver exited without ALL_DONE"
exit 1
