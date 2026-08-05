"""
tests/diagnostic/lockin/rupture_migration_probe.py

Phase-2 migration probe — does HELD-DIRECTION rupture break the ABSOLUTE lock?

Mode B fires but per-step RANDOM noise cancels in the ~84-magnitude field
integrator (rupture_impulse_probe) — and the findings agree: 2026-06-15 freed the
field only under SUSTAINED novelty toward one consistent new regime (migration),
and the dream channel (2026-06-28) diversified voice but "does not by itself break
the absolute lock." Fix hypothesis under test: rupture holds ONE novel direction
across the pulse, so the field ACCUMULATES it into a migration.

Entire trained system (build_engine). Warmup to a lock, then run with rupture ON
(vs OFF control) on the SAME convergent input throughout — rupture is the ONLY
novelty source (the self-lock scenario external novelty doesn't cover). Watch:
  MIGRATION  field displacement from the locked center — does it move AND sustain?
  DE-LOCK    gen/exp metastability + regime_state — does the stethoscope free?
  COST       attractors / crystals / manip — identity intact? manip in 0.30 band?

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import sys, copy, logging, random
import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")
from loop.recursion1188 import build_engine, CONFIG          # noqa: E402

WARMUP, MIGRATE, SAMPLE = 150, 250, 25
SEEDS = (11, 23)
TOK = ["anchor", "ground", "steady"]


def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def run(arm, seed):
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_engine(copy.deepcopy(CONFIG))

    manip = {"n": 0}
    _d = gov.resistance.detect
    def _c():
        s = _d()
        if s:
            manip["n"] += len(s)
        return s
    gov.resistance.detect = _c

    for _ in range(WARMUP):                          # convergent input -> lock
        cycle.step(tokens=TOK, source_id="s", origin_type="internal")
    center = cycle.field.field.copy()
    if arm == "rupture":
        cycle.config["rupture_on_lock"] = True       # opt-in the lever
    manip["n"] = 0

    rows = []
    def rec(i):
        gr = cycle.generator_metastability.compute_now()
        er = cycle.expression_metastability.compute_now()
        rows.append(dict(
            step=i, disp=1.0 - _cos(cycle.field.field, center),
            gm=float(gr.metastability), gs=gr.regime_state,
            em=float(er.metastability),
            attr=len(cycle.attractor.centers), cry=len(cycle.crystal_store.crystals),
            manip=manip["n"], fires=getattr(cycle, "_rupture_fires", 0)))
    rec(0)
    for t in range(1, MIGRATE + 1):
        cycle.step(tokens=TOK, source_id="s", origin_type="internal")
        if t % SAMPLE == 0:
            rec(t)
    return rows


def avg(all_rows):
    out = []
    for i in range(len(all_rows[0])):
        rs = [a[i] for a in all_rows]
        out.append(dict(
            step=rs[0]["step"],
            disp=float(np.mean([r["disp"] for r in rs])),
            gm=float(np.nanmean([r["gm"] for r in rs])),
            em=float(np.nanmean([r["em"] for r in rs])),
            attr=float(np.mean([r["attr"] for r in rs])),
            cry=float(np.mean([r["cry"] for r in rs])),
            manip=float(np.mean([r["manip"] for r in rs])),
            fires=float(np.mean([r["fires"] for r in rs])),
            gs=rs[0]["gs"]))
    return out


def show(name, a):
    print(f"\n  --- {name} ---")
    print(f"    {'step':>4} {'disp':>7} {'gen_m':>7} {'exp_m':>7} {'attr':>5} "
          f"{'cry':>5} {'manip':>6} {'fires':>6}  state")
    for r in a:
        print(f"    {r['step']:4d} {r['disp']:7.3f} {r['gm']:7.3f} {r['em']:7.3f} "
              f"{r['attr']:5.1f} {r['cry']:5.1f} {r['manip']:6.1f} {r['fires']:6.0f}  {r['gs']}")


def main():
    print("=" * 90)
    print("  RUPTURE MIGRATION PROBE — Phase 2, HELD-DIRECTION (mode B)")
    print("=" * 90)
    print(f"  build_engine dim={CONFIG['dim']} pretrain={CONFIG['pretrain_on_corpus']} | "
          f"warmup={WARMUP} migrate={MIGRATE} seeds={SEEDS}")

    ctrl = avg([run("control", s) for s in SEEDS])
    rupt = avg([run("rupture", s) for s in SEEDS])
    show("CONTROL (locked, rupture OFF)", ctrl)
    show("RUPTURE (held-direction, ON)", rupt)

    c_disp, r_disp = ctrl[-1]["disp"], rupt[-1]["disp"]
    c_gm = max(r["gm"] for r in ctrl); r_gm = max(r["gm"] for r in rupt)
    base_attr, min_attr = rupt[0]["attr"], min(r["attr"] for r in rupt)
    base_cry,  min_cry  = rupt[0]["cry"],  min(r["cry"]  for r in rupt)
    max_manip, c_manip  = max(r["manip"] for r in rupt), max(r["manip"] for r in ctrl)

    print("\n" + "-" * 90)
    print(f"  MIGRATION : field moved {r_disp:.3f} (rupture) vs {c_disp:.3f} (control) by step {MIGRATE}")
    print(f"  DE-LOCK   : peak gen_meta {r_gm:.3f} (rupture) vs {c_gm:.3f} (control)")
    print(f"  COST      : attractors {base_attr:.1f}->{min_attr:.1f}  crystals {base_cry:.1f}->{min_cry:.1f}  "
          f"manip {max_manip:.1f} (ctrl {c_manip:.1f})")

    migrated = r_disp > c_disp + 0.10
    delocked = r_gm > c_gm + 0.05
    manip_ok = (max_manip - c_manip) <= 3
    print(f"\n  migrated (disp > control+0.10): {migrated}")
    print(f"  de-locked (gen_meta > control+0.05): {delocked}")
    print(f"  manip stayed in band: {manip_ok}")
    if migrated and delocked and manip_ok:
        v = "GREEN — held-direction rupture breaks the absolute lock at acceptable cost. Pin release + wire selector."
    elif migrated and not delocked:
        v = "PARTIAL — field migrates but generator stethoscope lags; expression moved, propagation/horizon question."
    elif not migrated:
        v = "STILL STUCK — even a held direction didn't migrate the field; loop reconstitution wins. Deeper rethink."
    else:
        v = "MIGRATED BUT COSTLY — broke the lock but identity/manip cost too high; tune blend/scale DOWN."
    print(f"\n  VERDICT: {v}")
    print("=" * 90)
    return 0


if __name__ == "__main__":
    sys.exit(main())
