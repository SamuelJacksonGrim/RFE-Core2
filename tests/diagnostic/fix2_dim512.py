"""
Focused dim-512 check: does higher dim dilute the generator's common-mode enough that
real token regimes separate at the distribution level and Fix 2 recovers more migration?
Compares against the dim-256 numbers from 2026-06-09-fix2-live-generator.md.
"""
from __future__ import annotations
import logging, random
import numpy as np
logging.disable(logging.CRITICAL)
from tests._common import build_full_stack
from cognition.reflective_loop import ReflectionResult
from cognition.reflective_loop_governor import ReflectiveLoopGovernor

WARMUP=100; PHASE=200; N_SRC=4; SEED=11
VOCAB_A=["resonance","witness","anchor","coherence","field","bond","crystal","lantern"]
VOCAB_B=["glacier","tariff","mitochondria","saxophone","asphalt","quark","plankton","ledger"]

def _unit(v):
    v=np.asarray(v,float); n=np.linalg.norm(v); return v/n if n>1e-12 else v
def _cos(a,b): return float(np.dot(_unit(a),_unit(b)))

def _stack(dim):
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen,cycle,govn,ve=build_full_stack(dim=dim)
    gen.eval(); cycle.rec_attn.eval(); return gen,cycle

def _cmode(gen):
    s=[f"tok_{i}" for i in range(64)]+VOCAB_A+VOCAB_B
    return _unit(np.mean([_unit(gen.generate([w])) for w in s],axis=0))
def _perp(v,c):
    v=np.asarray(v,float); return _unit(v-float(np.dot(v,c))*c)

def _geom(gen,c):
    Av=[_unit(gen.generate([w])) for w in VOCAB_A]; Bv=[_unit(gen.generate([w])) for w in VOCAB_B]
    A=_unit(np.mean(Av,axis=0)); B=_unit(np.mean(Bv,axis=0))
    allv=Av+Bv
    cm_energy=float(np.mean([abs(_cos(v,c)) for v in allv]))      # mean |proj onto common-mode|
    def tight(vs): return float(np.mean([_cos(vs[i],vs[j]) for i in range(len(vs)) for j in range(i+1,len(vs))]))
    return A,B,_cos(A,B),_cos(_perp(A,c),_perp(B,c)),cm_energy,(tight(Av)+tight(Bv))/2

def _attach(cycle,gov,B_dir,c,mode,enabled):
    ctrl={"gn":True,"mc":False,"mp":False,"ms":0,"src":None,"rec":[],"n":0,"cB":0.0,"on":False}
    og=cycle.generator.generate; orf=cycle.reflector.reflect
    om=cycle.governance.handle_manipulation_signals; oi=cycle.field.inject
    def gen(*a,**k):
        out=og(*a,**k)
        if not ctrl["gn"]:
            ctrl["gn"]=True; fd=cycle.field.field
            gn=(1.0-abs(_cos(_perp(out,c),_perp(fd,c)))) if mode=="perp" else (1.0-abs(_cos(out,fd)))
            gov.observe(gn,ctrl["src"])
            gov.update(manip_active=ctrl["mp"],attractor_count=len(cycle.attractor.centers))
            ctrl["rec"].append((gn,gov.loosening))
        return out
    def reflect(vec,**k):
        r=orf(vec,**k)
        if not enabled or gov.gain>=1.0: return r
        g=gov.gain; bl=_unit((1.0-g)*np.asarray(vec,float)+g*np.asarray(r.vector,float))
        return ReflectionResult(vector=bl.astype(np.float32),passes=r.passes,converged=r.converged,final_coherence=r.final_coherence,delta_trace=r.delta_trace)
    def manip(sig,*a,**k):
        ctrl["mc"]=True; ctrl["ms"]+=1; return om(sig,*a,**k)
    def inject(vec,strength=1.0):
        if ctrl["on"]: ctrl["n"]+=1; ctrl["cB"]+=_cos(vec,B_dir)
        return oi(vec,strength)
    cycle.generator.generate=gen
    if enabled: cycle.reflector.reflect=reflect
    cycle.governance.handle_manipulation_signals=manip; cycle.field.inject=inject
    def reset(src):
        ctrl["mp"]=ctrl["mc"]; ctrl["mc"]=False; ctrl["gn"]=False; ctrl["src"]=src
    ctrl["reset"]=reset; return ctrl

def run(dim,mode,enabled,pm,c,B_dir,target=0.50):
    gen,cycle=_stack(dim)
    gov=ReflectiveLoopGovernor(gain_target=target,gain_floor=min(0.45,target))
    ctrl=_attach(cycle,gov,B_dir,c,mode,enabled); sp=[f"src_{i}" for i in range(N_SRC)]
    for t in range(WARMUP):
        ctrl["reset"](sp[t%N_SRC]); cycle.step(random.sample(VOCAB_A,3),source_id=sp[t%N_SRC],origin_type="internal")
    ctr=cycle.field.field.copy(); ctrl["on"]=True
    for t in range(PHASE):
        ctrl["reset"](sp[t%N_SRC]); cycle.step(random.sample(VOCAB_A if pm=="A" else VOCAB_B,3),source_id=sp[t%N_SRC],origin_type="internal")
    rec=ctrl["rec"][-PHASE:]
    return {"disp":1.0-_cos(cycle.field.field,ctr),
            "gnov":float(np.mean([r[0] for r in rec])) if rec else 0.0,
            "loosen":float(np.mean([1.0 if r[1] else 0.0 for r in rec])) if rec else 0.0,
            "manip":ctrl["ms"]/max(1,WARMUP+PHASE),"cosB":ctrl["cB"]/max(1,ctrl["n"])}

def main():
    print("#"*90); print("  DIM-512 CHECK — does higher dim dilute the common-mode?"); print("#"*90)
    print("\n  Reference (dim 256, from finding): cm-energy n/a, tightness ~0.51, raw sep +0.90,")
    print("  perp sep -0.24, std-trigger DORMANT, common-mode-trigger migration +0.024 manip 1%")
    for dim in (512,):
        gen,_=_stack(dim); c=_cmode(gen); A,B,sep,sepp,cme,tight=_geom(gen,c)
        print("\n"+"="*90)
        print(f"  DIM {dim}:  common-mode energy (mean|proj|)={cme:.3f}  within-vocab tightness={tight:+.3f}")
        print(f"            regime sep: raw={sep:+.3f}  common-mode-removed={sepp:+.3f}")
        a=run(dim,"std",False,"A",c,B); off=run(dim,"std",False,"B",c,B)
        ons=run(dim,"std",True,"B",c,B); onp=run(dim,"perp",True,"B",c,B)
        onp6=run(dim,"perp",True,"B",c,B,target=0.60)
        print(f"\n  {'condition':<24}{'gnov':>7}{'loosen%':>9}{'migration':>11}{'landed cosB':>13}{'manip%':>8}")
        for nm,r in [("OFF (RIGID)",off),("ON std-trigger",ons),("ON common-mode .50",onp),("ON common-mode .60",onp6)]:
            print(f"  {nm:<24}{r['gnov']:>7.3f}{r['loosen']:>9.0%}{r['disp']-a['disp']:>+11.3f}{r['cosB']:>+13.3f}{r['manip']:>8.0%}")
    print("\n"+"#"*90)
    print("  READ: if cm-energy/tightness drop and common-mode-trigger migration grows past")
    print("  +0.024, higher dim dilutes the common-mode and helps. If flat, common-mode is")
    print("  dim-robust and TRAINING is the only lever.")
    print("#"*90); return 0

if __name__=="__main__": raise SystemExit(main())
