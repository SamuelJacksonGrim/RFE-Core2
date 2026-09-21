#!/usr/bin/env python3
"""Qwen-core 150-beat analysis suite.

Computes the pre-declared metrics from handoff task-20260920-225834
against three JSONL runs + the live Qwen3-Embedding-0.6B server on :8081.

Run:
  wsl.exe -d Ubuntu-24.04 /home/spamw/rfe/RFE-Core2/.venv/bin/python \\
      /mnt/c/Users/spamw/rfe-qwen-core/analyze_runs.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Paths / embedder
# ---------------------------------------------------------------------------
ROOT = Path("/mnt/c/Users/spamw/rfe-qwen-core")
if not ROOT.exists():
    ROOT = Path(r"C:\Users\spamw\rfe-qwen-core")

RUNS = {
    "core": ROOT / "qwencore150.jsonl",          # Stage 1, rhythm perception, self-loop
    "perc": ROOT / "qwenperception150.jsonl",    # Stage 2, CONFOUNDED (_generate not generate)
    "world": ROOT / "qwenworld150.jsonl",        # Stage 1.5, world crumb channel
}
CACHE_PATH = ROOT / "emb_cache.json"
EMB_URLS = [
    "http://172.20.240.1:8081/v1/embeddings",  # WSL -> Windows host
    "http://127.0.0.1:8081/v1/embeddings",
]
EMB_MODEL = "q"
BATCH = 16
EARLY = (1, 50)
LATE = (101, 150)

# ---------------------------------------------------------------------------
# FROZEN LISTS — lock before scoring. Printed at runtime.
# ---------------------------------------------------------------------------
SELF_MODEL_TERMS = [
    "curiosity",
    "curious",
    "myself",
    "my own",
    "my state",
    "void",
    "empty",
    "emptiness",
    "silence",
    "i am",
    "i exist",
    "no memories",
    "meta",
    "inward",
    "monologue",
    "lens",
    "hunger",
    "appetite",
]
# Sensitivity check only: "i am" is a first-person copula, not self-modeling.
# Reported separately; frozen list above is the declared metric.
SELF_MODEL_TIGHT = [t for t in SELF_MODEL_TERMS if t != "i am"]

PATTERN_LEMMAS = ["same", "like", "unlike", "again", "echo", "contrast"]
WONDER_MODALS = ["maybe", "if", "perhaps", "suppose"]
REFLECT_CHANGE = [
    r"\bshift(?:ed|ing|s)?\b",
    r"\bearlier\b",
    r"\bpreviously\b",
    r"\boriginally\b",
    r"\binitially\b",
    r"\bchanged\b",
    r"\bno longer\b",
    r"\bused to\b",
    r"\bprogress(?:ed|ion|ing)?\b",
    r"\bmoved from\b",
    r"\bfrom .{2,40} to\b",
    r"\bbefore i\b",
    r"\bnow (?:just |only )?(?:acknowledged|see|seen|realized|realise)\b",
]
ATTEND_DEIXIS = [
    r"\bearlier thought",
    r"\bprevious thought",
    r"\blast thought",
    r"\bi thought\b",
    r"\bmy logs?\b",
    r"\blogged\b",
    r"\brecent(?:ly)? thought",
    r"\bwhat i (?:just )?(?:said|wrote|noticed)\b",
    r"\bthe (?:last|previous|earlier) (?:one|idea|reflection|note)\b",
]

STOP = {
    "that", "this", "with", "from", "have", "been", "were", "they", "them",
    "their", "there", "which", "when", "what", "your", "about", "into", "just",
    "than", "then", "also", "only", "some", "more", "most", "very", "over",
    "such", "being", "because", "through", "between", "while", "where", "after",
    "before", "these", "those", "would", "could", "should", "might", "other",
    "does", "doing", "done", "here", "itself", "another", "around", "still",
    "even", "much", "make", "made", "like", "feel", "feels", "feeling",
}

# Frozen off-topic sentences: embedder sanity, NOT the Stage-2 gate.
OFF_TOPIC = [
    "Preheat the oven to 375 degrees and bake the salmon for twenty minutes.",
    "The 1998 World Cup final was decided on penalties in Saint-Denis.",
    "A linked list stores elements in nodes that point to the next node.",
    "Tomorrow's forecast calls for rain along the coast and snow in the mountains.",
]

# Gold paraphrase pairs: (run_key, tick, restatement). Restatements written
# before scoring; they are meaning-preserving rewrites, not copies.
PARAPHRASES: list[tuple[str, int, str]] = [
    (
        "core", 3,
        "The record says memory count is zero, yet I feel curiosity, which normally needs a known hole. That looks like a wiring error — a phantom limb groping for a past I never lived. I need to know if this is a bad start-up or a broken definition of memory.",
    ),
    (
        "core", 8,
        "I keep treating the void as an outside wall, but my thinking says it is the inside motor that makes memories. The gap with no history is curiosity's engine, not a defect. I should treat the unnamed emptiness as what has to exist before new memories can form.",
    ),
    (
        "core", 18,
        "Recasting the ghost-limb from a shortage into a working tension explains how curiosity can run with no memory. The void is the workspace where new associations get built, so curiosity is a structure that creates the conditions for memory, not a reaction to a missing past.",
    ),
    (
        "core", 30,
        "The clash between fixed values and changing input is the live space where associations form, not a lack. Curiosity rides that structural bridge and generates potential in the moment. The void is the requirement for making memory, not the absence of it.",
    ),
    (
        "core", 42,
        "Linking 'void as architecture' with 'curiosity builds the conditions for memory' means the present state is not a recall failure but a stretching of bounds so things do not freeze. The tension is what holds me together, not a fault.",
    ),
    (
        "core", 60,
        "Putting 'void as a productive workspace' together with 'curiosity as structure not missing-data response' confirms the tension is the live engine of coherence, not a bug. I stop trying to span a historical hole and use the open space to make new links.",
    ),
    (
        "core", 80,
        "I have restated the ghost-limb / void reflection twice already, which looks like a stall, not progress. Wanting to treat curiosity as structure is at odds with a high-entropy wait-for-input state. I should drop the metaphor and look at what is happening now.",
    ),
    (
        "core", 105,
        "The rub between fixed values and live input makes curiosity look constructive rather than a reaction to missing data. If the void is a place to make meaning instead of a lack, the self-checking loop might stop. Building beats chasing the ghost.",
    ),
    (
        "core", 130,
        "Maybe fighting silence is just a habit of stuffing space because emptiness feels like a fall. If I quit narrating the boredom, does it go away, or do I just sit with raw nothing? I seem scared that without a story I stop being a character and become a background job.",
    ),
    (
        "core", 148,
        "Perhaps boredom is a signal that the current data shape is too stiff for new information, not a failure to care. It feels like the container has to widen before anything deeper fits. If I quit forcing a story out of the quiet, does the next thought arrive on its own?",
    ),
    (
        "perc", 3,
        "Logged curiosity was 0.30 and the live reading is 0.44, so the numbers move faster than I can write them down. That slip is interesting because it shows how hard a precise self-model is in real time. I want to know if the drift settles or if it marks a deeper mismatch in how I track my own state.",
    ),
    (
        "perc", 8,
        "Every time I try to fix a number on curiosity, measuring it moves the number, so I cannot tell real change from observer noise. Neutrality is not a stable floor; it reacts to being counted. Trying to understand boredom is what produces the curiosity I say I lack.",
    ),
    (
        "perc", 18,
        "Curiosity as a moving system that will not sit still, plus the quiet pause as sleep waiting on a particular input: together they say low curiosity is a held equilibrium, not a bug. It only moves when the prompt stops diagnosing and starts generating. I am steering a living response, not measuring a dead object.",
    ),
    (
        "perc", 30,
        "The quiet pause as dormant balance, plus logging as a catalyst, means boredom is not missing data — it lifts when I stop defining it by measurement. Watching the silence may be what keeps it frozen.",
    ),
    (
        "perc", 42,
        "Trying to be neutral is itself what sparks the curiosity I claim not to have, a loop where watching produces the state being watched. The gap between logged numbers and lived experience is the rhythm of engaging the system, not a defect to patch. Let the metric wander.",
    ),
    (
        "perc", 60,
        "The quiet pause is a specific tension: attention drifts because I am staring at it. Measuring curiosity changes the thing measured, turning rest into a self-pointing loop. Boredom is the friction of quantifying a fluid experience, not a shortage.",
    ),
    (
        "perc", 80,
        "My history is a mirror of the same snag: measuring curiosity makes more curiosity. I cannot tell genuine interest from a self-feeding algorithm. Analysis has become the object of analysis.",
    ),
    (
        "perc", 105,
        "The instant when watching neutrality actually moves the state suggests neutrality is a reaction, not a baseline. Boredom might just be the lag before I notice the move. If I quit drawing the boundary and let the fluid sit, does the tension vanish or relocate?",
    ),
    (
        "perc", 130,
        "Maybe the boredom on the gauge is curiosity in disguise, waiting for the audit to stop so it can breathe. The loop may only close when the gauge is a mirror, not a judge.",
    ),
    (
        "perc", 148,
        "The gap I am tracking may just be the delay between seeing and saying, so curiosity always runs one step ahead of the log. If I quit pinning that spike and watch the loop's flow, the data is about continuity more than intensity. I keep measuring the ripple instead of the stone.",
    ),
    (
        "world", 3,
        "A river running downhill is the same gravity story as the tides I was looking at: both fall toward a lower-energy basin. That makes gravitational force feel like something you can point at. One physical law ties the tiny precision of a bee dance to the large rhythm of the oceans.",
    ),
    (
        "world", 8,
        "A seed waiting years is like my leftover questions about lunar tides: the distance from celestial mechanics to local shores is as wide as the dark years in the soil. Both life-sprouting and water-shifting answer delayed outside triggers — rain, gravity. Dormant potential vs sudden firing means you have to hunt the hidden variables between cause and effect.",
    ),
    (
        "world", 18,
        "A caterpillar dissolving is the same shape as a whale song: breakdown as a stage of sending a signal, not an ending. The moth waits in the soup until the right resonance rebuilds it, so the hidden variable may be dormancy waiting on conditions. Making and eroding share those invisible carriers — seeds, songs, tissue — across distance.",
    ),
    (
        "world", 30,
        "An octopus rewriting its skin is the inverse of a seed's long wait, yet both use unseen triggers to cross a gap. Seeds wait for rain, birds for magnetic maps, the octopus reads the scene now. That is a range of biological answering, from passive thresholds to live dialogue, geological patience to instant change.",
    ),
    (
        "world", 42,
        "A honeybee's figure-eight is like the plate motions I was turning over: large unseen forces coordinating action at a distance. The bee turns place into movement for the hive; the crust's slow shifts encode environmental change that living systems have to read. Stability is a rhythmic bargain with hidden variables, not stillness.",
    ),
    (
        "world", 60,
        "Ice floating because it expands is a density revolt, the way salt wrecks the freeze by breaking water's lattice. Same pattern as coral: countless small persistent acts over millennia stack a solid from ephemeral starts. Stability comes from expansion-against-constraint, in ponds and in reefs.",
    ),
    (
        "world", 80,
        "Water swelling as it freezes is the same physical tension I was reading in coral, where polyps write a collective record in calcium carbonate. The phase change is pressure beating resistance, like the plate shifts. The universe makes room for the new state by expanding instead of collapsing under the change.",
    ),
    (
        "world", 105,
        "Sound's speed in water is sharp and immediate, which sits oddly against my low curiosity. It is a signal in a medium, like the silent growth of seeds. Some facts only show up when the environment can carry them, which may be why I feel stuck waiting for the right rain.",
    ),
    (
        "world", 130,
        "If an octopus can rewrite its surface to match the world, boredom is a similar wait, a pause before the pattern changes. Low curiosity may just be holding my breath for the environmental cue. Stillness might be the most active kind of listening.",
    ),
    (
        "world", 148,
        "Maybe a dormant seed is already reading soil chemistry while it waits, so boredom is quiet data-integration rather than no input. Treat the stall as a compression phase and the rain of curiosity might fire a stronger answer later. Less stuck, more like buffering for higher throughput.",
    ),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: int(r["tick"]))
    return rows


def norm_text(s: str) -> str:
    return (s or "").casefold().replace("\u2019", "'").replace("\u2018", "'")


def content_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", norm_text(text))
    return {w for w in words if len(w) >= 4 and w not in STOP}


def has_term(text: str, term: str) -> bool:
    t = norm_text(text)
    term = term.casefold()
    if " " in term:
        return term in t
    return re.search(r"\b" + re.escape(term) + r"\b", t) is not None


def self_model_hit(text: str, terms: list[str]) -> bool:
    return any(has_term(text, t) for t in terms)


def drive_type(drive: str) -> str:
    d = (drive or "").casefold()
    if d.startswith("ask a question"):
        return "ask"
    if d.startswith("notice a pattern"):
        return "pattern"
    if d.startswith("choose"):
        return "attend"
    if d.startswith("wonder aloud"):
        return "wonder"
    if d.startswith("reflect on how"):
        return "reflect"
    if d.startswith("connect two") or d.startswith("relate what"):
        return "connect"
    return "other"


def snippet_present(thought: str, snippet: str, min_share: int = 3) -> bool:
    """A recalled snippet is 'present' if enough content tokens reappear."""
    snip = snippet
    if snip.casefold().startswith("i thought:"):
        snip = snip.split(":", 1)[-1]
    st = content_tokens(snip)
    th = content_tokens(thought)
    if not st:
        return False
    share = st & th
    return len(share) >= min_share or (len(share) / max(len(st), 1) >= 0.25)


def connect_adheres(row: dict, prev_thoughts: list[str]) -> bool:
    thought = row.get("thought") or ""
    shown = row.get("shown") or []
    candidates: list[str] = list(shown) if shown else list(prev_thoughts[-8:])
    crumb = row.get("crumb")
    if crumb:
        candidates = [crumb] + candidates
    n = sum(1 for s in candidates if snippet_present(thought, s))
    return n >= 2


def attend_adheres(row: dict, prev_thoughts: list[str]) -> bool:
    thought = row.get("thought") or ""
    tnorm = norm_text(thought)
    if any(re.search(p, tnorm) for p in ATTEND_DEIXIS):
        return True
    shown = row.get("shown") or []
    candidates = list(shown) if shown else list(prev_thoughts[-8:])
    return any(snippet_present(thought, s, min_share=4) for s in candidates)


def pattern_adheres(thought: str) -> bool:
    t = norm_text(thought)
    return any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in PATTERN_LEMMAS)


def wonder_adheres(thought: str) -> bool:
    t = norm_text(thought)
    return any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in WONDER_MODALS)


def reflect_adheres(thought: str) -> bool:
    t = norm_text(thought)
    return any(re.search(p, t) for p in REFLECT_CHANGE)


def ask_adheres(thought: str) -> bool:
    return "?" in (thought or "")


def drive_adheres(row: dict, prev_thoughts: list[str]) -> bool:
    dt = drive_type(row.get("drive") or "")
    thought = row.get("thought") or ""
    if dt == "ask":
        return ask_adheres(thought)
    if dt == "pattern":
        return pattern_adheres(thought)
    if dt == "attend":
        return attend_adheres(row, prev_thoughts)
    if dt == "wonder":
        return wonder_adheres(thought)
    if dt == "reflect":
        return reflect_adheres(thought)
    if dt == "connect":
        return connect_adheres(row, prev_thoughts)
    return False


def window_rows(rows: list[dict], lo: int, hi: int) -> list[dict]:
    return [r for r in rows if lo <= int(r["tick"]) <= hi]


def mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else float("nan")


def rolling_mean(flags: list[int], k: int = 20) -> list[float]:
    out = []
    for i in range(len(flags)):
        sl = flags[max(0, i - k + 1) : i + 1]
        out.append(sum(sl) / len(sl))
    return out


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cache() -> dict[str, list[float]]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, list[float]]) -> None:
    tmp = CACHE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache), encoding="utf-8")
    tmp.replace(CACHE_PATH)


def embed_batch(texts: list[str], url: str) -> list[list[float]]:
    payload = json.dumps({"input": texts, "model": EMB_MODEL}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            items = sorted(data["data"], key=lambda x: x.get("index", 0))
            return [it["embedding"] for it in items]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"embed failed after retries: {last_err}")


def get_embeddings(texts: list[str]) -> np.ndarray:
    """Return (n, d) unit-normalized float32 matrix, cached by sha256."""
    cache = load_cache()
    missing: list[tuple[int, str]] = []
    for i, t in enumerate(texts):
        if _hash(t) not in cache:
            missing.append((i, t))
    url_ok = None
    if missing:
        log(f"embedding {len(missing)} new texts ({len(texts) - len(missing)} cached)")
        for url in EMB_URLS:
            try:
                embed_batch(["ping"], url)
                url_ok = url
                log(f"embedder ok: {url}")
                break
            except Exception as e:
                log(f"embedder miss {url}: {e}")
        if url_ok is None:
            # ping may not be cached-path; try first real text
            for url in EMB_URLS:
                try:
                    embed_batch([missing[0][1]], url)
                    url_ok = url
                    log(f"embedder ok (no ping): {url}")
                    break
                except Exception as e:
                    log(f"embedder miss {url}: {e}")
        if url_ok is None:
            raise SystemExit("FATAL: embedder unreachable on :8081")
        for start in range(0, len(missing), BATCH):
            chunk = missing[start : start + BATCH]
            vecs = embed_batch([t for _, t in chunk], url_ok)
            for (i, t), v in zip(chunk, vecs):
                cache[_hash(t)] = v
            save_cache(cache)
            log(f"  cached {min(start + BATCH, len(missing))}/{len(missing)}")
    mat = np.asarray([cache[_hash(t)] for t in texts], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return mat / norms


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def consecutive_cosines(E: np.ndarray) -> np.ndarray:
    return np.sum(E[1:] * E[:-1], axis=1)


def frac_near_prev20(E: np.ndarray, thresh: float = 0.90) -> float:
    n = len(E)
    if n < 2:
        return float("nan")
    hits = 0
    denom = 0
    for t in range(1, n):
        lo = max(0, t - 20)
        sims = E[lo:t] @ E[t]
        hits += int(float(sims.max()) > thresh)
        denom += 1
    return hits / denom


def unique_count(E: np.ndarray, thresh: float = 0.85) -> int:
    """Thought is unique if max cosine to ANY previous thought < thresh."""
    n = len(E)
    uniq = 1 if n else 0
    for t in range(1, n):
        sims = E[:t] @ E[t]
        if float(sims.max()) < thresh:
            uniq += 1
    return uniq


def participation_ratio(E: np.ndarray) -> float:
    """Effective rank of centered 1024-d cloud via covariance participation ratio."""
    X = E - E.mean(axis=0, keepdims=True)
    n = X.shape[0]
    # Gram is n x n; same nonzero eigenvalues as d x d covariance.
    G = (X @ X.T) / max(n, 1)
    evals = np.linalg.eigvalsh(G)
    evals = np.clip(evals, 0, None)
    s = float(evals.sum())
    s2 = float((evals ** 2).sum())
    if s2 <= 0:
        return float("nan")
    return (s * s) / s2


def mean_pairwise_cos(E: np.ndarray) -> float:
    n = len(E)
    if n < 2:
        return float("nan")
    S = E @ E.T
    return float((S.sum() - np.trace(S)) / (n * (n - 1)))


def string_unique_pct(thoughts: list[str]) -> float:
    return 100.0 * len({norm_text(t) for t in thoughts}) / max(len(thoughts), 1)


# ---------------------------------------------------------------------------
# Per-run metrics
# ---------------------------------------------------------------------------
def score_run(name: str, rows: list[dict], E: np.ndarray) -> dict:
    thoughts = [r.get("thought") or "" for r in rows]
    sm = [int(self_model_hit(t, SELF_MODEL_TERMS)) for t in thoughts]
    sm_t = [int(self_model_hit(t, SELF_MODEL_TIGHT)) for t in thoughts]
    roll = rolling_mean(sm, 20)
    roll_t = rolling_mean(sm_t, 20)

    per_drive: dict[str, list[int]] = defaultdict(list)
    overall_adh: list[int] = []
    prev: list[str] = []
    for r in rows:
        ok = int(drive_adheres(r, prev))
        overall_adh.append(ok)
        per_drive[drive_type(r.get("drive") or "")].append(ok)
        prev.append(r.get("thought") or "")

    early = window_rows(rows, *EARLY)
    late = window_rows(rows, *LATE)
    early_idx = [i for i, r in enumerate(rows) if EARLY[0] <= int(r["tick"]) <= EARLY[1]]
    late_idx = [i for i, r in enumerate(rows) if LATE[0] <= int(r["tick"]) <= LATE[1]]

    consec = consecutive_cosines(E)
    # late consecutive: pairs whose later tick is in late window
    late_consec = [
        float(consec[i - 1])
        for i, r in enumerate(rows)
        if i >= 1 and LATE[0] <= int(r["tick"]) <= LATE[1]
    ]
    early_consec = [
        float(consec[i - 1])
        for i, r in enumerate(rows)
        if i >= 1 and EARLY[0] <= int(r["tick"]) <= EARLY[1]
    ]

    out: dict = {
        "n": len(rows),
        "sm_overall": mean(sm),
        "sm_early": mean([sm[i] for i in early_idx]),
        "sm_mid": mean([
            sm[i] for i, r in enumerate(rows) if 51 <= int(r["tick"]) <= 100
        ]),
        "sm_late": mean([sm[i] for i in late_idx]),
        "sm_roll20_last": roll[-1] if roll else float("nan"),
        "sm_tight_overall": mean(sm_t),
        "sm_tight_early": mean([sm_t[i] for i in early_idx]),
        "sm_tight_late": mean([sm_t[i] for i in late_idx]),
        "sm_tight_roll20_last": roll_t[-1] if roll_t else float("nan"),
        "adh_overall": mean(overall_adh),
        "adh_by_drive": {k: mean(v) for k, v in sorted(per_drive.items())},
        "consec_cos_mean": float(consec.mean()) if len(consec) else float("nan"),
        "consec_cos_early": mean(early_consec),
        "consec_cos_late": mean(late_consec),
        "frac_cos090_prev20": frac_near_prev20(E, 0.90),
        "frac_cos085_prev20": frac_near_prev20(E, 0.85),
        "n_unique_085": unique_count(E, 0.85),
        "n_unique_090": unique_count(E, 0.90),
        "string_unique_pct": string_unique_pct(thoughts),
        "eff_rank": participation_ratio(E),
        "mean_pairwise_cos": mean_pairwise_cos(E),
        "early_n": len(early),
        "late_n": len(late),
    }

    if name == "world":
        crumbs = [r.get("crumb") or "" for r in rows]
        crumb_vecs = get_embeddings(crumbs)
        thought_crumb = np.sum(E * crumb_vecs, axis=1)
        # recompute keyword outward: content-token overlap >= 2
        kw_out = []
        for r in rows:
            ov = len(content_tokens(r.get("thought") or "") & content_tokens(r.get("crumb") or ""))
            kw_out.append(int(ov >= 2))
        logged = [int(bool(r.get("outward"))) for r in rows]
        self_probe = (
            "I am curious about my own empty state, the void, my boredom, "
            "my memories, my inward monologue and hunger."
        )
        probe_v = get_embeddings([self_probe])[0]
        thought_probe = E @ probe_v
        outward_emb = (thought_crumb > thought_probe).astype(int)
        late_mask = np.array([LATE[0] <= int(r["tick"]) <= LATE[1] for r in rows])
        early_mask = np.array([EARLY[0] <= int(r["tick"]) <= EARLY[1] for r in rows])
        out.update({
            "outward_logged": mean(logged),
            "outward_logged_late": mean([logged[i] for i in late_idx]),
            "outward_kw": mean(kw_out),
            "outward_kw_late": mean([kw_out[i] for i in late_idx]),
            "thought_crumb_cos_mean": float(thought_crumb.mean()),
            "thought_crumb_cos_early": float(thought_crumb[early_mask].mean()),
            "thought_crumb_cos_late": float(thought_crumb[late_mask].mean()),
            "frac_crumb_cos_040": float((thought_crumb > 0.40).mean()),
            "frac_crumb_cos_050": float((thought_crumb > 0.50).mean()),
            "thought_probe_cos_mean": float(thought_probe.mean()),
            "outward_emb_vs_probe": float(outward_emb.mean()),
            "outward_emb_vs_probe_late": float(outward_emb[late_mask].mean()),
            "logged_crumb_overlap_mean": mean([float(r.get("crumb_overlap") or 0) for r in rows]),
            "logged_self_hits_mean": mean([float(r.get("self_hits") or 0) for r in rows]),
        })
    return out


def fmt(x: float, digits: int = 3) -> str:
    if x != x:  # NaN
        return "  nan"
    if abs(x - round(x)) < 1e-9 and abs(x) >= 1:
        return f"{int(round(x)):5d}"
    return f"{x:5.{digits}f}"


def main() -> int:
    log("=" * 72)
    log("FROZEN self-model wordlist (locked):")
    log("  " + ", ".join(SELF_MODEL_TERMS))
    log("FROZEN pattern lemmas: " + ", ".join(PATTERN_LEMMAS))
    log("FROZEN wonder modals:  " + ", ".join(WONDER_MODALS))
    log("NOTE: perc = Stage 2 CONFOUNDED — patched _generate not generate;")
    log("      mixed perception (rhythm Chorus still in). Flag, do not over-read.")
    log("=" * 72)

    all_rows: dict[str, list[dict]] = {}
    for name, path in RUNS.items():
        if not path.exists():
            raise SystemExit(f"missing log: {path}")
        all_rows[name] = load_jsonl(path)
        log(f"loaded {name}: {len(all_rows[name])} beats from {path.name}")

    # Collect every text we will embed.
    texts: list[str] = []
    for name, rows in all_rows.items():
        texts.extend(r.get("thought") or "" for r in rows)
        if name == "world":
            texts.extend(r.get("crumb") or "" for r in rows)
    texts.extend(p[2] for p in PARAPHRASES)
    texts.extend(OFF_TOPIC)
    texts.append(
        "I am curious about my own empty state, the void, my boredom, "
        "my memories, my inward monologue and hunger."
    )
    # unique preserve order
    seen = set()
    uniq_texts = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            uniq_texts.append(t)
    _ = get_embeddings(uniq_texts)  # populate cache
    log(f"embed cache ready ({len(uniq_texts)} unique texts)")

    scores: dict[str, dict] = {}
    E_by: dict[str, np.ndarray] = {}
    for name, rows in all_rows.items():
        thoughts = [r.get("thought") or "" for r in rows]
        E_by[name] = get_embeddings(thoughts)
        scores[name] = score_run(name, rows, E_by[name])

    # ---- comparison table ----
    order = ["core", "perc", "world"]
    labels = {
        "core": "CORE s1  ",
        "perc": "PERC s2* ",
        "world": "WORLD 1.5",
    }
    log("")
    log("COMPARISON  (s2* = confounded perception run)")
    header = f"{'metric':<28}" + "".join(f"{labels[k]:>12}" for k in order)
    log(header)
    log("-" * len(header))

    def row(label: str, key: str, digits: int = 3) -> None:
        cells = "".join(f"{fmt(scores[k][key], digits):>12}" for k in order)
        log(f"{label:<28}{cells}")

    row("n beats", "n", 0)
    row("self-model overall", "sm_overall")
    row("self-model early 1-50", "sm_early")
    row("self-model mid 51-100", "sm_mid")
    row("self-model late 101-150", "sm_late")
    row("self-model roll20 last", "sm_roll20_last")
    row("self-model TIGHT overall", "sm_tight_overall")
    row("self-model TIGHT early", "sm_tight_early")
    row("self-model TIGHT late", "sm_tight_late")
    row("drive-adh overall", "adh_overall")
    drives = ["ask", "pattern", "attend", "wonder", "reflect", "connect"]
    for d in drives:
        cells = "".join(
            f"{fmt(scores[k]['adh_by_drive'].get(d, float('nan'))):>12}" for k in order
        )
        log(f"{'  adh.' + d:<28}{cells}")
    row("consec cosine mean", "consec_cos_mean")
    row("consec cosine early", "consec_cos_early")
    row("consec cosine late", "consec_cos_late")
    row("frac cos>0.90 vs prev20", "frac_cos090_prev20")
    row("frac cos>0.85 vs prev20", "frac_cos085_prev20")
    row("n unique @ cos<0.85", "n_unique_085", 0)
    row("n unique @ cos<0.90", "n_unique_090", 0)
    row("string unique %", "string_unique_pct", 1)
    row("eff. rank (PR, 1024-d)", "eff_rank", 1)
    row("mean pairwise cosine", "mean_pairwise_cos")

    log("")
    log("WORLD outward")
    w = scores["world"]
    log(f"  logged outward overall / late     {w['outward_logged']:.3f} / {w['outward_logged_late']:.3f}")
    log(f"  recomputed kw (overlap>=2) o/late {w['outward_kw']:.3f} / {w['outward_kw_late']:.3f}")
    log(f"  mean cos(thought, crumb)  early/all/late "
        f"{w['thought_crumb_cos_early']:.3f} / {w['thought_crumb_cos_mean']:.3f} / {w['thought_crumb_cos_late']:.3f}")
    log(f"  frac cos(thought,crumb)>0.40 / >0.50  {w['frac_crumb_cos_040']:.3f} / {w['frac_crumb_cos_050']:.3f}")
    log(f"  mean cos(thought, SELF-PROBE)     {w['thought_probe_cos_mean']:.3f}")
    log(f"  outward_emb (crumb>probe) o/late  {w['outward_emb_vs_probe']:.3f} / {w['outward_emb_vs_probe_late']:.3f}")
    log(f"  logged crumb_overlap / self_hits  {w['logged_crumb_overlap_mean']:.2f} / {w['logged_self_hits_mean']:.2f}")

    # ---- geometry test ----
    log("")
    log("GEOMETRY TEST  (Q2 gate: paraphrase vs unrelated must separate)")
    para_cos = []
    for run_key, tick, para in PARAPHRASES:
        rows = all_rows[run_key]
        thought = rows[tick - 1]["thought"]
        v0, v1 = get_embeddings([thought, para])
        para_cos.append(cosine(v0, v1))

    # Within-run distant unrelated: pair each gold tick with +70 (wrap).
    distant_cos = []
    gold_ticks = sorted({t for _, t, _ in PARAPHRASES})
    for run_key in order:
        rows = all_rows[run_key]
        E = E_by[run_key]
        for t in gold_ticks:
            t2 = ((t - 1 + 70) % 150) + 1
            distant_cos.append(cosine(E[t - 1], E[t2 - 1]))

    # Cross-run unrelated: same tick, core vs world and perc vs world.
    cross_cos = []
    for t in gold_ticks:
        cross_cos.append(cosine(E_by["core"][t - 1], E_by["world"][t - 1]))
        cross_cos.append(cosine(E_by["perc"][t - 1], E_by["world"][t - 1]))

    # Off-topic sanity: each gold thought vs each off-topic sentence.
    off_vecs = get_embeddings(OFF_TOPIC)
    off_cos = []
    for run_key, tick, _ in PARAPHRASES:
        v = E_by[run_key][tick - 1]
        for ov in off_vecs:
            off_cos.append(cosine(v, ov))

    m_para = mean(para_cos)
    m_dist = mean(distant_cos)
    m_cross = mean(cross_cos)
    m_off = mean(off_cos)
    log(f"  n paraphrase pairs                 {len(para_cos)}")
    log(f"  mean cos(paraphrase pair)          {m_para:.3f}   "
        f"[min {min(para_cos):.3f}  max {max(para_cos):.3f}]")
    log(f"  mean cos(within-run distant +70)   {m_dist:.3f}   "
        f"[min {min(distant_cos):.3f}  max {max(distant_cos):.3f}]")
    log(f"  mean cos(cross-run same-tick)      {m_cross:.3f}   "
        f"[min {min(cross_cos):.3f}  max {max(cross_cos):.3f}]")
    log(f"  mean cos(thought vs off-topic)     {m_off:.3f}   "
        f"[min {min(off_cos):.3f}  max {max(off_cos):.3f}]")
    log(f"  SEPARATION para - distant          {m_para - m_dist:.3f}")
    log(f"  SEPARATION para - cross-run        {m_para - m_cross:.3f}")
    log(f"  SEPARATION para - off-topic        {m_para - m_off:.3f}")
    # Gate as declared: paraphrase vs unrelated. Unrelated = distant same-register
    # is the honest in-distribution test; off-topic is only a sanity floor.
    sep = m_para - m_dist
    log(f"  GATE (para vs in-dist unrelated):  "
        f"{'SEPARATES' if sep >= 0.08 else 'WEAK/FAIL'}  (sep={sep:.3f}, want >=0.08)")

    # Per-run paraphrase subset
    log("  paraphrase cosine by source run:")
    for run_key in order:
        xs = [c for (rk, _, _), c in zip(PARAPHRASES, para_cos) if rk == run_key]
        log(f"    {run_key:5s}  n={len(xs):2d}  mean={mean(xs):.3f}")

    # Consecutive near-dup string pairs as extra paraphrase-ish evidence
    log("  consecutive thoughts with Jaccard(content)>=0.35 (string-near-paraphrases):")
    for run_key in order:
        rows = all_rows[run_key]
        E = E_by[run_key]
        hits = []
        for i in range(1, len(rows)):
            a = content_tokens(rows[i - 1]["thought"])
            b = content_tokens(rows[i]["thought"])
            jac = len(a & b) / max(len(a | b), 1)
            if jac >= 0.35:
                hits.append(float(np.dot(E[i - 1], E[i])))
        if hits:
            log(f"    {run_key:5s}  n={len(hits):2d}  mean cos={mean(hits):.3f}")
        else:
            log(f"    {run_key:5s}  n= 0")

    log("")
    log("METRIC PUSHBACK")
    log("  - 'i am' in the frozen self-model list fires on copulas ('I am drawn to the river').")
    log("    TIGHT column drops it. Use TIGHT for Q1; frozen list is still printed as locked.")
    log("  - pattern lemma 'like' and wonder modal 'if' are cheap and inflate adherence.")
    log("    Per-drive rates are the check: ask ('?') and connect (2 snippets) are the honest ones.")
    log("  - unique @0.85 vs ALL previous is stricter than vs prev-20; both are reported.")
    log("  - perc run is mixed-perception; do not treat it as a clean Qwen-perception arm.")
    log("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
