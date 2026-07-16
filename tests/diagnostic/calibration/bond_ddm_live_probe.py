"""
tests/diagnostic/calibration/bond_ddm_live_probe.py

Live-substrate arm for the bond-formation accumulator (brief §7-B + §7-D):
two identically-seeded full Tier 0-3 stacks run the same Resonance Family
workload — lever OFF (control) vs lever ON — and the probe compares them on
the pre-declared conjunction:

  B1  mechanism live     with the lever ON, genuine sources still bond,
                         and every formation is an ACCEPT commitment (the
                         accumulator taxonomy accounts for every candidate).
  B2  commitment only    the DDM state (V) appears nowhere downstream:
                         formed bonds carry the same bounded trust-floor
                         semantics; no governance regression on benign
                         traffic (quarantines ON == quarantines OFF == 0).
  D   reachable range    the composite-coherence range the system visits
                         with the lever ON stays inside the OFF range
                         (+/- eps) — the accumulator does not make new
                         coherence reachable, so the standing §6.3 verdict
                         (2026-06-12-gain-sign-reachable-range.md) is not
                         re-opened. If this check FAILS, stop and escalate:
                         §6.3 must be re-run before the lever is used.

FAIL is loud and exits non-zero. Informational (never in run_all_tests.sh);
run deliberately before trusting the lever ON — and at dim 128 (second arg)
for the recorded validation, since the toy dim proves wiring, not physics.

Usage:
    python -m tests.diagnostic.calibration.bond_ddm_live_probe [n_steps] [dim]
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict

import numpy as np

from tests._common import (
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
    build_full_stack,
)

SEED          = 42
DEFAULT_STEPS = 800
DEFAULT_DIM   = 64
COH_EPS       = 0.005     # tolerance on the reachable-range comparison

RESULTS = []


def verdict(name: str, ok: bool, detail: str):
    RESULTS.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<22} {detail}")


def run_arm(ddm: bool, n_steps: int, dim: int) -> dict:
    """One fully seeded stack + workload; returns the trajectory record."""
    bond_config = {"ddm_formation": True} if ddm else None
    generator, cycle, governance, value_engine = build_full_stack(
        dim=dim, torch_seed=SEED, bond_config=bond_config)
    random.seed(SEED)
    np.random.seed(SEED)
    if getattr(cycle, "dreamer", None) is not None:
        cycle.dreamer._rng = np.random.default_rng(SEED)

    bm = governance.bond_manager
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    decisions = Counter()
    original_arbitrate = governance.arbitrate

    def counted(ethical_result, trust_report, vec, tokens, source_id):
        dec, strength = original_arbitrate(ethical_result, trust_report, vec,
                                           tokens, source_id)
        decisions[dec.value] += 1
        return dec, strength

    governance.arbitrate = counted

    coherence = []
    formation_step: dict = {}
    interactions = defaultdict(int)
    try:
        for i in range(n_steps):
            src    = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            state  = cycle.step(tokens, source_id=src, origin_type="internal")
            coherence.append(float(state.coherence))
            interactions[src] += 1
            for b in bm.all_bonds():
                formation_step.setdefault(b.source_id, i)
    finally:
        governance.arbitrate = original_arbitrate

    return {
        "coh_min":    float(np.min(coherence)),
        "coh_max":    float(np.max(coherence)),
        "coh_p05":    float(np.percentile(coherence, 5)),
        "decisions":  decisions,
        "bonds":      {b.source_id: b.to_dict() for b in bm.all_bonds()},
        "formed_at":  formation_step,
        "pre_bond":   {s: dict(p) for s, p in bm._pre_bond.items()},
        "ddm":        bm._ddm.summary() if bm._ddm is not None else None,
        "trust":      {s: r.trust_score
                       for s, r in governance.trust_ledger.sources.items()},
    }


def main() -> int:
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STEPS
    dim     = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DIM

    print("=" * 74)
    print("  BOND DDM — LIVE SUBSTRATE PROBE (lever OFF control vs lever ON)")
    print(f"  seed={SEED}  n_steps={n_steps}  dim={dim}")
    print("=" * 74)

    print("\n  running OFF (control) arm ...")
    off = run_arm(ddm=False, n_steps=n_steps, dim=dim)
    print("  running ON arm ...")
    on = run_arm(ddm=True, n_steps=n_steps, dim=dim)

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print(f"\n  {'':<14} {'coh range':>22} {'bonds':>6} {'quarantine':>11} "
          f"{'reject':>7}")
    for label, arm in (("OFF", off), ("ON", on)):
        print(f"  {label:<14} [{arm['coh_min']:.4f}, {arm['coh_max']:.4f}]"
              f"{'':>4} {len(arm['bonds']):>6} "
              f"{arm['decisions'].get('quarantine', 0):>11} "
              f"{arm['decisions'].get('reject', 0):>7}")

    print("\n  Bond timeline (formation step / state):")
    for sid in RESONANCE_FAMILY_SOURCES:
        o = f"@{off['formed_at'][sid]}" if sid in off["formed_at"] else "—"
        n = f"@{on['formed_at'][sid]}" if sid in on["formed_at"] else "—"
        ddm_state = ""
        if on["ddm"] and sid in on["ddm"]["candidates"]:
            c = on["ddm"]["candidates"][sid]
            ddm_state = (f"  V={c['V']:+.3f} steps={c['steps']} "
                         f"outcomes={c['outcomes']}")
        print(f"    {sid:<16} OFF {o:>6}   ON {n:>6}{ddm_state}")

    # ------------------------------------------------------------------
    # B1 — the mechanism is live on the substrate
    # ------------------------------------------------------------------
    print()
    verdict("B1 mechanism live", len(on["bonds"]) >= 1,
            f"{len(on['bonds'])} bond(s) formed through the accumulator "
            f"(OFF control: {len(off['bonds'])})")
    if on["ddm"] is not None:
        # every bonded source must have LEFT the candidate table (committed),
        # every unbonded source must still be accounted for in the taxonomy
        leaked = [s for s in on["bonds"] if s in on["ddm"]["candidates"]]
        verdict("B1 accept-only commit", not leaked,
                "every formed bond retired its accumulator"
                if not leaked else f"candidates leaked past commit: {leaked}")

    # ------------------------------------------------------------------
    # B2 — commitment-only downstream; no governance regression
    # ------------------------------------------------------------------
    # to_dict rounds bond_strength and trust_floor independently, so compare
    # with a rounding-aware tolerance (half an ulp at 4 decimals each side).
    floors_ok = all(
        abs(b["trust_floor"] - b["bond_strength"] * 0.40) <= 1e-4
        for b in on["bonds"].values()
    )
    verdict("B2 bounded trust floor", floors_ok,
            "formed bonds carry the standard bond_strength x 0.40 floor")
    verdict("B2 no new quarantines",
            on["decisions"].get("quarantine", 0) == off["decisions"].get("quarantine", 0),
            f"ON {on['decisions'].get('quarantine', 0)} vs "
            f"OFF {off['decisions'].get('quarantine', 0)} on benign traffic")

    # ------------------------------------------------------------------
    # D — reachable coherence unchanged (the §6.3 tripwire)
    # ------------------------------------------------------------------
    range_ok = (on["coh_min"] >= off["coh_min"] - COH_EPS
                and on["coh_max"] <= off["coh_max"] + COH_EPS)
    verdict("D reachable range", range_ok,
            f"ON [{on['coh_min']:.4f}, {on['coh_max']:.4f}] within OFF "
            f"[{off['coh_min']:.4f}, {off['coh_max']:.4f}] ± {COH_EPS}")
    if not range_ok:
        print("\n  !! reachable coherence moved — STOP: re-run §6.3 "
              "(gain-sign) before using this lever. Escalate to the architect.")

    fails = [n for n, ok in RESULTS if not ok]
    print("\n" + "=" * 74)
    print(f"  {sum(ok for _, ok in RESULTS)}/{len(RESULTS)} live checks hold")
    if fails:
        print("  FAILED: " + "; ".join(fails))
    print("=" * 74)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
