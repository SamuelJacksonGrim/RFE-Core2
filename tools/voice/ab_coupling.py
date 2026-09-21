import json, numpy as np
SELF = ["curiosity","curious","myself","my own","my state","void","empty","emptiness","silence",
        "i exist","no memories","meta","inward","monologue","lens","hunger","appetite"]
def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def feats(rows):
    cur = np.array([r.get("curiosity",0.0) for r in rows], float)
    val = np.array([float(r.get("values",0)) for r in rows], float)
    th  = [str(r.get("thought","")).lower() for r in rows]
    sc  = np.array([sum(w in t for w in SELF) for t in th], float)   # self-word count
    sb  = np.array([1.0 if any(w in t for w in SELF) else 0.0 for t in th])
    q   = np.array([1.0 if "?" in t else 0.0 for t in th])
    return cur, val, sc, sb, q
def corr(a,b):
    return 0.0 if (np.std(a)==0 or np.std(b)==0) else float(np.corrcoef(a,b)[0,1])
def dcorr(a,b):
    return corr(np.diff(a), np.diff(b))
runs = [("world(rhythm ctrl)", "/mnt/c/Users/spamw/rfe-qwen-core/qwenworld150.jsonl"),
        ("perc2(qwen-percep)",  "/mnt/c/Users/spamw/rfe-qwen-core/perc2.jsonl")]
print("SCALAR-CONTENT COUPLING — Δ = first-differenced (drift stripped), the honest test")
print(f"{'run':<20}{'corr(Δcur,Δself)':>18}{'corr(Δcur,Δq)':>15}{'corr(Δval,Δself)':>18}{'selfbeats':>11}{'qbeats':>8}")
for name,p in runs:
    try:
        rows=load(p); cur,val,sc,sb,q=feats(rows)
        print(f"{name:<20}{dcorr(cur,sc):>18.3f}{dcorr(cur,q):>15.3f}{dcorr(val,sc):>18.3f}{int(sb.sum()):>11}{int(q.sum()):>8}")
    except Exception as e:
        print(f"{name:<20} ERROR {e}")
print("\ninterpretation: rhythm ctrl should be ~0 (perception is rhythm, not meaning);")
print("qwen-percep NONZERO => the body's mood tracks content (Stage 2 earns its keep). Both ~0 => 'better body, no coupling'.")
