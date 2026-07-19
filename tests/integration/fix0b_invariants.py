"""
tests/integration/fix0b_invariants.py

Hard-invariant gate for Fix 0-B (diversity fitness) + the Fix 0-C mechanism
(leaky bindings). Pass/fail CI companion to the informational probes
(fix0b_currency_census_probe / fix0b_effect_probe). Synthetic states, <1 s.

Locks down only what must never move:

  1. OFF is the default and OFF is byte-identical — no profile overrides,
     zero binding leak, DecayProfile.compute unchanged on a scripted state
     (diversity_weight defaults 0.0 in every shipped profile).
  2. The monitors stay observe-only — with tracking off the accessor reads
     inert values (share 1.0, credit 0.0), and stream_metastability imports
     nothing from loop/ or agents/ (structural).
  3. The credit is leaky, bounded, and volume-blind — EMA in [0,1], pulled
     DOWN by zero-credit steps (no second ratchet), and rate-based rather
     than traffic-cumulative.
  4. The fitness term has the right sign and the calibrated scale — a
     credited symbol out-survives an identical uncredited one when the
     lever is ON, and per-class diversity_weight = k × crystal weight.
  5. The leak demotes only the unrefreshed and never the exempt — sacred /
     protected / SPECIAL bindings are untouched at any leak; refreshed
     symbols keep full strength; module-level DECAY_PROFILES are never
     mutated by the lever.

Usage:
    python -m tests.integration.fix0b_invariants
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np

from agents.symbolic_memory import (
    DECAY_PROFILES,
    AddressSpace,
    SymbolRegistry,
    TokenClass,
)
from cognition.stream_metastability import StreamMetastabilityMonitor

REPO = Path(__file__).resolve().parents[2]

PASS = []
FAIL = []


def check(name: str, ok: bool, detail: str = ""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'✓' if ok else '✗'} {name}" + (f"  — {detail}" if detail else ""))


def fresh_registry(**kwargs) -> SymbolRegistry:
    return SymbolRegistry(AddressSpace(vocab_size=256), **kwargs)


# ---------------------------------------------------------------------------

def test_off_identical():
    print("\n[1] OFF is the default and byte-identical")
    check("every shipped profile has diversity_weight = 0.0",
          all(p.diversity_weight == 0.0 for p in DECAY_PROFILES.values()))
    reg = fresh_registry()
    check("registry defaults: no overrides, zero leak",
          reg._profiles is None and reg.binding_leak == 0.0)

    reg.register("alpha")
    st = reg.symbols["alpha"]
    st.recurrence, st.field_coherence, st.crystal_binding = 2.0, 0.9, 1.5
    st.diversity_credit = 0.7                      # must be inert at weight 0
    prof = DECAY_PROFILES[st.token_class]
    with_credit = prof.compute(st, 10)
    st.diversity_credit = 0.0
    without = prof.compute(st, 10)
    check("diversity_credit is inert under default profiles",
          abs(with_credit - without) < 1e-12)


def test_monitor_observe_only():
    print("\n[2] Monitors stay observe-only")
    m = StreamMetastabilityMonitor()               # tracking off (default)
    for i in range(20):
        m.observe(np.random.default_rng(i).standard_normal(8))
    check("tracking-off accessor is inert (share 1.0, credit 0.0)",
          m.current_regime_share() == 1.0 and m.diversity_credit() == 0.0)

    tree = ast.parse((REPO / "cognition" / "stream_metastability.py").read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    bad = [m_ for m_ in mods if m_.startswith(("loop", "agents"))]
    check("stream_metastability imports nothing from loop/ or agents/",
          not bad, f"imports={sorted(mods)}")


def test_credit_leaky_bounded():
    print("\n[3] Credit EMA: bounded, leaky, volume-blind")
    reg = fresh_registry()
    reg.register("beta")
    for _ in range(200):
        reg.update_diversity_credit("beta", 5.0)   # abusive input clipped
    hi = reg.symbols["beta"].diversity_credit
    check("bounded in [0,1] under abusive input", 0.0 <= hi <= 1.0, f"credit={hi:.3f}")
    for _ in range(100):
        reg.update_diversity_credit("beta", 0.0)   # conformist steps
    lo = reg.symbols["beta"].diversity_credit
    check("zero-credit steps pull the EMA down (no second ratchet)",
          lo < hi * 0.05, f"{hi:.3f} → {lo:.4f}")

    # volume-blind: many mediocre steps must not out-credit few rare ones
    reg.register("busy"); reg.register("rare")
    for _ in range(500):
        reg.update_diversity_credit("busy", 0.1)
    for _ in range(30):
        reg.update_diversity_credit("rare", 0.6)
    check("rate beats volume (EMA, not a sum)",
          reg.symbols["rare"].diversity_credit
          > reg.symbols["busy"].diversity_credit,
          f"rare={reg.symbols['rare'].diversity_credit:.3f} "
          f"busy={reg.symbols['busy'].diversity_credit:.3f}")


def test_fitness_sign_and_scale():
    print("\n[4] Fitness term: sign + calibrated scale")
    reg = fresh_registry()
    reg.set_diversity_weights()
    k_ok = all(
        abs(reg._profiles[cls].diversity_weight
            - 8.7 * DECAY_PROFILES[cls].crystal_binding_weight) < 1e-9
        for cls in DECAY_PROFILES
    )
    check("per-class weight = 8.7 × crystal_binding_weight (census constant)", k_ok)
    check("module-level DECAY_PROFILES untouched by the lever",
          all(p.diversity_weight == 0.0 for p in DECAY_PROFILES.values()))

    reg.register("credited"); reg.register("plain")
    a, b = reg.symbols["credited"], reg.symbols["plain"]
    for s in (a, b):
        s.usage, s.recurrence, s.last_seen_step = 1.0, 1.0, 0
    a.diversity_credit = 0.5
    prof = reg._profiles[a.token_class]
    check("credited symbol out-survives its uncredited twin",
          prof.compute(a, 5) > prof.compute(b, 5),
          f"{prof.compute(a, 5):.4f} vs {prof.compute(b, 5):.4f}")


def test_leak_semantics():
    print("\n[5] Binding leak: unrefreshed only; exempt untouched")
    reg = fresh_registry()
    reg.binding_leak = 0.10
    for name in ("stale", "fresh", "holy"):
        reg.register(name)
        st = reg.symbols[name]
        st.attractor_strength, st.crystal_binding = 2.0, 1.0
        st.created_step = 0
    reg.symbols["holy"].sacred = True
    reg.step_counter = 100
    reg._last_decay_at = 50
    reg.symbols["stale"].last_seen_step = 10     # unrefreshed since last pass
    reg.symbols["fresh"].last_seen_step = 80     # refreshed
    reg.symbols["holy"].last_seen_step  = 10     # unrefreshed but sacred
    reg.decay_step()
    s, f, h = (reg.symbols.get(n) for n in ("stale", "fresh", "holy"))
    check("unrefreshed binding leaked",
          s is None or abs(s.attractor_strength - 1.8) < 1e-9,
          "reaped" if s is None else f"attractor 2.0 → {s.attractor_strength:.3f}")
    check("refreshed binding untouched",
          f is not None and abs(f.attractor_strength - 2.0) < 1e-9)
    check("sacred binding untouched at any leak",
          h is not None and abs(h.attractor_strength - 2.0) < 1e-9)


# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("  FIX 0-B — HARD INVARIANTS GATE")
    print("=" * 70)
    test_off_identical()
    test_monitor_observe_only()
    test_credit_leaky_bounded()
    test_fitness_sign_and_scale()
    test_leak_semantics()
    print("\n" + "=" * 70)
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print(f"    ✗ {f}")
    print("=" * 70)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
