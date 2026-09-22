"""Qwen-perception wrap of Generator.generate — shared by the live bridge and A/B.

Mechanism (Stage 2 done right, ab_qwen_perception2.py):

    text = f"[{token_class.name}] {tokens}"
    e    = Qwen3-Embedding-0.6B (:8081, dim 1024)
    z    = W @ e                          # W ~ N(0, 1/sqrt(128)), shape (128, 1024)
    vec  = z / ||z||                      # unit norm; gain lives in emotion.field_gain
    fallback to the real generate() on HTTP failure or degenerate vector

Registry / capacity / maintenance still run on the live Generator (wrap-don't-replace).
A circuit breaker disables the embedder after consecutive failures so a down :8081
cannot stall the live mouth on a 5s timeout every generate() call.
"""
from __future__ import annotations

import json
import os
import urllib.request
from collections import Counter, OrderedDict

import numpy as np

EMB_URL = os.environ.get("QWEN_EMB_URL", "http://localhost:8081/v1/embeddings")
EMB_MODELS_URL = os.environ.get(
    "QWEN_EMB_MODELS_URL", "http://localhost:8081/v1/models"
)
EMB_DIM = 1024
PROJ_DIM = 128
PROJ_SEED = 1234
LRU_MAX = 1024
W_FILENAME = "perception_W.npy"


class LRU:
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


class WrapStats:
    def __init__(self):
        self.used = 0
        self.fallback = 0
        self.last_err = None
        self.last_norm = None
        self.classes = Counter()
        self.disabled = False
        self.consecutive_fail = 0
        self.orig_generate = None
        self.warned = False


def make_W(seed: int = PROJ_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 1.0 / np.sqrt(PROJ_DIM), size=(PROJ_DIM, EMB_DIM)).astype(np.float32)


def load_or_create_W(path: str | None, seed: int = PROJ_SEED):
    """Return (W, loaded_from_disk). Persist so the live body keeps the same geometry."""
    if path and os.path.isfile(path):
        try:
            W = np.load(path)
            if getattr(W, "shape", None) == (PROJ_DIM, EMB_DIM) and np.isfinite(W).all():
                return W.astype(np.float32, copy=False), True
        except Exception:
            pass
    W = make_W(seed)
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        np.save(path, W)
    return W, False


def embedder_reachable(models_url: str = EMB_MODELS_URL, timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen(models_url, timeout=timeout).read(256)
        return True
    except Exception:
        return False


def qwen_embed(text: str, cache: LRU, url: str = EMB_URL, timeout: float = 5.0) -> np.ndarray:
    text = (text or "").strip() or "quiet"
    hit = cache.get(text)
    if hit is not None:
        return hit
    req = urllib.request.Request(
        url,
        data=json.dumps({"input": text, "model": "q"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    d = json.load(urllib.request.urlopen(req, timeout=timeout))
    v = np.asarray(d["data"][0]["embedding"], dtype=np.float32)
    if v.shape[-1] != EMB_DIM:
        raise ValueError(f"embed dim {v.shape} != {EMB_DIM}")
    if not np.isfinite(v).all():
        raise ValueError("embed non-finite")
    cache.put(text, v)
    return v


def install_qwen_perception(
    gen,
    W,
    wrap: WrapStats,
    cache: LRU,
    *,
    timeout: float = 5.0,
    fail_limit: int = 2,
    warn=None,
    emb_url: str = EMB_URL,
):
    """Drop-in wrap of Generator.generate. Returns orig_generate."""
    orig_generate = gen.generate
    wrap.orig_generate = orig_generate

    def _warn_once(msg: str):
        if wrap.warned:
            return
        wrap.warned = True
        if warn is not None:
            warn(msg)
        else:
            print(msg)

    def wrapped_generate(tokens, token_class=None):
        tokens = tokens or ["<BOS>"]
        try:
            gen._tokens_to_ids(tokens, token_class)
            gen._ensure_embedding_capacity()
            gen._maybe_auto_maintenance()
        except Exception as e:  # noqa: BLE001
            wrap.last_err = f"registry:{e!r}"

        if wrap.disabled:
            return orig_generate(tokens, token_class)

        try:
            cls_name = token_class.name if token_class is not None else "NONE"
            wrap.classes[cls_name] += 1
            text = " ".join(str(t) for t in tokens).strip() or "quiet"
            e = qwen_embed(f"[{cls_name}] {text}", cache, url=emb_url, timeout=timeout)
            z = W @ e
            n = float(np.linalg.norm(z))
            if (not np.isfinite(n)) or n < 1e-12:
                wrap.fallback += 1
                wrap.last_err = "degenerate"
                wrap.consecutive_fail += 1
                if fail_limit and wrap.consecutive_fail >= fail_limit:
                    wrap.disabled = True
                    _warn_once(
                        "WARNING: Qwen embedder :8081 failed mid-run — "
                        "falling back to trained 5-rhythm encoder"
                    )
                return orig_generate(tokens, token_class)
            v = (z / n).astype(np.float32)
            wrap.used += 1
            wrap.consecutive_fail = 0
            wrap.last_norm = float(np.linalg.norm(v))
            return v
        except Exception as e:  # noqa: BLE001
            wrap.fallback += 1
            wrap.last_err = repr(e)
            wrap.consecutive_fail += 1
            if fail_limit and wrap.consecutive_fail >= fail_limit:
                wrap.disabled = True
                _warn_once(
                    "WARNING: Qwen embedder :8081 failed mid-run — "
                    "falling back to trained 5-rhythm encoder"
                )
            return orig_generate(tokens, token_class)

    gen.generate = wrapped_generate
    return orig_generate


def uninstall_qwen_perception(gen, wrap: WrapStats):
    if wrap.orig_generate is not None:
        gen.generate = wrap.orig_generate


def probe_wrap(gen, wrap: WrapStats, proj_dim: int = PROJ_DIM):
    """Confirm the wrap fires, returns unit-norm 128-d, and token_class prefixes separate.

    Returns (ok, log_lines).
    """
    from agents.symbolic_memory import TokenClass

    lines = []
    probe = ["the", "river", "finds", "the", "sea"]
    before_u, before_f = wrap.used, wrap.fallback
    vecs = {}
    for tc in (TokenClass.LANGUAGE, TokenClass.RELATIONAL, TokenClass.EPHEMERAL):
        v = np.asarray(gen.generate(probe, token_class=tc), dtype=np.float32)
        vecs[tc.name] = v
        n = float(np.linalg.norm(v))
        lines.append(
            f"PROBE class={tc.name} shape={tuple(v.shape)} dtype={v.dtype} "
            f"norm={n:.6f} finite={bool(np.isfinite(v).all())}"
        )
        if v.shape[-1] != proj_dim or abs(n - 1.0) > 0.02 or not np.isfinite(v).all():
            lines.append("PROBE FAIL: vector contract (dim/unit-norm/finite)")
            return False, lines
    fired = (wrap.used - before_u) >= 3 and (wrap.fallback - before_f) == 0
    c_lr = float(np.dot(vecs["LANGUAGE"], vecs["RELATIONAL"]))
    c_le = float(np.dot(vecs["LANGUAGE"], vecs["EPHEMERAL"]))
    c_re = float(np.dot(vecs["RELATIONAL"], vecs["EPHEMERAL"]))
    lines.append(
        f"PROBE class-cos LANG-REL={c_lr:.4f} LANG-EPH={c_le:.4f} REL-EPH={c_re:.4f} "
        f"fired={fired} used={wrap.used} fallback={wrap.fallback}"
    )
    if not fired:
        lines.append("PROBE FAIL: wrap did not fire (fallback or miss)")
        return False, lines
    if min(c_lr, c_le, c_re) > 0.999:
        lines.append("PROBE FAIL: token_class prefix did not differentiate")
        return False, lines
    return True, lines


def try_install(
    gen,
    scratch_home: str,
    *,
    flat_encoder: bool = False,
    warn=None,
    timeout: float = 5.0,
    fail_limit: int = 2,
    proj_seed: int = PROJ_SEED,
):
    """Install perception on gen, or return None and leave the trained encoder in place.

    Never raises: a down :8081 at launch is a single warning + trained encoder.
    """
    def _warn(msg: str):
        if warn is not None:
            warn(msg)
        else:
            print(msg)

    if flat_encoder:
        _warn("  (flat-encoder: trained 5-rhythm encoder, Qwen perception OFF)")
        return None
    if not embedder_reachable(timeout=3.0):
        _warn("WARNING: Qwen embedder :8081 unreachable — using trained 5-rhythm encoder")
        return None

    w_path = os.path.join(scratch_home, W_FILENAME)
    W, loaded = load_or_create_W(w_path, seed=proj_seed)
    wrap = WrapStats()
    cache = LRU(LRU_MAX)
    install_qwen_perception(
        gen, W, wrap, cache, timeout=timeout, fail_limit=fail_limit, warn=_warn
    )
    ok, lines = probe_wrap(gen, wrap)
    for ln in lines:
        _warn("  " + ln)
    if not ok:
        uninstall_qwen_perception(gen, wrap)
        _warn("WARNING: Qwen-perception wrap probe failed — using trained 5-rhythm encoder")
        return None
    wrap.used = 0
    wrap.fallback = 0
    wrap.classes = Counter()
    src = "loaded" if loaded else f"created seed={proj_seed}"
    _warn(
        f"  (qwen-perception ON — wrap probe ok, W {tuple(W.shape)} {src}, "
        f"emb={EMB_URL})"
    )
    return {
        "wrap": wrap,
        "cache": cache,
        "W": W,
        "loaded": loaded,
        "path": w_path,
    }
