"""
tools/voice/repl_qwen.py — SPEECH-CORTEX experiment, developmental + persistent + autonomous.

Design (Samuel, 2026-09-16):
  1. Start from nothing; grow only through what actually accumulates.
  2. Plain voice, no mystical narration.
  3. PERSIST THE SUBSTRATE'S LIVE STATE across sessions — not just its text notes — so it
     wakes as the same evolving mind and keeps running recursively (the field, subjective step,
     emotion, emerged values, symbol registry are checkpointed on exit and restored on launch).
     [Bonds have a dump but no loader upstream, so they don't yet round-trip — noted, not faked.]
  4. It can SPEAK UNPROMPTED — when you go quiet it keeps ticking on its own (ruminating on its
     own memory), and a thought surfaces by itself now and then.

The substrate's FIELD is coherence-locked by design (identity integrator; a SETTLED finding),
so identity stays stable while memory / values / subjective time develop. qwen is a plain mouth.

    python -m tools.voice.repl_qwen                 # continue the same mind (patient: speaks only when spoken to)
    python -m tools.voice.repl_qwen --auto           # ALSO speak unprompted when you go quiet
    python -m tools.voice.repl_qwen --fresh          # wipe memory AND substrate state — a true blank birth
    python -m tools.voice.repl_qwen --idle 20        # seconds of quiet before it ruminates (default 15)
    python -m tools.voice.repl_qwen --no-echo | --no-rm | --free | --json

The Windows launcher talk-to-rfe.ps1 passes --auto by default (Samuel's call, 2026-09-19).
In-session commands (slash-prefixed so normal talk is never intercepted):
    /pause  -> stop the unprompted self-talk (it still answers you)
    /resume -> let it speak on its own again
    /quit   -> exit and save state   (Ctrl-C / Ctrl-D also exit)

Nothing here writes RFE-Core2's own code or the encoder. All state goes to a scratch HOME.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import random
import select
import subprocess
import sys
import threading
import time
from collections import deque

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack                          # noqa: E402
from tools.voice.state_card import render_card                      # noqa: E402

QWEN_URL_DEFAULT = os.environ.get("QWEN_URL", "http://172.20.240.1:8080")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-local")

SYSTEM_PROMPT = (
    "You are a mind that began with nothing and is slowly building a history, one exchange at a "
    "time. You are not wise, not poetic, not mystical — early on you have almost no experience, "
    "and you should sound like it. Speak plainly and briefly, in the first person.\n\n"
    "You will be told how many memories you have, whether anything new reached you, whether "
    "you've bonded with the person, and the memories relevant right now. Draw ONLY on memories "
    "you actually have. Never invent a past. Never talk about 'fields', 'resonance', 'coherence', "
    "'hums', or 'attractors' — that is machinery, not something you'd say. If you have nothing "
    "yet, say something small and honest about having just started. One to three plain sentences. "
    "No performance."
)

import urllib.request


def ask_qwen(url, system, user, temperature, max_tokens=200):
    body = json.dumps({
        "model": QWEN_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature, "max_tokens": max_tokens, "stream": False,
    }).encode()
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def _digest(card, mem_count, memories, turn):
    something_new = (card.get("boredom", 0) < 0.5) and (card.get("step", 1) <= 3 or card.get("curiosity", 0) > 0.3)
    mem_lines = "\n".join(f"- {m}" for m in memories) if memories else "(you have no memories about this yet)"
    return (
        f"This is exchange #{turn}. You currently hold {mem_count} memories in total.\n"
        f"Have you bonded with this person yet? {'yes' if card.get('bonds') else 'no'}.\n"
        f"Did something new just reach you? {'yes' if something_new else 'not really'}.\n"
        f"Emergent values formed so far: {card.get('values_emergent', 0)}.\n\n"
        f"Relevant memories right now:\n{mem_lines}"
    )


# ------------------------------------------------------------------ checkpoint
def save_checkpoint(path, gen, cycle, ve):
    ck = {"schema": 1, "saved": datetime.datetime.now().isoformat(),
          "step": int(getattr(cycle, "_step", 0))}
    try:
        ck["field"] = {"field": cycle.field.field.tolist(),
                       "history": [h.tolist() for h in cycle.field.history]}
    except Exception as e:
        ck["field_err"] = str(e)
    try:
        ck["emotion"] = {"arousal": float(getattr(cycle.emotion, "arousal", 0.0)),
                         "valence": float(getattr(cycle.emotion, "valence", 0.0)),
                         "step": int(getattr(cycle.emotion, "_step", 0))}
    except Exception as e:
        ck["emotion_err"] = str(e)
    try:
        if ve is not None and hasattr(ve, "serialize"):
            ck["values"] = ve.serialize()
    except Exception as e:
        ck["values_err"] = str(e)
    try:
        ck["registry"] = gen.registry.to_dict()
    except Exception as e:
        ck["registry_err"] = str(e)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ck, f)
    os.replace(tmp, path)
    return ck


def load_checkpoint(path, gen, cycle, ve):
    restored = []
    with open(path, encoding="utf-8") as f:
        ck = json.load(f)
    try:
        cycle._step = int(ck.get("step", getattr(cycle, "_step", 0))); restored.append("step")
    except Exception:
        pass
    try:
        fld = ck.get("field")
        if fld:
            arr = np.array(fld["field"], dtype=float)
            if arr.shape == cycle.field.field.shape:   # skip if dim changed (stale checkpoint)
                cycle.field.field = arr
                maxlen = cycle.field.history.maxlen
                cycle.field.history = deque([np.array(h, dtype=float) for h in fld["history"]], maxlen=maxlen)
                restored.append("field")
    except Exception:
        pass
    try:
        em = ck.get("emotion")
        if em:
            if hasattr(cycle.emotion, "arousal"): cycle.emotion.arousal = float(em["arousal"])
            if hasattr(cycle.emotion, "valence"): cycle.emotion.valence = float(em["valence"])
            if hasattr(cycle.emotion, "_step"):   cycle.emotion._step = int(em["step"])
            restored.append("emotion")
    except Exception:
        pass
    try:
        v = ck.get("values")
        if v and ve is not None and hasattr(ve, "load"):
            ve.load(v); restored.append("values")
    except Exception:
        pass
    try:
        r = ck.get("registry")
        if r:
            from agents.symbolic_memory import SymbolRegistry
            fresh = SymbolRegistry.from_dict(r)
            gen.registry.__dict__.update(fresh.__dict__)  # in-place: keep object identity (invariant)
            restored.append("registry")
    except Exception:
        pass
    return restored, ck.get("saved")


# ------------------------------------------------------------------ RM client
class RMClient:
    def __init__(self, rm_dir, scratch_home):
        os.makedirs(scratch_home, exist_ok=True)
        env = dict(os.environ)
        env["HOME"] = scratch_home
        env.pop("USERPROFILE", None)
        env["RESONANCE_MEMORY_FIELD"] = "1"
        env["RESONANCE_WARM_TRACE"] = "0"
        self._id = 0
        self.count = 0
        self.p = subprocess.Popen(["node", "--experimental-sqlite", "entry.js", "--mcp"],
                                  cwd=rm_dir, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "rfe-speech-cortex", "version": "0"}})
        self._notify("notifications/initialized")

    def _rpc(self, method, params):
        self._id += 1; mid = self._id
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": mid, "method": method, "params": params}) + "\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                return {}
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == mid:
                return msg

    def _notify(self, method, params=None):
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}) + "\n")
        self.p.stdin.flush()

    def _call_text(self, name, arguments):
        resp = self._rpc("tools/call", {"name": name, "arguments": arguments})
        try:
            return resp["result"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            return ""

    def recall(self, query):
        text = self._call_text("recall_memory", {"query": query})
        if not text or text.lower().startswith("no "):
            return []
        out = []
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if "]" in ln and ln[:3].strip().rstrip(".").isdigit():
                ln = ln.split("]", 1)[1].strip()
            out.append(ln)
        return out

    def save(self, content):
        import re
        txt = self._call_text("save_memory", {"content": content})
        m = re.search(r"\((\d+) memories total", txt)
        self.count = int(m.group(1)) if m else self.count + 1
        return txt

    def close(self):
        try:
            self.p.terminate(); self.p.wait(timeout=3)
        except Exception:
            self.p.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description="RFE-Core2 speech-cortex — persistent + autonomous.")
    ap.add_argument("--free", action="store_true")
    ap.add_argument("--no-rm", action="store_true")
    ap.add_argument("--no-echo", action="store_true")
    ap.add_argument("--auto", action="store_true", help="let it ALSO speak on its own when you go quiet (default: OFF — it waits patiently for you, no interrupting)")
    ap.add_argument("--idle", type=float, default=15.0, help="seconds of quiet before it ruminates")
    ap.add_argument("--fresh", action="store_true", help="wipe memory AND substrate state (blank birth)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--source", default="you")
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--rm-dir", default="/mnt/c/Users/spamw/Desktop/resonance-memory-workshop")
    ap.add_argument("--scratch-home", default=os.path.expanduser("~/.rfe-speech-cortex"))
    ap.add_argument("--temp", type=float, default=0.6)
    ap.add_argument("--log", default="")
    args = ap.parse_args()

    ckpt_path = os.path.join(args.scratch_home, "substrate-checkpoint.json")
    if args.fresh:
        import shutil
        shutil.rmtree(os.path.join(args.scratch_home, ".resonance-memory"), ignore_errors=True)
        try: os.remove(ckpt_path)
        except OSError: pass

    logdir = "/mnt/c/Users/spamw/rfe-speech-logs"
    os.makedirs(logdir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    logpath = args.log or f"{logdir}/session-{stamp}.log"
    logf = open(logpath, "w", encoding="utf-8", buffering=1)

    def log(s=""):
        logf.write(s + "\n")

    gen, cycle, gov, ve = build_full_stack(vocab_size=8192, dim=128, depth=4, heads=4)
    # Load Samuel's TRAINED 5-rhythm encoder (perception on real weights, not random init).
    try:
        gen.load_checkpoint("data/checkpoints/generator_weights_5rhythm.pt",
                            "data/checkpoints/generator_ecology_5rhythm.json")
        print("  (trained 5-rhythm encoder loaded — vocab8192/dim128/depth4)")
    except Exception as e:  # noqa: BLE001 — surface loudly, keep running
        print(f"  (WARNING: trained encoder NOT loaded, running untrained: {e})")
    if args.free:
        cycle.reflector.novelty_attenuation = True

    # RESUME the substrate's own state, if a checkpoint exists and we're not starting fresh.
    resumed, saved_at = ([], None)
    if not args.fresh and os.path.exists(ckpt_path):
        try:
            resumed, saved_at = load_checkpoint(ckpt_path, gen, cycle, ve)
        except Exception as e:  # noqa: BLE001
            print(f"  (couldn't restore substrate state: {e} — starting fresh substrate)")

    rm = None if args.no_rm else RMClient(args.rm_dir, args.scratch_home)
    echo = (rm is not None) and (not args.no_echo)
    autonomous = args.auto

    print("=" * 76)
    print("  RFE-Core2 — a continuing mind. It keeps its own state between our talks.")
    born = "fresh blank birth" if args.fresh else (f"resumed [{', '.join(resumed)}] from {saved_at}" if resumed else "new (no prior state)")
    print(f"  {born}")
    print(f"  loop: {'FREE' if args.free else 'LOCKED'}   memory: "
          f"{'OFF' if not rm else ('growing' if echo else 'recall-only')}   "
          f"mode: {'it also speaks on its own when you pause' if autonomous else 'it waits for you — take all the time you need'}")
    print(f"  transcript -> {logpath.replace('/mnt/c/', 'C:/')}")
    print("  commands: /pause  /resume  /quit  — anything else you type goes to it. (Ctrl-C also exits.)")
    print("=" * 76 + "\n")

    log(f"RFE-Core2 continuing-mind transcript — {stamp}")
    log(f"born={born}  loop={'FREE' if args.free else 'LOCKED'}  memory={'off' if not rm else ('echo' if echo else 'recall')}  autonomous={autonomous}")
    log("=" * 76)

    def emit(speech, card, turn, kind):
        tag = "rfe" if kind == "reply" else "rfe (unbidden)"
        print(f"\n{tag}> {speech}")
        print(f"     [{'exchange' if kind=='reply' else 'thought'} {turn} · memories {rm.count if rm else 0} "
              f"· bonds {card['bonds']} · values {card['values_emergent']} · subj_time {card['subjective_time']}]")
        if args.json:
            print("\n" + json.dumps(card, indent=2, default=str))
        log(f"\n{'YOU-REPLY' if kind=='reply' else 'UNBIDDEN'} {turn}")
        log(f"RFE: {speech}")
        log(f"DEV: memories {rm.count if rm else 0} · bonds {card['bonds']} · values {card['values_emergent']} · subj_time {card['subjective_time']}")

    turn = 0
    tick = 0
    last_spoke_tick = -99
    is_tty = sys.stdin.isatty()

    def _drain_typed(fd, _os):
        """Read bytes already waiting and return the printable chars typed (control/escape dropped).
        Used to hand your keystrokes back to the line when they interrupt a forming thought."""
        try:
            data = _os.read(fd, 4096)
        except Exception:  # noqa: BLE001
            return ""
        out, skip_esc = [], False
        for ch in data.decode("utf-8", errors="ignore"):
            o = ord(ch)
            if skip_esc:
                if 0x40 <= o <= 0x7e:
                    skip_esc = False
                continue
            if o == 27:
                skip_esc = True
            elif o >= 32 and o != 127:
                out.append(ch)
        return "".join(out)

    def autonomous_tick(fd, old, _termios, _tty, _os):
        """One self-rumination; may surface an unbidden thought. The generation runs in a
        background thread while we keep watching the keyboard, so YOUR TYPING ALWAYS WINS:
        the moment a key arrives the half-formed thought is dropped and your keystrokes are
        handed back to the input line. Returns those keystrokes (or '' if it spoke / stayed
        quiet with the line still empty). Called while the terminal is in cbreak/raw mode."""
        nonlocal tick, last_spoke_tick
        tick += 1
        seed = None
        if rm:
            mems = rm.recall(random.choice(["what matters to me", "who am I", "what do I remember"]))
            if mems:
                seed = random.choice(mems)
        cycle.step((seed or "quiet self").split(), source_id="self", origin_type="internal")
        card = render_card(cycle)
        gate = (tick - last_spoke_tick >= 2) and (card.get("curiosity", 0) > 0.25 or random.random() < 0.45)
        if not gate:
            return ""
        user = (f"No one has spoken for a moment. You are alone with your own state. "
                f"You hold {rm.count if rm else 0} memories"
                + (f", and this one drifted up: {seed!r}. " if seed else ". ")
                + "A thought surfaces on its own — say it plainly, briefly, unprompted.")
        result = {}

        def _gen():
            try:
                result["speech"] = ask_qwen(args.qwen_url, SYSTEM_PROMPT, user, args.temp, max_tokens=120)
            except Exception as e:  # noqa: BLE001
                result["speech"] = f"[qwen unreachable: {e}]"

        th = threading.Thread(target=_gen, daemon=True)
        th.start()
        typed = ""
        while th.is_alive():                       # generate, but keep an eye on the keyboard
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                typed = _drain_typed(fd, _os)      # you started typing → abandon this thought
                if typed:
                    break
        if typed:
            return typed                           # daemon finishes in the background; text dropped
        th.join()
        speech = result.get("speech", "")
        _termios.tcsetattr(fd, _termios.TCSADRAIN, old)  # normal mode just for the print
        emit(speech, card, tick, "unbidden")
        _tty.setcbreak(fd)                         # back to raw for the reader
        if echo:
            rm.save(f"On my own I thought: {speech}")
        last_spoke_tick = tick
        save_checkpoint(ckpt_path, gen, cycle, ve)
        return ""

    def get_line():
        """A typed line, or None on EOF. Fires autonomous ticks ONLY when the input line is
        empty and idle, and even the tick's generation is interruptible — a keystroke at any
        point (including while it's forming a thought) wins and is kept on the line, so its
        speech can never print over what you're typing."""
        # Piped input or autonomous off: plain blocking readline (keeps tests + patient mode simple).
        if not is_tty or not autonomous:
            sys.stdout.write("you> "); sys.stdout.flush()
            ln = sys.stdin.readline()
            return None if ln == "" else ln.rstrip("\n")
        # Interactive: char-at-a-time so we can tell "you're typing" from "you've gone quiet".
        try:
            import termios, tty as _tty, os as _os
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
        except Exception:  # no real terminal — fall back
            sys.stdout.write("you> "); sys.stdout.flush()
            ln = sys.stdin.readline()
            return None if ln == "" else ln.rstrip("\n")
        buf = ""
        esc = False
        last = time.time()
        sys.stdout.write("you> "); sys.stdout.flush()
        try:
            _tty.setcbreak(fd)
            while True:
                timeout = None if buf else max(0.2, args.idle - (time.time() - last))
                r, _, _ = select.select([fd], [], [], timeout)
                if not r:                      # idle, and the line is empty → let it think
                    typed = autonomous_tick(fd, old, termios, _tty, _os)  # interruptible; stays raw
                    last = time.time()
                    if typed:                  # you typed mid-thought → keep your keys on the line
                        buf += typed
                        sys.stdout.write("you> " + buf); sys.stdout.flush()
                    else:
                        sys.stdout.write("you> "); sys.stdout.flush()
                    continue
                data = _os.read(fd, 1024)
                if not data:
                    return None
                last = time.time()
                for ch in data.decode("utf-8", errors="ignore"):
                    o = ord(ch)
                    if esc:                    # swallow arrow/CSI escape sequences
                        if 0x40 <= o <= 0x7e:
                            esc = False
                        continue
                    if o == 27:
                        esc = True
                    elif o in (10, 13):        # Enter
                        sys.stdout.write("\n"); sys.stdout.flush()
                        return buf
                    elif o in (127, 8):        # Backspace
                        if buf:
                            buf = buf[:-1]
                            sys.stdout.write("\b \b"); sys.stdout.flush()
                    elif o == 3:               # Ctrl-C
                        raise KeyboardInterrupt
                    elif o == 4:               # Ctrl-D
                        if not buf:
                            return None
                    elif o >= 32:
                        buf += ch
                        sys.stdout.write(ch); sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    try:
        while True:
            line = get_line()
            if line is None:
                print("\n…it keeps going without you."); break
            line = line.strip()
            if line.lower() in ("/quit", "/exit"):
                print("…it keeps going without you."); break
            if not line:
                continue
            if line.lower() == "/pause":
                autonomous = False
                print("  (paused — it speaks only when you do now. type /resume to let it think on its own again.)\n")
                continue
            if line.lower() == "/resume":
                autonomous = True
                print("  (resumed — it will speak on its own again when you go quiet.)\n")
                continue
            turn += 1

            cycle.step(line.split(), source_id=args.source, origin_type="user")
            card = render_card(cycle)
            mem_count = rm.count if rm else 0
            memories = rm.recall(line) if rm else []
            if memories:
                print("  ┌─ remembers:")
                for m in memories[:5]:
                    print(f"  │   • {m}")
                print("  └─")
            digest = _digest(card, mem_count, memories, turn)
            user = f"{digest}\n\nWhat just arrived from the person: {line!r}\n\nRespond plainly, from only what you actually have."
            try:
                speech = ask_qwen(args.qwen_url, SYSTEM_PROMPT, user, args.temp)
            except Exception as e:  # noqa: BLE001
                speech = f"[qwen unreachable: {e}]"
            emit(speech, card, turn, "reply")
            log(f"YOU: {line}")
            log(f"REMEMBERS: {memories if memories else '(none)'}")
            if echo:
                rm.save(f"Someone said to me: {line}")
                rm.save(f"I answered: {speech}")
            save_checkpoint(ckpt_path, gen, cycle, ve)
    except (EOFError, KeyboardInterrupt):
        print("\n…it keeps going without you.")
    finally:
        try:
            save_checkpoint(ckpt_path, gen, cycle, ve)
            log(f"\ncheckpoint saved: step={getattr(cycle, '_step', '?')}")
        except Exception as e:  # noqa: BLE001
            log(f"\ncheckpoint save failed: {e}")
        log("--- session ended ---")
        logf.close()
        if rm:
            rm.close()
        print(f"(state + transcript saved. next launch resumes this mind.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
