"""
tests/diagnostic/lockin/reconstruction_ablation_probe.py

Step 2-followup of the attractor-mobility arc: the migration probe found the field
RIGID because every injection path lands the ESTABLISHED regime (cos≈0.72 to A)
regardless of input. This probe isolates WHICH re-injection path does the
reconstituting — the remediation-target search — as a one-variable ablation against
the known-RIGID baseline.

Decomposition (attractor_migration_probe + per-caller attribution) found three
injectors, ~1/step each, all landing A-heavy / B-starved while the generator emits
B at cos≈0.95:
    step              main expression inject (chorus.harmonize → rec_attn.refine)  cos·B 0.19
    _activate_crystal crystal re-injection of the crystallized A vector            cos·B 0.11
    _explore_behavior inject_ambiguity(witness anchor) — mutated identity anchor   cos·B 0.17

Ablations (each suppresses one real path; clean hooks, no substrate edit). The
candidate set was corrected by TRACING the vec pipeline (generate → attractor.pull
→ refine → reflective-loop → inject) rather than guessing: the dominant locker is
the **reflective loop** (step 6, `reflector.reflect`), which in reflect/explore
rhythm iteratively pulls the expression vector to the anchor/attractor (A) before
injection — it was not in the original four candidates; the trace found it.
    no_reflect   reflector.reflect → passthrough (the deliberate-recursion loop)
    no_attractor attractor.pull (line 342) → identity
    blend_raw    rec_attn.diversity_blend = 1.0   → main inject = raw, no refine-blend
    no_crystal   crystal_store.field_injection_strength = 0.0 → crystal re-inject inert
    no_explore   _explore_behavior → no-op        → no mutated-anchor re-inject
    all          all three at once

Readout reuses the migration metric: warmup on A (multi-source, HHI<0.70), then a
persistent gate-surviving coherent new regime B; migration = disp(coherent) −
drift(control). Per-caller landed cos·B is reported so we SEE which path starts
carrying B when freed.

PRE-DECLARED SIGNATURES (discipline #4 — success AND failure, before the run)
----------------------------------------------------------------------------
Baseline must reproduce RIGID (disp ≈ 0.01); control drift ≈ 0.001. Then per ablation:
  LOCKER (this path): with it suppressed, migration > 0.10 AND coherent landed cos·B
      rises materially → this path was (a substantial part of) the lock; it is the
      remediation lever.
  NOT-THE-LEVER: disp ≈ baseline (< 0.10), landed cos·B ≈ baseline → suppressing
      this path alone does not free the attractor.
  DISTRIBUTED: only `all` crosses 0.10 → no single path is the lock; the three
      re-inject the shared A-context and any one alone is swamped by the other two.
      Remediation must address the context, not one path.
  CONTEXT-DEEPER (alarm/failure): even `all` stays RIGID (< 0.10) → the lock is NOT
      the re-injection CONTENT but the field context the surviving paths read (the
      anchor/history that chorus + refine attend to, or the raw moat magnitude).
      Routes to a different fix than any of these knobs.
  INSTRUMENT-LIE (alarm): an ablation gives byte-identical disp/landed to baseline →
      the hook didn't take effect; fix the probe before trusting any verdict. (Same
      reflex as the deque-energy catch in the migration probe.)

Informational. exit 0. NEVER in run_all_tests.sh (discipline #3).
"""
import sys
import logging
import random
import inspect
import types
from collections import defaultdict

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack  # noqa: E402

DIM    = 64
WARMUP = 200
PHASE  = 700        # ≫ field decay t½≈138
N_SRC  = 4          # HHI ≈ 0.25
NOISE  = 0.05
SEED   = 11


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def _apply_ablation(cycle, name):
    applied = []
    if name in ("no_reflect", "all"):
        # The reflective loop (step 6) iteratively pulls vec → anchor/attractor (A)
        # before injection — the dominant reconstitution. Pass vec through untouched.
        cycle.reflector.reflect = lambda vec, watcher=None, anchor=None, field=None, \
            attractor=None, generator=None: types.SimpleNamespace(
                vector=vec, passes=0, converged=False)
        applied.append("reflect=off")
    if name in ("no_attractor", "all"):
        cycle.attractor.pull = lambda vec, generator=None: vec   # line 342, before refine
        applied.append("attractor=off")
    if name in ("blend_raw", "all"):
        cycle.rec_attn.diversity_blend = 1.0
        applied.append("blend=raw")
    if name in ("no_crystal", "all"):
        cycle.crystal_store.field_injection_strength = 0.0
        applied.append("crystal=0")
    if name in ("no_explore", "all"):
        cycle._explore_behavior = lambda tokens: None
        applied.append("explore=noop")
    return applied


def run(ablation, mode, A, B, use_chorus=True):
    """mode 'A' = control (continue A, non-novel); 'B' = coherent novelty.
    use_chorus=False makes the explore main-injection the raw generator output (B)
    rather than chorus.harmonize(B against the field) — isolating the self-reference
    of the chorus from the raw magnitude moat."""
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(dim=DIM, use_chorus=use_chorus)
    field = cycle.field
    rng = np.random.default_rng(SEED + 2)

    applied = _apply_ablation(cycle, ablation)   # before warmup

    holder = {"mode": "A"}

    def gen_fn(tokens, token_class=None):
        tgt = A if holder["mode"] == "A" else B
        return _unit(tgt + NOISE * rng.standard_normal(DIM))
    cycle.generator.generate = gen_fn
    sources = [f"src_{i}" for i in range(N_SRC)]

    rec = {"on": False}
    per = defaultdict(lambda: [0, 0.0, 0.0])      # caller -> [n, sumcosA, sumcosB]
    orig_inject = field.inject

    def _inject(vec, strength=1.0):
        if rec["on"]:
            caller = inspect.stack()[1].function
            s = per[caller]; s[0] += 1; s[1] += _cos(vec, A); s[2] += _cos(vec, B)
        return orig_inject(vec, strength)
    field.inject = _inject

    for t in range(WARMUP):
        holder["mode"] = "A"
        cycle.step(tokens=[f"a_{t % 8}"], source_id=sources[t % N_SRC], origin_type="internal")
    center_warm = field.field.copy()

    rec["on"] = True
    holder["mode"] = mode
    for t in range(PHASE):
        tok = f"a_{t % 8}" if mode == "A" else f"b_{t % 8}"
        cycle.step(tokens=[tok], source_id=sources[t % N_SRC], origin_type="internal")

    n = sum(v[0] for v in per.values()) or 1
    d_end = field.field
    return {
        "disp":        1.0 - _cos(d_end, center_warm),
        "cosB_end":    _cos(d_end, B),
        "landed_cosB": sum(v[2] for v in per.values()) / n,
        "injps":       n / PHASE,
        "applied":     applied,
        "per":         {k: (v[0] / PHASE, v[1] / v[0], v[2] / v[0]) for k, v in per.items()},
    }


def main():
    print("=" * 84)
    print("  RECONSTRUCTION ABLATION — which re-injection path locks the attractor?")
    print("=" * 84)
    print(f"  dim={DIM} warmup={WARMUP} phase={PHASE} sources={N_SRC} (HHI≈0.25) seed={SEED}")

    rng = np.random.default_rng(SEED)
    A = _unit(rng.standard_normal(DIM))
    B0 = rng.standard_normal(DIM)
    B = _unit(B0 - np.dot(B0, A) * A)

    control = run("none", "A", A, B)
    drift = control["disp"]
    print(f"\n  CONTROL drift (continue A, no ablation): disp={drift:.3f}")

    results = {}
    for ab in ("none", "no_reflect", "no_attractor", "blend_raw", "no_crystal", "no_explore", "all"):
        r = run(ab, "B", A, B)
        results[ab] = r
        mig = r["disp"] - drift
        tag = "baseline RIGID" if ab == "none" else "+".join(r["applied"])
        print(f"\n  [{ab}]  {tag}")
        print(f"      disp={r['disp']:.3f}  migration={mig:+.3f}  cosB_end={r['cosB_end']:+.3f}  "
              f"landed cos·B={r['landed_cosB']:+.3f}  injects/step={r['injps']:.1f}")
        print(f"      per-path (calls/step, cos·A, cos·B):")
        for caller, (cps, ca, cb) in sorted(r["per"].items(), key=lambda x: -x[1][0]):
            print(f"        {caller:<20} {cps:>4.1f}  A={ca:+.3f}  B={cb:+.3f}")

    # DECISIVE: bypass chorus (raw B main inject) + all else off → only pure B enters.
    # A bare decaying accumulator MUST migrate; if it doesn't, a magnitude floor remains.
    pb = run("all", "B", A, B, use_chorus=False)
    results["pure_b"] = pb
    print(f"\n  [pure_b]  use_chorus=False + {'+'.join(pb['applied'])} (only raw B enters)")
    print(f"      disp={pb['disp']:.3f}  migration={pb['disp']-drift:+.3f}  "
          f"cosB_end={pb['cosB_end']:+.3f}  landed cos·B={pb['landed_cosB']:+.3f}  "
          f"injects/step={pb['injps']:.1f}")
    for caller, (cps, ca, cb) in sorted(pb["per"].items(), key=lambda x: -x[1][0]):
        print(f"        {caller:<20} {cps:>4.1f}  A={ca:+.3f}  B={cb:+.3f}")

    # ---- VERDICT -------------------------------------------------------
    print("\n" + "-" * 84)
    base = results["none"]["disp"] - drift
    singles = {ab: results[ab]["disp"] - drift
               for ab in ("no_reflect", "no_attractor", "blend_raw", "no_crystal", "no_explore")}
    allmig = results["all"]["disp"] - drift
    print(f"  VERDICT  baseline migration={base:+.3f}  "
          + "  ".join(f"{ab}={m:+.3f}" for ab, m in singles.items())
          + f"  all={allmig:+.3f}")

    if abs(base) >= 0.10:
        print("  → SANITY FAIL: baseline did not reproduce RIGID; do not trust the ablations.")
    else:
        levers = [ab for ab, m in singles.items() if m > 0.10]
        if levers:
            for ab in levers:
                print(f"  → LEVER: suppressing '{ab}' frees migration ({singles[ab]:+.3f}) — "
                      f"this path is (part of) the lock and is the remediation target.")
        elif allmig > 0.10:
            print("  → DISTRIBUTED: no single path frees it, but ALL together does")
            print(f"    (all={allmig:+.3f}). The three re-inject the shared A-context; any one")
            print("    alone is swamped by the other two. Remediation must address them jointly.")
        else:
            pbmig = results["pure_b"]["disp"] - drift
            print(f"  → CONTEXT-DEEPER: no in-stack ablation frees it (all={allmig:+.3f}).")
            if pbmig > 0.10:
                print("  → SELF-REFERENCE IS THE LOCK: but bypassing chorus so ONLY raw B enters")
                print(f"    DOES migrate (pure_b={pbmig:+.3f}, landed cos·B="
                      f"{results['pure_b']['landed_cosB']:+.3f}). The lock is the field's")
                print("    self-reference: every expression path reads the established state")
                print("    (chorus↔field, refine↔history, explore↔anchor, crystal↔stored) and")
                print("    reconstitutes it. The bare accumulator is PLASTIC; the machinery pins it.")
                print("    Remediation lever: decouple the main injection from the field it reads")
                print("    (chorus harmonizes against current field), not any single re-inject path.")
            else:
                print(f"  → MAGNITUDE FLOOR: even pure-B injection with all reconstitution off stays")
                print(f"    RIGID (pure_b={pbmig:+.3f}, landed cos·B="
                      f"{results['pure_b']['landed_cosB']:+.3f}). The moat magnitude itself resists")
                print("    rotation; the lock is below the expression machinery, in the")
                print("    accumulate-decay field. Routes to a field-side (paper-boat) fix.")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    sys.exit(main())
