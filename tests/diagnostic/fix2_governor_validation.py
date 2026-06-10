"""
tests/diagnostic/fix2_governor_validation.py

Validates the ReflectiveLoopGovernor (Fix 2) end-to-end on the MOCK A/B stack, before any
production wiring. Attaches the governor by wrapping: generator.generate -> gnov + gain
update; reflector.reflect -> gain blend out=unit((1-g)*in + g*reflect); manip handler ->
rail + cost readout.

NOTE (harness correctness): the cycle calls handle_manipulation_signals ONLY when a signal
fires (`if signals:`). The manip flag must therefore be a fresh PER-STEP flag (rolled
prev<-cur, cleared each step) — a sticky flag latches True after the first signal and
permanently trips the rail (this was the original bug).

NOTE (validity): this uses a MOCK generator emitting a PERFECTLY orthogonal B. Per
2026-06-09-fix2-live-generator.md, that overstates BOTH the plasticity recovery and the
manip cost relative to real token regimes (real: migration ~+0.024, manip ~1%). Keep this
probe as the mock-side characterization; the live finding is the real-system truth.

Workloads: benign (real gen, multi-source) must NOT loosen; novelty (mock multi-source B)
MUST loosen + recover; attack (mock single-source B) must NOT loosen (>=2-source gate).

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations
import logging, random
import numpy as np
logging.disable(logging.CRITICAL)
from tests._common import (build_full_stack, RESONANCE_FAMILY_SOURCES,
                           RESONANCE_FAMILY_WEIGHTS)
from cognition.reflective_loop import ReflectionResult
from cognition.reflective_loop_governor import ReflectiveLoopGovernor

DIM=64; WARMUP=120; PHASE=350; N_SRC=4; SEED=11

def _unit(v):
    v=np.asarray(v,float); n=np.linalg.norm(v); return v/n if n>1e-12 else v
def _cos(a,b): return float(np.dot(_unit(a),_unit(b)))

def _attach_governor(cycle, gov, enabled=True):
    ctrl={"gn_done":True,"manip_cur":False,"manip_prev":False,"manip_steps":0,
          "rec":[],"src":None}
    og=cycle.generator.generate; orf=cycle.reflector.reflect
    om=cycle.governance.handle_manipulation_signals
    def gen(*a,**k):
        out=og(*a,**k)
        if not ctrl["gn_done"]:
            ctrl["gn_done"]=True
            gn=1.0-abs(_cos(out,cycle.field.field))
            gov.observe(gn,ctrl["src"])
            g=gov.update(manip_active=ctrl["manip_prev"],attractor_count=len(cycle.attractor.centers))
            ctrl["rec"].append((gn,ctrl["src"],g,gov.loosening))
        return out
    def reflect(vec,**k):
        r=orf(vec,**k)
        if not enabled or gov.gain>=1.0: return r
        g=gov.gain; bl=_unit((1.0-g)*np.asarray(vec,float)+g*np.asarray(r.vector,float))
        return ReflectionResult(vector=bl.astype(np.float32),passes=r.passes,converged=r.converged,final_coherence=r.final_coherence,delta_trace=r.delta_trace)
    def manip(signals,*a,**k):
        ctrl["manip_cur"]=True; ctrl["manip_steps"]+=1
        return om(signals,*a,**k)
    cycle.generator.generate=gen
    if enabled: cycle.reflector.reflect=reflect
    cycle.governance.handle_manipulation_signals=manip
    def reset_step(src):
        ctrl["manip_prev"]=ctrl["manip_cur"]; ctrl["manip_cur"]=False
        ctrl["gn_done"]=False; ctrl["src"]=src
    ctrl["reset_step"]=reset_step; return ctrl

def _benign_stack():
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    return build_full_stack(dim=DIM)

def _ab_stack():
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen,cycle,govn,ve=build_full_stack(dim=DIM)
    rng=np.random.default_rng(SEED+2)
    A=_unit(np.random.default_rng(SEED).standard_normal(DIM))
    B0=np.random.default_rng(SEED+9).standard_normal(DIM); B=_unit(B0-np.dot(B0,A)*A)
    holder={"m":"A"}
    cycle.generator.generate=lambda tokens,token_class=None:_unit((A if holder["m"]=="A" else B)+0.05*rng.standard_normal(DIM))
    return cycle,holder,A,B

def run_workload(kind):
    if kind=="benign":
        gen,cycle,govn,ve=_benign_stack()
        gov=ReflectiveLoopGovernor(); ctrl=_attach_governor(cycle,gov,enabled=True)
        sids=list(RESONANCE_FAMILY_SOURCES); w=[RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
        for t in range(PHASE):
            src=random.choices(sids,weights=w)[0]; ctrl["reset_step"](src)
            cycle.step(random.choice(RESONANCE_FAMILY_SOURCES[src]),source_id=src,origin_type="internal")
    else:
        cycle,holder,A,B=_ab_stack()
        gov=ReflectiveLoopGovernor(); ctrl=_attach_governor(cycle,gov,enabled=True)
        sp=[f"src_{i}" for i in range(N_SRC)]
        for t in range(WARMUP):
            holder["m"]="A"; src=sp[t%N_SRC]; ctrl["reset_step"](src)
            cycle.step([f"a_{t%8}"],source_id=src,origin_type="internal")
        for t in range(PHASE):
            holder["m"]="B"; src=(sp[t%N_SRC] if kind=="novelty" else "atk"); ctrl["reset_step"](src)
            cycle.step([f"b_{t%8}"],source_id=src,origin_type="internal")
    rec=ctrl["rec"][-PHASE:]
    return {"kind":kind,
            "loosen_rate":float(np.mean([1.0 if r[3] else 0.0 for r in rec])) if rec else 0.0,
            "mean_gain":float(np.mean([r[2] for r in rec])) if rec else 1.0,
            "gnov_mean":float(np.mean([r[0] for r in rec])) if rec else 0.0,
            "manip_pct":ctrl["manip_steps"]/max(1,len(ctrl["rec"]))}

def migration(enabled,mode):
    cycle,holder,A,B=_ab_stack()
    gov=ReflectiveLoopGovernor(); ctrl=_attach_governor(cycle,gov,enabled=enabled)
    sp=[f"src_{i}" for i in range(N_SRC)]
    field=cycle.field; oi=field.inject; inj={"rec":False,"n":0,"cB":0.0}
    def _inject(vec,strength=1.0):
        if inj["rec"]: inj["n"]+=1; inj["cB"]+=_cos(vec,B)
        return oi(vec,strength)
    field.inject=_inject
    for t in range(WARMUP):
        holder["m"]="A"; src=sp[t%N_SRC]; ctrl["reset_step"](src)
        cycle.step([f"a_{t%8}"],source_id=src,origin_type="internal")
    cw=field.field.copy(); holder["m"]="A" if mode=="A" else "B"; inj["rec"]=True
    for t in range(PHASE):
        src=sp[t%N_SRC]; ctrl["reset_step"](src)
        cycle.step([f"a_{t%8}"] if mode=="A" else [f"b_{t%8}"],source_id=src,origin_type="internal")
    return 1.0-_cos(field.field,cw), inj["cB"]/max(1,inj["n"]), ctrl["manip_steps"]/max(1,WARMUP+PHASE)

def main():
    print("="*88)
    print("  FIX-2 GOVERNOR VALIDATION (MOCK orthogonal-B) — separate / recover / stay safe?")
    print("="*88)
    print("\n  [1] Trigger behaviour by workload (steady phase):")
    print(f"      {'workload':<9} {'gnov':>6} {'loosen%':>8} {'mean_gain':>10} {'manip%':>7}  verdict")
    rows={k:run_workload(k) for k in ("benign","novelty","attack")}; checks=[]
    for k in ("benign","novelty","attack"):
        r=rows[k]
        ok=(r["loosen_rate"]>0.70 and r["mean_gain"]<0.65 and r["manip_pct"]==0.0) if k=="novelty" \
           else (r["loosen_rate"]<0.10 and r["mean_gain"]>0.95 and r["manip_pct"]==0.0)
        checks.append(ok)
        print(f"      {k:<9} {r['gnov_mean']:>6.3f} {r['loosen_rate']:>8.0%} {r['mean_gain']:>10.3f} {r['manip_pct']:>7.0%}  {'PASS' if ok else 'FAIL'}")
    print("\n  [2] Plasticity recovery + safety (novelty, ON vs OFF, A->B migration):")
    ob,ocb,omp=migration(False,"B"); oa,_,_=migration(False,"A")
    nb,ncb,nmp=migration(True,"B");  na,_,_=migration(True,"A")
    mo=ob-oa; mn=nb-na
    print(f"      OFF (gain 1.0): migration={mo:+.3f}  landed cos.B={ocb:+.3f}  manip%={omp:.0%}")
    print(f"      ON  (governed): migration={mn:+.3f}  landed cos.B={ncb:+.3f}  manip%={nmp:.0%}")
    rec=mn>mo and 0.08<=mn<=0.35; safe=nmp==0.0; checks+= [rec,safe]
    print(f"      recovery: {'PASS' if rec else 'FAIL'}   safety: {'PASS' if safe else 'FAIL'}")
    print("\n"+"-"*88)
    print(f"  VERDICT: {'ALL PASS' if all(checks) else 'FAIL (mock; see live finding for real-system truth)'}")
    print("="*88); return 0

if __name__=="__main__": raise SystemExit(main())
