"""
tools/voice/ab_qwen_perception.py — Stage 2: replace the encoder with Qwen (Samuel's deep vote).

Same qwen-core thinking loop as Stage 1, but the substrate's PERCEPTION is now Qwen's embedding
instead of the trained 5-rhythm encoder. Injection point: loop/autonomous_cycle.py step() does
`vec = self._generate(tokens, rhythm)`. We monkeypatch `cycle._generate` so that vec = a Qwen
embedding of the tokens (via Qwen3-Embedding-0.6B on :8081, dim 1024), projected 1024->128 with a
fixed seeded Gaussian, then MAGNITUDE-MATCHED to the trained encoder's own output norm so the field /
attractor (tuned for the 5-rhythm regime) don't destabilize. Everything else identical to Stage 1.

Self-corrects: measures the trained encoder's typical norm at runtime (calibration), guards against
NaN/explosion, logs the substrate state each beat so we can SEE whether qwen-perception makes the
mood/values evolve more meaningfully than rhythm-perception.

Run:  cd ~/rfe/RFE-Core2 && .venv/bin/python -m tools.voice.ab_qwen_perception --beats 150
"""
import sys, os, json, time, random, argparse, shutil, datetime, re, urllib.request
sys.path.insert(0, ".")
import numpy as np
import torch

from tests._common import build_full_stack                          # noqa: E402
from tools.voice.state_card import render_card                      # noqa: E402
from tools.voice.repl_qwen import (                                 # noqa: E402
    ask_qwen, save_checkpoint, RMClient, QWEN_URL_DEFAULT,
)
from tools.voice.ab_qwen_core import CORE_SYSTEM, DRIVES, WEIGHTS, ECOLOGY, RM_DIR, SEED  # noqa: E402

OUTDIR = "/mnt/c/Users/spamw/rfe-qwen-core"
EMB_URL = "http://172.20.240.1:8081/v1/embeddings"
EMB_DIM = 1024

_emb_cache = {}
def qwen_embed(text):
    text = text.strip() or "quiet"
    if text in _emb_cache:
        return _emb_cache[text]
    req = urllib.request.Request(
        EMB_URL, data=json.dumps({"input": text, "model": "q"}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=20))
    v = np.asarray(d["data"][0]["embedding"], dtype=np.float32)
    _emb_cache[text] = v
    return v

def _norm(t):
    return set(re.sub(r"[^0-9a-z ]", " ", t.lower()).split())

def run(beats, url, temp, tag):
    scratch = os.path.join(OUTDIR, f"scratch-{tag}")
    shutil.rmtree(scratch, ignore_errors=True); os.makedirs(scratch, exist_ok=True); os.makedirs(OUTDIR, exist_ok=True)
    jsonl = open(os.path.join(OUTDIR, f"{tag}.jsonl"), "w", encoding="utf-8", buffering=1)
    txt   = open(os.path.join(OUTDIR, f"{tag}.txt"),   "w", encoding="utf-8", buffering=1)

    random.seed(SEED); torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(vocab_size=8192, dim=128, depth=4, heads=4)
    try:
        gen.load_checkpoint(WEIGHTS, ECOLOGY)
    except Exception as e:  # noqa: BLE001
        txt.write(f"(WARNING trained encoder not loaded: {e})\n")
    gen.eval()

    # ---- calibrate: what norm does the trained encoder (the thing we're replacing) put out? ----
    orig_generate = cycle._generate
    rng = np.random.default_rng(SEED)
    P = (rng.standard_normal((EMB_DIM, 128)).astype(np.float32)) / np.sqrt(EMB_DIM)  # fixed projection
    samples = ["I am here", "a quiet thought about memory", "what do I remember", "curiosity and silence",
               "I notice a pattern", "connect two ideas", "the void is a workspace", "I wonder about this"]
    norms = []
    for s in samples:
        try:
            v = orig_generate(s.split(), cycle.field.observe().rhythm)
            norms.append(float(np.linalg.norm(np.asarray(v, dtype=np.float32))))
        except Exception:  # noqa: BLE001
            pass
    target_norm = float(np.median(norms)) if norms else 1.0
    dim_ok = True
    try:
        probe = np.asarray(orig_generate("probe".split(), cycle.field.observe().rhythm), dtype=np.float32)
        dim_ok = (probe.shape[-1] == 128)
    except Exception:  # noqa: BLE001
        pass
    txt.write(f"QWEN-PERCEPTION run={tag} temp={temp}\ntarget_norm(trained encoder median)={target_norm:.4f} "
              f"n_samples={len(norms)} dim_ok={dim_ok}\n{'='*80}\n")

    # ---- patch perception: vec = magnitude-matched projection of the qwen embedding ----
    def patched_generate(tokens, rhythm):
        try:
            e = qwen_embed(" ".join(tokens) if tokens else "quiet")
            v = e @ P
            n = float(np.linalg.norm(v))
            if not np.isfinite(n) or n == 0.0:
                return orig_generate(tokens, rhythm)  # self-heal: fall back if degenerate
            v = (v / n) * target_norm
            return v.astype(np.float32)
        except Exception:  # noqa: BLE001 — any embedding failure → fall back to the real encoder
            return orig_generate(tokens, rhythm)
    cycle._generate = patched_generate

    ckpt = os.path.join(scratch, "substrate-checkpoint.json")
    rm = RMClient(RM_DIR, scratch)
    recent = []; last_thought = ""; stored = ndup = fallback = 0
    for tick in range(1, beats + 1):
        drive = DRIVES[tick % len(DRIVES)]
        q = last_thought or drive
        shown = (rm.recall(q) or [])[:4]
        card = render_card(cycle)
        mood = (f"curiosity {card.get('curiosity',0):.2f}, boredom {card.get('boredom',0):.2f}, "
                f"values {card.get('values_emergent',0)}, subjective-time {card.get('subjective_time',0):.1f}, "
                f"memories held {rm.count}")
        mem_block = ("\n".join(f"- {m}" for m in shown) if shown else "(nothing specific in mind yet)")
        user = f"Your current inner state: {mood}.\nWhat you remember right now:\n{mem_block}\n\n{drive}"
        try:
            thought = ask_qwen(url, CORE_SYSTEM, user, temp, max_tokens=160)
        except Exception as e:  # noqa: BLE001
            thought = f"[qwen unreachable: {e}]"
        try:
            cycle.step(thought.split()[:64], source_id="self", origin_type="internal")
        except Exception as e:  # noqa: BLE001 — catch field destabilization, log, keep going
            txt.write(f"[{tick} STEP-ERROR {e}]\n")
        k = _norm(thought)
        near = any(k and p and len(k & p) / len(k | p) >= 0.85 for p in recent[-8:])
        did = False
        if not near and not thought.startswith("[qwen unreachable"):
            rm.save(f"I thought: {thought}"); recent.append(k); did = True; stored += 1
        else:
            ndup += near
        last_thought = thought
        rec = {"tick": tick, "drive": drive, "thought": thought, "mem_count": rm.count, "stored": did,
               "curiosity": round(card.get("curiosity", 0), 4), "boredom": round(card.get("boredom", 0), 4),
               "values": card.get("values_emergent", 0), "subj_time": card.get("subjective_time", 0)}
        jsonl.write(json.dumps(rec) + "\n")
        txt.write(f"[{tick:4} m{rm.count} cur{card.get('curiosity',0):.2f} val{card.get('values_emergent',0)} "
                  f"{'ok ' if did else 'dup'}] «{drive[:32]}»\n     {thought}\n")
        save_checkpoint(ckpt, gen, cycle, ve)

    try: rm.close()
    except Exception: pass  # noqa: BLE001
    summary = {"tag": tag, "beats": beats, "stored": stored, "near_dup": ndup,
               "final_mem": rm.count, "target_norm": round(target_norm, 4), "emb_cache": len(_emb_cache)}
    txt.write(f"{'='*80}\nSUMMARY {json.dumps(summary)}\n"); jsonl.close(); txt.close()
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", type=int, default=150)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--tag", default="qwenperception")
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"[{stamp}] qwen-PERCEPTION Stage 2 — {args.beats} beats, temp {args.temp}", flush=True)
    t0 = time.time()
    s = run(args.beats, args.qwen_url, args.temp, args.tag)
    s["secs"] = round(time.time() - t0, 1)
    print("DONE " + json.dumps(s) + " -> " + OUTDIR.replace("/mnt/c/", "C:/"), flush=True)

if __name__ == "__main__":
    main()
