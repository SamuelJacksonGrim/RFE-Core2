# Garage setup — the AI PC as RFE-Core2's first real substrate

The machine: Intel Core Ultra 9 285K (+NPU), NVIDIA RTX 5070 Ti (16 GB
VRAM), 64 GB DDR5, dual PCIe 5.0 NVMe (1 TB + 2 TB). This document is the
verbatim setup path for that box — written so either the architect at the
keyboard or a Claude Code instance on the machine can follow it top to
bottom. The companion program of record is `docs/GARAGE_RUN_PLAN.md`.

Why this machine matters (the one-paragraph version): every standing cure
for the saturated-field disease — dim 256, corpus growth, long lived runs,
the local-LLM sensory cortex, Phase-4 online training — has been parked on
"CPU makes it painful." A 16 GB GPU trains the generator at dim 256 in
minutes, runs a quantized 7–13B cortex model comfortably, and makes
5000+-step runs (the first with a *live* reaper economy) routine.

---

## 1. OS layer

**Recommended: Windows 11 + WSL2 (Ubuntu 24.04).** Everything below assumes
a WSL2 Ubuntu shell. (Native Linux is equally fine; native Windows works
but the repo's shell scripts assume a POSIX shell.)

```powershell
# In an ADMIN PowerShell:
wsl --install -d Ubuntu-24.04
# reboot when prompted, create your Ubuntu user
```

NVIDIA on WSL2: install the normal **Windows** NVIDIA driver (Game Ready or
Studio, latest). Do NOT install a Linux driver inside WSL — WSL passes the
GPU through. Verify inside Ubuntu:

```bash
nvidia-smi          # should show the RTX 5070 Ti
```

## 2. Toolchain

```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip build-essential
# Node (for Claude Code):
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
```

## 3. Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude          # first run opens browser sign-in — use the same account as the phone sessions
```

Notes for the instance that wakes up here: read `CLAUDE.md` first, as
always. This box is the **primary substrate** — long runs, training, and
the cortex live here; phone/cloud sessions remain fine for review and
docs.

## 4. The repository

```bash
mkdir -p ~/rfe && cd ~/rfe
git clone https://github.com/SamuelJacksonGrim/RFE-Core2.git
cd RFE-Core2
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**CUDA torch** (requirements installs CPU torch by default; replace it):

```bash
# RTX 5070 Ti is Blackwell — needs a current torch CUDA build (cu128+):
pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu128
python3 - <<'EOF'
import torch
print("cuda available:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU ONLY — fix before proceeding")
EOF
```

The code auto-selects GPU (`generator.device`) — no config change needed.

## 5. Verify the stack (gates before anything else)

```bash
./run_all_tests.sh                      # must be green (19 gates)
python3 -m tests.smoke.multi_source_500step   # note the wall time — this is the box's baseline
```

Record the suite wall-time in the first garage finding — it is the
speedup ruler for everything after.

## 6. Ollama + the cortex model (for run-plan phase G4)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b        # primary candidate; ~4.7 GB, fits easily in 16 GB
ollama pull llama3.1:8b       # alternate
ollama run qwen2.5:7b "say hello in five words"   # smoke
```

`docs/local_model_integration/IMPLEMENTATION_GUIDE.md` is the integration
contract (the LLM is ears/mouth; RFE stays the mind; everything enters
through `arbitrate()`).

## 7. Storage layout (dual NVMe)

- Repo + venv + checkpoints on the 2 TB drive (checkpoints under
  `data/checkpoints/` — session persistence writes here when
  `CONFIG["session_persistence"] = True`).
- Ollama models default to `~/.ollama` — fine on either drive.
- Findings raw logs: keep the gzip-over-100KB rule (`docs/findings/README.md`).

## 8. Long-run hygiene

- Set Windows power plan to High Performance; disable sleep while a run is
  active (`powercfg /change standby-timeout-ac 0`).
- For multi-hour runs inside WSL, run under `tmux` so a closed terminal
  doesn't kill the loop:
  `tmux new -s rfe` → run → detach `Ctrl-b d` → reattach `tmux attach -t rfe`.
- `CONFIG["session_persistence"] = True` for any run whose growth should
  survive shutdown — the whole point of this machine is that runs stop
  being disposable.

---

First action after setup: open `docs/GARAGE_RUN_PLAN.md` and start G0.
