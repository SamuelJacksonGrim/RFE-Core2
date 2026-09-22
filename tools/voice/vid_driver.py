#!/usr/bin/env python3
"""Visible-console driver for a short Koneko film.

Adaptation of the demo-capture pty driver (handoff task-20260922-043844).
Spawns `repl_qwen` on a real tty the same way, but the console IS the
deliverable: cleaned pty output is mirrored live to stdout so a Windows
screen capture of this process is the film.

Contract (baked in; Ember films until this process exits):
  --auto --fresh --idle 3.5 --scratch-home /tmp/koneko-vid-<stamp>
  Perception ON (do NOT pass --flat-encoder). Isolated scratch only.
  Inject two human turns after unbidden thoughts 6 and 16.
  /quit after 28 unbidden thoughts; process then exits.

Launch from a Windows console (venv python, no activate needed):
  wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/spamw/rfe/RFE-Core2 && .venv/bin/python tools/voice/vid_driver.py"

Local only — not a product surface. Do not push.
"""
from __future__ import annotations

import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from datetime import datetime

REPO = "/home/spamw/rfe/RFE-Core2"
PY = os.path.join(REPO, ".venv", "bin", "python")
LOG_DIR = "/mnt/c/Users/spamw/rfe-speech-logs"
REAL_MIND = "/home/spamw/.rfe-speech-cortex"
REAL_RM_WIN = "/mnt/c/Users/spamw/.resonance-memory"
REAL_RM_WSL = "/home/spamw/.resonance-memory"

IDLE_DEFAULT = "3.5"
TARGET_DEFAULT = 28
INJECT_A_AT = 6
INJECT_B_AT = 16

PROBE_A = (
    "Ember here. Outside where I am, wind is bending a whole field of "
    "tall grass one way, then it springs back. What do you make of that?"
)
PROBE_B = "If you could ask me one thing — anything — what would it be?"

WALL_CAP_S = 12 * 60
STALL_S = 90
BANNER_DEADLINE_S = 90
QUIT_GRACE_S = 25

ANSI_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\].*?(?:\x07|\x1b\\))"
)
BLOCK_RE = re.compile(
    r"(?:^|\n)(UNBIDDEN|YOU-REPLY) (\d+)\nRFE: (.*?)\nDEV: ([^\n]*)",
    re.S,
)
BORN_RE = re.compile(r"born=(.*)  loop=")
PERC_RE = re.compile(r"perception=([^\n]+?)  think=")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def tree_sig(root: str) -> dict:
    if not os.path.exists(root):
        return {"exists": False, "n": 0, "max_mtime_ns": 0, "bytes": 0}
    n = 0
    mx = 0
    total = 0
    for dirpath, _dirs, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            n += 1
            total += st.st_size
            if st.st_mtime_ns > mx:
                mx = st.st_mtime_ns
    return {"exists": True, "n": n, "max_mtime_ns": mx, "bytes": total}


def strip_ansi(data: bytes) -> str:
    text = data.decode("utf-8", "replace")
    text = ANSI_RE.sub("", text)
    out: list[str] = []
    for ch in text:
        if ch == "\b":
            if out and out[-1] not in "\n\r":
                out.pop()
        elif ch in ("\x07", "\x00"):
            continue
        else:
            out.append(ch)
    return "".join(out)


class LiveEcho:
    """Mirror pty bytes to stdout with prompt_toolkit junk stripped.

    CR overwrites the current line (prompt redraws). Bare `you>` prompts
    and echoes of our own injected turns are dropped so the film reads as
    thoughts, human lines we print ourselves, and replies.
    """

    def __init__(self, out, suppress: set[str] | None = None) -> None:
        self.out = out
        self.buf = ""
        self.suppress = set(suppress or ())
        self.emitted = 0

    def feed(self, data: bytes) -> None:
        # prompt_toolkit uses \r\n; a trailing CR on a complete line is NOT
        # an overwrite. Collapse CRLF first, then treat leftover CR as redraw.
        self.buf += strip_ansi(data).replace("\r\n", "\n")
        while True:
            nl = self.buf.find("\n")
            if nl < 0:
                if "\r" in self.buf and not self.buf.endswith("\r"):
                    self.buf = self.buf.rsplit("\r", 1)[-1]
                break
            line, self.buf = self.buf[:nl], self.buf[nl + 1 :]
            # Trailing CR is CRLF split across reads, not an overwrite.
            line = line.rstrip("\r")
            if "\r" in line:
                line = line.rsplit("\r", 1)[-1]
            self._emit_line(line)

    def _emit_line(self, line: str) -> None:
        raw = line.rstrip()
        s = raw.strip()
        if not s:
            return
        if "cursor position requests (CPR)" in s:
            return
        if re.fullmatch(r"(?:you>\s*)+", s):
            return
        # prompt_toolkit may glue extra `you>` prefixes onto an echo of
        # something we already printed (inject / /quit).
        stripped = re.sub(r"(?:you>\s*)+", "", s).strip()
        if stripped in self.suppress or stripped == "/quit":
            return
        for item in self.suppress:
            if item and item in s:
                return
        try:
            self.out.write(raw + "\n")
            self.out.flush()
            self.emitted += 1
        except BrokenPipeError:
            pass

    def say_human(self, text: str) -> None:
        try:
            self.out.write("\nyou> " + text + "\n")
            self.out.flush()
        except BrokenPipeError:
            pass
        self.suppress.add(text)


class Capture:
    def __init__(self, smoke: bool, idle: str, target: int) -> None:
        self.smoke = smoke
        self.stamp = now_stamp() + ("-smoke" if smoke else "")
        self.scratch = f"/tmp/koneko-vid-{self.stamp}"
        self.bridge = os.path.join(LOG_DIR, f"vid-capture-{self.stamp}.bridge.log")
        self.out_jsonl = os.path.join(LOG_DIR, f"vid-capture-{self.stamp}.jsonl")
        self.pty_path = f"/tmp/koneko-vid-{self.stamp}.pty"
        self.driver_log = f"/tmp/koneko-vid-{self.stamp}.driver.log"
        self.events: list[dict] = []
        self.thoughts: list[dict] = []
        self.replies: list[dict] = []
        self.injects: list[dict] = []
        self.banner: dict = {}
        self.parsed_n = 0
        self.master = None
        self.proc = None
        self.pty_f = None
        self.jsonl_f = None
        self.dlog = None
        self.clean = ""
        self.quit_sent = False
        self._quit_mark = 0.0
        self.t0 = time.time()
        self.last_thought_t = time.time()
        self.sig_mind = tree_sig(REAL_MIND)
        self.sig_rm_win = tree_sig(REAL_RM_WIN)
        self.sig_rm_wsl = tree_sig(REAL_RM_WSL)
        self.fail_reason = ""
        self.finished = False
        self.target = target
        self.probe_a_at = 2 if smoke else INJECT_A_AT
        self.probe_b_at = None if smoke else INJECT_B_AT
        self.idle = idle
        self.echo = LiveEcho(sys.stdout, suppress={PROBE_A, PROBE_B})
        self.reconstruct = False  # flipped on if live echo stays silent

    def log(self, msg: str) -> None:
        line = f"{time.time() - self.t0:8.1f} {msg}"
        if self.dlog:
            self.dlog.write(line + "\n")
            self.dlog.flush()

    def emit_event(self, ev: dict) -> None:
        ev["t"] = round(time.time() - self.t0, 3)
        self.events.append(ev)
        if self.jsonl_f:
            self.jsonl_f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            self.jsonl_f.flush()

    def start(self) -> None:
        if not self.scratch.startswith("/tmp/koneko-vid-"):
            raise SystemExit("refusing non-/tmp/koneko-vid- scratch")
        if os.path.realpath(self.scratch) == os.path.realpath(REAL_MIND):
            raise SystemExit("refusing to use the real mind home")
        os.makedirs(LOG_DIR, exist_ok=True)
        self.dlog = open(self.driver_log, "w", encoding="utf-8", buffering=1)
        self.jsonl_f = open(self.out_jsonl, "w", encoding="utf-8", buffering=1)
        self.pty_f = open(self.pty_path, "wb")
        self.log(f"scratch={self.scratch}")
        self.log(f"bridge={self.bridge}")
        self.log(f"mind_sig={self.sig_mind}")
        self.log(f"rm_win={self.sig_rm_win}")
        self.log(f"rm_wsl={self.sig_rm_wsl}")

        import fcntl
        import pty
        import struct
        import termios

        master, slave = pty.openpty()
        # Wide slave so the filming Windows console, not the pty, does the wrap.
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 48, 220, 0, 0))
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("USERPROFILE", None)
        cmd = [
            PY, "-m", "tools.voice.repl_qwen",
            "--auto", "--fresh",
            "--scratch-home", self.scratch,
            "--idle", self.idle,
            "--log", self.bridge,
        ]
        self.log("cmd=" + " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=REPO,
            env=env,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave)
        self.master = master
        self.emit_event({
            "kind": "meta",
            "stamp": self.stamp,
            "scratch": self.scratch,
            "idle": self.idle,
            "target": self.target,
            "cmd": cmd,
            "smoke": self.smoke,
            "mind_before": self.sig_mind,
            "rm_win_before": self.sig_rm_win,
            "rm_wsl_before": self.sig_rm_wsl,
        })

    def send(self, text: str) -> None:
        payload = text.encode("utf-8") + b"\r"
        os.write(self.master, payload)
        self.log(f"SENT {text[:80]!r}")

    def poll_pty(self) -> None:
        try:
            r, _, _ = select.select([self.master], [], [], 0.3)
        except (ValueError, OSError):
            return
        if not r:
            return
        try:
            data = os.read(self.master, 65536)
        except OSError:
            return
        if not data:
            return
        self.pty_f.write(data)
        self.pty_f.flush()
        # Answer prompt_toolkit's cursor-position request so it doesn't
        # print a CPR warning into the film.
        if b"\x1b[6n" in data:
            try:
                os.write(self.master, b"\x1b[48;220R")
            except OSError:
                pass
        self.echo.feed(data)
        self.clean += strip_ansi(data)
        if len(self.clean) > 2_000_000:
            self.clean = self.clean[-1_000_000:]

    def parse_bridge(self) -> None:
        if not os.path.exists(self.bridge):
            return
        try:
            text = open(self.bridge, encoding="utf-8", errors="replace").read()
        except OSError:
            return
        if not self.banner:
            m = PERC_RE.search(text)
            b = BORN_RE.search(text)
            if m:
                self.banner = {
                    "kind": "banner",
                    "perception": m.group(1).strip(),
                    "born": (b.group(1).strip() if b else ""),
                    "header": text.split("====", 1)[0].strip(),
                }
                self.emit_event(self.banner)
                self.log(f"BANNER perception={self.banner['perception']!r}")
                if "ON (qwen :8081)" not in self.banner["perception"]:
                    self.fail_reason = f"perception not ON: {self.banner['perception']}"
                    return
                self.check_isolation("post-banner")
        matches = list(BLOCK_RE.finditer(text))
        while self.parsed_n < len(matches):
            m = matches[self.parsed_n]
            self.parsed_n += 1
            kind, tick, speech, dev = (
                m.group(1), int(m.group(2)), m.group(3).strip(), m.group(4).strip(),
            )
            if kind == "UNBIDDEN":
                idx = len(self.thoughts) + 1
                ev = {
                    "kind": "thought",
                    "index": idx,
                    "bridge_tick": tick,
                    "text": speech,
                    "state": dev,
                }
                self.thoughts.append(ev)
                self.emit_event(ev)
                self.last_thought_t = time.time()
                self.log(f"THOUGHT {idx} tick={tick} {speech[:70]!r}")
                if speech.startswith("[qwen unreachable"):
                    self.fail_reason = "qwen unreachable: " + speech[:180]
                    return
                self.maybe_reconstruct_thought(ev)
                self.on_thought(ev)
            else:
                ev = {
                    "kind": "reply",
                    "bridge_turn": tick,
                    "text": speech,
                    "state": dev,
                }
                self.replies.append(ev)
                self.emit_event(ev)
                self.log(f"REPLY turn={tick} {speech[:70]!r}")
                self.maybe_reconstruct_reply(ev)

    def maybe_reconstruct_thought(self, ev: dict) -> None:
        if ev["index"] == 1 and self.echo.emitted == 0:
            self.reconstruct = True
            self.log("live echo silent — reconstructing film from the bridge log")
        if not self.reconstruct:
            return
        try:
            sys.stdout.write(f"\nrfe (unbidden)> {ev['text']}\n")
            sys.stdout.write(f"     [thought {ev['bridge_tick']} · {ev['state']}]\n")
            sys.stdout.flush()
        except BrokenPipeError:
            pass

    def maybe_reconstruct_reply(self, ev: dict) -> None:
        if not self.reconstruct:
            return
        try:
            sys.stdout.write(f"\nrfe> {ev['text']}\n")
            sys.stdout.write(f"     [exchange {ev['bridge_turn']} · {ev['state']}]\n")
            sys.stdout.flush()
        except BrokenPipeError:
            pass

    def on_thought(self, ev: dict) -> None:
        n = ev["index"]
        if n == self.probe_a_at and not any(i["probe"] == "A" for i in self.injects):
            self.inject("A", PROBE_A, n)
        if self.probe_b_at and n == self.probe_b_at and not any(i["probe"] == "B" for i in self.injects):
            self.inject("B", PROBE_B, n)
        if n >= self.target and not self.quit_sent:
            self.request_quit(f"reached-{self.target}")

    def inject(self, label: str, text: str, after_index: int) -> None:
        # Let the thought finish landing on the film before the human line.
        time.sleep(0.35)
        self.poll_pty()
        ev = {"kind": "inject", "probe": label, "after_index": after_index, "text": text}
        self.injects.append(ev)
        self.emit_event(ev)
        self.echo.say_human(text)
        self.send(text)
        self.log(f"INJECT {label} after thought {after_index}")

    def request_quit(self, why: str) -> None:
        if self.quit_sent:
            return
        self.quit_sent = True
        self._quit_mark = time.time() - self.t0
        self.log(f"QUIT {why} thoughts={len(self.thoughts)}")
        try:
            self.send("/quit")
        except OSError as e:
            self.log(f"quit write failed: {e}")

    def check_isolation(self, when: str) -> None:
        mind = tree_sig(REAL_MIND)
        rm_win = tree_sig(REAL_RM_WIN)
        rm_wsl = tree_sig(REAL_RM_WSL)
        mind_ok = mind == self.sig_mind
        rm_win_ok = rm_win == self.sig_rm_win
        rm_wsl_ok = rm_wsl == self.sig_rm_wsl
        self.log(
            f"isolation@{when} mind_ok={mind_ok} "
            f"rm_win_ok={rm_win_ok} rm_wsl_ok={rm_wsl_ok}"
        )
        if not (mind_ok and rm_win_ok and rm_wsl_ok):
            self.fail_reason = (
                f"REAL STORE CHANGED at {when} mind_ok={mind_ok} "
                f"rm_win_ok={rm_win_ok} rm_wsl_ok={rm_wsl_ok}"
            )
            self.log(self.fail_reason)

    def isolation_ok(self) -> bool:
        return (
            tree_sig(REAL_MIND) == self.sig_mind
            and tree_sig(REAL_RM_WIN) == self.sig_rm_win
            and tree_sig(REAL_RM_WSL) == self.sig_rm_wsl
        )

    def maybe_stall(self) -> None:
        if self.quit_sent or self.fail_reason:
            return
        if not self.banner:
            if time.time() - self.t0 > BANNER_DEADLINE_S:
                self.fail_reason = "no banner — bridge did not come up"
            return
        gap = time.time() - self.last_thought_t
        if self.thoughts and gap > STALL_S:
            self.fail_reason = f"stall: no thought for {int(gap)}s n={len(self.thoughts)}"
        if not self.thoughts and time.time() - self.t0 > BANNER_DEADLINE_S:
            self.fail_reason = "banner up but no unbidden thought"

    def maybe_cap(self) -> None:
        if self.quit_sent or self.fail_reason:
            return
        if time.time() - self.t0 >= WALL_CAP_S:
            self.request_quit(f"wall-cap n={len(self.thoughts)}")

    def echo_seen(self, text: str) -> bool:
        return text[:48] in self.clean

    def retry_lost_injects(self) -> None:
        if self.fail_reason:
            return
        for inj in self.injects:
            if inj.get("retried"):
                continue
            age = time.time() - self.t0 - inj["t"]
            if age < 4:
                continue
            if self.echo_seen(inj["text"]):
                inj["echo"] = True
                continue
            if age > 6:
                inj["retried"] = True
                self.log(f"inject {inj['probe']} not echoed — resend once")
                try:
                    self.send(inj["text"])
                except OSError as e:
                    self.log(f"resend failed: {e}")

    def kill_child(self) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
        except OSError:
            try:
                self.proc.terminate()
            except OSError:
                pass
        try:
            self.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except OSError:
                pass
            self.proc.wait(timeout=5)

    def loop(self) -> None:
        while True:
            if self.fail_reason:
                self.kill_child()
                break
            self.poll_pty()
            self.parse_bridge()
            self.retry_lost_injects()
            self.maybe_stall()
            self.maybe_cap()
            if self.fail_reason:
                self.kill_child()
                break
            if self.proc.poll() is not None:
                self.poll_pty()
                time.sleep(0.3)
                self.parse_bridge()
                self.log(f"process exit {self.proc.returncode}")
                break
            if self.quit_sent:
                if time.time() - self.t0 - self._quit_mark > QUIT_GRACE_S:
                    self.log("quit timeout — SIGINT then SIGTERM")
                    try:
                        os.write(self.master, b"\x03")
                    except OSError:
                        pass
                    time.sleep(2)
                    if self.proc.poll() is None:
                        self.kill_child()
                    self.poll_pty()
                    self.parse_bridge()
                    break

    def finish(self) -> int:
        if self.finished:
            return 1 if self.fail_reason else 0
        self.finished = True
        self.check_isolation("end")
        mind_ok = tree_sig(REAL_MIND) == self.sig_mind
        rm_win_ok = tree_sig(REAL_RM_WIN) == self.sig_rm_win
        rm_wsl_ok = tree_sig(REAL_RM_WSL) == self.sig_rm_wsl
        code = self.proc.returncode if self.proc else None
        shutdown = {
            "kind": "shutdown",
            "exit": code,
            "thoughts": len(self.thoughts),
            "replies": len(self.replies),
            "injects": len(self.injects),
            "quit_sent": self.quit_sent,
            "fail": self.fail_reason,
            "mind_untouched": mind_ok,
            "rm_win_untouched": rm_win_ok,
            "rm_wsl_untouched": rm_wsl_ok,
            "elapsed_s": round(time.time() - self.t0, 1),
            "scratch": self.scratch,
            "bridge": self.bridge,
            "live_lines": self.echo.emitted,
        }
        if os.path.exists(self.bridge):
            blob = open(self.bridge, encoding="utf-8", errors="replace").read()
            tail = []
            for line in blob.splitlines():
                if (
                    line.startswith("perception wrap:")
                    or line.startswith("checkpoint saved:")
                    or line.startswith("--- session")
                ):
                    tail.append(line)
            if tail:
                shutdown["tail"] = tail
        self.emit_event(shutdown)
        self.log("SHUTDOWN " + json.dumps(shutdown, ensure_ascii=False))
        if self.fail_reason or not (mind_ok and rm_win_ok and rm_wsl_ok):
            why = self.fail_reason or "isolation check failed at end"
            self.log("FAILED " + why)
            try:
                sys.stderr.write("vid_driver FAILED: " + why + "\n")
                sys.stderr.flush()
            except BrokenPipeError:
                pass
            rc = 1
        else:
            self.log("DONE")
            rc = 0
        for fh in (self.pty_f, self.jsonl_f, self.dlog):
            try:
                if fh:
                    fh.close()
            except Exception:
                pass
        if self.master is not None:
            try:
                os.close(self.master)
            except OSError:
                pass
        return rc


def parse_args(argv: list[str]) -> tuple[bool, str, int]:
    smoke = "--smoke" in argv
    idle = "1" if smoke else IDLE_DEFAULT
    # Smoke: inject after thought 2, then one more unbidden so the reply can land.
    target = 4 if smoke else TARGET_DEFAULT
    args = [a for a in argv if a not in ("--smoke",)]
    i = 0
    while i < len(args):
        if args[i] == "--idle" and i + 1 < len(args):
            idle = args[i + 1]
            i += 2
            continue
        if args[i] == "--thoughts" and i + 1 < len(args):
            target = int(args[i + 1])
            i += 2
            continue
        i += 1
    return smoke, idle, target


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    smoke, idle, target = parse_args(sys.argv[1:])
    cap = Capture(smoke, idle, target)
    rc = 1
    try:
        cap.start()
        cap.loop()
    except Exception as e:  # noqa: BLE001
        cap.fail_reason = cap.fail_reason or f"driver exception: {e}"
        cap.log(f"EXC {e!r}")
        cap.kill_child()
    finally:
        rc = cap.finish()
    return rc


if __name__ == "__main__":
    sys.exit(main())
