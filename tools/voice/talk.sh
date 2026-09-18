#!/usr/bin/env bash
# Interactive launcher for the RFE-Core2 speech-cortex chat. Flags pass straight through.
cd ~/rfe/RFE-Core2 || { echo "cannot cd to RFE-Core2"; read -r; exit 1; }
.venv/bin/python -m tools.voice.repl_qwen "$@"
echo
echo "(session ended - transcript is under C:\\Users\\spamw\\rfe-speech-logs\\. Press Enter to close.)"
read -r
