#!/usr/bin/env bash
# Interactive launcher for the RFE-Core2 speech-cortex chat. Flags pass straight through.
# Perception is ON by default (Qwen embedder :8081). Pass --flat-encoder to use the
# trained 5-rhythm encoder instead (Windows: talk-to-rfe.ps1 -FlatEncoder).
cd ~/rfe/RFE-Core2 || { echo "cannot cd to RFE-Core2"; read -r; exit 1; }
.venv/bin/python -m tools.voice.repl_qwen "$@"
echo
echo "(session ended - transcript is under C:\\Users\\spamw\\rfe-speech-logs\\. Press Enter to close.)"
read -r
