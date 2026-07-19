"""
tests/diagnostic/lockin/fix0b_currency_census_probe.py

Measure-before-change ruler for Fix 0-B (metastability → reinforcement) and
its bundled demotion path (Fix 0-C mechanism). Nothing is changed here —
this is the census that the fitness-term design and constants must be
calibrated against (same discipline as the bond-DDM and F9 arcs).

Three questions, each with a table:

  1. SURVIVAL CURRENCY — for every living symbol, decompose the reaper's
     reinforcement term (1 + Σ weight·signal) into per-component
     contributions. Which currency actually buys tenure today, per token
     class? (The conformity-lean hypothesis: field_coherence + crystal
     binding dominate; the existing recurrence-gated novelty term is small.)

  2. SIGNAL ROOM — the candidate fitness signal is "this step's expression
     visited a rare regime of a genuinely multi-regime stream":
     credit = (1 − occupancy_share) × metastability_score, computed on the
     stage-C expression stream with the SAME clustering the online monitor
     uses. Distribution of that credit over a live run = how much
     counterweight the term can actually deliver, and at what rate.

  3. RATCHET EVIDENCE — the demotion case: how many symbols hold binding
     signals (attractor_strength / crystal_binding > 0) that have not been
     refreshed recently (last_seen lag)? Those are exactly the "past
     dominating the future" holdings a leaky-binding demotion would tax.

Reads the monitors' stream from OUTSIDE (the plan's sanctioned read path —
the monitors themselves stay observe-only terminal sinks). Informational;
never in run_all_tests.sh.

Usage:
    python -m tests.diagnostic.lockin.fix0b_currency_census_probe [n_steps]
"""

from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict

import numpy as np

from agents.symbolic_memory import DECAY_PROFILES, TokenClass
from substrate.metastability import _cluster_configs, compute_metastability
from tests._common import (
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
    build_full_stack,
)

SEED          = 42
DEFAULT_STEPS = 800
WINDOW        = 128     # match StreamMetastabilityMonitor defaults
MIN_SAMPLES   = 16


def pct(xs, q):
    return float(np.percentile(xs, q)) if len(xs) else float("nan")


def main() -> int:
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STEPS

    generator, cycle, governance, value_engine = build_full_stack(torch_seed=SEED)
    random.seed(SEED)
    np.random.seed(SEED)
    if getattr(cycle, "dreamer", None) is not None:
        cycle.dreamer._rng = np.random.default_rng(SEED)

    # ------------------------------------------------------------------
    # Tap the stage-C expression stream (outside the monitor — read-only).
    # ------------------------------------------------------------------
    expr_stream: list = []
    mon = cycle.expression_metastability
    if mon is not None:
        orig_observe = mon.observe

        def tapped(vec):
            expr_stream.append(np.asarray(vec, dtype=float).copy())
            return orig_observe(vec)

        mon.observe = tapped

    # Track which tokens were active at each expression step (for the
    # attribution question: rare-regime steps → whose tokens?)
    step_tokens: list = []

    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    try:
        for i in range(n_steps):
            src    = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            cycle.step(tokens, source_id=src, origin_type="internal")
            step_tokens.append(tokens)
    finally:
        if mon is not None:
            mon.observe = orig_observe

    registry = generator.registry

    print("=" * 78)
    print("  FIX 0-B CURRENCY CENSUS — measure before change")
    print(f"  seed={SEED}  n_steps={n_steps}  symbols={len(registry.symbols)}  "
          f"expr_samples={len(expr_stream)}")
    print("=" * 78)

    # ------------------------------------------------------------------
    # 1. Survival currency decomposition
    # ------------------------------------------------------------------
    comp_names = ["recurrence", "attractor", "centrality",
                  "field_coherence", "crystal_binding", "novelty"]
    by_class: dict = defaultdict(lambda: defaultdict(list))
    reaper_hist: Counter = Counter()

    import math
    for state in registry.symbols.values():
        prof = DECAY_PROFILES.get(state.token_class, DECAY_PROFILES[TokenClass.LANGUAGE])
        novelty = max(0.0, 1.0 - state.field_coherence)
        recurrence_gate = 1.0 - math.exp(-0.5 * state.recurrence)
        comps = {
            "recurrence":      prof.recurrence_weight      * state.recurrence,
            "attractor":       prof.attractor_weight       * state.attractor_strength,
            "centrality":      prof.centrality_weight      * state.centrality,
            "field_coherence": prof.field_coherence_weight * state.field_coherence,
            "crystal_binding": prof.crystal_binding_weight * state.crystal_binding,
            "novelty":         prof.novelty_weight         * (novelty * recurrence_gate),
        }
        total = sum(comps.values())
        for k, v in comps.items():
            by_class[state.token_class.value][k].append(v)
            by_class[state.token_class.value][k + "_share"].append(
                v / total if total > 1e-12 else 0.0)
        reaper_hist[state.reaper_stage.value] += 1

    print("\n[1] SURVIVAL CURRENCY — mean contribution (mean share of Σ) per class")
    hdr = f"  {'class':<12} {'n':>5} | " + " | ".join(f"{c[:9]:>15}" for c in comp_names)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for cls, comps in sorted(by_class.items()):
        n = len(comps["recurrence"])
        cells = []
        for c in comp_names:
            mean_v = float(np.mean(comps[c])) if comps[c] else 0.0
            mean_s = float(np.mean(comps[c + "_share"])) if comps[c + "_share"] else 0.0
            cells.append(f"{mean_v:6.3f} ({mean_s:4.0%})")
        print(f"  {cls:<12} {n:>5} | " + " | ".join(f"{c:>15}" for c in cells))
    print(f"\n  reaper stages: {dict(reaper_hist)}")

    # ------------------------------------------------------------------
    # 2. Signal room — candidate diversity credit on the expression stream
    # ------------------------------------------------------------------
    print("\n[2] SIGNAL ROOM — credit = (1 − regime occupancy) × metastability")
    credits, shares, scores = [], [], []
    token_credit: Counter = Counter()
    if len(expr_stream) >= MIN_SAMPLES:
        arr = np.stack(expr_stream)
        for t in range(MIN_SAMPLES, len(arr)):
            win = arr[max(0, t - WINDOW + 1): t + 1]
            labels = _cluster_configs(win)
            occ = labels.count(labels[-1]) / len(labels)
            rep = compute_metastability(win)
            credit = (1.0 - occ) * rep.metastability
            shares.append(occ)
            scores.append(rep.metastability)
            credits.append(credit)
            if t < len(step_tokens):
                for tok in step_tokens[t]:
                    token_credit[tok] += credit
        print(f"  occupancy share : p10={pct(shares,10):.3f}  p50={pct(shares,50):.3f}  "
              f"p90={pct(shares,90):.3f}")
        print(f"  metastability   : p10={pct(scores,10):.3f}  p50={pct(scores,50):.3f}  "
              f"p90={pct(scores,90):.3f}")
        print(f"  credit/step     : p10={pct(credits,10):.3f}  p50={pct(credits,50):.3f}  "
              f"p90={pct(credits,90):.3f}  mean={float(np.mean(credits)):.3f}")
        top = token_credit.most_common(8)
        print("  top credited tokens: " +
              ", ".join(f"{t} {c:.1f}" for t, c in top))

        # Calibration pre-analysis: with an EMA accumulator (alpha=0.05) the
        # steady-state per-symbol credit ≈ mean credit of its active steps.
        # A fitness weight w contributes w × credit to reinforcement; print
        # the w that makes a p90-credit symbol's term match the measured
        # dominant-component means per class.
        p90c = pct(credits, 90)
        if p90c > 1e-9:
            print("\n  weight sizing (w s.t. w × p90-credit ≈ dominant component mean):")
            for cls, comps in sorted(by_class.items()):
                dom = max(comp_names,
                          key=lambda c: float(np.mean(comps[c])) if comps[c] else 0.0)
                dom_mean = float(np.mean(comps[dom])) if comps[dom] else 0.0
                print(f"    {cls:<12} dominant={dom:<15} mean={dom_mean:6.3f}  "
                      f"→ w ≈ {dom_mean / p90c:5.2f}")
    else:
        print("  (expression stream too short — monitors off?)")

    # ------------------------------------------------------------------
    # 3. Ratchet evidence — stale bindings a demotion path would tax
    # ------------------------------------------------------------------
    print("\n[3] RATCHET EVIDENCE — bound symbols not refreshed recently")
    now = registry.step_counter
    for lag in (50, 150, 400):
        stale_att = sum(
            1 for s in registry.symbols.values()
            if s.attractor_strength > 0 and (now - s.last_seen_step) > lag)
        stale_cry = sum(
            1 for s in registry.symbols.values()
            if s.crystal_binding > 0 and (now - s.last_seen_step) > lag)
        print(f"  lag > {lag:>3}: attractor-bound stale={stale_att:>4}   "
              f"crystal-bound stale={stale_cry:>4}")
    bound = [s for s in registry.symbols.values()
             if s.attractor_strength > 0 or s.crystal_binding > 0]
    if bound:
        lags = [now - s.last_seen_step for s in bound]
        print(f"  bound symbols: {len(bound)}  last-seen lag p50={pct(lags,50):.0f}  "
              f"p90={pct(lags,90):.0f}")

    print("\n" + "=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
