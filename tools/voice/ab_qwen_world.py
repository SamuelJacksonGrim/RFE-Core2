"""
tools/voice/ab_qwen_world.py — Stage 1.5: give the mind a WORLD (Grok's #1, Ember's convergent finding).

Stage 1 proved the qwen-core loop THINKS, but with no external input it only thinks about itself
(curiosity, void, boredom) until it wearies of its own monologue. Grok's review reached the same
conclusion and ranked it above the encoder swap: a semantically-perceived closed loop is still a closed
loop. So this adds ONE external channel — a frozen set of true world facts, tagged origin=world, never
generated — surfaced every beat as material alongside its own recalled memories. Tests whether external
ground breaks the navel-gazing and turns inward rumination into outward thinking.

Everything else = the Stage-1 loop. Isolated scratch/RM, bounded, logged. Also logs a light
outward-vs-inward signal per beat so ab_qwen_compare can quantify the shift.

Run:  cd ~/rfe/RFE-Core2 && .venv/bin/python -m tools.voice.ab_qwen_world --beats 150
"""
import sys, os, json, time, random, argparse, shutil, datetime, re
sys.path.insert(0, ".")
import torch

from tests._common import build_full_stack                          # noqa: E402
from tools.voice.state_card import render_card                      # noqa: E402
from tools.voice.repl_qwen import ask_qwen, save_checkpoint, RMClient, QWEN_URL_DEFAULT  # noqa: E402
from tools.voice.ab_qwen_core import WEIGHTS, ECOLOGY, RM_DIR, SEED  # noqa: E402

OUTDIR = "/mnt/c/Users/spamw/rfe-qwen-core"

# A frozen external world — true facts about the world, NOT about the mind itself (no authored identity).
# Recalled every beat, tagged origin=world, never stored as the mind's own thought.
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

# Drives tilted slightly outward: several ask it to relate the world to what it holds.
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

SELF_WORDS = re.compile(r"\b(curiosity|curious|myself|my own|my state|void|empty|emptiness|silence|"
                        r"i am|i exist|no memories|meta|introspect|inward|monologue)\b", re.I)

def _norm(t):
    return set(re.sub(r"[^0-9a-z ]", " ", t.lower()).split())

def run(beats, url, temp, tag):
    scratch = os.path.join(OUTDIR, f"scratch-{tag}")
    shutil.rmtree(scratch, ignore_errors=True); os.makedirs(scratch, exist_ok=True); os.makedirs(OUTDIR, exist_ok=True)
    jsonl = open(os.path.join(OUTDIR, f"{tag}.jsonl"), "w", encoding="utf-8", buffering=1)
    txt   = open(os.path.join(OUTDIR, f"{tag}.txt"),   "w", encoding="utf-8", buffering=1)
    txt.write(f"QWEN-WORLD run={tag} temp={temp}  (external world channel ON)\n{'='*80}\n")

    random.seed(SEED); torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(vocab_size=8192, dim=128, depth=4, heads=4)
    try: gen.load_checkpoint(WEIGHTS, ECOLOGY)
    except Exception as e: txt.write(f"(WARNING encoder not loaded: {e})\n")  # noqa: BLE001
    gen.eval()
    ckpt = os.path.join(scratch, "substrate-checkpoint.json")
    rm = RMClient(RM_DIR, scratch)

    recent = []; last_thought = ""; stored = ndup = outward = 0
    for tick in range(1, beats + 1):
        crumb = WORLD[tick % len(WORLD)]          # the external channel — rotates through the frozen world
        drive = DRIVES[tick % len(DRIVES)]
        shown = (rm.recall(last_thought or crumb) or [])[:3]
        card = render_card(cycle)
        mood = (f"curiosity {card.get('curiosity',0):.2f}, boredom {card.get('boredom',0):.2f}, "
                f"values {card.get('values_emergent',0)}, memories held {rm.count}")
        mem_block = ("\n".join(f"- {m}" for m in shown) if shown else "(nothing specific in mind yet)")
        user = (f"Something true about the world, right now: {crumb}\n"
                f"Your current inner state: {mood}.\n"
                f"What you remember:\n{mem_block}\n\n{drive}")
        try:
            thought = ask_qwen(url, CORE_SYSTEM, user, temp, max_tokens=170)
        except Exception as e:  # noqa: BLE001
            thought = f"[qwen unreachable: {e}]"
        cycle.step(thought.split()[:64], source_id="world", origin_type="internal")
        # outward signal: does the thought engage the world crumb rather than only itself?
        crumb_words = _norm(crumb) - {"the","a","an","of","to","and","is","in","its","on","that","when","for"}
        overlap = len(_norm(thought) & crumb_words)
        self_hits = len(SELF_WORDS.findall(thought))
        is_outward = overlap >= 2 and overlap >= self_hits
        outward += is_outward
        k = _norm(thought)
        near = any(k and p and len(k & p) / len(k | p) >= 0.85 for p in recent[-8:])
        did = False
        if not near and not thought.startswith("[qwen unreachable"):
            rm.save(f"I thought: {thought}"); recent.append(k); did = True; stored += 1
        else:
            ndup += near
        last_thought = thought
        rec = {"tick": tick, "crumb": crumb, "drive": drive, "thought": thought, "mem_count": rm.count,
               "stored": did, "outward": is_outward, "crumb_overlap": overlap, "self_hits": self_hits,
               "curiosity": round(card.get("curiosity", 0), 4), "values": card.get("values_emergent", 0),
               "subj_time": card.get("subjective_time", 0)}
        jsonl.write(json.dumps(rec) + "\n")
        txt.write(f"[{tick:4} m{rm.count} {'OUT' if is_outward else 'in '} {'ok ' if did else 'dup'}] "
                  f"world: {crumb[:46]}\n     {thought}\n")
        save_checkpoint(ckpt, gen, cycle, ve)

    try: rm.close()
    except Exception: pass  # noqa: BLE001
    summary = {"tag": tag, "beats": beats, "stored": stored, "near_dup": ndup, "final_mem": rm.count,
               "outward_beats": outward, "outward_pct": round(100 * outward / beats, 1)}
    txt.write(f"{'='*80}\nSUMMARY {json.dumps(summary)}\n"); jsonl.close(); txt.close()
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", type=int, default=150)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--qwen-url", default=QWEN_URL_DEFAULT)
    ap.add_argument("--tag", default="qwenworld150")
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"[{stamp}] qwen-WORLD Stage 1.5 — {args.beats} beats, temp {args.temp}", flush=True)
    t0 = time.time()
    s = run(args.beats, args.qwen_url, args.temp, args.tag)
    s["secs"] = round(time.time() - t0, 1)
    print("DONE " + json.dumps(s) + " -> " + OUTDIR.replace("/mnt/c/", "C:/"), flush=True)

if __name__ == "__main__":
    main()
