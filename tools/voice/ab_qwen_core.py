"""
tools/voice/ab_qwen_core.py — Stage 1 of "put qwen at the core" (Samuel, 2026-09-20).

The A/B showed the autonomous loop is a MEDITATION loop: fed only a count + one random crumb, told to
report honestly and never invent, with a blank life → it recites emptiness. This flips it: qwen is the
CENTER of a tight loop, and RFE-Core2 is its nervous system.

Each beat:
  1. pick a rotating DRIVE (connect / question / notice-pattern / choose-attention / wonder) — an
     OPERATION to perform, not "report your state".
  2. recall SEVERAL real memories (their CONTENT, not a count) via the last thought, as material.
  3. read the live mood/state from render_card.
  4. qwen generates a thought FROM that material under the drive (allowed to wonder/question/hypothesize,
     NOT to fabricate a past event).
  5. qwen's OUTPUT drives cycle.step — the substrate integrates what it actually thought (loop closure).
  6. store the thought (near-dup collapse only; NO denial-miss filter — we want it to explore).

Isolated scratch + RM per run; live bridge and real RM untouched. Bounded by --beats. Logged to
C:/Users/spamw/rfe-qwen-core/. Compare its transcript to the meditation arms.

Run:  cd ~/rfe/RFE-Core2 && .venv/bin/python -m tools.voice.ab_qwen_core --beats 150
"""
import sys, os, json, time, random, argparse, shutil, datetime, re
sys.path.insert(0, ".")
import torch

from tests._common import build_full_stack                          # noqa: E402
from tools.voice.state_card import render_card                      # noqa: E402
from tools.voice.repl_qwen import (                                 # noqa: E402
    ask_qwen, save_checkpoint, RMClient, QWEN_URL_DEFAULT,
)

WEIGHTS = "data/checkpoints/generator_weights_5rhythm.pt"
ECOLOGY = "data/checkpoints/generator_ecology_5rhythm.json"
RM_DIR  = "/mnt/c/Users/spamw/Desktop/resonance-memory-workshop"
OUTDIR  = "/mnt/c/Users/spamw/rfe-qwen-core"
SEED    = 1234

# qwen is the cortex; it is allowed to THINK, not just report. Guardrails kept: first person, plain,
# no fabricated autobiography, no cosmic mysticism. Note this is a light frame on purpose (the A/B
# showed a bare no-frame collapses into Qwen's factory register).
CORE_SYSTEM = (
    "You are thinking quietly to yourself. You have a memory and a running inner state; work WITH them. "
    "Thinking means you may wonder, ask questions, imagine possibilities, notice patterns, and connect "
    "ideas — do that. Do not fabricate a past event as though it truly happened, and do not drift into "
    "cosmic, mystical, or grandiose language. Speak plainly and in the first person, two to four sentences."
)

DRIVES = [
    "Connect two of the things you remember into a single new thought.",
    "Ask a question about something you don't yet understand.",
    "Notice a pattern, tension, or contradiction across what you remember.",
    "Choose one thing to pay attention to right now, and say why it draws you.",
    "Wonder aloud about something — you may imagine or hypothesize, marking it as a wondering, not a memory.",
    "Reflect on how your thinking has shifted since your earliest thoughts.",
]

def _norm(t):
    return set(re.sub(r"[^0-9a-z ]", " ", t.lower()).split())

def run(beats, url, temp, tag):
    scratch = os.path.join(OUTDIR, f"scratch-{tag}")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch, exist_ok=True); os.makedirs(OUTDIR, exist_ok=True)
    jsonl = open(os.path.join(OUTDIR, f"{tag}.jsonl"), "w", encoding="utf-8", buffering=1)
    txt   = open(os.path.join(OUTDIR, f"{tag}.txt"),   "w", encoding="utf-8", buffering=1)
    txt.write(f"QWEN-CORE run={tag}  temp={temp}\nCORE_SYSTEM={CORE_SYSTEM!r}\n{'='*80}\n")

    random.seed(SEED); torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(vocab_size=8192, dim=128, depth=4, heads=4)
    try:
        gen.load_checkpoint(WEIGHTS, ECOLOGY)
    except Exception as e:  # noqa: BLE001
        txt.write(f"(WARNING trained encoder not loaded: {e})\n")
    gen.eval()
    ckpt = os.path.join(scratch, "substrate-checkpoint.json")
    rm = RMClient(RM_DIR, scratch)

    recent = []; last_thought = ""
    stored = ndup = 0
    for tick in range(1, beats + 1):
        drive = DRIVES[tick % len(DRIVES)]
        # recall real CONTENT — several memories, keyed on the last thought (continuity) or the drive
        q = last_thought or drive
        mems = rm.recall(q) or []
        shown = mems[:4]
        card = render_card(cycle)
        mood = (f"curiosity {card.get('curiosity',0):.2f}, boredom {card.get('boredom',0):.2f}, "
                f"values {card.get('values_emergent',0)}, subjective-time {card.get('subjective_time',0):.1f}, "
                f"memories held {rm.count}")
        mem_block = ("\n".join(f"- {m}" for m in shown) if shown
                     else "(you don't have anything specific in mind yet)")
        user = (f"Your current inner state: {mood}.\n"
                f"What you remember right now:\n{mem_block}\n\n"
                f"{drive}")
        try:
            thought = ask_qwen(url, CORE_SYSTEM, user, temp, max_tokens=160)
        except Exception as e:  # noqa: BLE001
            thought = f"[qwen unreachable: {e}]"
        # qwen's OUTPUT drives the substrate (loop closure) — the mind steps on what it just thought
        cycle.step(thought.split()[:64], source_id="self", origin_type="internal")
        k = _norm(thought)
        near = any(k and p and len(k & p) / len(k | p) >= 0.85 for p in recent[-8:])
        did = False
        if not near and not thought.startswith("[qwen unreachable"):
            rm.save(f"I thought: {thought}"); recent.append(k); did = True; stored += 1
        else:
            ndup += near
        last_thought = thought
        rec = {"tick": tick, "drive": drive, "thought": thought, "shown": shown,
               "mem_count": rm.count, "stored": did, "near_dup": bool(near),
               "curiosity": round(card.get("curiosity", 0), 4), "values": card.get("values_emergent", 0),
               "subj_time": card.get("subjective_time", 0)}
        jsonl.write(json.dumps(rec) + "\n")
        txt.write(f"[{tick:4} m{rm.count} {'ok ' if did else 'dup'}] «{drive[:38]}»\n     {thought}\n")
        save_checkpoint(ckpt, gen, cycle, ve)

    try: rm.close()
    except Exception: pass  # noqa: BLE001
    summary = {"tag": tag, "beats": beats, "stored": stored, "near_dup": ndup, "final_mem": rm.count}
    txt.write(f"{'='*80}\nSUMMARY {json.dumps(summary)}\n"); jsonl.close(); txt.close()
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", type=int, default=150)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--tag", default="qwencore")
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"[{stamp}] qwen-core Stage 1 — {args.beats} beats, temp {args.temp}, url {args.qwen_url}", flush=True)
    t0 = time.time()
    s = run(args.beats, args.qwen_url, args.temp, args.tag)
    s["secs"] = round(time.time() - t0, 1)
    print("DONE " + json.dumps(s) + " -> " + OUTDIR.replace("/mnt/c/", "C:/"), flush=True)

if __name__ == "__main__":
    main()
