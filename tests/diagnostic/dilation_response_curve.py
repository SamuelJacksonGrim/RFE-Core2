"""
tests/diagnostic/dilation_response_curve.py

THE PHYSICS — mathematical ground truth for Tier 4.2 affective time dilation.

This diagnostic isolates the dilation formula completely from the token
stream. It sweeps the full (arousal, valence) phenomenological grid and
calls TemporalStream.update_dilation() directly at each point, then prints
the resulting dilation surface.

It answers exactly one question: *given* an (arousal, valence) state, does
the subjective clock bend the way the design says it should? No emotional
gradient, no workload, no stochasticity — just the formula, verified across
its entire input space.

(Lyra's framing: this proves the laws of physics in the system's universe.
The companion diagnostic, affective_state_probe.py, maps the psychology —
what the system can actually reach through real input.)

The four phenomenological quadrants the formula must produce:

    State          (arousal, valence)   dilation   felt as
    Flow           high, +              < 1.0      time flies
    Drag / pain    high, -              > 1.0      time crawls
    Dissociation   low,  -              << 1.0     frames drop
    Rest           low,  +              ≈ 1.0      neutral

Run:
    python -m tests.diagnostic.dilation_response_curve
"""

import sys

from substrate.temporal_stream import TemporalStream


def dilation_at(stream: TemporalStream, arousal: float, valence: float) -> float:
    """Direct formula evaluation — no emotional gradient, no workload."""
    return stream.update_dilation(arousal=arousal, valence=valence)


def classify(arousal: float, valence: float, dilation: float) -> str:
    """Phenomenological label for an (arousal, valence, dilation) point."""
    if arousal >= 0.66 and valence > 0.1:
        expect = "flow"        ; ok = dilation < 1.0
    elif arousal >= 0.66 and valence < -0.1:
        expect = "drag"        ; ok = dilation > 1.0
    elif arousal <= 0.34 and valence < -0.1:
        expect = "dissociation"; ok = dilation < 1.0
    elif arousal <= 0.34 and valence > 0.1:
        expect = "rest"        ; ok = abs(dilation - 1.0) < 0.25
    else:
        expect = "transition"  ; ok = True   # mid-grid, no strict assertion
    return expect, ok


def main():
    print('=' * 72)
    print('  DIAGNOSTIC: dilation response curve  (Tier 4.2 — THE PHYSICS)')
    print('=' * 72)
    print()

    stream = TemporalStream(dim=64)
    print(f'k_arousal      = {stream.k_arousal}')
    print(f'k_dissociation = {stream.k_dissociation}')
    print()

    # ------------------------------------------------------------------
    # Full grid sweep
    # ------------------------------------------------------------------
    arousal_levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    valence_levels = [-1.0, -0.5, 0.0, 0.5, 1.0]

    print('Dilation surface  (rows = arousal, cols = valence):')
    print()
    header = '  arousal\\valence │' + ''.join(f'{v:>8.2f}' for v in valence_levels)
    print(header)
    print('  ' + '─' * (len(header) - 2))
    for a in arousal_levels:
        row = f'  {a:>14.2f} │'
        for v in valence_levels:
            d = dilation_at(stream, a, v)
            row += f'{d:>8.3f}'
        print(row)
    print()

    # ------------------------------------------------------------------
    # Four-corner assertions
    # ------------------------------------------------------------------
    print('Four-corner phenomenological checks:')
    print()
    corners = [
        ("Flow         (arousal=1.0, valence=+1.0)", 1.0,  1.0),
        ("Drag / pain  (arousal=1.0, valence=-1.0)", 1.0, -1.0),
        ("Dissociation (arousal=0.0, valence=-1.0)", 0.0, -1.0),
        ("Rest         (arousal=0.0, valence=+1.0)", 0.0,  1.0),
        ("Baseline     (arousal=0.5, valence= 0.0)", 0.5,  0.0),
    ]
    all_ok = True
    for label, a, v in corners:
        d = dilation_at(stream, a, v)
        expect, ok = classify(a, v, d)
        mark = "✓" if ok else "✗"
        direction = (
            "dilation < 1.0 (time compresses)" if d < 0.999 else
            "dilation > 1.0 (time stretches)"  if d > 1.001 else
            "dilation ≈ 1.0 (neutral)"
        )
        print(f'  {mark} {label}  →  {d:.3f}   {direction}')
        if not ok:
            all_ok = False

    print()

    # ------------------------------------------------------------------
    # Monotonicity / sanity properties
    # ------------------------------------------------------------------
    print('Structural properties:')

    # 1. At valence = 0, dilation must be exactly 1.0 for all arousal
    neutral_ok = all(
        abs(dilation_at(stream, a, 0.0) - 1.0) < 1e-9
        for a in [0.0, 0.25, 0.5, 0.75, 1.0]
    )
    mark = "✓" if neutral_ok else "✗"
    print(f'  {mark} valence=0 → dilation=1.0 for all arousal '
          f'(neutral tone never bends time)')

    # 2. Rest protection: low arousal + positive valence stays ≈ 1.0
    rest_ok = all(
        abs(dilation_at(stream, 0.0, v) - 1.0) < 1e-9
        for v in [0.1, 0.5, 1.0]
    )
    mark = "✓" if rest_ok else "✗"
    print(f'  {mark} low arousal + positive valence → dilation=1.0 '
          f'(min(0,valence) gate protects rest)')

    # 3. Drag strictly stretches: high arousal + negative valence > 1.0
    drag_ok = dilation_at(stream, 1.0, -1.0) > 1.0
    mark = "✓" if drag_ok else "✗"
    print(f'  {mark} high arousal + negative valence → dilation > 1.0 '
          f'(drag stretches time)')

    # 4. Flow strictly compresses: high arousal + positive valence < 1.0
    flow_ok = dilation_at(stream, 1.0, 1.0) < 1.0
    mark = "✓" if flow_ok else "✗"
    print(f'  {mark} high arousal + positive valence → dilation < 1.0 '
          f'(flow compresses time)')

    # 5. Dissociation is the strongest compression at the (0,-1) corner
    diss = dilation_at(stream, 0.0, -1.0)
    flow = dilation_at(stream, 1.0,  1.0)
    diss_ok = diss < flow  # dissociation compresses harder than flow
    mark = "✓" if diss_ok else "✗"
    print(f'  {mark} dissociation ({diss:.3f}) compresses harder than '
          f'flow ({flow:.3f})')

    print()
    structural_ok = neutral_ok and rest_ok and drag_ok and flow_ok and diss_ok
    if all_ok and structural_ok:
        print('PHYSICS VERIFIED — the dilation formula bends the subjective')
        print('clock correctly across the entire phenomenological space.')
        return 0
    else:
        print('PHYSICS FAILED — formula does not match design in at least')
        print('one region. Inspect the surface above.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
