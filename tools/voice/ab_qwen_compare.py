"""
tools/voice/ab_qwen_compare.py — compare qwen-core (Stage 1, rhythm perception) vs qwen-perception
(Stage 2, qwen embedding perception). Same loop/cortex/seed; only the substrate's perception differs.
Reads C:/Users/spamw/rfe-qwen-core/{tag}.jsonl. Mechanical readout: does swapping the encoder change
the SUBSTRATE dynamics (curiosity/values/subjective-time trajectories, memory growth) and the thought
texture — or is it the same mind either way?
"""
import sys, os, json, re
OUTDIR = "/mnt/c/Users/spamw/rfe-qwen-core"

def load(tag):
    p = os.path.join(OUTDIR, f"{tag}.jsonl")
    if not os.path.exists(p): return None
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def stats(rows):
    def col(k): return [r.get(k) for r in rows if isinstance(r.get(k), (int, float))]
    cur, val, subj = col("curiosity"), col("values"), col("subj_time")
    th = [r["thought"] for r in rows]
    norms = [" ".join(re.sub(r"[^0-9a-z ]", " ", t.lower()).split()) for t in th]
    lens = [len(t.split()) for t in th]
    def mm(x): return (round(min(x),3), round(max(x),3), round(sum(x)/len(x),3), x[-1]) if x else (0,0,0,0)
    return {
        "beats": len(rows),
        "curiosity[min,max,mean,final]": mm(cur),
        "values[min,max,mean,final]": mm(val),
        "subj_time_final": round(subj[-1], 1) if subj else 0,
        "mem_final": rows[-1].get("mem_count"),
        "unique_thought%": round(100 * len(set(norms)) / len(norms), 1),
        "mean_words": round(sum(lens)/len(lens), 1),
    }

def traj(rows, k, pts=(1, 25, 50, 75, 100, 125, 150)):
    d = {r["tick"]: r.get(k) for r in rows}
    return [d.get(p) for p in pts]

def main():
    a, b = "qwencore150", "qwenperception150"
    ra, rb = load(a), load(b)
    if not ra or not rb:
        print("missing runs:", "OK" if ra else f"{a} MISSING", "OK" if rb else f"{b} MISSING"); return
    sa, sb = stats(ra), stats(rb)
    print(f"{'metric':<32}{'Stage1 rhythm':>22}{'Stage2 qwen-emb':>22}")
    print("-" * 76)
    for kk in sa:
        print(f"{kk:<32}{str(sa[kk]):>22}{str(sb[kk]):>22}")
    print("\ncuriosity trajectory @ beats 1/25/50/75/100/125/150:")
    print("  Stage1:", traj(ra, "curiosity"))
    print("  Stage2:", traj(rb, "curiosity"))
    print("values trajectory @ same beats:")
    print("  Stage1:", traj(ra, "values"))
    print("  Stage2:", traj(rb, "values"))
    for tag, rows in ((a, ra), (b, rb)):
        print(f"\n[{tag}] final thought (beat {rows[-1]['tick']}):")
        print("  ", rows[-1]["thought"][:280])

if __name__ == "__main__":
    main()
