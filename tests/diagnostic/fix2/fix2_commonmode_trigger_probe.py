"""
tests/diagnostic/fix2/fix2_commonmode_trigger_probe.py

Follow-up to fix2_live_token_probe.py. That probe found Fix 2 DORMANT on the real
generator at dim 64 AND 256: regime MEANS are collinear (sep ~0.89) because the generator
emits a dominant COMMON-MODE direction, even though within-vocab tightness drops to ~0.5.
So real token novelty (distribution-level) never crosses gnov > 0.65.

Hypothesis: the common-mode is the blocker. A trigger that projects it OUT before
measuring novelty should (a) make the regimes separate, (b) let Fix 2 engage on real
tokens, (c) finally expose the real-token manip cost (testing whether the mock's 14%
at gain 0.5 was an artifact of PERFECT orthogonality).

Conditions (live generator, eval, dim 256, real VOCAB_A->VOCAB_B):
  OFF              : governor disabled (RIGID baseline)
  ON standard      : gnov = 1-|cos(out, field)|                    (expect DORMANT)
  ON common-mode   : gnov = 1-|cos(perp(out), perp(field))|, perp removes common-mode c
                     (expect ENGAGED if hypothesis holds)
Plus a target sweep on the common-mode trigger if it engages.

Common-mode c = unit(mean generator output over a broad token sample). perp(v)=unit(v-(v.c)c).
The blend (gain attenuation) operates on the FULL vectors; only the TRIGGER changes.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations
import logging, random
import numpy as np
logging.disable(logging.CRITICAL)
from tests._common import build_full_stack
from cognition.reflective_loop import ReflectionResult
from cognition.reflective_loop_governor import ReflectiveLoopGovernor

DIM = 256; WARMUP = 100; PHASE = 250; N_SRC = 4; SEED = 11
VOCAB_A = ["resonance","witness","anchor","coherence","field","bond","crystal","lantern"]
VOCAB_B = ["glacier","tariff","mitochondria","saxophone","asphalt","quark","plankton","ledger"]

def _unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v); return v/n if n > 1e-12 else v
def _cos(a, b): return float(np.dot(_unit(a), _unit(b)))

def _eval_stack():
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, govn, ve = build_full_stack(dim=DIM)
    gen.eval(); cycle.rec_attn.eval()
    return gen, cycle

def _common_mode(gen):
    sample = [f"tok_{i}" for i in range(64)] + VOCAB_A + VOCAB_B
    vs = [gen.generate([w]) for w in sample]
    return _unit(np.mean([_unit(v) for v in vs], axis=0))

def _perp(v, c):
    v = np.asarray(v, float); return _unit(v - float(np.dot(v, c)) * c)

def _regime_sep(gen, c):
    A = _unit(np.mean([_unit(gen.generate([w])) for w in VOCAB_A], axis=0))
    B = _unit(np.mean([_unit(gen.generate([w])) for w in VOCAB_B], axis=0))
    return _cos(A, B), _cos(_perp(A, c), _perp(B, c)), B

def _attach(cycle, gov, B_dir, c, mode, enabled):
    """mode: 'std' or 'perp' gnov. enabled: apply gain blend."""
    ctrl = {"gn_done": True, "manip_cur": False, "manip_prev": False, "manip_steps": 0,
            "src": None, "rec": [], "inj_n": 0, "inj_cB": 0.0, "inj_on": False}
    og = cycle.generator.generate; orf = cycle.reflector.reflect
    om = cycle.governance.handle_manipulation_signals; oi = cycle.field.inject

    def gen(*a, **k):
        out = og(*a, **k)
        if not ctrl["gn_done"]:
            ctrl["gn_done"] = True
            fd = cycle.field.field
            if mode == "perp":
                gn = 1.0 - abs(_cos(_perp(out, c), _perp(fd, c)))
            else:
                gn = 1.0 - abs(_cos(out, fd))
            gov.observe(gn, ctrl["src"])
            g = gov.update(manip_active=ctrl["manip_prev"],
                           attractor_count=len(cycle.attractor.centers))
            ctrl["rec"].append((gn, ctrl["src"], g, gov.loosening))
        return out

    def reflect(vec, **k):
        r = orf(vec, **k)
        if not enabled or gov.gain >= 1.0:
            return r
        g = gov.gain
        bl = _unit((1.0 - g) * np.asarray(vec, float) + g * np.asarray(r.vector, float))
        return ReflectionResult(vector=bl.astype(np.float32), passes=r.passes,
                                converged=r.converged, final_coherence=r.final_coherence,
                                delta_trace=r.delta_trace)

    def manip(signals, *a, **k):
        ctrl["manip_cur"] = True; ctrl["manip_steps"] += 1
        return om(signals, *a, **k)

    def inject(vec, strength=1.0):
        if ctrl["inj_on"]:
            ctrl["inj_n"] += 1; ctrl["inj_cB"] += _cos(vec, B_dir)
        return oi(vec, strength)

    cycle.generator.generate = gen
    if enabled:
        cycle.reflector.reflect = reflect
    cycle.governance.handle_manipulation_signals = manip
    cycle.field.inject = inject

    def reset(src):
        ctrl["manip_prev"] = ctrl["manip_cur"]; ctrl["manip_cur"] = False
        ctrl["gn_done"] = False; ctrl["src"] = src
    ctrl["reset"] = reset
    return ctrl

def run(mode, enabled, phase_mode, c, B_dir, target=0.50):
    gen, cycle = _eval_stack()
    gov = ReflectiveLoopGovernor(gain_target=target, gain_floor=min(0.45, target))
    ctrl = _attach(cycle, gov, B_dir, c, mode, enabled)
    sp = [f"src_{i}" for i in range(N_SRC)]
    for t in range(WARMUP):
        ctrl["reset"](sp[t % N_SRC])
        cycle.step(random.sample(VOCAB_A, 3), source_id=sp[t % N_SRC], origin_type="internal")
    center = cycle.field.field.copy()
    ctrl["inj_on"] = True
    for t in range(PHASE):
        ctrl["reset"](sp[t % N_SRC])
        toks = random.sample(VOCAB_A if phase_mode == "A" else VOCAB_B, 3)
        cycle.step(toks, source_id=sp[t % N_SRC], origin_type="internal")
    rec = ctrl["rec"][-PHASE:]
    return {"disp": 1.0 - _cos(cycle.field.field, center),
            "gnov": float(np.mean([r[0] for r in rec])) if rec else 0.0,
            "loosen": float(np.mean([1.0 if r[3] else 0.0 for r in rec])) if rec else 0.0,
            "manip": ctrl["manip_steps"] / max(1, WARMUP + PHASE),
            "cosB": ctrl["inj_cB"] / max(1, ctrl["inj_n"])}

def main():
    print("#" * 92)
    print("  FIX-2 COMMON-MODE TRIGGER — does projecting out the generator's shared axis")
    print("  let real token novelty engage Fix 2? (live generator, eval, dim 256)")
    print("#" * 92)
    gen, _ = _eval_stack()
    c = _common_mode(gen)
    sep, sep_perp, B_dir = _regime_sep(gen, c)
    print(f"\n  regime sep cos(A,B): raw = {sep:+.3f}   common-mode-removed = {sep_perp:+.3f}")
    print(f"  -> common-mode removal {'SEPARATES' if sep_perp < 0.70 else 'does NOT separate'} "
          f"the regimes (threshold 0.70)")

    a_ctrl = run("std", False, "A", c, B_dir)
    off    = run("std", False, "B", c, B_dir)
    on_std = run("std", True,  "B", c, B_dir)
    on_perp= run("perp", True, "B", c, B_dir)

    def line(name, r):
        m = r["disp"] - a_ctrl["disp"]
        print(f"  {name:<22}{r['gnov']:>7.3f}{r['loosen']:>9.0%}{m:>+11.3f}"
              f"{r['cosB']:>+13.3f}{r['manip']:>8.0%}")
        return m
    print(f"\n  {'condition':<22}{'gnov':>7}{'loosen%':>9}{'migration':>11}{'landed cosB':>13}{'manip%':>8}")
    line("OFF (RIGID)", off)
    line("ON std-trigger", on_std)
    m_perp = line("ON common-mode trig", on_perp)

    engaged = on_perp["loosen"] > 0.05
    if engaged:
        print("\n  TARGET SWEEP (common-mode trigger, dim 256, real tokens):")
        print(f"  {'target':>8}{'loosen%':>9}{'migration':>11}{'landed cosB':>13}{'manip%':>8}")
        for tg in (0.50, 0.60, 0.70):
            r = run("perp", True, "B", c, B_dir, target=tg)
            m = r["disp"] - a_ctrl["disp"]
            print(f"  {tg:>8.2f}{r['loosen']:>9.0%}{m:>+11.3f}{r['cosB']:>+13.3f}{r['manip']:>8.0%}")

    print("\n" + "#" * 92)
    print("  READ: if common-mode trigger engages (loosen>0) and recovers migration with")
    print("  manip% well below the mock's 14%, then (1) Fix 2's trigger should project out")
    print("  the common-mode, and (2) the mock's manip cost WAS an orthogonality artifact.")
    print("#" * 92)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
