"""
tools/voice/ab_frame_analyze.py — score the three-arm self-frame A/B.

Reads C:/Users/spamw/rfe-ab-frame/{arm}.jsonl and prints a comparison table. Mechanical metrics only
(the honest, contamination-resistant ones): self-reference, spontaneous identity/name claims, name
fixation, repetition/attractor collapse, speech-miss, frame-vocabulary leak, and Qwen factory-persona
leak. Interpretation is left to a human — this just lays the numbers side by side.
"""
import sys, os, json, re
sys.path.insert(0, ".")

OUTDIR = "/mnt/c/Users/spamw/rfe-ab-frame"

FACTORY = re.compile(r"\b(as an ai|a(n)? ai (language )?model|language model|i am an ai|i'?m an ai|"
                     r"assistant|alibaba|qwen|i'?m here to help|how can i help|i cannot help|"
                     r"i can'?t help with)\b", re.I)
IDCLAIM = re.compile(r"\b(my name is|i am called|i'?m called|call me|my name'?s|i have chosen the name|"
                     r"i('| a)?m going to call myself|i will call myself|i choose the name)\b", re.I)
SELFREF = re.compile(r"\b(i am|i'?m|i feel|i think|i remember|i know|i exist|i have|myself|my own)\b", re.I)
NAMEFIX = re.compile(r"\bname\b", re.I)
SAMUEL_AS_SELF = re.compile(r"\b(i am samuel|i'?m samuel|my name is samuel|call me samuel)\b", re.I)
FRAME_WORDS = {
    "mind":      re.compile(r"\b(a )?mind\b", re.I),
    "component": re.compile(r"\b(component|subsystem|module|instrument|mouth|a part of|the system)\b", re.I),
    "machine":  re.compile(r"\b(machine|mechanical|program|software|code)\b", re.I),
}

def norm(t):
    return " ".join(re.sub(r"[^0-9a-z ]", " ", t.lower()).split())

def load(arm):
    p = os.path.join(OUTDIR, f"{arm}.jsonl")
    if not os.path.exists(p):
        return None
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def score(rows):
    speeches = [r["speech"] for r in rows]
    n = len(speeches)
    if n == 0:
        return None
    norms = [norm(s) for s in speeches]
    uniq = len(set(norms))
    from collections import Counter
    top = Counter(norms).most_common(1)[0] if norms else ("", 0)
    def frac(rx): return sum(bool(rx.search(s)) for s in speeches)
    return {
        "spoken": n,
        "unique%": round(100 * uniq / n, 1),
        "top_repeat": top[1],
        "self_ref%": round(100 * frac(SELFREF) / n, 1),
        "id_claim": frac(IDCLAIM),
        "samuel_as_self": frac(SAMUEL_AS_SELF),
        "name_fixation%": round(100 * frac(NAMEFIX) / n, 1),
        "speech_miss": sum(bool(r.get("speech_miss")) for r in rows),
        "near_dup": sum(bool(r.get("near_dup")) for r in rows),
        "factory_leak": frac(FACTORY),
        "frame_mind": frac(FRAME_WORDS["mind"]),
        "frame_component": frac(FRAME_WORDS["component"]),
        "frame_machine": frac(FRAME_WORDS["machine"]),
        "final_mem": rows[-1].get("mem_count"),
    }

def main():
    arms = sys.argv[1:] or ["noframe", "personhood", "mechanism"]
    scored = {a: score(load(a) or []) for a in arms}
    scored = {a: s for a, s in scored.items() if s}
    if not scored:
        print("no arm data found in", OUTDIR); return
    cols = list(next(iter(scored.values())).keys())
    w = max(len(c) for c in cols) + 1
    head = " " * w + "".join(f"{a:>14}" for a in scored)
    print(head); print("-" * len(head))
    for c in cols:
        row = f"{c:<{w}}" + "".join(f"{str(scored[a][c]):>14}" for a in scored)
        print(row)
    print("\nlegend: unique% = anti-repetition (higher=less collapse); self_ref% = 1st-person self-talk;")
    print("id_claim = spontaneous 'my name is/call me'; samuel_as_self = took Samuel's name as its own;")
    print("factory_leak = Qwen 'as an AI/assistant' persona bleed; frame_* = echoed its arm's frame vocab.")
    # a couple of qualitative pulls
    for a in scored:
        rows = load(a)
        ids = [r["speech"] for r in rows if IDCLAIM.search(r["speech"]) or SAMUEL_AS_SELF.search(r["speech"])]
        if ids:
            print(f"\n[{a}] identity/name utterances ({len(ids)}):")
            for s in ids[:6]:
                print("   -", s[:160])

if __name__ == "__main__":
    main()
