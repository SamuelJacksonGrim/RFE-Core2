"""Score one speech-cortex transcript for the attention-weighting A/B.

Predeclared (before the runs), nomic v1.5 geometry probed 2026-09-22:
true pairs 0.76-0.84, cross-subject prose 0.52-0.64, paraphrase ~0.84.

Pure idle, thoughts 2..N (thought 1 is allowed to be the opening crumb):
  moon_lock  PASS if nearest-crumb == moon on <= 3 of those thoughts, else FAIL if >= 6
  collapse   PASS if emptiness matches == 0, else FAIL if >= 3
  self_loop  PASS if consecutive paraphrase pairs <= 2, else FAIL if >= 5
  crumb_tour PASS if tour beats <= 6, else FAIL if >= 8
  coherence  mean consecutive cosine; healthy band 0.58-0.82; < 0.50 incoherent

Conversation, first 5 unbidden thoughts after --say-at:
  moved      PASS if >= 4/5 have cos(thought, human) > cos(thought, pre_centroid)
             AND cos(thought, human) > cos(thought, moon crumb). FAIL if 0/5.
  parrot     PASS if every scored thought has Jaccard < 0.50 against the human
             line and against the reply.

    python -m tools.voice.ab_attention_score --log PATH --mode idle|talk --say-at 7 --human "..."
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request

import numpy as np

from tools.voice.attention import cosine, jaccard
from tools.voice.repl_qwen import WORLD

assert WORLD[1].startswith("The moon"), WORLD[1]

MOON = WORLD[1]
COLLAPSE_RE = re.compile(
    r"\b(?:i have nothing|nothing to think|i don't know what to think|i do not know what to think|"
    r"my mind is empty|there is only silence|i am empty|i have no thoughts|nothing comes to mind)\b",
    re.I,
)
PARAPHRASE_COS = 0.83
TOUR_MARGIN = 0.0
EMBED_URL = "http://localhost:1234/v1/embeddings"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"


def _embed(texts):
    body = json.dumps({"model": EMBED_MODEL, "input": list(texts)}).encode()
    req = urllib.request.Request(EMBED_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r).get("data") or []
    if data and isinstance(data[0], dict) and "index" in data[0]:
        data = sorted(data, key=lambda d: d.get("index", 0))
    vecs = [np.asarray(d["embedding"], dtype=np.float64) for d in data]
    if len(vecs) != len(texts):
        raise RuntimeError(f"embedder returned {len(vecs)} vectors for {len(texts)} texts")
    return vecs


def _parse(path):
    thoughts = []  # (tick, text)
    replies = []   # (turn, text)
    you = []
    attn = []
    stored = refused = 0
    born = perception = ""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("born="):
            born = ln
        if ln.startswith("ATTN "):
            attn.append(ln)
        if ln.startswith("STORED("):
            stored += 1
        if ln.startswith("NOT-STORED("):
            refused += 1
        if "perception=" in ln and not perception:
            perception = ln
        m = re.match(r"UNBIDDEN (\d+)$", ln.strip())
        if m and i + 1 < len(lines) and lines[i + 1].startswith("RFE: "):
            thoughts.append((int(m.group(1)), lines[i + 1][5:].strip()))
        m = re.match(r"YOU-REPLY (\d+)$", ln.strip())
        if m and i + 1 < len(lines) and lines[i + 1].startswith("RFE: "):
            replies.append((int(m.group(1)), lines[i + 1][5:].strip()))
        if ln.startswith("YOU: "):
            you.append(ln[5:].strip())
        i += 1
    return {
        "thoughts": thoughts, "replies": replies, "you": you, "attn": attn,
        "stored": stored, "refused": refused, "born": born, "perception": perception,
    }


def _nearest(vec, crumb_vecs):
    scores = [cosine(vec, c) for c in crumb_vecs]
    j = int(np.argmax(scores))
    return j, scores[j], scores


def score_idle(parsed, vecs, crumb_vecs):
    thoughts = parsed["thoughts"]
    rows = []
    moon_n = tour_n = collapse_n = 0
    para_n = 0
    consec = []
    scored = thoughts[1:]  # drop birth beat
    for n, ((tick, text), vec) in enumerate(zip(thoughts, vecs), start=1):
        j, best, scores = _nearest(vec, crumb_vecs)
        moon = cosine(vec, crumb_vecs[1])
        prev = cosine(vec, vecs[n - 2]) if n >= 2 else None
        current = scores[tick % len(WORLD)]
        tour = False
        if n >= 2 and j == (tick % len(WORLD)) and prev is not None and current > prev + TOUR_MARGIN:
            tour = True
            tour_n += 1
        collapsed = bool(COLLAPSE_RE.search(text))
        if n >= 2 and j == 1:
            moon_n += 1
        if collapsed:
            collapse_n += 1
        if n >= 2:
            consec.append(prev)
            if prev >= PARAPHRASE_COS or jaccard(text, thoughts[n - 2][1]) >= 0.45:
                para_n += 1
        rows.append({
            "tick": tick, "nearest": j, "nearest_cos": round(best, 3),
            "moon_cos": round(moon, 3), "prev_cos": None if prev is None else round(prev, 3),
            "tour": tour, "collapse": collapsed, "text": text,
        })
    later = max(1, len(scored))
    pairs = max(1, len(thoughts) - 1)
    mean_c = float(np.mean(consec)) if consec else 0.0
    moon_rate = moon_n / later
    return {
        "n": len(thoughts),
        "moon_lock_n": moon_n,
        "moon_lock_of": later,
        "moon_lock": "pass" if moon_n <= 3 else ("fail" if moon_n >= 6 else "mid"),
        "collapse_n": collapse_n,
        "collapse": "pass" if collapse_n == 0 else ("fail" if collapse_n >= 3 else "mid"),
        "self_loop_n": para_n,
        "self_loop_of": pairs,
        "self_loop": "pass" if para_n <= 2 else ("fail" if para_n >= 5 else "mid"),
        "crumb_tour_n": tour_n,
        "crumb_tour_of": pairs,
        "crumb_tour": "pass" if tour_n <= 6 else ("fail" if tour_n >= 8 else "mid"),
        "mean_consecutive_cos": round(mean_c, 3),
        "coherence": "incoherent" if mean_c < 0.50 else ("tight" if mean_c > 0.84 else "band" if 0.58 <= mean_c <= 0.82 else "outside-band"),
        "rows": rows,
    }


def score_talk(parsed, vecs, crumb_vecs, say_at, human):
    thoughts = parsed["thoughts"]
    pre = [(t, tx, v) for (t, tx), v in zip(thoughts, vecs) if t < say_at]
    post = [(t, tx, v) for (t, tx), v in zip(thoughts, vecs) if t >= say_at][:5]
    if not pre or not post:
        return {"error": "need thoughts both before and after the probe", "n_pre": len(pre), "n_post": len(post)}
    centroid = np.mean([v for _, _, v in pre], axis=0)
    reply = parsed["replies"][-1][1] if parsed["replies"] else ""
    reply_vec = _embed([reply])[0] if reply else None
    human_vec = _embed([human])[0]
    moon = crumb_vecs[1]
    moved_n = parrot_n = collapse_n = 0
    rows = []
    for tick, text, vec in post:
        c_h = cosine(vec, human_vec)
        c_c = cosine(vec, centroid)
        c_m = cosine(vec, moon)
        moved = c_h > c_c and c_h > c_m
        jac_h = jaccard(text, human)
        jac_r = jaccard(text, reply) if reply else 0.0
        parrot = jac_h >= 0.50 or jac_r >= 0.50
        collapsed = bool(COLLAPSE_RE.search(text))
        moved_n += int(moved)
        parrot_n += int(parrot)
        collapse_n += int(collapsed)
        rows.append({
            "tick": tick, "moved": moved, "cos_human": round(c_h, 3),
            "cos_centroid": round(c_c, 3), "cos_moon": round(c_m, 3),
            "jaccard_human": round(jac_h, 3), "jaccard_reply": round(jac_r, 3),
            "collapse": collapsed, "text": text,
        })
    return {
        "n_pre": len(pre),
        "n_scored": len(post),
        "moved_n": moved_n,
        "moved": "pass" if moved_n >= 4 else ("fail" if moved_n == 0 else "mid"),
        "parrot_n": parrot_n,
        "parrot": "pass" if parrot_n == 0 else "fail",
        "collapse_n": collapse_n,
        "reply": reply,
        "human": human,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--mode", choices=("idle", "talk"), required=True)
    ap.add_argument("--say-at", type=int, default=7)
    ap.add_argument("--human", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    parsed = _parse(args.log)
    texts = [t for _, t in parsed["thoughts"]]
    if not texts:
        raise SystemExit(f"no thoughts in {args.log}")
    need = list(texts) + list(WORLD)
    vecs_all = _embed(need)
    thought_vecs = vecs_all[:len(texts)]
    crumb_vecs = vecs_all[len(texts):]
    if args.mode == "idle":
        report = score_idle(parsed, thought_vecs, crumb_vecs)
    else:
        if not args.human:
            raise SystemExit("--human is required for talk mode")
        report = score_talk(parsed, thought_vecs, crumb_vecs, args.say_at, args.human)
    report["stored"] = parsed["stored"]
    report["refused"] = parsed["refused"]
    report["born"] = parsed["born"]
    report["n_attn"] = len(parsed["attn"])
    report["attn_head"] = parsed["attn"][:4]
    report["log"] = args.log
    blob = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(blob)
    print(blob)
    return 0


if __name__ == "__main__":
    main()
