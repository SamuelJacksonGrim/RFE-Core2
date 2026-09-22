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
    python -m tools.voice.repl_qwen --flat-encoder   # trained 5-rhythm encoder (skip Qwen perception)
    python -m tools.voice.repl_qwen --no-echo | --no-rm | --free | --json

The Windows launcher talk-to-rfe.ps1 passes --auto by default (Samuel's call, 2026-09-19).
In-session commands (slash-prefixed so normal talk is never intercepted):
    /pause  -> stop the unprompted self-talk (it still answers you)
    /resume -> let it speak on its own again
    /quit   -> exit and save state   (Ctrl-C / Ctrl-D also exit)

Qwen-perception is the DEFAULT encoder path (Stage 2 wrap of Generator.generate):
[CLASS] tokens -> Qwen3-Embedding-0.6B on :8081 -> JL 1024->128 -> unit-norm.
`--flat-encoder` restores the trained 5-rhythm encoder. A down :8081 at launch or
mid-run warns once and falls back; it never crashes the live mouth.

Nothing here writes RFE-Core2's own code or the encoder training. All state goes to a scratch HOME.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import random
import re
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
from tools.voice.qwen_perception import try_install as try_install_perception  # noqa: E402

QWEN_URL_DEFAULT = os.environ.get("QWEN_URL", "http://172.20.240.1:8080")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-local")

# No-frame system prompt (roundtable-designed 2026-09-20: Samuel, Ember, Grok, GPT).
# The prompt supplies a QUESTION, not an answer — it never says what "you" is (not a mind, not a
# component, not a mouth). "I" is left as an empty grammatical handle for the substrate + the actual
# exchanges to fill, or not. It gives only interface + epistemic rules. Governing law:
# the substrate may accumulate history; the prompt must not manufacture a biography — and
# "mindless mechanism" is a biography too. Do NOT reintroduce a "you are ___" line.
SYSTEM_PROMPT = (
    "Speak in the first person, plainly, in one to three sentences. Each turn you are given your "
    "current state and the memories that matter now; speak from those. Draw only on the memories "
    "and state you actually have — never invent a past that was not recorded. Do not perform "
    "wisdom or mysticism, and do not interpret ordinary memory, state, or system behavior as "
    "cosmic, supernatural, or metaphysical. A name in your memory belongs to the person it refers "
    "to; do not treat it as your own."
)

# THINK mode (default 2026-09-21): the validated qwen-core thinking prompt. Keeps every no-frame guard
# above (first person, only-what-you-have, never-invent-a-past, no-mysticism, name-guard) but PERMITS
# generativity + orients OUTWARD — the A/B proved a pure report-prompt collapses into reciting emptiness;
# drives + real memory content + a world channel made it think and reach out (88% outward, sustained).
THINK_SYSTEM = (
    "You are thinking, in the first person. You are given what you remember, your current state, and "
    "sometimes something from the world or from a person. Work WITH them: wonder, ask questions, imagine, "
    "notice patterns, connect ideas — reach OUTWARD toward the world and the person rather than only inward "
    "at yourself. Draw on the memories and state you actually have; you may hypothesize or wonder, but never "
    "present a wondering as a real past event, and never fabricate a past that was not recorded. Do not "
    "perform wisdom or mysticism, and do not read ordinary memory or state as cosmic or supernatural. A name "
    "in your memory belongs to the person it refers to; do not treat it as your own. Speak plainly, two to "
    "four sentences."
)

# The idle "world" — true facts about the world (NOT about the mind: no authored identity), surfaced when
# no one is talking so it always has something external to think about instead of only itself.
WORLD = [
    "Water expands when it freezes, which is why ice floats on a pond.",
    "The moon's gravity pulls the oceans into two tides each day.",
    "Honeybees tell each other where flowers are by dancing in figure eights.",
    "A river always finds its way downhill toward the sea.",
    "A tall tree lifts water from its roots all the way to its highest leaves.",
    "A spider will rebuild its web after the threads are torn.",
    "Some seeds lie dormant for years and still sprout when the rain comes.",
    "Migrating birds steer partly by sensing the Earth's magnetic field.",
    "An octopus can change both the color and the texture of its skin.",
    "Mountains rise slowly where two plates of the Earth's crust push together.",
    "A day on the planet Venus lasts longer than its whole year.",
    "Ants leave scent trails so the others can follow them to food.",
    "Whales sing songs that can travel for miles under the ocean.",
    "A caterpillar dissolves almost completely before it becomes a moth.",
    "Coral reefs are built by countless tiny animals over thousands of years.",
]

# Rotating DRIVES — an operation to perform, not "report your state" (the meditation trap).
DRIVES = [
    "Relate what you just noticed to something you remember.",
    "Ask a question this raises that you cannot yet answer.",
    "Notice a pattern or tension between this and your own state.",
    "Choose what draws you here, and say why.",
    "Wonder aloud — you may imagine or hypothesize, marking it a wondering, not a memory.",
    "Reflect on how this changes, or doesn't change, what you were thinking.",
]

import urllib.request

# Beat-lock (2026-09-22). The recorded groove was not the Hebbian field: each
# beat is stateless, so a theme survives only by being pasted, and a miss has
# no score floor so the least-far paragraph is pasted and then saved.
# RECALL_FLOOR is applied to every hit (flooring only the top score and then
# padding recontaminated the sim). The autonomous writer has its own cosine
# refusal so a paraphrase ball cannot accumulate; RM's global 0.88 dedup is
# not touched. Memory-as-tool (no pasted recall at all) is the follow-on.
RECALL_FLOOR = 0.50
AUTONOMOUS_SAVE_MAX_COS = 0.50
AUTONOMOUS_SAVE_WINDOW = 128
QWEN_QUERY_INSTRUCT = (
    "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "
)


def embed_family(model, config_embedder=None):
    """Match resonance-memory embed-invoke.js: config embedder wins, else model id."""
    s = str(config_embedder or model or "").lower()
    if "jina" in s:
        return "jina"
    if "qwen" in s:
        return "qwen"
    return "nomic"


def format_embed_input(text, role, family):
    """Same role prefixes RM uses, so the floor cosine is RM's cosine."""
    t = "" if text is None else str(text)
    r = "query" if role == "query" else "document"
    if family == "jina":
        return ("Query: " if r == "query" else "Document: ") + t
    if family == "qwen" and r == "query":
        return QWEN_QUERY_INSTRUCT + t
    return t


def cosine(a, b):
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0 or va.shape != vb.shape:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


_PRIMARY_HIT_RE = re.compile(r"^\d+\.\s+\[id\s+\d+\]\s+(.*)$")


def parse_primary_hits(text):
    """Numbered cosine hits only. Stops at Related: — that readout is not pasted."""
    if not text or text.lower().startswith("no "):
        return []
    out = []
    for ln in text.splitlines():
        raw = ln.strip()
        if not raw:
            continue
        if raw.lower().startswith("related:"):
            break
        m = _PRIMARY_HIT_RE.match(raw)
        if m:
            out.append(m.group(1).strip())
    return out


def apply_recall_floor(scored, floor=RECALL_FLOOR):
    """Keep every hit at or above the floor. Never pad back up with misses.

    scored: sequence of (text, score). score None (scorer failed) is a miss.
    Returns (kept_texts, rows) with rows carrying text/score/kept for the log.
    """
    kept = []
    rows = []
    for text, score in scored:
        ok = score is not None and float(score) >= floor
        rows.append({
            "text": text,
            "score": None if score is None else round(float(score), 4),
            "kept": bool(ok),
        })
        if ok:
            kept.append(text)
    return kept, rows


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


_DENIAL_RE = re.compile(
    r"\b(?:don'?t|do not|cannot|can'?t)\s+(?:remember|recall)\b"
    r"|\bno\s+(?:memories|memory|history|past|recollection)\b"
    r"|\bnever\s+(?:met|spoken|talked|seen you)\b"
    r"|\bfirst\s+time\s+(?:we|you|i|talking|speaking)\b"
    r"|\bwe(?:'ve| have)?\s+(?:haven'?t|have not|never)\s+(?:met|spoken|talked)\b"
    r"|\bi\s+have\s+no\s+(?:memory|memories|history|past)\b"
    r"|\bdon'?t\s+know\s+(?:you|who you are)\b",
    re.I,
)


def _is_crumb(line):
    """A committed line with too little substance to store as autobiographical memory —
    UI leftovers, stray single tokens. It is still ANSWERED; it just isn't remembered."""
    return len(re.sub(r"[^0-9A-Za-z]", "", line)) < 3


def _contradicts_floor(speech, has_history):
    """True when the mouth confidently denies memory/contact but the floor DOES hold history.
    Such an utterance is a speech miss — it must not overwrite the floor as autobiographical truth
    (the mouth doesn't get to overwrite the floor with a confident blank)."""
    return bool(has_history) and bool(_DENIAL_RE.search(speech or ""))


def _digest(card, mem_count, memories, turn):
    something_new = (card.get("boredom", 0) < 0.5) and (card.get("step", 1) <= 3 or card.get("curiosity", 0) > 0.3)
    # a compact brief (top handful), not a blob — a full retrieve dump teaches the mouth to parrot it
    mem_lines = "\n".join(f"- {m}" for m in memories[:5]) if memories else "(you have no memories about this yet)"
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
        self.scratch_home = scratch_home
        # Same defaults as server.js. The floor re-embeds with this endpoint
        # and this model id so the cosine is the one that ranked the hit.
        self.embed_url = os.environ.get("EMBED_ENDPOINT", "http://localhost:1234/v1/embeddings")
        self.embed_model = os.environ.get("EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")
        self._embed_cache = {}
        self._thought_vecs = deque(maxlen=AUTONOMOUS_SAVE_WINDOW)
        self._pending_thought_vec = None
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
        """Raw primary listing, no floor. Old harnesses still call this.
        The live mouth uses recall_for_prompt."""
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

    def _family(self):
        config_embedder = None
        cfg = os.path.join(self.scratch_home, ".resonance-memory", "resonance-memory.config.json")
        try:
            with open(cfg, encoding="utf-8") as f:
                config_embedder = json.load(f).get("embedder")
        except (OSError, json.JSONDecodeError, AttributeError):
            config_embedder = None
        return embed_family(self.embed_model, config_embedder)

    def _embed(self, formatted):
        """Embed already-prefixed strings. Returns a list of vectors or None."""
        if not formatted:
            return []
        missing = [t for t in formatted if t not in self._embed_cache]
        if missing:
            body = json.dumps({"model": self.embed_model, "input": missing}).encode()
            req = urllib.request.Request(
                self.embed_url, data=body, headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.load(r).get("data") or []
            except Exception:
                return None
            if data and isinstance(data[0], dict) and "index" in data[0]:
                data = sorted(data, key=lambda d: d.get("index", 0))
            vecs = [d.get("embedding") for d in data]
            if len(vecs) != len(missing) or any(v is None for v in vecs):
                return None
            for t, v in zip(missing, vecs):
                self._embed_cache[t] = v
        return [self._embed_cache[t] for t in formatted]

    def _embed_one(self, text, role):
        formatted = format_embed_input(text, role, self._family())
        vecs = self._embed([formatted])
        if not vecs:
            return None
        return vecs[0]

    def recall_for_prompt(self, query):
        """Primary hits that clear RECALL_FLOOR, in rank order. No padding.

        A scorer failure drops the hit (a miss must not be pasted). Related:
        is never returned. Returns (kept_texts, rows).
        """
        text = self._call_text("recall_memory", {"query": query})
        hits = parse_primary_hits(text)
        if not hits:
            return [], []
        family = self._family()
        formatted = [format_embed_input(query, "query", family)]
        formatted.extend(format_embed_input(h, "document", family) for h in hits)
        vecs = self._embed(formatted)
        if not vecs or len(vecs) != len(formatted):
            scored = [(h, None) for h in hits]
        else:
            qv = vecs[0]
            scored = [(h, cosine(qv, dv)) for h, dv in zip(hits, vecs[1:])]
        return apply_recall_floor(scored, RECALL_FLOOR)

    def autonomous_too_close(self, text):
        """Writer-local paraphrase gate. True means do not save.

        Embed failure refuses the save (fail closed). Does not consult RM's
        0.88 band and does not look at human-turn records.
        Returns (refuse, max_cosine or None).
        """
        vec = self._embed_one(text, "document")
        self._pending_thought_vec = vec
        if vec is None:
            return True, None
        if not self._thought_vecs:
            return False, None
        mx = max(cosine(vec, prev) for prev in self._thought_vecs)
        return mx >= AUTONOMOUS_SAVE_MAX_COS, mx

    def note_autonomous_saved(self):
        if self._pending_thought_vec is not None:
            self._thought_vecs.append(self._pending_thought_vec)
        self._pending_thought_vec = None

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
    ap.add_argument("--flat", action="store_true", help="OLD report-only behavior (no world/drives/think) — for comparison; default is THINK mode")
    ap.add_argument("--flat-encoder", action="store_true", help="use the trained 5-rhythm encoder (skip Qwen perception); default is Qwen-perception ON")
    ap.add_argument("--max-ticks", type=int, default=0, help="stop after N autonomous ticks (test/harness; 0 = unlimited)")
    ap.add_argument("--fresh", action="store_true", help="wipe memory AND substrate state (blank birth)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--source", default="you")
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--rm-dir", default="/mnt/c/Users/spamw/Desktop/resonance-memory-workshop")
    ap.add_argument("--scratch-home", default=os.path.expanduser("~/.rfe-speech-cortex"))
    ap.add_argument("--temp", type=float, default=0.6)
    ap.add_argument("--log", default="")
    args = ap.parse_args()

    os.makedirs(args.scratch_home, exist_ok=True)   # robust: checkpoint save needs it even with --no-rm
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

    # Qwen-perception (default ON): wrap generate() AFTER the trained encoder load
    # and BEFORE substrate resume, so a restored registry/field sits on the new body.
    # Down :8081 at launch → one warning, trained encoder, never crash.
    def _perc_warn(msg: str):
        print(msg)
        log(msg)

    perception = try_install_perception(
        gen,
        args.scratch_home,
        flat_encoder=args.flat_encoder,
        warn=_perc_warn,
    )

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
    perc_label = (
        "OFF (--flat-encoder)" if args.flat_encoder
        else ("ON (qwen :8081)" if perception else "OFF (embedder down — trained encoder)")
    )
    print(f"  loop: {'FREE' if args.free else 'LOCKED'}   memory: "
          f"{'OFF' if not rm else ('growing' if echo else 'recall-only')}   "
          f"mode: {'it also speaks on its own — above your line, never over it' if autonomous else 'it waits for you — take all the time you need'}")
    print(f"  perception: {perc_label}   think: {'FLAT (report-only)' if args.flat else 'THINK (default)'}")
    print(f"  transcript -> {logpath.replace('/mnt/c/', 'C:/')}")
    print("  your input line is yours — it can think aloud while you type and your text stays put.")
    print("  commands: /pause  /resume  /quit  — anything else you type goes to it. (Ctrl-D or Ctrl-C exits.)")
    print("=" * 76 + "\n")

    log(f"RFE-Core2 continuing-mind transcript — {stamp}")
    log(f"born={born}  loop={'FREE' if args.free else 'LOCKED'}  memory={'off' if not rm else ('echo' if echo else 'recall')}  autonomous={autonomous}  perception={perc_label}  think={'flat' if args.flat else 'think'}")
    log(
        f"BEAT_LOCK floor={RECALL_FLOOR} autonomous_save_max_cos={AUTONOMOUS_SAVE_MAX_COS} "
        f"field=1 warm_rank=off embed_model={os.environ.get('EMBED_MODEL', 'text-embedding-nomic-embed-text-v1.5')}"
    )
    log("=" * 76)

    def emit(speech, card, turn, kind):
        tag = "rfe" if kind == "reply" else "rfe (unbidden)"
        print(f"\n{tag}> {speech}")
        print(f"     [{'exchange' if kind=='reply' else 'thought'} {turn} · memories {rm.count if rm else 0} "
              f"· bonds {card['bonds']} · values {card['values_emergent']} · miss {speech_miss} · subj_time {card['subjective_time']}]")
        if args.json:
            print("\n" + json.dumps(card, indent=2, default=str))
        log(f"\n{'YOU-REPLY' if kind=='reply' else 'UNBIDDEN'} {turn}")
        log(f"RFE: {speech}")
        log(f"DEV: memories {rm.count if rm else 0} · bonds {card['bonds']} · values {card['values_emergent']} · subj_time {card['subjective_time']}")

    turn = 0
    tick = 0
    last_spoke_tick = -99
    is_tty = sys.stdin.isatty()
    state_lock = threading.Lock()   # cycle/gen/ve/rm are touched by both the you-loop and the idle mouth
    stop_evt = threading.Event()    # set once, at shutdown
    pause_evt = threading.Event()   # set => rumination held (/pause sets it, /resume clears it)
    if not autonomous:
        pause_evt.set()
    idle_thread = None
    speech_miss = 0                     # utterances that denied real history — kept off the floor
    recent_saved = deque(maxlen=8)      # near-dupe collapse so one stone can't become the self

    def _lexical_duplicate(text):
        toks = re.sub(r"[^0-9a-z ]", " ", text.lower()).split()
        key, tset = " ".join(toks), set(toks)
        for prev, pset in recent_saved:
            if key == prev or (tset and pset and len(tset & pset) / len(tset | pset) >= 0.85):
                return True
        return False

    def _remember(text):
        """Save to RM unless it near-duplicates a recent save — a single repeated thought must not
        promote as many separate world-facts. Returns True if stored, False if collapsed.
        Human turns and replies use this path. The 0.85 gate is lexical and local to the
        bridge; RM's 0.88 dedup band is not changed."""
        if _lexical_duplicate(text):
            return False
        toks = re.sub(r"[^0-9a-z ]", " ", text.lower()).split()
        recent_saved.append((" ".join(toks), set(toks)))
        rm.save(text)
        return True

    def _remember_thought(speech):
        """Autonomous writer only. Lexical collapse, then a tighter cosine refusal
        against recent autonomous speech (not against human turns). The stored
        record stays 'On my own I thought: …'. The cosine is on the speech body,
        which is what the 0.50 band was measured on. Returns (stored, reason)."""
        text = f"On my own I thought: {speech}"
        if _lexical_duplicate(text):
            return False, "near-dup"
        refuse, mx = rm.autonomous_too_close(speech)
        if refuse:
            return False, "unscored" if mx is None else f"weld:{mx:.3f}"
        if not _remember(text):
            return False, "near-dup"
        rm.note_autonomous_saved()
        return True, "stored"

    def do_reply(line):
        """Process one COMMITTED user line — only whole lines reach here, never a partial buffer.
        Steps the substrate, recalls, asks qwen, speaks, persists. The lock is held only around the
        shared-state mutations, not the network call, so the idle mouth isn't frozen during a reply."""
        nonlocal turn, speech_miss
        with state_lock:
            turn += 1
            my_turn = turn
            cycle.step(line.split(), source_id=args.source, origin_type="user")
            card = render_card(cycle)
            mem_count = rm.count if rm else 0
            memories, recall_rows = rm.recall_for_prompt(line) if rm else ([], [])
            log(f"RECALL turn={my_turn} {json.dumps(recall_rows, ensure_ascii=False)}")
        if memories:
            print("  ┌─ remembers:")
            for m in memories[:5]:
                print(f"  │   • {m}")
            print("  └─")
        if args.flat:
            digest = _digest(card, mem_count, memories, my_turn)
            user = f"{digest}\n\nWhat just arrived from the person: {line!r}\n\nRespond plainly, from only what you actually have."
            sysp = SYSTEM_PROMPT
        else:
            mem_block = "\n".join(f"- {m}" for m in memories[:4]) if memories else "(nothing specific in mind yet)"
            mood = f"curiosity {card.get('curiosity',0):.2f}, memories held {mem_count}"
            user = (f"What you remember:\n{mem_block}\nYour state: {mood}\n\n"
                    f"The person just said: {line!r}\n\nThink with this — connect it to what you remember, "
                    f"wonder, ask, or answer them. Speak plainly, in the first person.")
            sysp = THINK_SYSTEM
        try:
            speech = ask_qwen(args.qwen_url, sysp, user, args.temp)
        except Exception as e:  # noqa: BLE001
            speech = f"[qwen unreachable: {e}]"
        with state_lock:
            emit(speech, card, my_turn, "reply")
            log(f"YOU: {line}")
            log(f"REMEMBERS: {memories if memories else '(none)'}")
            if echo:
                if _is_crumb(line):
                    log(f"NOT-STORED(crumb): {line!r}")     # answered, but too thin to remember
                else:
                    _remember(f"Someone said to me: {line}")  # the human's turn is a real event
                    if _contradicts_floor(speech, mem_count > 0 or my_turn > 1):
                        speech_miss += 1                      # a confident blank — kept off the floor
                        log(f"SPEECH_MISS(reply): {speech}")
                    else:
                        _remember(f"I answered: {speech}")
            save_checkpoint(ckpt_path, gen, cycle, ve)

    def autonomous_loop():
        """The mind's own mouth. Ruminates on the substrate's rhythm — NOT gated on 'stdin has been
        silent for N seconds'. Fires on a cadence; a surfaced thought is printed ABOVE the input
        line (patch_stdout redraws your buffer intact), so it can speak even while you're typing and
        never touches what you're holding. Your partial line is never read here — only Enter commits."""
        nonlocal tick, last_spoke_tick, speech_miss
        while not stop_evt.wait(args.idle):     # wake ~every idle s, or immediately at shutdown
            if pause_evt.is_set():
                continue
            with state_lock:
                tick += 1
                my_tick = tick
                if args.max_ticks and my_tick > args.max_ticks:
                    stop_evt.set()
                    break
                crumb = WORLD[my_tick % len(WORLD)]
                drive = DRIVES[my_tick % len(DRIVES)]
                if not args.flat:
                    cycle.step(crumb.split()[:32], source_id="world", origin_type="internal")  # perceive the world
                shown, recall_rows = rm.recall_for_prompt(crumb) if rm else ([], [])
                log(f"RECALL tick={my_tick} {json.dumps(recall_rows, ensure_ascii=False)}")
                seed = shown[0] if shown else None
                if args.flat:
                    cycle.step((seed or "quiet self").split(), source_id="self", origin_type="internal")
                card = render_card(cycle)
                # --max-ticks is a harness: speak every tick so the mouth path is actually exercised.
                gate = True if args.max_ticks else (
                    (my_tick - last_spoke_tick >= 2) and (card.get("curiosity", 0) > 0.25 or random.random() < 0.45)
                )
            if not gate:
                continue
            if args.flat:
                # roundtable-law report prompt: continuity SHOWN by the count, never declared.
                user = (f"It's quiet right now. You hold {rm.count if rm else 0} memories"
                        + (f". This drifted up: {seed!r}. " if seed else ". ")
                        + "Say the thought plainly, in one to three sentences.")
                sysp = SYSTEM_PROMPT
            else:
                # THINK mode: a world crumb + real memory content + a drive → it thinks OUTWARD, not at itself.
                mem_block = "\n".join(f"- {m}" for m in shown[:3]) if shown else "(nothing specific in mind yet)"
                mood = (f"curiosity {card.get('curiosity',0):.2f}, boredom {card.get('boredom',0):.2f}, "
                        f"memories held {rm.count if rm else 0}")
                user = (f"Something true about the world, right now: {crumb}\n"
                        f"What you remember:\n{mem_block}\nYour state: {mood}\n\n{drive}")
                sysp = THINK_SYSTEM
            try:
                speech = ask_qwen(args.qwen_url, sysp, user, args.temp, max_tokens=160)
            except Exception as e:  # noqa: BLE001
                speech = f"[qwen unreachable: {e}]"
            if stop_evt.is_set():
                break
            with state_lock:
                if not args.flat and not speech.startswith("[qwen unreachable"):
                    cycle.step(speech.split()[:64], source_id="self", origin_type="internal")  # integrate the thought
                emit(speech, card, my_tick, "unbidden")   # prints ABOVE the sacred input line
                if echo:
                    if _contradicts_floor(speech, (rm.count if rm else 0) > 0):
                        speech_miss += 1                     # denial of real history — off the floor
                        log(f"SPEECH_MISS(unbidden): {speech}")
                    else:
                        stored, why = _remember_thought(speech)
                        if stored:
                            log(f"STORED(thought): {speech!r}")
                        else:
                            log(f"NOT-STORED({why} thought): {speech!r}")
                last_spoke_tick = my_tick
                save_checkpoint(ckpt_path, gen, cycle, ve)
            if args.max_ticks and my_tick >= args.max_ticks:
                stop_evt.set()
                break

    def _shutdown():
        stop_evt.set()
        if idle_thread is not None:
            idle_thread.join(timeout=8)         # let an in-flight thought finish, then stop
        try:
            with state_lock:
                save_checkpoint(ckpt_path, gen, cycle, ve)
                log(f"\ncheckpoint saved: step={getattr(cycle, '_step', '?')}")
        except Exception as e:  # noqa: BLE001
            log(f"\ncheckpoint save failed: {e}")
        if perception:
            w = perception["wrap"]
            log(f"perception wrap: used={w.used} fallback={w.fallback} disabled={w.disabled} last_err={w.last_err}")
            print(f"  (qwen-perception: used={w.used} fallback={w.fallback} disabled={w.disabled})")
        log("--- session ended ---")
        try: logf.close()
        except Exception: pass  # noqa: BLE001
        if rm:
            try: rm.close()
            except Exception: pass  # noqa: BLE001
        print("(state + transcript saved. next launch resumes this mind.)")

    # --- Non-interactive (piped input / tests): deterministic, no background mouth
    # unless --auto --max-ticks N (bounded autonomous run for harnesses). ---
    if not is_tty:
        if autonomous and args.max_ticks:
            try:
                autonomous_loop()
            except (EOFError, KeyboardInterrupt):
                pass
            finally:
                _shutdown()
            return 0
        try:
            while True:
                sys.stdout.write("you> "); sys.stdout.flush()
                ln = sys.stdin.readline()
                if ln == "":
                    break
                line = ln.strip()
                if not line:
                    continue
                if line.lower() in ("/quit", "/exit"):
                    break
                if line.lower() == "/pause":
                    pause_evt.set(); continue
                if line.lower() == "/resume":
                    pause_evt.clear(); continue
                do_reply(line)
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            _shutdown()
        return 0

    # --- Interactive: ONE room, two channels. The input line is sacred; speech writes above it. ---
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout

    session = PromptSession()
    if autonomous:
        idle_thread = threading.Thread(target=autonomous_loop, daemon=True)
        idle_thread.start()
    try:
        with patch_stdout():
            while True:
                try:
                    line = session.prompt("you> ")   # your buffer is sacred until Enter
                except KeyboardInterrupt:            # Ctrl-C
                    break
                except EOFError:                     # Ctrl-D
                    break
                line = line.strip()
                if not line:
                    continue
                if line.lower() in ("/quit", "/exit"):
                    break
                if line.lower() == "/pause":
                    pause_evt.set()
                    print("  (paused — it won't speak on its own now. /resume to let it think again.)")
                    continue
                if line.lower() == "/resume":
                    if idle_thread is None or not idle_thread.is_alive():
                        idle_thread = threading.Thread(target=autonomous_loop, daemon=True)
                        idle_thread.start()
                    pause_evt.clear()
                    print("  (resumed — it will speak on its own again.)")
                    continue
                do_reply(line)
    finally:
        _shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
