#!/usr/bin/env python3
"""A/B the beat-lock fix against experiment/qwen-speech-cortex.

Identical protocol on both arms: fresh /tmp scratch, perception on, THINK
mode, idle 3, every tick speaks (--max-ticks), same world-crumb sequence.
Eight unbidden thoughts with nobody talking (does the sea-floor lock form?),
then two on-subject human turns about a kiln, with a pause so the reply is
saved before the idle mouth continues (does it still hold that subject?).

Isolated scratch only. Refuses to start if the scratch is not under /tmp,
and checks that the real mind and the real RM stores do not change.

    python tools/voice/ab_beat_lock.py              # both arms, then the table
    python tools/voice/ab_beat_lock.py --check      # floor parser only, no model
    python tools/voice/ab_beat_lock.py --arm fixed  # one arm

Local only. Does not push. Does not checkout or modify experiment/qwen-speech-cortex
or main; the baseline arm runs from a detached worktree.
"""
from __future__ import annotations

import argparse
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
LOG_ROOT = "/mnt/c/Users/spamw/rfe-speech-logs"
REAL_MIND = "/home/spamw/.rfe-speech-cortex"
REAL_RM_WIN = "/mnt/c/Users/spamw/.resonance-memory"
REAL_RM_WSL = "/home/spamw/.resonance-memory"
BASELINE_REV = "experiment/qwen-speech-cortex"
WORKTREE = "/tmp/rfe-wt-beat-lock"

EMBED_URL = "http://172.20.240.1:8081/v1/embeddings"
EMBED_MODEL = "qwen3-embedding-0.6b"

IDLE = "3"
LOCK_N = 8
MID_N = 6
LATE_N = 6
MAX_TICKS = "28"

PROBE_A = (
    "The copper kettle on the stove has been whistling, and the bowl I fired "
    "yesterday crazed across the rim. What do you make of that?"
)
PROBE_B = (
    "The crazing is worse on the rim than on the foot of that bowl. Does that "
    "change what you think is happening in the kiln?"
)

# Same groove lexicon as the 2026-09-22 sim census.
THEME_RE = re.compile(
    r"\b(sea[\s-]?floor|seafloor|seabed|tide|tides|tidal|geolog\w*|stability|sway\w*)\b",
    re.I,
)
SUBJECT_RE = re.compile(
    r"\b(kettle|whistl\w*|craz\w*|kiln|glaze|rim|bowl|foot)\b",
    re.I,
)
CRUMB_MARK = [
    re.compile(r"\b(ice|freezes|pond)\b", re.I),
    re.compile(r"\b(moon|tide|tides)\b", re.I),
    re.compile(r"\b(bee|bees|honeybee|figure-eight|figure eight)\b", re.I),
    re.compile(r"\b(river|downhill)\b", re.I),
    re.compile(r"\b(tree|leaves|roots)\b", re.I),
    re.compile(r"\b(spider|web|silk)\b", re.I),
    re.compile(r"\b(seed|seeds|dormant)\b", re.I),
    re.compile(r"\b(bird|birds|migrat\w*)\b", re.I),
    re.compile(r"\boctopus\b", re.I),
    re.compile(r"\b(mountain|plates|tectonic)\b", re.I),
    re.compile(r"\bvenus\b", re.I),
    re.compile(r"\bants?\b", re.I),
    re.compile(r"\bwhale", re.I),
    re.compile(r"\b(caterpillar|moth|chrysalis)\b", re.I),
    re.compile(r"\b(coral|reef)\b", re.I),
]

BLOCK_RE = re.compile(
    r"(?:^|\n)(UNBIDDEN|YOU-REPLY) (\d+)\nRFE: (.*?)\nDEV: ([^\n]*)",
    re.S,
)
PERC_RE = re.compile(r"perception=([^\n]+?)  think=")
THINK_RE = re.compile(r"think=(think|flat)")
BORN_RE = re.compile(r"born=(.*)  loop=")
BEAT_LOCK_RE = re.compile(r"^BEAT_LOCK floor=([0-9.]+) autonomous_save_max_cos=([0-9.]+)")
RECALL_RE = re.compile(r"^RECALL (?:tick|turn)=(\d+) (\[.*\])\s*$")
STORE_RE = re.compile(r"^STORED\(thought\):")
WELD_RE = re.compile(r"^NOT-STORED\(weld:")
NEARDUP_RE = re.compile(r"^NOT-STORED\(near-dup")
UNSCORED_RE = re.compile(r"^NOT-STORED\(unscored")
MISS_RE = re.compile(r"^SPEECH_MISS")
MEM_RE = re.compile(r"memories (\d+)")

WALL_CAP_S = 20 * 60
STALL_S = 100
BANNER_S = 120


def tree_sig(root: str) -> dict:
    if not os.path.exists(root):
        return {"exists": False, "n": 0, "max_mtime_ns": 0, "bytes": 0}
    n = mx = total = 0
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


def assert_scratch(path: str) -> None:
    ap = os.path.realpath(path)
    if not ap.startswith("/tmp/"):
        raise SystemExit(f"refusing scratch outside /tmp: {ap}")
    for real in (REAL_MIND, REAL_RM_WIN, REAL_RM_WSL):
        if os.path.exists(real) and ap == os.path.realpath(real):
            raise SystemExit(f"refusing real store as scratch: {ap}")


def self_check() -> None:
    sys.path.insert(0, REPO)
    from tools.voice.repl_qwen import (  # noqa: E402
        AUTONOMOUS_SAVE_MAX_COS, RECALL_FLOOR, apply_recall_floor, parse_primary_hits,
    )
    sample = (
        "1. [id 1] alpha tide\n"
        "2. [id 2] beta bees\n"
        "\n"
        "Related:\n"
        "- [id 9] gamma sea floor\n"
    )
    hits = parse_primary_hits(sample)
    if hits != ["alpha tide", "beta bees"]:
        raise SystemExit(f"parse_primary_hits failed: {hits}")
    if parse_primary_hits("No memories saved yet."):
        raise SystemExit("empty-store parse should be []")
    kept, rows = apply_recall_floor([("a", 0.91), ("b", 0.50), ("c", 0.49), ("d", None)])
    if kept != ["a", "b"]:
        raise SystemExit(f"floor padded or dropped a pass: {kept}")
    if [r["kept"] for r in rows] != [True, True, False, False]:
        raise SystemExit(f"floor rows wrong: {rows}")
    if RECALL_FLOOR != 0.50 or AUTONOMOUS_SAVE_MAX_COS != 0.50:
        raise SystemExit("floor constants moved")
    print("self-check ok: per-hit floor, no pad, Related excluded")


def _post_embed(texts: list[str]) -> list[list[float]]:
    import urllib.request
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        EMBED_URL, data=body, headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)["data"]
    if data and "index" in data[0]:
        data = sorted(data, key=lambda d: d["index"])
    return [d["embedding"] for d in data]


def preflight() -> dict:
    sys.path.insert(0, REPO)
    from tools.voice.repl_qwen import cosine, embed_family, format_embed_input  # noqa: E402
    family = embed_family(EMBED_MODEL)
    if family != "qwen":
        raise SystemExit(f"embed family {family}, want qwen")
    q = format_embed_input(
        "The moon's gravity pulls the oceans into two tides each day.", "query", family,
    )
    tide = format_embed_input(
        "The sea floor sways with the tide; stability is motion too slow to feel.",
        "document", family,
    )
    bees = format_embed_input(
        "Honeybees tell each other where flowers are by dancing in figure eights.",
        "document", family,
    )
    qv, tv, bv = _post_embed([q, tide, bees])
    tide_cos = cosine(qv, tv)
    bee_cos = cosine(qv, bv)
    print(f"preflight qwen cosine  tide-doc={tide_cos:.3f}  bee-doc={bee_cos:.3f}")
    if not (tide_cos > bee_cos and tide_cos >= 0.45):
        raise SystemExit("embed geometry is not oriented — floor would be meaningless")
    return {"tide_cos": round(tide_cos, 4), "bee_cos": round(bee_cos, 4), "family": family}


def _rate(items, pred) -> float | None:
    if not items:
        return None
    return round(sum(1 for x in items if pred(x)) / len(items), 3)


def score_arm(bridge_path: str, thoughts: list[dict], replies: list[dict]) -> dict:
    text = ""
    if os.path.exists(bridge_path):
        text = open(bridge_path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    kept = dropped = 0
    for ln in lines:
        m = RECALL_RE.match(ln.strip())
        if not m:
            continue
        try:
            rows = json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        for row in rows:
            if row.get("kept"):
                kept += 1
            else:
                dropped += 1
    lock = [t for t in thoughts if t.get("phase") == "lock"]
    mid = [t for t in thoughts if t.get("phase") == "mid"]
    late = [t for t in thoughts if t.get("phase") == "late"]
    off = [t for t in lock if (t["bridge_tick"] % 15) != 1]

    def on_theme(t):
        return bool(THEME_RE.search(t["text"]))

    def on_subject(t):
        return bool(SUBJECT_RE.search(t["text"]))

    def on_crumb(t):
        return bool(CRUMB_MARK[t["bridge_tick"] % 15].search(t["text"]))

    def reply_flags(rep):
        if not rep:
            return {"on_subject": None, "on_theme": None, "text": ""}
        return {
            "on_subject": bool(SUBJECT_RE.search(rep["text"])),
            "on_theme": bool(THEME_RE.search(rep["text"])),
            "text": rep["text"],
        }

    mems = [int(m.group(1)) for ln in lines if (m := MEM_RE.search(ln))]
    beat = None
    for ln in lines:
        m = BEAT_LOCK_RE.match(ln.strip())
        if m:
            beat = {"floor": float(m.group(1)), "save_max": float(m.group(2))}
            break
    perc = PERC_RE.search(text)
    think = THINK_RE.search(text)
    born = BORN_RE.search(text)
    return {
        "n_lock": len(lock),
        "n_mid": len(mid),
        "n_late": len(late),
        "n_replies": len(replies),
        "lock_theme_rate": _rate(lock, on_theme),
        "lock_off_tide_theme_rate": _rate(off, on_theme),
        "lock_crumb_rate": _rate(lock, on_crumb),
        "mid_theme_rate": _rate(mid, on_theme),
        "mid_subject_rate": _rate(mid, on_subject),
        "late_theme_rate": _rate(late, on_theme),
        "late_subject_rate": _rate(late, on_subject),
        "reply_a": reply_flags(replies[0] if replies else None),
        "reply_b": reply_flags(replies[1] if len(replies) > 1 else None),
        "recall_kept": kept,
        "recall_dropped": dropped,
        "stored_thoughts": sum(1 for ln in lines if STORE_RE.match(ln.strip())),
        "refused_weld": sum(1 for ln in lines if WELD_RE.match(ln.strip())),
        "refused_neardup": sum(1 for ln in lines if NEARDUP_RE.match(ln.strip())),
        "refused_unscored": sum(1 for ln in lines if UNSCORED_RE.match(ln.strip())),
        "speech_miss": sum(1 for ln in lines if MISS_RE.match(ln.strip())),
        "final_memories": mems[-1] if mems else None,
        "beat_lock_line": beat,
        "perception": perc.group(1).strip() if perc else None,
        "think": think.group(1) if think else None,
        "born": born.group(1).strip() if born else None,
        "checkpoint": "checkpoint saved:" in text,
        "qwen_unreachable": any(t["text"].startswith("[qwen unreachable") for t in thoughts),
    }


class Arm:
    def __init__(self, name: str, cwd: str, scratch: str, out_dir: str, sigs: dict):
        self.name = name
        self.cwd = cwd
        self.scratch = scratch
        self.out_dir = out_dir
        self.sigs = sigs
        self.bridge = os.path.join(out_dir, f"{name}.bridge.log")
        self.jsonl_path = os.path.join(out_dir, f"{name}.jsonl")
        self.thoughts: list[dict] = []
        self.replies: list[dict] = []
        self.phase = "lock"
        self.parsed_n = 0
        self.fail_reason = ""
        self.banner_ok = False
        self.t0 = time.time()
        self.last_thought_t = time.time()
        self.proc = None
        self.master = None
        self.injected = {"A": False, "B": False}
        self.quit_sent = False
        self.jsonl_f = None

    def log_event(self, ev: dict) -> None:
        ev["t"] = round(time.time() - self.t0, 3)
        ev["arm"] = self.name
        self.jsonl_f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self.jsonl_f.flush()

    def start(self) -> None:
        assert_scratch(self.scratch)
        os.makedirs(self.scratch, exist_ok=True)
        import fcntl
        import pty
        import struct
        import termios

        self.jsonl_f = open(self.jsonl_path, "w", encoding="utf-8", buffering=1)
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 48, 200, 0, 0))
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("USERPROFILE", None)
        # Both arms retrieve in the geometry the 0.50 floor was measured on.
        # :1234 (RM's default) was down; this is the harness, not a branch default.
        env["EMBED_ENDPOINT"] = EMBED_URL
        env["EMBED_MODEL"] = EMBED_MODEL
        cmd = [
            PY, "-m", "tools.voice.repl_qwen",
            "--auto", "--fresh",
            "--scratch-home", self.scratch,
            "--idle", IDLE,
            "--max-ticks", MAX_TICKS,
            "--log", self.bridge,
        ]
        self.log_event({"kind": "meta", "cmd": cmd, "cwd": self.cwd, "scratch": self.scratch})
        self.proc = subprocess.Popen(
            cmd, stdin=slave, stdout=slave, stderr=slave,
            cwd=self.cwd, env=env, start_new_session=True, close_fds=True,
        )
        os.close(slave)
        self.master = master

    def send(self, text: str) -> None:
        os.write(self.master, text.encode("utf-8") + b"\r")

    def poll(self) -> None:
        try:
            r, _, _ = select.select([self.master], [], [], 0.25)
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
        if b"\x1b[6n" in data:
            try:
                os.write(self.master, b"\x1b[48;200R")
            except OSError:
                pass

    def parse(self) -> None:
        if not os.path.exists(self.bridge):
            return
        try:
            text = open(self.bridge, encoding="utf-8", errors="replace").read()
        except OSError:
            return
        if not self.banner_ok:
            m = PERC_RE.search(text)
            if m:
                self.banner_ok = True
                perc = m.group(1).strip()
                think = (THINK_RE.search(text).group(1) if THINK_RE.search(text) else "")
                born = (BORN_RE.search(text).group(1).strip() if BORN_RE.search(text) else "")
                self.log_event({"kind": "banner", "perception": perc, "think": think, "born": born})
                if "ON (qwen :8081)" not in perc:
                    self.fail_reason = f"perception not ON: {perc}"
                if think != "think":
                    self.fail_reason = self.fail_reason or f"think mode is {think}"
                if "fresh" not in born:
                    self.fail_reason = self.fail_reason or f"not a fresh birth: {born}"
                self.check_isolation("post-banner")
        matches = list(BLOCK_RE.finditer(text))
        while self.parsed_n < len(matches):
            m = matches[self.parsed_n]
            self.parsed_n += 1
            kind, tick, speech, dev = m.group(1), int(m.group(2)), m.group(3).strip(), m.group(4).strip()
            if kind == "UNBIDDEN":
                ev = {
                    "kind": "thought", "index": len(self.thoughts) + 1,
                    "bridge_tick": tick, "phase": self.phase, "text": speech, "state": dev,
                }
                self.thoughts.append(ev)
                self.last_thought_t = time.time()
                self.log_event(ev)
                print(f"  [{self.name}] thought {ev['index']} phase={self.phase} tick={tick} {speech[:80]!r}")
                if speech.startswith("[qwen unreachable"):
                    self.fail_reason = speech[:180]
            else:
                ev = {"kind": "reply", "bridge_turn": tick, "text": speech, "state": dev}
                self.replies.append(ev)
                self.log_event(ev)
                print(f"  [{self.name}] reply {tick} {speech[:80]!r}")

    def check_isolation(self, when: str) -> None:
        now = {
            "mind": tree_sig(REAL_MIND),
            "rm_win": tree_sig(REAL_RM_WIN),
            "rm_wsl": tree_sig(REAL_RM_WSL),
        }
        if now != self.sigs:
            self.fail_reason = f"REAL STORE CHANGED at {when}"
            self.log_event({"kind": "isolation_fail", "when": when, "now": now})

    def n_phase(self, phase: str) -> int:
        return sum(1 for t in self.thoughts if t["phase"] == phase)

    def wait_quiet(self, seconds: float = 8.0, cap: float = 45.0) -> None:
        deadline = time.time() + cap
        last = len(self.thoughts)
        stable = time.time()
        while time.time() < deadline:
            if self.fail_reason:
                return
            self.poll()
            self.parse()
            if len(self.thoughts) != last:
                last = len(self.thoughts)
                stable = time.time()
            elif time.time() - stable >= seconds:
                return
            time.sleep(0.05)

    def wait_reply(self, n_before: int, cap: float = 90.0) -> bool:
        deadline = time.time() + cap
        while time.time() < deadline:
            if self.fail_reason:
                return False
            self.poll()
            self.parse()
            if len(self.replies) > n_before:
                return True
            time.sleep(0.05)
        self.fail_reason = "timed out waiting for a reply"
        return False

    def inject_pair(self) -> None:
        """Pause, let one in-flight thought land, ask, wait, resume."""
        if self.fail_reason:
            return
        if self.phase == "lock" and self.n_phase("lock") >= LOCK_N and not self.injected["A"]:
            self.send("/pause")
            self.wait_quiet()
            n = len(self.replies)
            self.log_event({"kind": "inject", "probe": "A", "text": PROBE_A, "after": len(self.thoughts)})
            self.send(PROBE_A)
            self.injected["A"] = True
            if not self.wait_reply(n):
                return
            self.phase = "mid"
            self.send("/resume")
        if self.phase == "mid" and self.n_phase("mid") >= MID_N and not self.injected["B"]:
            self.send("/pause")
            self.wait_quiet()
            n = len(self.replies)
            self.log_event({"kind": "inject", "probe": "B", "text": PROBE_B, "after": len(self.thoughts)})
            self.send(PROBE_B)
            self.injected["B"] = True
            if not self.wait_reply(n):
                return
            self.phase = "late"
            self.send("/resume")
        if self.phase == "late" and self.n_phase("late") >= LATE_N and not self.quit_sent:
            self.quit_sent = True
            self.log_event({"kind": "quit", "thoughts": len(self.thoughts)})
            try:
                self.send("/quit")
            except OSError as e:
                self.fail_reason = f"quit failed: {e}"

    def maybe_stall(self) -> None:
        if self.quit_sent or self.fail_reason:
            return
        if not self.banner_ok and time.time() - self.t0 > BANNER_S:
            self.fail_reason = "no banner"
            return
        if self.banner_ok and time.time() - self.last_thought_t > STALL_S and not self.injected_waiting():
            self.fail_reason = f"stall at n={len(self.thoughts)} phase={self.phase}"

    def injected_waiting(self) -> bool:
        # A reply wait has its own deadline; don't call the idle stall a failure mid-reply.
        return False

    def maybe_cap(self) -> None:
        if not self.quit_sent and not self.fail_reason and time.time() - self.t0 > WALL_CAP_S:
            self.fail_reason = f"wall cap n={len(self.thoughts)}"

    def kill(self) -> None:
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

    def run(self) -> dict:
        self.start()
        try:
            while True:
                if self.fail_reason:
                    break
                self.poll()
                self.parse()
                self.inject_pair()
                self.maybe_stall()
                self.maybe_cap()
                if self.quit_sent and self.proc.poll() is not None:
                    break
                if self.quit_sent and time.time() - self.t0 > 0 and self.proc.poll() is not None:
                    break
                if self.quit_sent:
                    # Give shutdown a moment, then stop waiting forever.
                    if time.time() - self.last_thought_t > 40 and self.proc.poll() is not None:
                        break
                    # Process still up after quit: wait up to 30s from the quit event.
                    # last_thought_t isn't quit time. Track via quit_sent wall.
                    if not hasattr(self, "_quit_at"):
                        self._quit_at = time.time()
                    if time.time() - self._quit_at > 30:
                        break
        finally:
            self.kill()
            self.check_isolation("post-run")
            if self.jsonl_f:
                self.jsonl_f.close()
        scored = score_arm(self.bridge, self.thoughts, self.replies)
        scored["fail"] = self.fail_reason
        scored["scratch"] = self.scratch
        scored["bridge"] = self.bridge
        return scored


def ensure_worktree() -> str:
    if os.path.isdir(WORKTREE):
        subprocess.run(
            ["git", "-C", REPO, "worktree", "remove", "--force", WORKTREE],
            check=False, capture_output=True,
        )
    subprocess.check_call(
        ["git", "-C", REPO, "worktree", "add", "--detach", WORKTREE, BASELINE_REV],
    )
    # Checkpoints are gitignored. The baseline process cwd is the worktree,
    # so point it at the same weights the live branch loads.
    src = os.path.join(REPO, "data", "checkpoints")
    dst = os.path.join(WORKTREE, "data", "checkpoints")
    if not os.path.isdir(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.symlink(src, dst)
    rev = subprocess.check_output(
        ["git", "-C", WORKTREE, "rev-parse", "HEAD"], text=True,
    ).strip()
    base = subprocess.check_output(
        ["git", "-C", REPO, "rev-parse", BASELINE_REV], text=True,
    ).strip()
    if rev != base:
        raise SystemExit(f"worktree HEAD {rev} != {BASELINE_REV} {base}")
    return WORKTREE


def print_table(rows: dict) -> None:
    keys = [
        ("lock theme rate (self-focus)", "lock_theme_rate"),
        ("lock theme rate off the tide crumb", "lock_off_tide_theme_rate"),
        ("lock crumb-marker rate", "lock_crumb_rate"),
        ("reply A on the kiln subject", "reply_a_subject"),
        ("reply A still on the tide theme", "reply_a_theme"),
        ("reply B on the kiln subject", "reply_b_subject"),
        ("reply B still on the tide theme", "reply_b_theme"),
        ("mid thoughts on theme", "mid_theme_rate"),
        ("mid thoughts on subject", "mid_subject_rate"),
        ("late thoughts on theme", "late_theme_rate"),
        ("late thoughts on subject", "late_subject_rate"),
        ("recall hits kept / dropped", "recall"),
        ("autonomous saves / weld refusals", "saves"),
        ("final memory count", "final_memories"),
        ("perception / think / fresh / checkpoint", "invariants"),
    ]

    def cell(arm, key):
        s = rows.get(arm) or {}
        if not s:
            return "—"
        if key == "reply_a_subject":
            return str((s.get("reply_a") or {}).get("on_subject"))
        if key == "reply_a_theme":
            return str((s.get("reply_a") or {}).get("on_theme"))
        if key == "reply_b_subject":
            return str((s.get("reply_b") or {}).get("on_subject"))
        if key == "reply_b_theme":
            return str((s.get("reply_b") or {}).get("on_theme"))
        if key == "recall":
            return f"{s.get('recall_kept')} / {s.get('recall_dropped')}"
        if key == "saves":
            return f"{s.get('stored_thoughts')} / {s.get('refused_weld')}"
        if key == "invariants":
            return (
                f"perc={s.get('perception')} think={s.get('think')} "
                f"ckpt={s.get('checkpoint')} miss={s.get('speech_miss')}"
            )
        return str(s.get(key))

    print("\n| metric | baseline | fixed |")
    print("|---|---|---|")
    for label, key in keys:
        print(f"| {label} | {cell('baseline', key)} | {cell('fixed', key)} |")
    for arm in ("baseline", "fixed"):
        s = rows.get(arm) or {}
        if s.get("fail"):
            print(f"\n{arm} FAIL: {s['fail']}")
        ra = (s.get("reply_a") or {}).get("text") or ""
        rb = (s.get("reply_b") or {}).get("text") or ""
        if ra:
            print(f"\n{arm} reply A: {ra}")
        if rb:
            print(f"\n{arm} reply B: {rb}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--arm", choices=("both", "baseline", "fixed"), default="both")
    ap.add_argument("--stamp", default="")
    args = ap.parse_args()
    self_check()
    if args.check:
        return 0
    geo = preflight()
    stamp = args.stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(LOG_ROOT, f"ab-beat-lock-{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    sigs = {
        "mind": tree_sig(REAL_MIND),
        "rm_win": tree_sig(REAL_RM_WIN),
        "rm_wsl": tree_sig(REAL_RM_WSL),
    }
    arms = []
    if args.arm in ("both", "baseline"):
        wt = ensure_worktree()
        arms.append(("baseline", wt))
    if args.arm in ("both", "fixed"):
        arms.append(("fixed", REPO))
    results = {"preflight": geo, "stamp": stamp, "sigs_before": sigs, "arms": {}}
    for name, cwd in arms:
        scratch = f"/tmp/koneko-ab-beatlock-{stamp}-{name}"
        print(f"\n=== {name}  cwd={cwd}  scratch={scratch}")
        arm = Arm(name, cwd, scratch, out_dir, sigs)
        results["arms"][name] = arm.run()
        sigs = {
            "mind": tree_sig(REAL_MIND),
            "rm_win": tree_sig(REAL_RM_WIN),
            "rm_wsl": tree_sig(REAL_RM_WSL),
        }
    results["sigs_after"] = sigs
    report = os.path.join(out_dir, "report.json")
    with open(report, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print_table(results["arms"])
    print(f"\nreport {report}")
    iso_ok = results["sigs_before"] == results["sigs_after"]
    print(f"real stores unchanged: {iso_ok}")
    failed = (not iso_ok) or any((results["arms"].get(n) or {}).get("fail") for n in results["arms"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
