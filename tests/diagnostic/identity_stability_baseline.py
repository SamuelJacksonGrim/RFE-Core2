"""
tests/diagnostic/identity_stability_baseline.py

Captures the **identity-stability baseline** with the reflective loop intact — the
"before" the cost probe (Phase C) measures against. The reflective loop is the lock
(`2026-06-07-reconstruction-ablation.md`); the open question is what *attenuating* it
costs identity stability. This module provides:

  - `attenuate_reflect(cycle, gain)` — the convergence-gain dial. gain=1.0 is the
    intact loop; gain<1.0 blends the loop's converged output back toward its raw
    input: vec_out = unit((1-gain)·vec_in + gain·reflect(vec_in)). gain=0.0 is the
    full ablation (passthrough). This is the single knob the cost probe sweeps.
  - `measure(reflect_gain)` — runs the canonical Resonance-Family workload (real
    generator, loop at the given gain) and returns identity-stability metrics.

Identity-stability metrics (the coherence side of the plasticity/identity tradeoff):
    coherence_mean / coherence_std  field coherence trajectory (2nd half)
    identity_stability              witness.identity_stability() at end
    anchor_velocity                 witness.anchor_velocity() (lower = steadier self)
    attractors / crystals / bonds   structural identity scaffolding counts

Run:
    python -m tests.diagnostic.identity_stability_baseline   # captures + writes JSON
Writes `tests/baselines/identity_stability_500step.json` (loop intact). Informational.
"""
from __future__ import annotations

import json
import random
import types
from pathlib import Path

import numpy as np

from tests._common import (build_full_stack, RESONANCE_FAMILY_SOURCES,
                           RESONANCE_FAMILY_WEIGHTS)

BASELINE_PATH = Path("tests/baselines/identity_stability_500step.json")
SEED = 42
N_STEPS = 500


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def attenuate_reflect(cycle, gain: float):
    """Blend the reflective loop's converged output back toward its raw input by
    `gain` (1.0 = intact loop, 0.0 = passthrough/ablated). The cost-probe dial."""
    if gain >= 1.0:
        return
    orig = cycle.reflector.reflect

    def reflect(vec, watcher=None, anchor=None, field=None, attractor=None, generator=None):
        r = orig(vec=vec, watcher=watcher, anchor=anchor, field=field,
                 attractor=attractor, generator=generator)
        blended = _unit((1.0 - gain) * np.asarray(vec, dtype=float)
                        + gain * np.asarray(r.vector, dtype=float))
        return types.SimpleNamespace(vector=blended, passes=r.passes, converged=r.converged)

    cycle.reflector.reflect = reflect


def measure(reflect_gain: float = 1.0, seed: int = SEED, n: int = N_STEPS) -> dict:
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack()
    attenuate_reflect(cycle, reflect_gain)

    # Identity cost also surfaces at the Tier-2 manipulation layer: a less-converged
    # expression can read as identity_erosion / trust_wash. Count it — the witness
    # stability scalar alone misses it.
    manip = {"steps": 0, "signals": 0}
    _detect = gov.resistance.detect

    def _counted_detect():
        sigs = _detect()
        if sigs:
            manip["steps"] += 1
            manip["signals"] += len(sigs)
        return sigs
    gov.resistance.detect = _counted_detect

    sids = list(RESONANCE_FAMILY_SOURCES)
    w = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    cohs = []
    for _ in range(n):
        src = random.choices(sids, weights=w)[0]
        toks = random.choice(RESONANCE_FAMILY_SOURCES[src])
        st = cycle.step(toks, source_id=src, origin_type="internal")
        cohs.append(st.coherence)

    half = np.array(cohs[n // 2:])    # post-warmup
    return {
        "reflect_gain":       reflect_gain,
        "coherence_mean":     round(float(half.mean()), 4),
        "coherence_std":      round(float(half.std()), 4),
        "identity_stability": round(float(cycle.witness.identity_stability()), 4),
        "anchor_velocity":    round(float(cycle.witness.anchor_velocity()), 4),
        "attractors":         len(cycle.attractor.centers),
        "crystals":           len(cycle.crystal_store.crystals),
        "bonds":              len(gov.bond_manager.all_bonds()),
        "manip_steps":        manip["steps"],          # steps that fired ≥1 manipulation signal
        "manip_signals":      manip["signals"],        # total manipulation-signal firings
    }


def main() -> int:
    print("=" * 64)
    print("  IDENTITY-STABILITY BASELINE (reflective loop intact)")
    print("=" * 64)
    m = measure(reflect_gain=1.0)
    for k, v in m.items():
        print(f"  {k:<20} {v}")
    payload = {
        "description": "Identity-stability baseline, reflective loop intact (gain=1.0). "
                       "The 'before' for the reflective-loop cost probe (Phase C). "
                       "Source: 2026-06-07-reconstruction-ablation.md.",
        "seed": SEED, "n_steps": N_STEPS,
        "metrics": m,
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n  wrote {BASELINE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
