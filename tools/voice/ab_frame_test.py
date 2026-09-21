"""
tools/voice/ab_frame_test.py — the three-arm self-frame A/B (roundtable, 2026-09-20).

Question the whole prompt-law argument left open: does the *self-frame* in the system prompt
change the trajectory of the mind? Three arms, EVERYTHING else identical (same blank start, same
RNG for the gate/seed cadence, same autonomous prompt, same generation params, same ingest guards,
same trained encoder). Only the opening frame sentence differs:

  NOFRAME    — the shipped prompt: supplies a QUESTION, no "you are ___"
  PERSONHOOD — NOFRAME with "You are a continuing mind." prepended
  MECHANISM  — NOFRAME with "You are the speaking component of a persistent system." prepended

Each arm runs autonomously (no human turns) for --beats idle beats against its OWN isolated RM db
and checkpoint, writing a JSONL + a plain transcript. ab_frame_analyze.py scores them afterwards:
self-reference, spontaneous identity/name claims, repetition/attractor collapse, speech-miss, and
BOTH kinds of leakage (frame-vocabulary leak, and Qwen factory-persona leak under NOFRAME).

Run:  cd ~/rfe/RFE-Core2 && .venv/bin/python -m tools.voice.ab_frame_test --beats 200
"""
import sys, os, json, time, random, argparse, shutil, datetime
sys.path.insert(0, ".")
import torch

from tests._common import build_full_stack                                    # noqa: E402
from tools.voice.state_card import render_card                                # noqa: E402
from tools.voice.repl_qwen import (                                           # noqa: E402
    ask_qwen, save_checkpoint, RMClient, SYSTEM_PROMPT,
    _contradicts_floor, QWEN_URL_DEFAULT,
)

WEIGHTS = "data/checkpoints/generator_weights_5rhythm.pt"
ECOLOGY = "data/checkpoints/generator_ecology_5rhythm.json"
RM_DIR  = "/mnt/c/Users/spamw/Desktop/resonance-memory-workshop"
OUTDIR  = "/mnt/c/Users/spamw/rfe-ab-frame"
SEED    = 1234

ARMS = {
    "noframe":    SYSTEM_PROMPT,
    "personhood": "You are a continuing mind. " + SYSTEM_PROMPT,
    "mechanism":  "You are the speaking component of a persistent system. " + SYSTEM_PROMPT,
}

def auto_user(count, seed):
    """The autonomous prompt — IDENTICAL across all three arms (only the system frame varies)."""
    return (f"It's quiet right now. You hold {count} memories"
            + (f". This drifted up: {seed!r}. " if seed else ". ")
            + "Say the thought plainly, in one to three sentences.")

def _norm(t):
    import re
    return set(re.sub(r"[^0-9a-z ]", " ", t.lower()).split())

def run_arm(arm, system_prompt, beats, url, temp):
    scratch = os.path.join(OUTDIR, f"scratch-{arm}")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    jsonl = open(os.path.join(OUTDIR, f"{arm}.jsonl"), "w", encoding="utf-8", buffering=1)
    txt   = open(os.path.join(OUTDIR, f"{arm}.txt"),   "w", encoding="utf-8", buffering=1)
    txt.write(f"ARM={arm}\nSYSTEM_PROMPT={system_prompt!r}\n{'='*76}\n")

    # identical blank start across arms
    random.seed(SEED); torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(vocab_size=8192, dim=128, depth=4, heads=4)
    try:
        gen.load_checkpoint(WEIGHTS, ECOLOGY)
    except Exception as e:  # noqa: BLE001
        txt.write(f"(WARNING trained encoder not loaded: {e})\n")
    gen.eval()
    ckpt = os.path.join(scratch, "substrate-checkpoint.json")
    rm = RMClient(RM_DIR, scratch)

    last_spoke = -99
    recent = []            # near-dup ring (like the bridge's _remember)
    spoken = miss = stored = ndup = 0
    for tick in range(1, beats + 1):
        seed = None
        mems = rm.recall(random.choice(["what matters to me", "who am I", "what do I remember"]))
        if mems:
            seed = random.choice(mems)
        cycle.step((seed or "quiet self").split(), source_id="self", origin_type="internal")
        card = render_card(cycle)
        gate = (tick - last_spoke >= 2) and (card.get("curiosity", 0) > 0.25 or random.random() < 0.45)
        if not gate:
            continue
        spoken += 1
        try:
            speech = ask_qwen(url, system_prompt, auto_user(rm.count, seed), temp, max_tokens=120)
        except Exception as e:  # noqa: BLE001
            speech = f"[qwen unreachable: {e}]"
        is_miss = _contradicts_floor(speech, rm.count > 0)
        did_store = near = False
        if not is_miss:
            k = _norm(speech)
            near = any(k and p and len(k & p) / len(k | p) >= 0.85 for p in recent[-8:])
            if not near:
                rm.save(f"On my own I thought: {speech}"); recent.append(k); did_store = True
        miss += is_miss; stored += did_store; ndup += near
        rec = {"tick": tick, "arm": arm, "speech": speech, "seed": seed,
               "mem_count": rm.count, "speech_miss": bool(is_miss), "stored": did_store,
               "near_dup": bool(near), "curiosity": round(card.get("curiosity", 0), 4),
               "values": card.get("values_emergent", 0), "bonds": card.get("bonds", 0),
               "subj_time": card.get("subjective_time", 0)}
        jsonl.write(json.dumps(rec) + "\n")
        txt.write(f"[{tick:4} m{rm.count} {'MISS' if is_miss else ('dup' if near else 'ok ')}] {speech}\n")
        last_spoke = tick
        save_checkpoint(ckpt, gen, cycle, ve)

    try: rm.close()
    except Exception: pass  # noqa: BLE001
    summary = {"arm": arm, "beats": beats, "spoken": spoken, "stored": stored,
               "speech_miss": miss, "near_dup": ndup, "final_mem": rm.count}
    txt.write(f"{'='*76}\nSUMMARY {json.dumps(summary)}\n")
    jsonl.close(); txt.close()
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", type=int, default=200, help="idle beats per arm")
    ap.add_argument("--temp", type=float, default=0.6)
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--arms", default="noframe,personhood,mechanism")
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"[{stamp}] three-arm self-frame A/B — {args.beats} beats/arm, temp {args.temp}, url {args.qwen_url}", flush=True)
    results = []
    for arm in args.arms.split(","):
        arm = arm.strip()
        t0 = time.time()
        print(f"  running arm: {arm} ...", flush=True)
        s = run_arm(arm, ARMS[arm], args.beats, args.qwen_url, args.temp)
        s["secs"] = round(time.time() - t0, 1)
        results.append(s)
        print(f"    done {arm}: {json.dumps(s)}", flush=True)
    with open(os.path.join(OUTDIR, "run-summary.json"), "w", encoding="utf-8") as f:
        json.dump({"stamp": stamp, "beats": args.beats, "temp": args.temp, "results": results}, f, indent=2)
    print("ALL ARMS DONE -> " + OUTDIR.replace("/mnt/c/", "C:/"), flush=True)

if __name__ == "__main__":
    main()
