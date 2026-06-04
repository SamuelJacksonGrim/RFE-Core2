"""
cognition/stream_metastability.py — online metastability over a vector stream.

The loop's stethoscope on its own config dynamics, read at two cycle stages:
  - the GENERATOR output (stage A — raw generated vector, before attractor-pull
    and refinement): where the system's expressive diversity originates, and
  - the EXPRESSION (stage C — post recursive-attention refinement, what is
    actually injected into the field): where the de-collapse blend is validated.

Fix 1's metastability metric (substrate/metastability.py) measures whether a
TRAJECTORY hovers among several shallow, semi-stable configurations and switches
between them aperiodically — the "paper boat" health signature, as opposed to
rigid-attractor lock-in. The lock-in remediation work established WHERE to read
it: UPSTREAM, on these per-stage vector streams, not on the integrated resonance
field. The field's long-memory decay (decay ∈ [0.97,0.9999], the identity-
persistence invariant) is a heavy integrator that smooths config wander away by
construction; metastability cannot live there. It lives in the generator's
output (diverse, ~10 regimes) — which untrained recursive attention then
collapses unless the diversity-preservation blend weights the raw vector back in.

This class wraps compute_metastability for ONLINE use over ANY such stream:
  - a bounded ring of the most recent vectors (O(1) append), and
  - a lazy recompute, run once every `interval` observations, so the metric never
    sits on the per-step hot path.

It is an OPTIONAL instrument: the loop runs identically without it, and it only
OBSERVES — never feeds back into cognition or governance. Like dilation_factor it
is a terminal sink, read by diagnostics (and, later, by the Fix 0-B survival/
selection formula as the counterweight to coherence's lock-in-breeding pressure).
"""

from __future__ import annotations

from collections import deque

import numpy as np

from substrate.metastability import compute_metastability, MetastabilityReport


class StreamMetastabilityMonitor:
    """Sliding-window metastability over a vector stream (generator or expression).

    Parameters
    ----------
    window : int
        Ring-buffer size — how many recent vectors the metric sees. Must be >= 4
        (compute_metastability needs at least that to assess).
    interval : int
        Recompute cadence: the report is refreshed once every `interval`
        observations, keeping the per-step cost to an O(1) append. On-demand
        callers can force a fresh read with compute_now().
    min_samples : int
        Defer the first recompute until the ring holds at least this many
        samples, so an early reading isn't dominated by warmup transients.
    """

    def __init__(self, window: int = 128, interval: int = 16, min_samples: int = 16):
        if window < 4:
            raise ValueError("window must be >= 4 (metric needs >=4 samples)")
        self.window      = window
        self.interval    = max(1, interval)
        self.min_samples = max(4, min(min_samples, window))

        self._vecs: deque = deque(maxlen=window)
        self._seen: int   = 0
        self._report: MetastabilityReport = MetastabilityReport(notes="no samples yet")

    def observe(self, vec: np.ndarray) -> None:
        """Record one vector from the observed stream.

        Cheap: an O(1) copy + append. The metastability report is recomputed
        lazily — only on every `interval`-th observation — so this stays off the
        hot path. A copy is stored so later in-place mutation of `vec` downstream
        (attractor pull, refinement) cannot corrupt the recorded trajectory.
        """
        self._vecs.append(np.asarray(vec, dtype=float).copy())
        self._seen += 1
        if len(self._vecs) >= self.min_samples and self._seen % self.interval == 0:
            self._recompute()

    def _stream_alignment(self) -> float:
        """Mean cosine alignment of the windowed stream — the metric's coherence
        context, derived from the STREAM ITSELF, not the field. The locked-vs-
        structureless label needs a coherence proxy; for an upstream stream that
        proxy is how aligned the stream's own directions are (high => collapsed to
        one direction => 'locked'; low => scattered => 'structureless'). Borrowing
        the field's coherence here would be a category error — it would let the
        field's rigidity mislabel a diverse generator stream as locked."""
        n = len(self._vecs)
        if n < 2:
            return 0.0
        units = [v / (np.linalg.norm(v) + 1e-12) for v in self._vecs]
        # local pairwise cosine (each step vs the next few) — O(n·k), captures
        # run-to-run alignment without an O(n^2) full matrix.
        sims, k = [], 12
        for i in range(n):
            for j in range(i + 1, min(i + k, n)):
                sims.append(float(np.dot(units[i], units[j])))
        return float(np.mean(sims)) if sims else 0.0

    def _recompute(self) -> None:
        self._report = compute_metastability(
            list(self._vecs), coherence=self._stream_alignment()
        )

    def compute_now(self) -> MetastabilityReport:
        """Force an immediate recompute over the current window (on-demand read)."""
        if len(self._vecs) >= 4:
            self._recompute()
        return self._report

    @property
    def report(self) -> MetastabilityReport:
        """The most recent cached report (may be up to `interval` steps stale)."""
        return self._report

    def snapshot(self) -> dict:
        """Compact, governance-legible view for status() dumps."""
        r = self._report
        return {
            "metastability": r.metastability,
            "state":         r.regime_state,
            "n_regimes":     r.n_regimes,
            "samples":       len(self._vecs),
            "window":        self.window,
            "seen":          self._seen,
        }
