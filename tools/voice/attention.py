"""Idle-beat attention for the speech bridge.

The mouth never sees a weight. Relevance is which block leads the prompt,
which string is the recall query, and whether the world crumb is stepped
into the field. Numbers here are gates on those choices, not blend
coefficients.

Silence is autonomous ticks since the last committed human line in THIS
process. The rings are not checkpointed and are not a second memory.
"""
from __future__ import annotations

import re

import numpy as np

# Silence gates, in autonomous wakes (not wall seconds, so --idle does not
# retune them). Under the live every-other-tick speak gate, 12 ticks is a
# handful of spoken thoughts — the window that failed to follow a person.
HOT_UNTIL = 12
WARM_UNTIL = 28
BOREDOM_LEAVE_HOT = 0.6
SPOKEN_BEFORE_BOREDOM_LEAVE = 2

# One near-paraphrase of the previous thought arms a single crumb-led beat.
STICKY_JACCARD = 0.45
STICKY_ARM = 1
# Cold thoughts on the current thread before a far crumb may relocate it.
THREAD_MIN_BEFORE_RELOCATE = 3
# Token overlap at which a recall hit is the line we already showed.
RING_DEDUPE_JACCARD = 0.85
PROMPT_HITS = 2

# Cosine gates, re-measured per embedder. The 0.50 pair is the Qwen-embedder
# beat-lock A/B (2026-09-22). Nomic v1.5 on :1234 is a tighter space:
# true pairs sat at 0.76–0.84 and cross-subject prose at 0.52–0.64, so 0.50
# would paste almost every hit. Far-crumb is the gap between those bands.
RECALL_FLOOR_QWEN = 0.50
RECALL_FLOOR_NOMIC = 0.70
SAVE_MAX_QWEN = 0.50
SAVE_MAX_NOMIC = 0.72
FAR_COS_QWEN = 0.35
FAR_COS_NOMIC = 0.68
AUTONOMOUS_SAVE_WINDOW = 128

QWEN_QUERY_INSTRUCT = (
    "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "
)
_PRIMARY_HIT_RE = re.compile(r"^\d+\.\s+\[id\s+\d+\]\s+(.*)$")
_TOKEN_RE = re.compile(r"[^0-9a-z ]+")


def embed_family(model, config_embedder=None):
    """Match resonance-memory embed-invoke.js: config embedder wins, else model id."""
    s = str(config_embedder or model or "").lower()
    if "jina" in s:
        return "jina"
    if "qwen" in s:
        return "qwen"
    return "nomic"


def recall_floor_for(family):
    if family == "qwen":
        return RECALL_FLOOR_QWEN
    return RECALL_FLOOR_NOMIC


def save_max_for(family):
    if family == "qwen":
        return SAVE_MAX_QWEN
    return SAVE_MAX_NOMIC


def far_cos_max(family):
    """A crumb below this cosine to the last thought is a different subject."""
    if family == "qwen":
        return FAR_COS_QWEN
    return FAR_COS_NOMIC


def format_embed_input(text, role, family):
    """Same role prefixes RM uses, so a floor cosine is RM's cosine."""
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


def tokens(text):
    return _TOKEN_RE.sub(" ", (text or "").lower()).split()


def jaccard(a, b):
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


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


def apply_recall_floor(scored, floor):
    """Keep every hit at or above the floor. Never pad misses back in.

    scored: sequence of (text, score). score None (scorer failed) is a miss.
    Returns (kept_texts, rows).
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


def drop_ring_dupes(hits, rings, threshold=RING_DEDUPE_JACCARD):
    """Drop a hit that restates a line already in the prompt rings.

    Containment covers the stored wrapper ("On my own I thought: …"), which
    shares too few extra tokens to clear a Jaccard of 0.85 against the speech.
    """
    bases = [str(t).strip() for t in rings if t and str(t).strip()]
    kept = []
    for hit in hits:
        h = str(hit).strip()
        drop = False
        for base in bases:
            if base in h or h in base or jaccard(h, base) >= threshold:
                drop = True
                break
        if not drop:
            kept.append(hit)
    return kept


def classify_regime(silence, boredom, spoken_since_human):
    """silence None = nobody has spoken in this process (cold, outward).

    Hot is the recent conversation. Warm is the conversation fading and the
    crumb allowed back as a subordinate line. Cold is alone, or quiet long
    enough that the world is the external again.
    """
    if silence is None or silence >= WARM_UNTIL:
        return "cold"
    if silence >= HOT_UNTIL:
        return "warm"
    try:
        bored = float(boredom) >= BOREDOM_LEAVE_HOT
    except (TypeError, ValueError):
        bored = False
    if bored and int(spoken_since_human) >= SPOKEN_BEFORE_BOREDOM_LEAVE:
        return "warm"
    return "hot"


def should_promote(regime, has_thought, sticky, thoughts_since_move, far_cos, family):
    """One cold beat where the crumb leads, to break a loop or leave a stuck theme.

    Lexical stickiness arms it immediately. A semantically far crumb arms it
    only after the thread has had THREAD_MIN_BEFORE_RELOCATE thoughts, so a
    new fact cannot reset the subject every tick. Embed failure (far_cos
    None) does not promote — fail toward the thread, not toward a tour.
    """
    if regime != "cold" or not has_thought:
        return False
    if int(sticky) >= STICKY_ARM:
        return True
    if int(thoughts_since_move) < THREAD_MIN_BEFORE_RELOCATE:
        return False
    if far_cos is None:
        return False
    return float(far_cos) < far_cos_max(family)


def recall_query(regime, promoted, thoughts, exchange, crumb):
    """One query. A blended vector would be a third meaning nobody said."""
    if regime in ("hot", "warm"):
        for kind, text in reversed(list(exchange)):
            if kind == "they" and str(text).strip():
                return str(text)
    if promoted or not list(thoughts):
        return crumb
    return str(list(thoughts)[-1])


def step_world(regime):
    """Hot does not repaint the field with the crumb. The person's line was stepped once."""
    return regime != "hot"


def _mem_block(memories):
    mems = [m for m in (memories or []) if m][:PROMPT_HITS]
    if not mems:
        return "(nothing specific in mind yet)"
    return "\n".join(f"- {m}" for m in mems)


def _thought_block(thoughts):
    last = [t for t in list(thoughts)[-2:] if t]
    if not last:
        return ""
    lines = "\n".join(f"- {t}" for t in last)
    return f"What you were just thinking:\n{lines}\n\n"


def _exchange_lines(items):
    lines = []
    for kind, text in items:
        if kind == "they":
            lines.append(f"- They said: {text}")
        else:
            lines.append(f"- You replied: {text}")
    return "\n".join(lines)


def _hot_exchange(exchange):
    """Up to the last three exchanges (a they-line plus its reply)."""
    items = list(exchange)
    they_at = [i for i, (kind, _) in enumerate(items) if kind == "they"]
    if not they_at:
        return items[-6:]
    start = they_at[-3] if len(they_at) >= 3 else they_at[0]
    return items[start:]


def _warm_exchange(exchange):
    items = list(exchange)
    for i in range(len(items) - 1, -1, -1):
        if items[i][0] == "they":
            return items[i:]
    return items[-2:]


def render_idle_prompt(*, regime, promoted, thoughts, exchange, crumb, memories, mood, drive):
    """Assemble the idle user turn. No biography and no authored feeling.

    Birth (cold, no thought yet) is the historical crumb-led prompt, so a
    blank mind still has an external on beat one. Every later cold beat
    leads with the thread. Hot omits the crumb. Promoted cold leads with
    the crumb for exactly one beat.
    """
    mem_block = _mem_block(memories)
    mood_line = f"Your state: {mood}"
    if regime == "cold" and not list(thoughts):
        return (
            f"Something true about the world, right now: {crumb}\n"
            f"What you remember:\n{mem_block}\n{mood_line}\n\n{drive}"
        )
    if regime == "cold" and promoted:
        return (
            f"{_thought_block(thoughts)}"
            "The world is offering a different fact. Start from it, and leave "
            "the previous image unless it truly bears on this fact:\n"
            f"{crumb}\n\n"
            f"What you remember:\n{mem_block}\n{mood_line}\n\n{drive}"
        )
    if regime == "cold":
        return (
            f"{_thought_block(thoughts)}"
            "Something true about the world, not necessarily your subject: "
            f"{crumb}\n"
            "Continue from your own thread. Let that fact in only when it "
            "changes what you were thinking. Do not restart on it, and do not "
            "repeat yourself.\n\n"
            f"What you remember:\n{mem_block}\n{mood_line}\n\n{drive}"
        )
    if regime == "warm":
        ex = _warm_exchange(exchange)
        ex_block = ""
        if ex:
            ex_block = (
                "Recent exchange, oldest first:\n"
                f"{_exchange_lines(ex)}\n\n"
            )
        return (
            f"{_thought_block(thoughts)}"
            f"{ex_block}"
            "Think onward from your own thread. What they raised still bears "
            "if it still bears; do not answer them again.\n\n"
            "Something true about the world — use it only if it bears on the "
            f"above, otherwise leave it: {crumb}\n\n"
            f"What you remember from before:\n{mem_block}\n{mood_line}\n\n{drive}"
        )
    # hot
    ex = _hot_exchange(exchange)
    ex_block = ""
    if ex:
        ex_block = (
            "A person has been speaking with you. Recent exchange, newest last:\n"
            f"{_exchange_lines(ex)}\n\n"
            "Think onward from your own thread, but let what they raised move it. "
            "Do not answer them again. Do not return to an image that does not "
            "bear on what they raised.\n\n"
        )
    return (
        f"{_thought_block(thoughts)}"
        f"{ex_block}"
        f"What you remember from before:\n{mem_block}\n{mood_line}\n\n{drive}"
    )


def parse_say_at(items):
    """Harness only: 'TICK=text' commits that line before autonomous tick TICK."""
    out = {}
    for item in items or []:
        raw = str(item)
        if "=" not in raw:
            raise ValueError(f"--say-at expects TICK=text, got {raw!r}")
        n, text = raw.split("=", 1)
        tick = int(n.strip())
        if tick < 1:
            raise ValueError(f"--say-at tick must be >= 1, got {tick}")
        if not text.strip():
            raise ValueError("--say-at text is empty")
        out[tick] = text
    return out


def note_sticky(previous, speech, sticky):
    """Return the sticky count after this spoken thought."""
    if not previous:
        return 0
    if jaccard(previous, speech) >= STICKY_JACCARD:
        return int(sticky) + 1
    return 0
