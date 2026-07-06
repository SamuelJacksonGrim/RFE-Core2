"""
cognition/stream_recorder.py — observe-only census of the live token stream.

The `docs/training/data_curation.md` §5 open item made real: "a deque-bounded
stream recorder would make the operational-vocabulary census trivial and is
observe-only."

The corpus lesson (2026-06-11 effect probe) is mechanical: training only
restructures tokens the corpus covers; a token the corpus never saw keeps its
untrained, collinear geometry no matter how well everything else is tuned.
Coverage is the binding constraint — and the only honest census of what the
system actually encounters is taken at the loop itself. This recorder is that
census instrument: a bounded ring of (step, tokens, source, rhythm, decision)
records, appended once per cycle.

It is an INSTRUMENT in the strict repo sense — the same discipline as
`dilation_factor` and `StreamMetastabilityMonitor`: an observe-only terminal
sink, O(1) append on the hot path, never read by the cognitive or governance
loop. The governance decision is *recorded*, not consulted, so future corpus
curation can be trust-gated (data_curation.md §4: "no quarantined sources")
without re-deriving history.

All derived views (census, source mix, uncovered tokens) are computed lazily
from the bounded ring, so the recorder holds no unbounded state regardless of
how many unique token strings external callers inject.
"""

from __future__ import annotations

import json
from collections import Counter, deque
from typing import Deque, Iterable, List, Set

__all__ = ["StreamRecorder"]


class StreamRecorder:
    """Bounded, observe-only ring of per-step token-stream records.

    Parameters
    ----------
    window : int
        Ring size — how many recent steps the census sees. The ring is the
        only storage; every derived view is recomputed from it on demand.
    """

    def __init__(self, window: int = 4096):
        if window < 1:
            raise ValueError("window must be >= 1")
        self._ring: Deque[dict] = deque(maxlen=window)
        self._total_observed: int = 0   # scalar, monotonic — how many ever seen

    # ------------------------------------------------------------------
    # Hot path
    # ------------------------------------------------------------------

    def observe(
        self,
        step:      int,
        tokens:    List[str],
        source_id: str,
        rhythm:    str,
        decision:  str,
    ) -> None:
        """Record one step's consumed input. O(1); never raises on content."""
        self._ring.append({
            "step":     int(step),
            "tokens":   list(tokens),
            "source":   source_id,
            "rhythm":   rhythm,
            "decision": decision,
        })
        self._total_observed += 1

    # ------------------------------------------------------------------
    # Derived views (lazy, off the hot path)
    # ------------------------------------------------------------------

    def census(self) -> Counter:
        """Token → occurrence count over the window."""
        c: Counter = Counter()
        for rec in self._ring:
            c.update(rec["tokens"])
        return c

    def uncovered(self, vocab: Iterable[str]) -> List[str]:
        """Tokens seen live in the window but absent from `vocab` (e.g. the
        corpus training vocabulary) — the coverage gap, sorted by frequency
        (most-seen first) then alphabetically."""
        vocab_set: Set[str] = set(vocab)
        gap = {t: n for t, n in self.census().items() if t not in vocab_set}
        return sorted(gap, key=lambda t: (-gap[t], t))

    def snapshot(self) -> dict:
        """Small status card (for `AutonomousCycle.status()` / diagnostics)."""
        sources: Counter = Counter(rec["source"] for rec in self._ring)
        decisions: Counter = Counter(rec["decision"] for rec in self._ring)
        return {
            "window":         self._ring.maxlen,
            "records":        len(self._ring),
            "total_observed": self._total_observed,
            "unique_tokens":  len(self.census()),
            "sources":        dict(sources),
            "decisions":      dict(decisions),
        }

    def dump_jsonl(self, path) -> int:
        """Write the window to a JSONL file (one record per line, corpus-
        adjacent schema). Returns the number of records written. This is how
        a run's lived vocabulary becomes reviewable curation input — the
        records are *candidates* for a future corpus version, never fed back
        into anything automatically."""
        n = 0
        with open(path, "w", encoding="utf-8") as f:
            for rec in self._ring:
                f.write(json.dumps(rec) + "\n")
                n += 1
        return n
