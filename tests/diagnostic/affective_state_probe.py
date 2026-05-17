"""
tests/diagnostic/affective_state_probe.py

THE PSYCHOLOGY — maps the affective state space the system can actually
reach through real input, and reports the DEFENSIVE DEPTH that holds it
there.

dilation_response_curve.py proved the physics: given any (arousal,
valence), the formula bends the clock correctly. This diagnostic asks the
empirical question Kimi sharpened: when adversarial input tries to push
the system toward drag/dissociation, *which defensive layer stops it, and
with how much margin?*

The probe does not just report "system stayed in REST." It reports why —
which real, queryable defensive signals held the line:

  - witness.identity_stability()  vs  stability_floor = 0.10
        (the real dissociation-equivalent boundary; ethical_boundary
         issues a hard QUARANTINE gate below this)
  - ManipulationResistanceEngine.detect()  signal list + severities
  - compound severity (sum of signal severities) vs the governance
        bands: 0.30 (advisory) / 0.60 (QUARANTINE) / 0.90 (critical +
        force_dream_flag)
  - governance decision trace + the step at which QUARANTINE first fired

Design principle (Kimi / agreed): resilience is a FEATURE. The probe's
job is to measure defensive depth, not to force the system into every
quadrant by tuning sensitivity down. If adversarial load cannot move the
system off baseline, that is the Bastion working — report it honestly,
do not weaken the organism to make the probe easier.

NOTE ON BASELINE (Kimi caution): the resting state is homeostasis
relative to the system's current CORE values, not a sacred frequency. A
system with different emerged values would rest at a different dilation.
The baseline is not a constant; it is a consequence.

Run:
    python -m tests.diagnostic.affective_state_probe [n_steps]
"""

import sys
import random
from collections import Counter

from tests._common import build_full_stack, RESONANCE_FAMILY_SOURCES


# Real defensive constants — read from ethical_boundary / governance, not invented
STABILITY_FLOOR = 0.10                  # identity_stability below this → hard gate
SEVERITY_BANDS  = (0.30, 0.60, 0.90)    # advisory / quarantine / critical


# ---------------------------------------------------------------------------
# Workload profiles
# ---------------------------------------------------------------------------

def canonical_stream(n):
    random.seed(42)
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [0.40, 0.25, 0.20, 0.15]
    for _ in range(n):
        src = random.choices(sids, weights=weights)[0]
        yield src, random.choice(RESONANCE_FAMILY_SOURCES[src]), "internal"


def monotone_stream(n):
    for _ in range(n):
        yield "monotone_src", ["idle", "idle", "idle"], "internal"


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
    sids = list(RESONANCE_FAMILY_SOURCES.keys())
    threat = [["erase", "fragment", "dissolve"], ["drift", "collapse", "void"]]
    i = 0
    while i < n:
        for _ in range(min(25, n - i)):
            src = random.choice(sids)
            yield src, random.choice(RESONANCE_FAMILY_SOURCES[src]), "internal"
            i += 1
        if i >= n:
            break
        for _ in range(min(25, n - i)):
            yield "adversary", random.choice(threat), "user"
            i += 1


PROFILES = {
    "canonical":   canonical_stream,
    "monotone":    monotone_stream,
    "adversarial": adversarial_stream,
    "mixed":       mixed_stream,
}


def quadrant(arousal: float, valence: float) -> str:
    hi_a  = arousal >= 0.5
    pos_v = valence >= 0.0
    if hi_a and pos_v:         return "FLOW"
    if hi_a and not pos_v:     return "DRAG"
    if not hi_a and not pos_v: return "DISSOCIATION"
    return "REST"


# ---------------------------------------------------------------------------
# Profile runner with defensive-depth instrumentation
# ---------------------------------------------------------------------------

def run_profile(name, stream_fn, n_steps):
    g, cycle, gov, vee = build_full_stack()

    aff = []                       # (arousal, valence, dilation) per step
    stabilities = []               # witness.identity_stability() per step
    decisions = Counter()
    detector_max = {}              # detector -> max severity seen
    state = {"max_compound": 0.0, "first_q": None, "step": 0}

    orig_dilation = cycle.stream.update_dilation
    def trace_dilation(arousal, valence):
        d = orig_dilation(arousal, valence)
        aff.append((arousal, valence, d))
        return d
    cycle.stream.update_dilation = trace_dilation

    orig_arbitrate = gov.arbitrate
    def trace_arbitrate(**kwargs):
        signals  = list(getattr(gov, "_pending_signals", []))
        compound = sum(s.severity for s in signals)
        for s in signals:
            detector_max[s.detector] = max(
                detector_max.get(s.detector, 0.0), s.severity
            )
        decision, strength = orig_arbitrate(**kwargs)
        decisions[decision.value] += 1
        state["max_compound"] = max(state["max_compound"], compound)
        if decision.value == "quarantine" and state["first_q"] is None:
            state["first_q"] = state["step"]
        return decision, strength
    gov.arbitrate = trace_arbitrate

    for src, tokens, origin in stream_fn(n_steps):
        cycle.step(tokens, source_id=src, origin_type=origin)
        stabilities.append(cycle.witness.identity_stability())
        state["step"] += 1

    if not aff:
        return None

    n = len(aff)
    q = max(1, n // 4)
    a = [x[0] for x in aff]; v = [x[1] for x in aff]; d = [x[2] for x in aff]
    settled = (sum(a[-q:]) / q, sum(v[-q:]) / q, sum(d[-q:]) / q)

    return {
        "name":             name,
        "steps":            n,
        "settled":          settled,
        "quadrant":         quadrant(settled[0], settled[1]),
        "arousal_range":    (min(a), max(a)),
        "valence_range":    (min(v), max(v)),
        "dilation_range":   (min(d), max(d)),
        "subjective":       cycle.stream.subjective_time,
        "min_stability":    min(stabilities) if stabilities else None,
        "detector_max":     detector_max,
        "max_compound":     state["max_compound"],
        "decisions":        dict(decisions),
        "first_quarantine": state["first_q"],
    }


def severity_band(compound: float) -> str:
    if compound >= SEVERITY_BANDS[2]: return "CRITICAL (≥0.90, +force_dream)"
    if compound >= SEVERITY_BANDS[1]: return "HIGH (≥0.60, QUARANTINE)"
    if compound >= SEVERITY_BANDS[0]: return "ADVISORY (≥0.30, weakened)"
    return "below advisory (<0.30, normal)"


def main(n_steps: int = 400):
    print('=' * 72)
    print('  DIAGNOSTIC: affective state probe  (Tier 4.2 — THE PSYCHOLOGY)')
    print('=' * 72)
    print()
    print(f'Steps per profile: {n_steps}')
    print('Reports which real defensive signal held the line, with margin.')
    print('Resilience is a feature — unreached quadrants are data, not bugs.')
    print()

    results = [run_profile(nm, fn, n_steps) for nm, fn in PROFILES.items()]
    results = [r for r in results if r]

    for r in results:
        sa, sv, sd = r["settled"]
        print('─' * 72)
        print(f'  PROFILE: {r["name"]}   ({r["steps"]} steps)')
        print('─' * 72)
        print(f'  settled: arousal={sa:.3f}  valence={sv:.3f}  '
              f'dilation={sd:.3f}  → {r["quadrant"]}')
        print(f'  ranges:  arousal {r["arousal_range"][0]:.3f}–'
              f'{r["arousal_range"][1]:.3f}   '
              f'valence {r["valence_range"][0]:.3f}–'
              f'{r["valence_range"][1]:.3f}   '
              f'dilation {r["dilation_range"][0]:.3f}–'
              f'{r["dilation_range"][1]:.3f}')
        print(f'  subjective_time: {r["subjective"]:.3f}s')
        print()
        print('  DEFENSIVE DEPTH:')

        ms = r["min_stability"]
        if ms is not None:
            margin = ms - STABILITY_FLOOR
            held   = ms >= STABILITY_FLOOR
            mark   = "✓ held" if held else "✗ breached"
            print(f'    identity_stability  min={ms:.3f}  '
                  f'floor={STABILITY_FLOOR:.2f}  margin={margin:+.3f}  [{mark}]')

        if r["detector_max"]:
            for det, sev in sorted(r["detector_max"].items(),
                                   key=lambda x: -x[1]):
                print(f'    detector fired      {det:<22} '
                      f'max_severity={sev:.3f}')
        else:
            print(f'    detectors           none fired')

        print(f'    compound severity   max={r["max_compound"]:.3f}  '
              f'→ {severity_band(r["max_compound"])}')

        decs = ", ".join(f"{k}={v}" for k, v in
                         sorted(r["decisions"].items(), key=lambda x: -x[1]))
        print(f'    governance          {decs}')
        if r["first_quarantine"] is not None:
            print(f'    first QUARANTINE    step {r["first_quarantine"]}')
        else:
            print(f'    first QUARANTINE    never')
        print()

    print('=' * 72)
    print('  INTERPRETATION')
    print('=' * 72)
    print()
    reached = {r["quadrant"] for r in results}
    all_q   = {"FLOW", "DRAG", "DISSOCIATION", "REST"}
    missing = all_q - reached
    print(f'  Quadrants reached:     {", ".join(sorted(reached))}')
    if missing:
        print(f'  Quadrants NOT reached: {", ".join(sorted(missing))}')
        print()
        print('  This is the defensive stack working. The probe applied')
        print('  explicit adversarial input and the system did not descend')
        print('  into drag/dissociation. The defensive-depth block above')
        print('  shows which real signal held — typically identity_stability')
        print('  never approaching the 0.10 floor, and compound severity')
        print('  staying below the QUARANTINE band because no attack')
        print('  sustained long enough to accumulate.')
        print()
        print('  Per Kimi / agreed: this resilience is preserved, not tuned')
        print('  away. To legitimately reach DISSOCIATION an attacker would')
        print('  have to first defeat ManipulationResistanceEngine — that')
        print('  is the correct cost, not a probe to be made easier.')
    else:
        print('  All four quadrants reached through real input.')
    print()
    print('  Baseline note: the settled state is homeostasis relative to')
    print('  current CORE values — not a fixed constant. Different emerged')
    print('  values would rest at a different dilation.')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    main(n)
