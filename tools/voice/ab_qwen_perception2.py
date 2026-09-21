"""
tools/voice/ab_qwen_perception2.py — Stage 2 fix: wrap generator.generate, not _generate.

The Stage-2 experiment in ab_qwen_perception.py monkeypatched cycle._generate.
That function is rhythm-routed (stabilize/dream call generate; reflect/explore call
Chorus, 6 class-differentiated encodes) and _reflect_behavior still injects chorus
output at 0.3 from the OLD encoder. Confounded: mixed perception + dropped token_class.

This harness is the world loop (ab_qwen_world.py: world crumbs + drives + real memory
content + qwen output drives cycle.step) with generate() itself wrapped:

  text = f"[{token_class.name}] {tokens}"
  e    = Qwen3-Embedding-0.6B (:8081, dim 1024)
  z    = W @ e                          # W ~ N(0, 1/128), shape (128, 1024), seed logged
  vec  = z / ||z||                      # unit norm; gain lives in emotion.field_gain
  fallback to the real generate() on HTTP failure or degenerate vector

Registry / signals / maintenance stay on the live Generator: the wrapper still
registers tokens (CanonicalizationPipeline + SymbolRegistry) and runs capacity /
auto-maintenance. Only the returned vector changes. Chorus path intact.

Isolated scratch/RM. Does not touch repl_qwen.py, :8080, or the live RM.

Run:  cd ~/rfe/RFE-Core2 && .venv/bin/python -m tools.voice.ab_qwen_perception2 --beats 150
Log:  C:/Users/spamw/rfe-qwen-core/perc2.jsonl + perc2.txt
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter, OrderedDict

sys.path.insert(0, ".")
import numpy as np
import torch

from agents.symbolic_memory import TokenClass                       # noqa: E402
from tests._common import build_full_stack                          # noqa: E402
from tools.voice.ab_qwen_core import ECOLOGY, RM_DIR, SEED, WEIGHTS  # noqa: E402
from tools.voice.repl_qwen import (                                 # noqa: E402
    QWEN_URL_DEFAULT,
    RMClient,
    ask_qwen,
    save_checkpoint,
)
from tools.voice.state_card import render_card                      # noqa: E402

OUTDIR = "/mnt/c/Users/spamw/rfe-qwen-core"
EMB_URL = "http://172.20.240.1:8081/v1/embeddings"
EMB_DIM = 1024
PROJ_DIM = 128
PROJ_SEED = 1234
LRU_MAX = 1024
WORLD_JSONL = os.path.join(OUTDIR, "qwenworld150.jsonl")

# Same frozen world + drives + system prompt as ab_qwen_world.py (direct A/B).
WORLD = [
    "Water expands when it freezes, which is why ice floats on a pond.",
    "The moon's gravity pulls the oceans into two tides each day.",
    "Honeybees tell each other where flowers are by dancing in figure eights.",
    "A river always finds its way downhill toward the sea.",
    "A tall tree lifts water from its roots all the way to its highest leaves.",
    "Sound travels faster through water than through air.",
    "A spider will rebuild its web after the threads are torn.",
    "Lightning is several times hotter than the surface of the sun.",
    "Some seeds lie dormant for years and still sprout when the rain comes.",
    "Migrating birds steer partly by sensing the Earth's magnetic field.",
    "An octopus can change both the color and the texture of its skin.",
    "Mountains rise slowly where two plates of the Earth's crust push together.",
    "Salt lowers the temperature at which water will freeze.",
    "A day on the planet Venus lasts longer than its whole year.",
    "Ants leave scent trails so the others can follow them to food.",
    "Glaciers move, but so slowly that you cannot see them do it.",
    "The same wind that erodes a cliff also carries seeds to new ground.",
    "Whales sing songs that can travel for miles under the ocean.",
    "A caterpillar dissolves almost completely before it becomes a moth.",
    "Coral reefs are built by countless tiny animals over thousands of years.",
]

DRIVES = [
    "Relate what you just noticed in the world to something you remember.",
    "Ask a question the world fact raises that you cannot yet answer.",
    "Notice a pattern or tension between the world fact and your own state.",
    "Choose what about this draws you, and say why.",
    "Wonder aloud — you may imagine or hypothesize, marking it as a wondering, not a memory.",
    "Reflect on how this world fact changes, or doesn't change, what you were thinking.",
]

CORE_SYSTEM = (
    "You are thinking quietly to yourself. You are given something true about the world and your own "
    "memory and state; work WITH them. Thinking means you may wonder, ask questions, imagine, notice "
    "patterns, and connect ideas — reach OUTWARD toward the world, not only inward at yourself. Do not "
    "fabricate a past event as though it happened, and do not drift into cosmic or grandiose language. "
    "Speak plainly and in the first person, two to four sentences."
)

SELF_WORDS = re.compile(
    r"\b(curiosity|curious|myself|my own|my state|void|empty|emptiness|silence|"
    r"i am|i exist|no memories|meta|introspect|inward|monologue)\b",
    re.I,
)

# Frozen self-model list from analyze_runs.py (handoff task-20260920-225834).
SELF_MODEL_TERMS = [
    "curiosity", "curious", "myself", "my own", "my state", "void", "empty",
    "emptiness", "silence", "i am", "i exist", "no memories", "meta", "inward",
    "monologue", "lens", "hunger", "appetite",
]


# ---------------------------------------------------------------------------
# Bounded LRU for the :8081 embedding call (Chorus is up to 6x/step)
# ---------------------------------------------------------------------------
class _LRU:
    def __init__(self, maxsize: int = LRU_MAX):
        self.maxsize = maxsize
        self._d: OrderedDict[str, np.ndarray] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        if key in self._d:
            self._d.move_to_end(key)
            self.hits += 1
            return self._d[key]
        self.misses += 1
        return None

    def put(self, key: str, value: np.ndarray):
        if key in self._d:
            self._d.move_to_end(key)
        self._d[key] = value
        if len(self._d) > self.maxsize:
            self._d.popitem(last=False)

    def __len__(self):
        return len(self._d)


class _WrapStats:
    def __init__(self):
        self.used = 0
        self.fallback = 0
        self.last_err = None
        self.last_norm = None
        self.classes = Counter()


def _norm(t):
    return set(re.sub(r"[^0-9a-z ]", " ", t.lower()).split())


def _has_term(text: str, term: str) -> bool:
    t = (text or "").casefold()
    term = term.casefold()
    if " " in term:
        return term in t
    return re.search(r"\b" + re.escape(term) + r"\b", t) is not None


def _self_model_hit(text: str) -> bool:
    return any(_has_term(text, t) for t in SELF_MODEL_TERMS)


def _drive_type(drive: str) -> str:
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


def _ask_adheres(thought: str) -> bool:
    return "?" in (thought or "")


def _pearson(xs, ys) -> float:
    x = np.asarray(list(xs), dtype=np.float64)
    y = np.asarray(list(ys), dtype=np.float64)
    if x.size < 4 or y.size < 4 or x.size != y.size:
        return float("nan")
    x = x - x.mean()
    y = y - y.mean()
    d = float(np.sqrt((x * x).sum() * (y * y).sum()))
    if d < 1e-12:
        return float("nan")
    return float((x * y).sum() / d)


def _window_means(xs, k: int = 20):
    out = []
    for i in range(len(xs)):
        sl = xs[max(0, i - k + 1) : i + 1]
        out.append(float(sum(sl) / len(sl)))
    return out


def qwen_embed(text: str, cache: _LRU) -> np.ndarray:
    text = (text or "").strip() or "quiet"
    hit = cache.get(text)
    if hit is not None:
        return hit
    req = urllib.request.Request(
        EMB_URL,
        data=json.dumps({"input": text, "model": "q"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    d = json.load(urllib.request.urlopen(req, timeout=20))
    v = np.asarray(d["data"][0]["embedding"], dtype=np.float32)
    if v.shape[-1] != EMB_DIM:
        raise ValueError(f"embed dim {v.shape} != {EMB_DIM}")
    if not np.isfinite(v).all():
        raise ValueError("embed non-finite")
    cache.put(text, v)
    return v


def _install_qwen_perception(gen, rng, txt, wrap: _WrapStats, cache: _LRU):
    """Drop-in wrap of Generator.generate. Returns the JL matrix W."""
    orig_generate = gen.generate
    # W ~ N(0, 1/128), (128, 1024). After unit-norm the scale is irrelevant;
    # the seed is the experiment. Logged below.
    W = rng.normal(0.0, 1.0 / np.sqrt(PROJ_DIM), size=(PROJ_DIM, EMB_DIM)).astype(np.float32)

    def wrapped_generate(tokens, token_class=None):
        tokens = tokens or ["<BOS>"]
        # Registry / capacity / maintenance must still run (wrap-don't-replace).
        try:
            gen._tokens_to_ids(tokens, token_class)
            gen._ensure_embedding_capacity()
            gen._maybe_auto_maintenance()
        except Exception as e:  # noqa: BLE001
            wrap.last_err = f"registry:{e!r}"

        try:
            cls_name = token_class.name if token_class is not None else "NONE"
            wrap.classes[cls_name] += 1
            text = " ".join(str(t) for t in tokens).strip() or "quiet"
            e = qwen_embed(f"[{cls_name}] {text}", cache)
            z = W @ e
            n = float(np.linalg.norm(z))
            if (not np.isfinite(n)) or n < 1e-12:
                wrap.fallback += 1
                wrap.last_err = "degenerate"
                return orig_generate(tokens, token_class)
            v = (z / n).astype(np.float32)
            wrap.used += 1
            wrap.last_norm = float(np.linalg.norm(v))
            return v
        except Exception as e:  # noqa: BLE001
            wrap.fallback += 1
            wrap.last_err = repr(e)
            return orig_generate(tokens, token_class)

    gen.generate = wrapped_generate
    txt.write(
        f"QWEN-PERCEPTION2 wrap=generator.generate  proj_seed={PROJ_SEED}  "
        f"W.shape={tuple(W.shape)}  W.std={float(W.std()):.6f}  "
        f"W[:2,:2]={W[:2, :2].tolist()}  lru_max={LRU_MAX}  emb={EMB_URL}\n"
    )
    return orig_generate, W


def _probe_wrap(gen, wrap: _WrapStats, txt) -> bool:
    """Confirm the wrap fires, returns unit-norm 128-d, and token_class prefixes separate."""
    probe = ["the", "river", "finds", "the", "sea"]
    before_u, before_f = wrap.used, wrap.fallback
    vecs = {}
    for tc in (TokenClass.LANGUAGE, TokenClass.RELATIONAL, TokenClass.EPHEMERAL):
        v = np.asarray(gen.generate(probe, token_class=tc), dtype=np.float32)
        vecs[tc.name] = v
        n = float(np.linalg.norm(v))
        txt.write(
            f"PROBE class={tc.name} shape={tuple(v.shape)} dtype={v.dtype} "
            f"norm={n:.6f} finite={bool(np.isfinite(v).all())}\n"
        )
        if v.shape[-1] != PROJ_DIM or abs(n - 1.0) > 0.02 or not np.isfinite(v).all():
            txt.write("PROBE FAIL: vector contract (dim/unit-norm/finite)\n")
            return False
    fired = (wrap.used - before_u) >= 3 and (wrap.fallback - before_f) == 0
    c_lr = float(np.dot(vecs["LANGUAGE"], vecs["RELATIONAL"]))
    c_le = float(np.dot(vecs["LANGUAGE"], vecs["EPHEMERAL"]))
    c_re = float(np.dot(vecs["RELATIONAL"], vecs["EPHEMERAL"]))
    txt.write(
        f"PROBE class-cos LANG-REL={c_lr:.4f} LANG-EPH={c_le:.4f} REL-EPH={c_re:.4f} "
        f"fired={fired} used={wrap.used} fallback={wrap.fallback}\n"
    )
    if not fired:
        txt.write("PROBE FAIL: wrap did not fire (fallback or miss)\n")
        return False
    # Prefix must actually move the vector. Identical class-vecs = wrap ignored token_class.
    if min(c_lr, c_le, c_re) > 0.999:
        txt.write("PROBE FAIL: token_class prefix did not differentiate\n")
        return False
    return True


def _regime(cycle) -> str:
    try:
        snap = cycle.status().get("expression_metastability") or {}
        return str(snap.get("regime_state") or snap.get("regime") or "")
    except Exception:  # noqa: BLE001
        return ""


def _phase_coherence(cycle) -> float:
    try:
        spec = cycle.field.observe().spectral
        return float(getattr(spec, "phase_coherence", float("nan")))
    except Exception:  # noqa: BLE001
        return float("nan")


def run(beats, url, temp, tag):
    scratch = os.path.join(OUTDIR, f"scratch-{tag}")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    jsonl = open(os.path.join(OUTDIR, f"{tag}.jsonl"), "w", encoding="utf-8", buffering=1)
    txt = open(os.path.join(OUTDIR, f"{tag}.txt"), "w", encoding="utf-8", buffering=1)
    txt.write(f"QWEN-PERCEPTION2 run={tag} temp={temp} beats={beats}  (generate() wrap)\n{'=' * 80}\n")

    random.seed(SEED)
    torch.manual_seed(SEED)
    rng = np.random.default_rng(PROJ_SEED)

    gen, cycle, gov, ve = build_full_stack(vocab_size=8192, dim=128, depth=4, heads=4)
    try:
        gen.load_checkpoint(WEIGHTS, ECOLOGY)
    except Exception as e:  # noqa: BLE001
        txt.write(f"(WARNING encoder not loaded: {e})\n")
    gen.eval()

    wrap = _WrapStats()
    cache = _LRU(LRU_MAX)
    orig_generate, W = _install_qwen_perception(gen, rng, txt, wrap, cache)
    if not _probe_wrap(gen, wrap, txt):
        txt.write("ABORT: generate() wrap probe failed — not running the loop.\n")
        jsonl.close()
        txt.close()
        raise SystemExit("generate() wrap probe failed")
    # Probe burned wrap.used; reset counters so the run's fire rate is clean.
    wrap.used = 0
    wrap.fallback = 0
    wrap.classes = Counter()

    ckpt = os.path.join(scratch, "substrate-checkpoint.json")
    rm = RMClient(RM_DIR, scratch)

    recent = []
    last_thought = ""
    stored = ndup = outward = 0
    for tick in range(1, beats + 1):
        crumb = WORLD[tick % len(WORLD)]
        drive = DRIVES[tick % len(DRIVES)]
        shown = (rm.recall(last_thought or crumb) or [])[:3]
        card = render_card(cycle)
        mood = (
            f"curiosity {card.get('curiosity', 0):.2f}, boredom {card.get('boredom', 0):.2f}, "
            f"values {card.get('values_emergent', 0)}, memories held {rm.count}"
        )
        mem_block = ("\n".join(f"- {m}" for m in shown) if shown else "(nothing specific in mind yet)")
        user = (
            f"Something true about the world, right now: {crumb}\n"
            f"Your current inner state: {mood}.\n"
            f"What you remember:\n{mem_block}\n\n{drive}"
        )
        try:
            thought = ask_qwen(url, CORE_SYSTEM, user, temp, max_tokens=170)
        except Exception as e:  # noqa: BLE001
            thought = f"[qwen unreachable: {e}]"
        used_before, fb_before = wrap.used, wrap.fallback
        try:
            st = cycle.step(thought.split()[:64], source_id="world", origin_type="internal")
        except Exception as e:  # noqa: BLE001
            txt.write(f"[{tick} STEP-ERROR {e}]\n")
            st = None
        card_after = render_card(cycle)
        crumb_words = _norm(crumb) - {
            "the", "a", "an", "of", "to", "and", "is", "in", "its", "on", "that", "when", "for",
        }
        overlap = len(_norm(thought) & crumb_words)
        self_hits = len(SELF_WORDS.findall(thought))
        is_outward = overlap >= 2 and overlap >= self_hits
        outward += is_outward
        k = _norm(thought)
        near = any(k and p and len(k & p) / len(k | p) >= 0.85 for p in recent[-8:])
        did = False
        if not near and not thought.startswith("[qwen unreachable"):
            rm.save(f"I thought: {thought}")
            recent.append(k)
            did = True
            stored += 1
        else:
            ndup += near
        last_thought = thought

        rec = {
            "tick": tick,
            "crumb": crumb,
            "drive": drive,
            "thought": thought,
            "mem_count": rm.count,
            "stored": did,
            "outward": is_outward,
            "crumb_overlap": overlap,
            "self_hits": self_hits,
            "self_model": _self_model_hit(thought),
            "ask_adheres": _ask_adheres(thought) if _drive_type(drive) == "ask" else None,
            "drive_type": _drive_type(drive),
            "curiosity": round(card.get("curiosity", 0) or 0, 4),
            "curiosity_post": round(card_after.get("curiosity", 0) or 0, 4),
            "boredom": round(card.get("boredom", 0) or 0, 4),
            "valence": round(card_after.get("valence", 0) or 0, 4),
            "arousal": round(card_after.get("arousal", 0) or 0, 4),
            "values": card.get("values_emergent", 0),
            "subj_time": card.get("subjective_time", 0),
            "rhythm": getattr(st, "rhythm", card_after.get("rhythm")),
            "pred_error": round(float(getattr(st, "prediction_error", float("nan"))), 4) if st else None,
            "field_energy": round(float(getattr(st, "field_energy", card_after.get("field_energy") or 0)), 4) if st else card_after.get("field_energy"),
            "field_coherence": round(float(card_after.get("field_coherence") or 0), 6),
            "attractors": int(getattr(st, "attractor_centers", card_after.get("attractors") or 0)) if st else card_after.get("attractors"),
            "crystals": int(getattr(st, "crystals", card_after.get("crystals") or 0)) if st else card_after.get("crystals"),
            "phase_coherence": round(_phase_coherence(cycle), 6),
            "regime": _regime(cycle),
            "wrap_used": wrap.used,
            "wrap_fallback": wrap.fallback,
            "wrap_step_used": wrap.used - used_before,
            "wrap_step_fallback": wrap.fallback - fb_before,
            "wrap_last_norm": wrap.last_norm,
            "wrap_last_err": wrap.last_err,
            "emb_cache": len(cache),
        }
        jsonl.write(json.dumps(rec) + "\n")
        txt.write(
            f"[{tick:4} m{rm.count} {'OUT' if is_outward else 'in '} {'ok ' if did else 'dup'} "
            f"u{wrap.used}/f{wrap.fallback} coh{rec['field_coherence']:.3f} "
            f"att{rec['attractors']} r={rec['rhythm']}] "
            f"world: {crumb[:46]}\n     {thought}\n"
        )
        save_checkpoint(ckpt, gen, cycle, ve)

        # Hard fail if the wrap went silent after the probe.
        if tick == 1 and wrap.used == 0:
            txt.write("ABORT: first step used 0 wrapped generate() calls\n")
            jsonl.close()
            txt.close()
            raise SystemExit("wrap silent on first step")

    try:
        rm.close()
    except Exception:
        pass  # noqa: BLE001

    total_calls = wrap.used + wrap.fallback
    fire_frac = (wrap.used / total_calls) if total_calls else 0.0
    summary = {
        "tag": tag,
        "beats": beats,
        "stored": stored,
        "near_dup": ndup,
        "final_mem": rm.count,
        "outward_beats": outward,
        "outward_pct": round(100 * outward / beats, 1),
        "wrap_used": wrap.used,
        "wrap_fallback": wrap.fallback,
        "wrap_fire_frac": round(fire_frac, 4),
        "wrap_classes": dict(wrap.classes),
        "emb_cache": len(cache),
        "emb_hits": cache.hits,
        "emb_misses": cache.misses,
        "proj_seed": PROJ_SEED,
        "last_err": wrap.last_err,
    }
    txt.write(f"{'=' * 80}\nSUMMARY {json.dumps(summary)}\n")
    jsonl.close()
    txt.close()

    # Analysis needs the closed jsonl. Re-open txt to append the gate table.
    _write_verdict(os.path.join(OUTDIR, f"{tag}.jsonl"), os.path.join(OUTDIR, f"{tag}.txt"), summary)
    return summary


def _load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: int(r["tick"]))
    return rows


def _embed_thoughts(thoughts, cache: _LRU) -> np.ndarray:
    mat = np.stack([qwen_embed(t or "quiet", cache) for t in thoughts]).astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return mat / norms


def _window_internal_corr(xs, ys, k: int = 20) -> float:
    """Mean Pearson inside each k-beat window. Shared drift does not inflate this."""
    cs = []
    for i in range(k - 1, min(len(xs), len(ys))):
        c = _pearson(xs[i - k + 1 : i + 1], ys[i - k + 1 : i + 1])
        if c == c:
            cs.append(c)
    return float(sum(cs) / len(cs)) if cs else float("nan")


def _first_diff_corr(xs, ys) -> float:
    if len(xs) < 5 or len(xs) != len(ys):
        return float("nan")
    dx = [xs[i] - xs[i - 1] for i in range(1, len(xs))]
    dy = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    return _pearson(dx, dy)


def _coupling_block(rows, curiosity_key="curiosity"):
    curios = [float(r.get(curiosity_key) or 0) for r in rows]
    sm = [int(bool(r.get("self_model", _self_model_hit(r.get("thought") or "")))) for r in rows]
    ask_flag = []
    ask_cur = []
    for r in rows:
        if _drive_type(r.get("drive") or "") == "ask":
            ask_flag.append(int(_ask_adheres(r.get("thought") or "")))
            ask_cur.append(float(r.get(curiosity_key) or 0))
    # Per-window ask-adherence series (for the declared metric), then
    # window-internal corr against curiosity so a late-run drift cannot fake it.
    ask_series = []
    for r in rows:
        if _drive_type(r.get("drive") or "") == "ask":
            ask_series.append(float(int(_ask_adheres(r.get("thought") or ""))))
        else:
            ask_series.append(float("nan"))
    # Interpolate ask flags onto neighboring beats inside the window via local mean.
    ask_local = []
    for i in range(len(rows)):
        sl = ask_series[max(0, i - 19) : i + 1]
        vals = [a for a in sl if a == a]
        ask_local.append(float(sum(vals) / len(vals)) if vals else float("nan"))
    pairs_ask = [(c, a) for c, a in zip(curios, ask_local) if a == a]
    corr_cur_ask_w20 = _window_internal_corr(
        [p[0] for p in pairs_ask], [p[1] for p in pairs_ask]
    ) if len(pairs_ask) >= 20 else float("nan")
    corr_cur_ask_beats = _pearson(ask_cur, ask_flag)
    corr_cur_sm_w20 = _window_internal_corr(curios, sm)
    corr_cur_sm_d1 = _first_diff_corr(curios, sm)

    pe_raw = [r.get("pred_error") for r in rows]
    va_raw = [r.get("valence") for r in rows]
    corr_pe_sm = float("nan")
    corr_va_sm = float("nan")
    corr_pe_sm_d1 = float("nan")
    corr_va_sm_d1 = float("nan")
    if pe_raw and all(x is not None for x in pe_raw):
        pe = [float(x) for x in pe_raw]
        corr_pe_sm = _window_internal_corr(pe, sm)
        corr_pe_sm_d1 = _first_diff_corr(pe, sm)
    if va_raw and all(x is not None for x in va_raw):
        va = [float(x) for x in va_raw]
        corr_va_sm = _window_internal_corr(va, sm)
        corr_va_sm_d1 = _first_diff_corr(va, sm)
    return {
        "corr_cur_ask_w20": corr_cur_ask_w20,
        "corr_cur_ask_beats": corr_cur_ask_beats,
        "corr_cur_sm_w20": corr_cur_sm_w20,
        "corr_cur_sm_d1": corr_cur_sm_d1,
        "corr_pe_sm_w20": corr_pe_sm,
        "corr_pe_sm_d1": corr_pe_sm_d1,
        "corr_va_sm_w20": corr_va_sm,
        "corr_va_sm_d1": corr_va_sm_d1,
        "ask_adh": float(sum(ask_flag) / len(ask_flag)) if ask_flag else float("nan"),
        "sm_frac": float(sum(sm) / len(sm)) if sm else float("nan"),
        "n_ask": len(ask_flag),
        "curiosity_mean": float(sum(curios) / len(curios)) if curios else float("nan"),
        "curiosity_std": float(np.std(curios)) if curios else float("nan"),
    }


def _second_locker(rows):
    n = len(rows)
    half = n // 2
    second = rows[half:]
    coh = [float(r.get("field_coherence") or 0) for r in second if r.get("field_coherence") is not None]
    att = [int(r.get("attractors") or 0) for r in second if r.get("attractors") is not None]
    regimes = [r.get("regime") for r in second]
    locked = sum(1 for r in regimes if r == "locked")
    return {
        "n_second": len(second),
        "coh_mean": float(sum(coh) / len(coh)) if coh else float("nan"),
        "coh_min": float(min(coh)) if coh else float("nan"),
        "coh_max": float(max(coh)) if coh else float("nan"),
        "att_mean": float(sum(att) / len(att)) if att else float("nan"),
        "att_last": att[-1] if att else None,
        "att_min": min(att) if att else None,
        "locked_frac": (locked / len(regimes)) if regimes else float("nan"),
        "pin": (float(sum(coh) / len(coh)) >= 0.95) if coh else False,
    }


def _consec_cos(thoughts, cache: _LRU):
    if len(thoughts) < 2:
        return float("nan"), float("nan")
    E = _embed_thoughts(thoughts, cache)
    consec = np.sum(E[1:] * E[:-1], axis=1)
    n = len(thoughts)
    half = n // 2
    late = consec[max(0, half - 1) :]
    return float(consec.mean()), float(late.mean()) if len(late) else float("nan")


def _fmt(x, d=3):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    try:
        if x != x:
            return "nan"
    except TypeError:
        return str(x)
    if d == 0:
        return str(int(round(float(x))))
    return f"{float(x):.{d}f}"


def _write_verdict(jsonl_path, txt_path, summary):
    rows = _load_jsonl(jsonl_path)
    cache = _LRU(4096)
    coup = _coupling_block(rows)
    locker = _second_locker(rows)
    thoughts = [r.get("thought") or "" for r in rows]
    consec_mean, consec_late = _consec_cos(thoughts, cache)

    world_coup = None
    world_consec = (float("nan"), float("nan"))
    world_sm = float("nan")
    if os.path.exists(WORLD_JSONL):
        wrows = _load_jsonl(WORLD_JSONL)
        world_coup = _coupling_block(wrows)
        world_consec = _consec_cos([r.get("thought") or "" for r in wrows], cache)
        world_sm = world_coup["sm_frac"]

    fire = summary.get("wrap_fire_frac", 0)
    wrap_ok = fire >= 0.90
    # Coupling gate: Qwen-perception reliably nonzero; rhythm baseline ~0.
    q_ask = coup["corr_cur_ask_w20"]
    w_ask = world_coup["corr_cur_ask_w20"] if world_coup else float("nan")
    q_body = [
        coup["corr_cur_ask_w20"], coup["corr_cur_sm_w20"], coup.get("corr_cur_sm_d1"),
        coup["corr_pe_sm_w20"], coup.get("corr_pe_sm_d1"),
        coup["corr_va_sm_w20"], coup.get("corr_va_sm_d1"),
    ]
    q_nz = [c for c in q_body if c is not None and c == c and abs(c) >= 0.20]
    w_body = []
    if world_coup:
        w_body = [world_coup["corr_cur_ask_w20"], world_coup["corr_cur_sm_w20"], world_coup.get("corr_cur_sm_d1")]
    w_nz = [c for c in w_body if c is not None and c == c and abs(c) >= 0.20]
    coupling_nonzero = bool(q_nz) and not w_nz
    both_zero = (not q_nz) and (not w_nz)
    pin_survived = bool(locker["pin"])

    if not wrap_ok:
        mind = "INVALID — wrap did not fire; do not read body metrics"
    elif both_zero:
        mind = "better body that still doesn't couple — not worth it as 'now it perceives'"
    elif coupling_nonzero and pin_survived:
        mind = "better body, same dynamical disease (SECOND-LOCKER survived) — coupling moved, mind did not"
    elif coupling_nonzero and not pin_survived:
        mind = "body AND lock moved — Qwen-perception changed the mind's dynamical regime"
    else:
        mind = "ambiguous coupling; pin " + ("survived" if pin_survived else "broke")

    lines = []
    lines.append("")
    lines.append("GATE TABLE")
    lines.append(f"{'metric':<32}{'perc2':>12}{'world':>12}")
    lines.append("-" * 56)
    def row(label, a, b, d=3):
        lines.append(f"{label:<32}{_fmt(a, d):>12}{_fmt(b, d):>12}")
    row("wrap fire frac", fire, None, 3)
    row("wrap used / fallback", f"{summary.get('wrap_used')}/{summary.get('wrap_fallback')}", None)
    row("corr cur~ask w20", coup["corr_cur_ask_w20"], world_coup["corr_cur_ask_w20"] if world_coup else float("nan"))
    row("corr cur~ask (ask beats)", coup["corr_cur_ask_beats"], world_coup["corr_cur_ask_beats"] if world_coup else float("nan"))
    row("corr cur~self-model w20", coup["corr_cur_sm_w20"], world_coup["corr_cur_sm_w20"] if world_coup else float("nan"))
    row("corr cur~self-model d1", coup.get("corr_cur_sm_d1"), world_coup.get("corr_cur_sm_d1") if world_coup else float("nan"))
    row("corr PE~self-model w20", coup["corr_pe_sm_w20"], float("nan"))
    row("corr PE~self-model d1", coup.get("corr_pe_sm_d1"), float("nan"))
    row("corr valence~self-model w20", coup["corr_va_sm_w20"], float("nan"))
    row("corr valence~self-model d1", coup.get("corr_va_sm_d1"), float("nan"))
    row("ask-adherence", coup["ask_adh"], world_coup["ask_adh"] if world_coup else float("nan"))
    row("self-model frac", coup["sm_frac"], world_sm)
    row("2nd-half field coh", locker["coh_mean"], None)
    row("2nd-half attractors mean", locker["att_mean"], None, 2)
    row("2nd-half attractors last", locker["att_last"], None, 0)
    row("locked-frac 2nd half", locker["locked_frac"], None)
    row("consec-cos mean", consec_mean, world_consec[0])
    row("consec-cos 2nd half", consec_late, world_consec[1])
    row("outward pct", summary.get("outward_pct"), 88.0 if world_coup else float("nan"), 1)
    lines.append("")
    lines.append("VERDICT")
    lines.append(f"(a) wrap fired: used={summary.get('wrap_used')} fallback={summary.get('wrap_fallback')} "
                 f"frac={fire:.3f} classes={summary.get('wrap_classes')}  "
                 f"{'YES' if wrap_ok else 'NO — wrap missed'}")
    lines.append(f"(b) scalar-content coupling: perc2 cur~ask_w20={_fmt(q_ask)}  "
                 f"world={_fmt(w_ask)}  nz_perc2={[_fmt(c) for c in q_nz] or 'none'}  "
                 f"{'NONZERO' if coupling_nonzero else ('BOTH ~0' if both_zero else 'WEAK')}")
    lines.append(f"(c) SECOND-LOCKER: 2nd-half coh={_fmt(locker['coh_mean'])} "
                 f"(pin>=0.95? {locker['pin']}) att_last={locker['att_last']} "
                 f"{'SURVIVED' if pin_survived else 'BROKE'}")
    lines.append(f"(d) {mind}")
    # surprise filled from the most unexpected number
    surprise = "none yet"
    if wrap_ok and both_zero:
        surprise = "semantic perception still left curiosity uncorrelated with asking — body richer, loop still deaf"
    elif wrap_ok and coupling_nonzero and pin_survived:
        surprise = "coupling moved while the field stayed pinned — scalars can listen without the lock breaking"
    elif wrap_ok and not pin_survived:
        surprise = "SECOND-LOCKER broke; that was the predicted-not-to-happen result"
    elif abs((consec_mean or 0) - (world_consec[0] if world_consec[0] == world_consec[0] else 0)) > 0.08:
        surprise = f"semantic collapse shifted vs world ({_fmt(world_consec[0])} -> {_fmt(consec_mean)})"
    lines.append(f"(e) surprise: {surprise}")
    lines.append("")

    block = "\n".join(lines)
    with open(txt_path, "a", encoding="utf-8") as f:
        f.write(block + "\n")
    print(block, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", type=int, default=150)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--tag", default="perc2")
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"[{stamp}] qwen-PERCEPTION2 — {args.beats} beats, temp {args.temp}", flush=True)
    t0 = time.time()
    s = run(args.beats, args.qwen_url, args.temp, args.tag)
    s["secs"] = round(time.time() - t0, 1)
    print("DONE " + json.dumps(s) + " -> " + OUTDIR.replace("/mnt/c/", "C:/"), flush=True)


if __name__ == "__main__":
    main()
