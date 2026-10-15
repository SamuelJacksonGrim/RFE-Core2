"""
tests/smoke/emotion_checkpoint_roundtrip.py

The speech bridge's checkpoint must carry emotion across a restart. Before
2026-10-14 it saved only arousal/valence (read-only, derived) and the loader's
assignment threw inside a swallowed except, so emotion silently reset to its
defaults on every restart. Now the six scalars are the saved state and
arousal/valence ride along as a record.

Checks: after real steps move the emotion off its defaults, save -> fresh
stack -> load restores all six scalars, arousal and valence recompute to the
same values, and an old-format checkpoint (arousal/valence only) is refused
without touching state.

Run:
    python -m tests.smoke.emotion_checkpoint_roundtrip
"""

import os
import sys
import tempfile

from tests._common import build_full_stack
from tools.voice.repl_qwen import load_checkpoint, save_checkpoint

SCALARS = ("curiosity", "wonder", "joy", "tension", "boredom", "stability")


def main():
    print('=' * 72)
    print('  SMOKE: emotion survives a bridge checkpoint round-trip')
    print('=' * 72)

    gen, cycle, gov, ve = build_full_stack()
    defaults = {k: getattr(cycle.emotion, k) for k in SCALARS}
    for i in range(40):
        cycle.step(tokens=['signal', 'pattern', f'novel{i}'], source_id='smoke', origin_type='internal')
    before = {k: getattr(cycle.emotion, k) for k in SCALARS}
    moved = [k for k in SCALARS if abs(before[k] - defaults[k]) > 1e-6]
    assert moved, "40 steps did not move any emotion scalar; the test would prove nothing"

    path = os.path.join(tempfile.mkdtemp(), 'ck.json')
    save_checkpoint(path, gen, cycle, ve)

    gen2, cycle2, gov2, ve2 = build_full_stack()
    restored, _saved_at = load_checkpoint(path, gen2, cycle2, ve2)
    assert 'emotion' in restored, f"emotion not restored (restored={restored})"
    for k in SCALARS:
        assert abs(getattr(cycle2.emotion, k) - before[k]) < 1e-9, f"{k} did not round-trip"
    assert abs(cycle2.emotion.arousal - cycle.emotion.arousal) < 1e-9
    assert abs(cycle2.emotion.valence - cycle.emotion.valence) < 1e-9

    gen3, cycle3, gov3, ve3 = build_full_stack()
    old = {'arousal': 0.9, 'valence': -0.5, 'step': 7}
    snap = cycle3.emotion.snapshot()
    assert cycle3.emotion.restore(old) is False, "old-format checkpoint should be refused"
    assert cycle3.emotion.snapshot() == snap, "a refused restore must not change state"

    print(f'  moved by 40 steps: {", ".join(moved)}')
    print(f'  restored: {restored}')
    print(f'  arousal {cycle2.emotion.arousal:.4f}  valence {cycle2.emotion.valence:.4f} (match)')
    print('Emotion round-trips; old-format checkpoints are refused cleanly.')


if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print(f'FAIL: {e}')
        sys.exit(1)
