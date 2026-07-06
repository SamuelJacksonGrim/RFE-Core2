"""
tests/smoke/stream_recorder_smoke.py

Smoke test for the observe-only StreamRecorder (cognition/stream_recorder.py)
— the operational-vocabulary coverage census (data_curation.md §5).

Verifies:
  1. attach + record — one record per step, exact ring behavior at the window
  2. census / uncovered — token counts and the coverage-gap view are correct
  3. snapshot — surfaces through cycle.status()["stream_recorder"]
  4. dump_jsonl — round-trips the window to disk, corpus-adjacent schema
  5. observe-only — a cycle without a recorder has stream_recorder None and
     steps identically (no attribute errors, no status key)

Run:
    python -m tests.smoke.stream_recorder_smoke
"""

import json
import tempfile
from pathlib import Path

from cognition.stream_recorder import StreamRecorder
from tests._common import build_full_stack, RESONANCE_FAMILY_SOURCES


def main():
    print('=' * 72)
    print('  SMOKE: stream recorder (observe-only coverage census)')
    print('=' * 72)
    print()

    # --- default: absent, cycle steps identically -------------------------
    generator, cycle, governance, value_engine = build_full_stack()
    assert cycle.stream_recorder is None, "recorder must be opt-in (None by default)"
    cycle.step(['warmup', 'no', 'recorder'], source_id='source_samuel',
               origin_type='internal')
    assert 'stream_recorder' not in cycle.status(), \
        "status must not carry a recorder key when none is attached"

    # --- attach + record ---------------------------------------------------
    recorder = StreamRecorder(window=16)
    cycle.attach_stream_recorder(recorder)

    n_steps = 24  # > window: exercises the bounded-ring eviction
    sources = list(RESONANCE_FAMILY_SOURCES.keys())
    for i in range(n_steps):
        sid = sources[i % len(sources)]
        seq = RESONANCE_FAMILY_SOURCES[sid][i % len(RESONANCE_FAMILY_SOURCES[sid])]
        cycle.step(seq, source_id=sid, origin_type='internal')

    snap = recorder.snapshot()
    assert snap['records'] == 16, f"ring must cap at window: {snap['records']}"
    assert snap['total_observed'] == n_steps, \
        f"total_observed must count every step: {snap['total_observed']}"
    assert set(snap['sources']) <= set(sources), f"unexpected sources: {snap['sources']}"
    assert all(d in ('ALLOW', 'ALLOW_WEAKENED', 'MONITOR', 'QUARANTINE',
                     'REJECT', 'SACRED_SHIELD')
               for d in snap['decisions']), f"unexpected decisions: {snap['decisions']}"

    # --- census / uncovered --------------------------------------------------
    census = recorder.census()
    assert census, "census must be non-empty after recording"
    assert sum(census.values()) == sum(len(r['tokens']) for r in recorder._ring)
    seen = set(census)
    gap = recorder.uncovered(seen - {'witness'})
    assert 'witness' in gap or 'witness' not in seen, \
        "uncovered() must report tokens missing from the given vocab"
    assert recorder.uncovered(seen) == [], "full vocab means empty coverage gap"

    # --- status surfacing ----------------------------------------------------
    st = cycle.status()
    assert st.get('stream_recorder', {}).get('records') == 16, \
        "recorder snapshot must surface through cycle.status()"

    # --- dump round-trip -----------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'stream.jsonl'
        n = recorder.dump_jsonl(path)
        lines = [json.loads(l) for l in path.read_text().splitlines()]
        assert n == 16 and len(lines) == 16, "dump must write the full window"
        assert set(lines[0]) == {'step', 'tokens', 'source', 'rhythm', 'decision'}, \
            f"unexpected record schema: {sorted(lines[0])}"

    print(f'  records (window/total):  {snap["records"]}/{snap["total_observed"]}')
    print(f'  unique tokens censused:  {snap["unique_tokens"]}')
    print(f'  sources seen:            {sorted(snap["sources"])}')
    print(f'  decisions seen:          {sorted(snap["decisions"])}')
    print()
    print('SMOKE PASSED — recorder is bounded, observe-only, and censuses correctly.')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
