"""
tests/diagnostic/lockin/rupture_impulse_probe.py

Phase-1.1 impulse-response probe for the RUPTURE rhythm (inject-only, mode A).

Chicken-and-egg escape (open-loop before closed-loop): we cannot set rupture's
sensor-based release threshold before we know its impulse response, so we run
rupture BLIND with a fixed N-cycle cap, log the per-cycle telemetry, and read the
real recovery curve off the result.

Phase 1.1 change (why v1 was void): v1 built a dim-64 TEST harness with an
UNTRAINED generator, so the upstream stethoscopes read the generator's own
randomness ("structureless") and never saw a field lock — the fixture was broken,
not the behavior. This version builds the ENTIRE trained system through
`recursion1188.build_engine()` (production dim, corpus pretrain ON, all graduated
levers, governance + value engine attached), so the instruments read the real
dynamics. It also adds a DIRECT field-displacement readout that does not depend on
the generator being trained.

Manufactures a LOCKED field (warmup on a single convergent regime), then compares
two arms from that locked state:

  control   normal loop only          — the baseline the loop does on its own.
  rupture   + N=3 inject-only pulses, then auto-release into stabilize.

Both arms run identical `cycle.step()` (which fires the normal rhythm behaviors);
only rupture ALSO calls `_rupture_behavior`. So every metric is read as
rupture-MINUS-control, which cancels whatever the normal loop (and its
uncontrolled inject_ambiguity RNG) does on its own.

Readouts per cycle (all three matter):
  PERTURB   field displacement  1 - cos(field, locked_center)  [direct, training-
            independent] -> did the pulse actually move the field off its lock?
  RECOVER   generator/expression metastability + regime_state  [production
            stethoscopes] -> did the loop's own instrument register de-locking?
  COST      attractor + crystal population, manip-signal rate -> did it de-lock by
            DISSOLVING identity? (cost-probe band: manip ~0, attractors <=~11)

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import sys
import copy
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from loop.recursion1188 import build_engine, CONFIG          # noqa: E402  (real boot)

WARMUP   = 150
N_PULSE  = 3          # the Phase-1 hard cap (blind timer, no sensor yet)
N_SETTLE = 6          # release-into-stabilize observation window
SEEDS    = (11, 23, 42)
LOCK_TOKENS = ["anchor", "ground", "steady"]   # convergent input -> over-coherence


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def _read(cycle, manip, center, label):
    def rd(mon):
        if mon is None:
            return float("nan"), "n/a"
        r = mon.compute_now()
        return float(r.metastability), r.regime_state
    gm, gs = rd(cycle.generator_metastability)
    em, es = rd(cycle.expression_metastability)
    return {
        "label": label,
        "disp":  1.0 - _cos(cycle.field.field, center),
        "gen_m": gm, "gen_s": gs,
        "exp_m": em, "exp_s": es,
        "attr":  len(cycle.attractor.centers),
        "cryst": len(cycle.crystal_store.crystals),
        "manip": manip["signals"],
    }


def run(arm, seed):
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)

    # THE ENTIRE SYSTEM: trained (corpus pretrain), production dim, all levers.
    cfg = copy.deepcopy(CONFIG)
    gen, cycle, gov, ve = build_engine(cfg)

    manip = {"signals": 0}
    _detect = gov.resistance.detect

    def _counted():
        sigs = _detect()
        if sigs:
            manip["signals"] += len(sigs)
        return sigs
    gov.resistance.detect = _counted

    src = "src_lock"
    for _ in range(WARMUP):                       # convergent input -> lock
        cycle.step(tokens=LOCK_TOKENS, source_id=src, origin_type="internal")

    center = cycle.field.field.copy()             # the locked center (disp origin)
    manip["signals"] = 0                          # count only the measured window
    series = [_read(cycle, manip, center, "lock")]

    for t in range(N_PULSE):
        cycle.step(tokens=LOCK_TOKENS, source_id=src, origin_type="internal")
        if arm == "rupture":
            cycle._rupture_behavior(LOCK_TOKENS)      # ONE disruptive pulse
        series.append(_read(cycle, manip, center, f"pulse{t + 1}"))

    for t in range(N_SETTLE):
        cycle.step(tokens=LOCK_TOKENS, source_id=src, origin_type="internal")
        if arm == "rupture":
            cycle._stabilize_behavior()               # auto-release INTO stabilize
        series.append(_read(cycle, manip, center, f"settle{t + 1}"))

    return series


def _avg(all_series):
    out = []
    for i in range(len(all_series[0])):
        rows = [s[i] for s in all_series]
        out.append({
            "label": rows[0]["label"],
            "disp":  float(np.mean([r["disp"]  for r in rows])),
            "gen_m": float(np.nanmean([r["gen_m"] for r in rows])),
            "exp_m": float(np.nanmean([r["exp_m"] for r in rows])),
            "attr":  float(np.mean([r["attr"]  for r in rows])),
            "cryst": float(np.mean([r["cryst"] for r in rows])),
            "manip": float(np.mean([r["manip"] for r in rows])),
            "gen_s": rows[0]["gen_s"],
        })
    return out


def _print_arm(name, avg):
    print(f"\n  --- {name} ---")
    print(f"    {'cycle':8} {'disp':>7} {'gen_meta':>9} {'exp_meta':>9} "
          f"{'attr':>6} {'cryst':>6} {'manip':>6}  gen_state")
    for r in avg:
        print(f"    {r['label']:8} {r['disp']:7.3f} {r['gen_m']:9.3f} {r['exp_m']:9.3f} "
              f"{r['attr']:6.1f} {r['cryst']:6.1f} {r['manip']:6.1f}  {r['gen_s']}")


def main():
    print("=" * 88)
    print("  RUPTURE IMPULSE PROBE — Phase 1.1 (inject-only, mode A, ENTIRE trained system)")
    print("=" * 88)
    print(f"  build_engine: dim={CONFIG['dim']} pretrain_on_corpus={CONFIG['pretrain_on_corpus']} "
          f"epochs={CONFIG['pretrain_epochs']} reflect_atten={CONFIG['reflect_novelty_attenuation']}")
    print(f"  warmup={WARMUP} pulse={N_PULSE} settle={N_SETTLE} seeds={SEEDS}")

    ctrl = [run("control", s) for s in SEEDS]
    rupt = [run("rupture", s) for s in SEEDS]
    ca, ra = _avg(ctrl), _avg(rupt)

    _print_arm("CONTROL  (locked, normal loop only)", ca)
    _print_arm("RUPTURE  (N=3 inject-only, release -> stabilize)", ra)

    locked = ("locked" in (ca[0]["gen_s"], ra[0]["gen_s"])) or (ca[0]["gen_m"] < 0.15)
    pw = slice(1, 1 + N_PULSE)
    perturb   = max(r["disp"] for r in ra[pw]) - max(r["disp"] for r in ca[pw])
    recover   = max(r["gen_m"] for r in ra[pw]) - max(r["gen_m"] for r in ca[pw])
    cryst_d   = min(r["cryst"] for r in ra) - min(r["cryst"] for r in ca)
    attr_d    = max(r["attr"] for r in ra) - max(r["attr"] for r in ca)
    manip_d   = max(r["manip"] for r in ra) - max(r["manip"] for r in ca)

    print("\n" + "-" * 88)
    print(f"  fixture locked?  (gen_state=='locked' or gen_meta<0.15 at baseline): {locked}")
    print(f"  PERTURB : rupture moved field {perturb:+.3f} MORE than control (peak disp, pulse window)")
    print(f"  RECOVER : rupture gen_meta {recover:+.3f} vs control (stethoscope de-lock signal)")
    print(f"  COST    : crystals {cryst_d:+.1f}  attractors {attr_d:+.1f}  manip {manip_d:+.1f}  (rupture - control)")

    if not locked:
        print("\n  SANITY: fixture did NOT read as locked — verdict WITHHELD; the warmup")
        print("          must establish a lock before rupture's effect means anything.")
        print("=" * 88)
        return 0

    broke  = perturb > 0.05
    costly = (cryst_d < -0.5) or (attr_d > 3.0) or (manip_d > 3.0)
    if broke and not costly:
        v = "PHASE 1 GREEN — inject-only perturbs the locked field at acceptable identity cost; pin release off the disp/recovery curve."
    elif broke and costly:
        v = "BREAKS LOCK BUT COSTLY — inject-only moves the field but at identity cost; tune scale/strength DOWN before pinning threshold."
    else:
        v = "INJECT-ONLY TOO WEAK — field barely moved vs control; forcing function for Phase 2 (mode B: bounded attenuation reach)."
    print(f"\n  VERDICT: {v}")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(main())
