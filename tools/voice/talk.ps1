# Windows counterpart of talk.sh — runs the bridge via the repo venv. No WSL.
# Flags pass straight through to tools.voice.repl_qwen.
# Perception is ON by default (Qwen embedder :8081). Pass --flat-encoder for the
# trained 5-rhythm encoder (Windows: talk-to-rfe.ps1 -FlatEncoder).
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$BridgeArgs)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host "cannot find venv python at $py"
    exit 1
}
Set-Location $root
& $py -m tools.voice.repl_qwen @BridgeArgs
$exit = $LASTEXITCODE
Write-Host ""
Write-Host "(session ended - transcript is under C:\Users\spamw\rfe-speech-logs\.)"
exit $exit
