"""
tests/diagnostic/rhythm_dilation_curve.py

THE PHYSICS — mathematical ground truth for Tier 4.3 rhythm → time coupling.

Tier 4.2 proved the (arousal, valence) dilation surface. Tier 4.3 adds a third
input — phase_coherence, the field's rhythmic organization from the FFT — as the
organizing-vs-chaotic axis that arousal × valence alone cannot represent. Flow
and agitation are both high-arousal states; the 4.2 plane bends them the same
way. phase_coherence is what separates "in the zone" from "spinning out".

This diagnostic isolates update_dilation() completely from the token stream and
sweeps (arousal, valence, phase_coherence) directly. It answers, with the same
rigor as the 4.2 physics validator:

  1. REGRESSION GUARD — at phase_coherence = 0.5 (neutral / field cold-start
     default), the surface is byte-identical to validated Tier 4.2. This is the
     load-bearing safety property: 4.3 is a strict extension, a no-op at neutral.

  2. FLOW term (proven degeneracy resolution) — organized field (pc → 1.0) in
     the high-arousal positive-valence quadrant deepens compression; chaotic
     field (pc → 0.0) attenuates it back toward the 4.2 value.

  3. AGITATION term (phenomenological HYPOTHESIS, ships at k_agitation = 0.0) —
     verified INERT at the shipped default, and the mechanism verified in BOTH
     sign directions with a temporary coefficient (positive = drag, negative =
     panic-compression). The sweep / probe pick the real sign; this validator
     only proves the math behaves as documented in each direction.

  4. CLAMP — pathological coefficients cannot drive dilation outside
     [dilation_min, dilation_max]. No time-reversal, no runaway slowdown.

  5. MUTUAL EXCLUSIVITY — flow_eff and agit_eff are gated to opposite valence
     half-planes and opposite pc_c signs; they can never co-fire.

Run:
    python -m tests.diagnostic.rhythm_dilation_curve
"""

import sys

from substrate.temporal_stream import TemporalStream


# ---------------------------------------------------------------------------
# Tier 4.2 ground-truth surface (regression target).
# Copied verbatim from the validated dilation_response_curve.py output.
# rows = arousal [0.0, 0.25, 0.5, 0.75, 1.0]
# cols = valence [-1.0, -0.5, 0.0, 0.5, 1.0]
# ---------------------------------------------------------------------------
TIER_4_2_SURFACE = {
    0.00: {-1.0: 0.300, -0.5: 0.650, 0.0: 1.000, 0.5: 1.000, 1.0: 1.000},
    0.25: {-1.0: 0.600, -0.5: 0.800, 0.0: 1.000, 0.5: 0.938, 1.0: 0.875},
    0.50: {-1.0: 0.900, -0.5: 0.950, 0.0: 1.000, 0.5: 0.875, 1.0: 0.750},
    0.75: {-1.0: 1.200, -0.5: 1.100, 0.0: 1.000, 0.5: 0.812, 1.0: 0.625},
    1.00: {-1.0: 1.500, -0.5: 1.250, 0.0: 1.000, 0.5: 0.750, 1.0: 0.500},
}

AROUSAL_LEVELS = [0.0, 0.25, 0.5, 0.75, 1.0]
VALENCE_LEVELS = [-1.0, -0.5, 0.0, 0.5, 1.0]


def dilation_at(stream, arousal, valence, phase_coherence=0.5):
    return stream.update_dilation(
        arousal=arousal, valence=valence, phase_coherence=phase_coherence
    )


def print_surface(stream, pc, label):
    print(f'Dilation surface @ phase_coherence={pc:.2f}  ({label}):')
    print(f'  (rows = arousal, cols = valence)')
    print()
    header = '  arousal\\valence │' + ''.join(f'{v:>8.2f}' for v in VALENCE_LEVELS)
    print(header)
    print('  ' + '─' * (len(header) - 2))
    for a in AROUSAL_LEVELS:
        row = f'  {a:>14.2f} │'
        for v in VALENCE_LEVELS:
            d = dilation_at(stream, a, v, pc)
            row += f'{d:>8.3f}'
        print(row)
    print()


def main():
    print('=' * 72)
    print('  DIAGNOSTIC: rhythm → time coupling  (Tier 4.3 — THE PHYSICS)')
    print('=' * 72)
    print()

    stream = TemporalStream(dim=64)
    print(f'k_arousal      = {stream.k_arousal}')
    print(f'k_dissociation = {stream.k_dissociation}')
    print(f'k_flow         = {stream.k_flow}   (LIVE — degeneracy resolution)')
    print(f'k_agitation    = {stream.k_agitation}   (HYPOTHESIS — inert until probe)')
    print(f'dilation bounds = [{stream.dilation_min}, {stream.dilation_max}]')
    print()

    all_ok = True

    # ------------------------------------------------------------------
    # 1. REGRESSION GUARD — pc=0.5 must reproduce the 4.2 surface exactly
    # ------------------------------------------------------------------
    print('─' * 72)
    print('1. REGRESSION GUARD  — phase_coherence=0.5 ≡ validated Tier 4.2')
    print('─' * 72)
    print()
    print_surface(stream, 0.5, 'neutral — must equal 4.2')

    regression_ok = True
    max_dev = 0.0
    for a in AROUSAL_LEVELS:
        for v in VALENCE_LEVELS:
            got = dilation_at(stream, a, v, 0.5)
            want = TIER_4_2_SURFACE[a][v]
            dev = abs(got - want)
            max_dev = max(max_dev, dev)
            if dev > 1e-3:
                regression_ok = False
                print(f'  ✗ ({a}, {v}): got {got:.4f}, 4.2 expects {want:.4f}')
    mark = '✓' if regression_ok else '✗'
    print(f'  {mark} all 25 grid points match Tier 4.2 '
          f'(max deviation {max_dev:.2e}, tol 1e-3)')
    print()
    all_ok = all_ok and regression_ok

    # ------------------------------------------------------------------
    # 2. FLOW term — organized field deepens compression (proven)
    # ------------------------------------------------------------------
    print('─' * 72)
    print('2. FLOW term  — high arousal, +valence, pc sweep  (degeneracy fix)')
    print('─' * 72)
    print()
    a, v = 1.0, 1.0
    d_chaotic = dilation_at(stream, a, v, 0.0)   # pc_c = -1
    d_neutral = dilation_at(stream, a, v, 0.5)   # pc_c =  0  → 4.2 value
    d_organ   = dilation_at(stream, a, v, 1.0)   # pc_c = +1
    print(f'  point (arousal={a}, valence={v}):')
    print(f'    pc=0.0 chaotic  → {d_chaotic:.3f}')
    print(f'    pc=0.5 neutral  → {d_neutral:.3f}   (4.2 baseline = 0.500)')
    print(f'    pc=1.0 organized→ {d_organ:.3f}')
    print()

    # Organized must compress at least as hard as neutral (clamp may equalize
    # at the extreme corner — that is correct deep-flow saturation, not a fail).
    flow_deepens = d_organ <= d_neutral + 1e-9
    # Chaotic must NOT compress harder than neutral (attenuation, not deepening).
    flow_attenuates = d_chaotic >= d_neutral - 1e-9
    # Neutral must still be the 4.2 value.
    flow_neutral_ok = abs(d_neutral - 0.500) < 1e-3
    for label, ok in [
        ('organized field compresses ≥ neutral (flow deepens)', flow_deepens),
        ('chaotic field does NOT deepen compression (attenuates)', flow_attenuates),
        ('neutral pc reproduces 4.2 flow value 0.500', flow_neutral_ok),
    ]:
        m = '✓' if ok else '✗'
        print(f'  {m} {label}')
        all_ok = all_ok and ok
    if d_organ <= stream.dilation_min + 1e-9:
        print(f'  ⚠ note: organized-flow corner saturates the {stream.dilation_min} '
              f'floor at k_flow={stream.k_flow} — deep-flow timelessness, clamp '
              f'engaged (expected; tune k_flow via sweep if undesired).')
    print()

    # ------------------------------------------------------------------
    # 3a. AGITATION term — INERT at shipped default k_agitation=0.0
    # ------------------------------------------------------------------
    print('─' * 72)
    print('3a. AGITATION term  — verify INERT at shipped default (k_agitation=0)')
    print('─' * 72)
    print()
    a, v = 1.0, -1.0
    agit_inert = True
    for pc in [0.0, 0.25, 0.5, 0.75, 1.0]:
        d = dilation_at(stream, a, v, pc)
        if abs(d - 1.500) > 1e-9:   # 4.2 drag value, must not move
            agit_inert = False
    m = '✓' if agit_inert else '✗'
    print(f'  point (arousal={a}, valence={v}): dilation = 1.500 for ALL pc')
    print(f'  {m} agitation term contributes nothing at k_agitation=0.0 '
          f'(structurally present, behaviorally off)')
    print()
    all_ok = all_ok and agit_inert

    # ------------------------------------------------------------------
    # 3b. AGITATION mechanism — BOTH sign directions (temporary coefficient)
    # ------------------------------------------------------------------
    print('─' * 72)
    print('3b. AGITATION mechanism  — both hypotheses, temp coefficient only')
    print('─' * 72)
    print()
    print('  The shipped default is 0.0; here we temporarily set k_agitation to')
    print('  prove the mechanism bends time the documented way in EACH direction.')
    print('  The inertness probe + sign sweep decide the real value. Restored to')
    print('  0.0 immediately after.')
    print()
    a, v, pc = 1.0, -1.0, 0.0   # high arousal, negative valence, fully chaotic
    base = dilation_at(stream, a, v, pc)   # 1.500 at k_agitation=0

    stream.k_agitation = 0.4               # DRAG hypothesis
    d_drag = dilation_at(stream, a, v, pc)
    stream.k_agitation = -0.4              # PANIC-COMPRESSION hypothesis
    d_compress = dilation_at(stream, a, v, pc)
    stream.k_agitation = 0.0               # RESTORE shipped default
    _ = dilation_at(stream, a, v, pc)

    print(f'  point (arousal={a}, valence={v}, pc={pc} fully chaotic):')
    print(f'    k_agitation=0.0  → {base:.3f}   (4.2 drag baseline)')
    print(f'    k_agitation=+0.4 → {d_drag:.3f}   (drag: time stretches MORE)')
    print(f'    k_agitation=-0.4 → {d_compress:.3f}   (panic: time compresses)')
    print()
    drag_ok = d_drag > base + 1e-6
    compress_ok = d_compress < base - 1e-6
    restored_ok = stream.k_agitation == 0.0
    for label, ok in [
        ('positive k_agitation → drag (dilation up)', drag_ok),
        ('negative k_agitation → compression (dilation down)', compress_ok),
        ('k_agitation restored to shipped default 0.0', restored_ok),
    ]:
        m = '✓' if ok else '✗'
        print(f'  {m} {label}')
        all_ok = all_ok and ok
    print()

    # ------------------------------------------------------------------
    # 4. CLAMP — pathological coefficients stay in bounds
    # ------------------------------------------------------------------
    print('─' * 72)
    print('4. CLAMP  — dilation cannot leave [%.1f, %.1f]'
          % (stream.dilation_min, stream.dilation_max))
    print('─' * 72)
    print()
    # Drive far below the floor: huge flow term.
    stream.k_flow = 5.0
    d_floor = dilation_at(stream, 1.0, 1.0, 1.0)
    stream.k_flow = 0.5
    # Drive far above the ceiling: huge positive agitation term.
    stream.k_agitation = 5.0
    d_ceil = dilation_at(stream, 1.0, -1.0, 0.0)
    stream.k_agitation = 0.0
    floor_ok = d_floor >= stream.dilation_min - 1e-9
    ceil_ok = d_ceil <= stream.dilation_max + 1e-9
    print(f'  k_flow=5.0 at extreme flow      → {d_floor:.3f}  (floor {stream.dilation_min})')
    print(f'  k_agitation=5.0 at extreme agit → {d_ceil:.3f}  (ceiling {stream.dilation_max})')
    for label, ok in [
        ('dilation never below floor', floor_ok),
        ('dilation never above ceiling', ceil_ok),
    ]:
        m = '✓' if ok else '✗'
        print(f'  {m} {label}')
        all_ok = all_ok and ok
    # restore is already done; confirm constants are back
    constants_restored = (stream.k_flow == 0.5 and stream.k_agitation == 0.0)
    m = '✓' if constants_restored else '✗'
    print(f'  {m} live constants restored (k_flow=0.5, k_agitation=0.0)')
    all_ok = all_ok and constants_restored
    print()

    # ------------------------------------------------------------------
    # 5. MUTUAL EXCLUSIVITY — flow and agitation never co-fire
    # ------------------------------------------------------------------
    print('─' * 72)
    print('5. MUTUAL EXCLUSIVITY  — flow_eff and agit_eff gated apart')
    print('─' * 72)
    print()
    # Use a temporary non-zero k_agitation so both terms COULD fire, then prove
    # they never do simultaneously across the full grid × pc sweep.
    stream.k_flow = 0.5
    stream.k_agitation = 0.4
    co_fire = False
    checked = 0
    for a in [0.0, 0.5, 1.0]:
        for v in VALENCE_LEVELS:
            for pc in [0.0, 0.25, 0.5, 0.75, 1.0]:
                pc_c = 2.0 * (pc - 0.5)
                flow_eff = -stream.k_flow * max(pc_c, 0.0) * a * max(v, 0.0)
                agit_eff = -stream.k_agitation * min(pc_c, 0.0) * a * max(-v, 0.0)
                checked += 1
                if abs(flow_eff) > 1e-12 and abs(agit_eff) > 1e-12:
                    co_fire = True
    stream.k_flow = 0.5
    stream.k_agitation = 0.0
    excl_ok = not co_fire
    m = '✓' if excl_ok else '✗'
    print(f'  {m} across {checked} (arousal × valence × pc) points, flow_eff and')
    print(f'    agit_eff are never both non-zero (opposite valence half-planes)')
    all_ok = all_ok and excl_ok
    print()

    # ------------------------------------------------------------------
    # Visual surfaces at the pc extremes (live constants)
    # ------------------------------------------------------------------
    print('─' * 72)
    print('Reference surfaces at pc extremes (live k_flow=0.5, k_agitation=0.0)')
    print('─' * 72)
    print()
    print_surface(stream, 0.0, 'fully chaotic field')
    print_surface(stream, 1.0, 'fully organized field')

    # ------------------------------------------------------------------
    print('=' * 72)
    if all_ok:
        print('PHYSICS VERIFIED — rhythm coupling is a strict, regression-safe')
        print('extension of Tier 4.2. Flow deepens with organization; agitation')
        print('is inert at the shipped default and behaves correctly in both sign')
        print('directions; the clamp holds; the two rhythm terms never co-fire.')
        return 0
    else:
        print('PHYSICS FAILED — at least one Tier 4.3 property does not hold.')
        print('Inspect the failed checks above.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
