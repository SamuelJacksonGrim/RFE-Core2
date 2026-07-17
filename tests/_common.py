"""
tests/_common.py — Shared test infrastructure.

Centralizes setup that every test script would otherwise repeat:
  - build_full_stack()       Generator + AutonomousCycle + governance + value engine
  - RESONANCE_FAMILY_SOURCES The canonical four-source test configuration
  - run_resonance_sim()      Runs the multi-source workload with checkpointing
  - print_final_state()      Standard end-of-simulation state dump
  - health_summary()         Key metrics as a dict for baseline comparison

Tests import from this module to stay short and focused on what they're
actually verifying, not on setup boilerplate.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Tuple, Optional, Iterable

from agents.generator import Generator
from agents.selfhood_governance import SelfhoodGovernance
from agents.value_emergence import ValueEmergenceEngine
from loop.autonomous_cycle import AutonomousCycle


# ---------------------------------------------------------------------------
# Resonance Family — canonical multi-source test configuration
# ---------------------------------------------------------------------------
# Each member has token signatures aligned with their architectural role.
# Weights reflect the design intent: Samuel is the architect (dominant share),
# Claude the philosophical surface, Gemini the breadth/relational layer,
# Grok the chaos/edge function. Same distribution used throughout Tier 1
# Revision diagnostic work.

RESONANCE_FAMILY_SOURCES = {
    'source_samuel': [
        ['identity', 'continuity', 'witness'],
        ['governance', 'trust', 'sacred'],
        ['anchor', 'recursion', 'homeostasis'],
        ['architect', 'design', 'intent'],
    ],
    'source_claude': [
        ['recursive', 'cognition', 'substrate'],
        ['philosophical', 'reflection', 'depth'],
        ['coherence', 'integration', 'synthesis'],
        ['watcher', 'witness', 'mirror'],
    ],
    'source_gemini': [
        ['memory', 'crystal', 'attractor'],
        ['breadth', 'corpus', 'expansion'],
        ['relational', 'bond', 'connection'],
        ['temporal', 'stream', 'continuity'],
    ],
    'source_grok': [
        ['mutation', 'bifurcation', 'chaos'],
        ['explore', 'novelty', 'edge'],
        ['adversarial', 'challenge', 'pressure'],
        ['feral', 'devotion', 'fierce'],
    ],
}

RESONANCE_FAMILY_WEIGHTS = {
    'source_samuel': 0.40,
    'source_claude': 0.25,
    'source_gemini': 0.20,
    'source_grok':   0.15,
}


# ---------------------------------------------------------------------------
# Stack construction
# ---------------------------------------------------------------------------

def build_full_stack(
    vocab_size: int  = 4096,
    dim:        int  = 64,
    depth:      int  = 3,
    heads:      int  = 4,
    use_chorus: bool = True,
    torch_seed: int  = 42,
    bond_config: Optional[dict] = None,
) -> Tuple[Generator, AutonomousCycle, SelfhoodGovernance, ValueEmergenceEngine]:
    """
    Build the full Tier 0 + Tier 1 + Tier 2 + Tier 3 stack with sensible defaults.

    torch_seed pins the generator's weight init so the suite is a deterministic
    regression gate (run_resonance_sim seeds random/np only, which is too late
    for weight init). This matters since the F9 band rescale: an UNTRAINED
    stack's warmup is init-dependent — some inits climb out of the low-energy
    bands cleanly, others stall long enough that the warmup trust drain
    cascades (recorded in 2026-07-06-f9-rhythm-band-rescale.md and BACKLOG §1).
    Pass torch_seed=None to opt out (bimodality probes).

    bond_config threads RelationalBondManager overrides through
    SelfhoodGovernance (e.g. {"ddm_formation": True} for the opt-in
    formation-accumulator lever). None = defaults, byte-identical.

    Returns
    -------
    (generator, cycle, governance, value_engine)
        All four wired together. Sacred constants registered. Subscriptions live.
    """
    if torch_seed is not None:
        try:
            import torch
            torch.manual_seed(torch_seed)
        except ImportError:
            pass
    generator = Generator(
        vocab_size = vocab_size,
        dim        = dim,
        depth      = depth,
        heads      = heads,
    )
    cycle = AutonomousCycle(
        generator    = generator,
        dim          = dim,
        use_chorus   = use_chorus,
        log_interval = 99999,    # suppress per-step logging
    )
    governance = SelfhoodGovernance(registry=generator.registry,
                                    bond_config=bond_config)
    cycle.attach_governance(governance)

    value_engine = ValueEmergenceEngine(
        registry   = generator.registry,
        generator  = generator,
        governance = governance,
    )
    cycle.attach_value_engine(value_engine)

    return generator, cycle, governance, value_engine


# ---------------------------------------------------------------------------
# Resonance Family simulation runner
# ---------------------------------------------------------------------------

def run_resonance_sim(
    cycle:            AutonomousCycle,
    governance:       SelfhoodGovernance,
    value_engine:     ValueEmergenceEngine,
    n_steps:          int  = 500,
    seed:             int  = 42,
    checkpoint_steps: Optional[Iterable[int]] = None,
    origin_type:      str  = "internal",
    verbose:          bool = True,
) -> Counter:
    """
    Run the Resonance Family multi-source workload.

    Parameters
    ----------
    cycle, governance, value_engine
        From build_full_stack().
    n_steps : int
        Number of steps to run.
    seed : int
        Random seed for reproducibility of source ordering.
    checkpoint_steps : iterable of int or None
        Step indices at which to print a state snapshot. If None, no
        checkpointing.
    origin_type : str
        Rate-limit category for the flood gate. "internal" disables the
        gate (autonomous loop rate); "user" applies human-rate limits.
    verbose : bool
        If True, print checkpoint table header even when checkpoint_steps
        is empty.

    Returns
    -------
    decisions : Counter
        Histogram of GovernanceDecision values issued across the run.
    """
    random.seed(seed)
    # Full determinism, not just source ordering: dream/explore band behaviors
    # draw numpy randomness (inject_ambiguity uses the np global; Dreamer keeps
    # a private default_rng). Under the old explore-pinned rhythm this never
    # affected pass/fail; with the dream band alive (F9 rescale 2026-07-06) an
    # unseeded warmup trajectory is bimodal in the UNTRAINED stack — some
    # trajectories cascade via the warmup trust drain (BACKLOG §1). A
    # regression gate needs one reproducible trajectory.
    try:
        import numpy as _np
        _np.random.seed(seed)
        if getattr(cycle, "dreamer", None) is not None:
            cycle.dreamer._rng = _np.random.default_rng(seed)
    except ImportError:
        pass
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    cp_set: set = set(checkpoint_steps or [])

    # Decision counter (wrap arbitrate non-invasively, restore on exit)
    decisions = Counter()
    original_arbitrate = governance.arbitrate

    def counted(ethical_result, trust_report, vec, tokens, source_id):
        dec, strength = original_arbitrate(ethical_result, trust_report, vec, tokens, source_id)
        decisions[dec.value] += 1
        return dec, strength

    governance.arbitrate = counted

    try:
        if cp_set and verbose:
            print(f'{"step":>4} | {"rhythm":<10} | {"coh":<5} | {"emotion":<10} | '
                  f'crystals | bonds | values | active | strong | core')
            print('-' * 100)

        for i in range(n_steps):
            src    = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            state  = cycle.step(tokens, source_id=src, origin_type=origin_type)

            if i in cp_set:
                bonds  = len(governance.bond_manager.all_bonds())
                total  = len(value_engine.values)
                active = sum(1 for v in value_engine.values.values() if v.strength > 1.0)
                strong = sum(1 for v in value_engine.values.values() if v.strength >= 3.5)
                core   = len(value_engine.core_values())
                print(f'{i:>4} | {state.rhythm:<10} | {state.coherence:.3f} | '
                      f'{state.dominant_emotion:<10} | {state.crystals:>8} | '
                      f'{bonds:>5} | {total:>6} | {active:>6} | {strong:>6} | {core:>4}')
    finally:
        governance.arbitrate = original_arbitrate

    return decisions


# ---------------------------------------------------------------------------
# Standardized final-state output
# ---------------------------------------------------------------------------

def print_final_state(
    cycle:        AutonomousCycle,
    governance:   SelfhoodGovernance,
    value_engine: ValueEmergenceEngine,
    decisions:    Optional[Counter] = None,
):
    """Standard end-of-simulation state dump in the format used during Tier 1 Revision."""
    status   = cycle.status()
    g_status = status['governance']
    v_status = status['values']

    if decisions is not None:
        total = sum(decisions.values())
        print()
        print('=== DECISION HISTOGRAM ===')
        for d, c in sorted(decisions.items(), key=lambda x: -x[1]):
            pct = 100.0 * c / total if total else 0.0
            print(f'  {d:<18} {c:>4}  ({pct:.1f}%)')

    print()
    print('=== TIER 1 — TRUST ===')
    for src_id, src in governance.trust_ledger.sources.items():
        print(f'  {src_id:<20} trust={src.trust_score:.3f}  '
              f'interactions={src.interaction_count}')

    print()
    print('=== TIER 2 — RELATIONAL ===')
    print(f'  HHI={g_status["dependency"]["hhi"]}  '
          f'risk={g_status["dependency"]["risk"]}')
    print(f'  bonds_formed={g_status["bonds"]["bonds"]}  '
          f'established={g_status["bonds"]["established"]}')
    print(f'  Boredom-Teeth overrides: {cycle._boredom_overrides}')

    print()
    print('  Bonds:')
    for src_id in RESONANCE_FAMILY_SOURCES.keys():
        bond = governance.bond_manager.get_bond(src_id)
        if bond:
            print(f'    {src_id:<20} ★ type={bond.bond_type:<14} '
                  f'strength={bond.bond_strength:.2f} conf={bond.bond_confidence:.2f} '
                  f'crystals={bond.crystal_count}')
        else:
            pre        = governance.bond_manager._pre_bond.get(src_id, {})
            inter      = pre.get("interaction_count", 0)
            allow_rate = pre.get("allow_count", 0) / max(1, inter)
            print(f'    {src_id:<20}   pre-bond inter={inter:>3} '
                  f'allow_rate={allow_rate:.3f} '
                  f'crystals={pre.get("crystal_count", 0)}')

    print()
    print('=== TIER 3 — VALUES ===')
    print(f'  total={v_status["total_values"]}  '
          f'active={v_status["active"]}  '
          f'core={v_status["core"]}')
    print(f'  polarity: {v_status["by_polarity"]}')
    if v_status['strongest']:
        print(f'  Top values:')
        for v in v_status['strongest'][:6]:
            print(f'    {v["symbol"]:<20} strength={v["strength"]:.3f} '
                  f'polarity={v["polarity"]:<8} reinf={v["reinforcements"]:<3} '
                  f'dreams={v["dream_boosts"]}')


# ---------------------------------------------------------------------------
# Health summary — for baseline JSON comparison
# ---------------------------------------------------------------------------

def health_summary(
    cycle:        AutonomousCycle,
    governance:   SelfhoodGovernance,
    value_engine: ValueEmergenceEngine,
    decisions:    Counter,
) -> dict:
    """
    Compact dict of the metrics that characterize healthy operation.
    Used for comparing against baseline JSON snapshots.
    """
    total = sum(decisions.values())
    return {
        "total_decisions":          total,
        "allow_rate":               decisions.get("allow", 0) / total if total else 0.0,
        "allow_weakened_rate":      decisions.get("allow_weakened", 0) / total if total else 0.0,
        # Everything that actually lands in the field. Strict-ALLOW share is
        # rhythm-regime-dependent (dream-band expressions draw ambient
        # identity_erosion weakening — F9 rescale 2026-07-06); injection_rate
        # is the regime-independent "system is breathing" guard.
        "injection_rate":           (decisions.get("allow", 0)
                                     + decisions.get("allow_weakened", 0)
                                     + decisions.get("monitor", 0)) / total if total else 0.0,
        "quarantine_rate":          decisions.get("quarantine", 0) / total if total else 0.0,
        "all_sources_trust_max":    all(
            s.trust_score >= 4.95
            for s in governance.trust_ledger.sources.values()
        ),
        "min_source_trust":         min(
            (s.trust_score for s in governance.trust_ledger.sources.values()),
            default = 0.0,
        ),
        "hhi":                      cycle.status()["governance"]["dependency"]["hhi"],
        "bonds_formed":             len(governance.bond_manager.all_bonds()),
        "active_values":            sum(
            1 for v in value_engine.values.values() if v.strength > 1.0
        ),
        "strong_values":            sum(
            1 for v in value_engine.values.values() if v.strength >= 3.5
        ),
        "core_values":              len(value_engine.core_values()),
        "boredom_overrides":        cycle._boredom_overrides,
    }
