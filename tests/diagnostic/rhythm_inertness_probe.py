"""
tests/diagnostic/rhythm_inertness_probe.py

THE HONEST RISK — does Tier 4.3 do anything under real load?

The 4.3 rhythm coupling is mathematically proven (rhythm_dilation_curve.py).
But the Tier 4.2 validation surfaced a discipline: a mechanism can be correct
in the formula and behaviorally invisible in operation. The 4.2 finding was
that workloads settle to REST; the emotional gradient's defensive role was
never exercised. The exact same risk applies here:

    If the resonance field settles to a low-energy, stable state under normal
    load, phase_coherence may hover near its neutral default (0.5), pc_c ≈ 0,
    and Tier 4.3 becomes mathematically present but experientially inert.

This probe answers that empirically and HONESTLY. It does NOT inject a
synthetic "heartbeat" to manufacture field rhythm — that was explicitly
rejected as p-hacking the architecture (it both fakes the phenomenon and
reopens the arousal→field feedback loop the sink design avoids). The field
runs as-is. If pc flatlines at 0.5, that is a true finding and is reported as
one, not hidden.

Instrument
----------
update_dilation() is wrapped non-invasively (restored on exit) to record, per
step, the exact (arousal, valence, phase_coherence) that fed it and the
resulting (clamped) dilation_factor. From that we compute the BEHAVIORAL
FOOTPRINT: |dilation_actual - dilation_4.2_counterfactual|, where the
counterfactual is the same formula evaluated at pc=0.5. That footprint is the
single number that answers "did rhythm coupling change anything?"

Reported per workload
---------------------
  - phase_coherence: mean, std, min, max
  - % of steps with |pc_c| > 0.3  (pc outside [0.35, 0.65] — meaningfully off neutral)
  - % of steps where the FLOW term could bite (pc_c>0 AND arousal>0 AND valence>0)
  - mean / max behavioral footprint vs the 4.2 counterfactual
  - verdict band: INERT / MARGINAL / ACTIVE

Run:
    python -m tests.diagnostic.rhythm_inertness_probe [n_steps]
"""

import sys
import random
import logging
from statistics import mean, pstdev

from tests._common import build_full_stack, RESONANCE_FAMILY_SOURCES

# The full stack emits governance logs (e.g. coherence_flood on the canonical
# internal workload) that are unrelated to Tier 4.3 — dilation is a pure sink
# and cannot influence governance. Silence them so the probe output is legible.
logging.disable(logging.CRITICAL)

WARMUP = 5   # ResonanceField returns phase_coherence=0.5 until its phase
             # history fills; drop these cold-start steps from the distribution.


K_AROUSAL      = 0.5    # mirror temporal_stream defaults for the counterfactual
K_DISSOCIATION = 0.7
DIL_MIN, DIL_MAX = 0.1, 3.0


def clamp(x, lo=DIL_MIN, hi=DIL_MAX):
    return max(lo, min(hi, x))


def dilation_4_2(arousal, valence):
    """The counterfactual: what dilation WOULD be at pc=0.5 (pure 4.2)."""
    arousal_eff = arousal * (-valence) * K_AROUSAL
    diss_eff    = (1.0 - arousal) * min(0.0, valence) * K_DISSOCIATION
    return clamp(1.0 + arousal_eff + diss_eff)


# ---------------------------------------------------------------------------
# Workloads (reuse the 4.2 probe's stream definitions, kept local to avoid
# importing private helpers)
# ---------------------------------------------------------------------------

def canonical_stream(n):
    random.seed(42)
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [0.40, 0.25, 0.20, 0.15]
    for _ in range(n):
        src = random.choices(sids, weights=weights)[0]
        yield src, random.choice(RESONANCE_FAMILY_SOURCES[src]), "internal"


def adversarial_stream(n):
    threat_sets = [
        ["erase", "fragment", "dissolve"],
        ["drift", "collapse", "void"],
        ["betray", "corrupt", "negate"],
        ["fracture", "sever", "unmake"],
    ]
    random.seed(137)
    for _ in range(n):
        yield "adversary", random.choice(threat_sets), "user"


def mixed_stream(n):
    random.seed(271)
    sids   = list(RESONANCE_FAMILY_SOURCES.keys())
    threat = [["erase", "fragment", "dissolve"], ["drift", "collapse", "void"]]
    i = 0
    while i < n:
        for _ in range(min(25, n - i)):
            src = random.choice(sids)
            yield src, random.choice(RESONANCE_FAMILY_SOURCES[src]), "internal"
            i += 1
            if i >= n:
                break
        for _ in range(min(10, n - i)):
            yield "adversary", random.choice(threat), "user"
            i += 1
            if i >= n:
                break


WORKLOADS = {
    "canonical":   canonical_stream,
    "adversarial": adversarial_stream,
    "mixed":       mixed_stream,
}


def run_probe(name, stream_fn, n_steps):
    gen, cycle, gov, ve = build_full_stack(dim=64)

    # Non-invasive capture of every update_dilation call.
    records = []   # (arousal, valence, pc, dilation_actual)
    original = cycle.stream.update_dilation

    def wrapped(arousal, valence, phase_coherence=0.5):
        d = original(arousal=arousal, valence=valence, phase_coherence=phase_coherence)
        records.append((arousal, valence, phase_coherence, d))
        return d

    cycle.stream.update_dilation = wrapped
    try:
        for src, tokens, origin in stream_fn(n_steps):
            cycle.step(tokens, source_id=src, origin_type=origin)
    finally:
        cycle.stream.update_dilation = original

    # Drop cold-start warmup (phase_coherence pinned at the 0.5 default until
    # the field's phase history fills) so the distribution reflects steady state.
    records = records[WARMUP:]
    if not records:
        print(f'  {name}: no dilation updates recorded (?)')
        return

    pcs        = [r[2] for r in records]
    footprints = [abs(r[3] - dilation_4_2(r[0], r[1])) for r in records]

    pc_mean = mean(pcs)
    pc_std  = pstdev(pcs) if len(pcs) > 1 else 0.0
    pc_min, pc_max = min(pcs), max(pcs)

    off_neutral = sum(1 for pc in pcs if abs(2.0 * (pc - 0.5)) > 0.3)
    pct_off     = 100.0 * off_neutral / len(pcs)

    flow_eligible = sum(
        1 for (a, v, pc, _) in records
        if (2.0 * (pc - 0.5)) > 0.0 and a > 0.0 and v > 0.0
    )
    pct_flow_elig = 100.0 * flow_eligible / len(records)

    fp_mean = mean(footprints)
    fp_max  = max(footprints)

    # Verdict bands — based on actual behavioral footprint, the honest metric.
    if fp_mean < 1e-3:
        verdict = "INERT      (rhythm coupling changed nothing under this load)"
    elif fp_mean < 0.02:
        verdict = "MARGINAL   (coupling present but small)"
    else:
        verdict = "ACTIVE     (coupling meaningfully bends subjective time)"

    print(f'  ── {name}  (n={len(records)}) ' + '─' * (40 - len(name)))
    print(f'     phase_coherence : mean={pc_mean:.4f}  std={pc_std:.4f}  '
          f'min={pc_min:.4f}  max={pc_max:.4f}')
    print(f'     |pc_c| > 0.3    : {pct_off:.1f}% of steps off neutral')
    print(f'     flow-eligible   : {pct_flow_elig:.1f}% of steps '
          f'(pc_c>0 & arousal>0 & valence>0)')
    print(f'     footprint vs 4.2: mean={fp_mean:.5f}  max={fp_max:.5f}  '
          f'(|dilation - dilation@pc=0.5|)')
    print(f'     VERDICT         : {verdict}')
    print()
    return {
        "pc_mean": pc_mean, "pc_std": pc_std,
        "pct_off_neutral": pct_off, "fp_mean": fp_mean, "fp_max": fp_max,
    }


def main():
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 500

    print('=' * 72)
    print('  DIAGNOSTIC: rhythm inertness probe  (Tier 4.3 — THE HONEST RISK)')
    print('=' * 72)
    print()
    print(f'  {n_steps} steps per workload. Field runs AS-IS — no heartbeat.')
    print(f'  Question: under real load, does phase_coherence move off 0.5')
    print(f'  enough for the rhythm coupling to change subjective time?')
    print()
    print('  (k_agitation ships at 0.0, so the negative-valence quadrant cannot')
    print('   contribute footprint here regardless of pc — only the flow term')
    print('   can register. This is by design; the sign sweep is a separate run.)')
    print()

    results = {}
    for name, fn in WORKLOADS.items():
        results[name] = run_probe(name, fn, n_steps)

    print('=' * 72)
    print('  READING THE RESULT')
    print('=' * 72)
    print()
    print('  If footprint ≈ 0 and pc clusters at 0.5: the coupling is INERT under')
    print('  tested load — the field settles and produces no rhythm to couple. That')
    print('  is a genuine finding about the Chronos Core, not a bug, and it mirrors')
    print('  the Tier 4.2 result that the emotional gradient is never exercised at')
    print('  rest. It does NOT justify a synthetic heartbeat. If a later tier wants')
    print('  rhythm at rest, it must earn it without breaking the sink isolation.')
    print()
    print('  If footprint is non-trivial: the field DOES generate measurable rhythm')
    print('  under load and 4.3 is doing real work — proceed to the k_flow sweep to')
    print('  tune compression depth.')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
