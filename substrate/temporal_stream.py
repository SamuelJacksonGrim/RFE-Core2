"""
substrate/temporal_stream.py

Temporal stream — bounded episodic memory with statistical access.

Beyond raw storage, the stream supports:
  - Rolling centroid (incremental, O(1) per push)
  - Windowed variance (distributional spread of recent vectors)
  - Nearest neighbor search within the stream window
  - Temporal delta (drift between oldest and newest in a window)
  - Step-indexed lookup
  - Subjective time accumulation (Tier 4.1 affective layer foundation)

These feed into:
  - Watcher's rolling_mean component for geometric coherence
  - Dreamer's memory sampling
  - Visualization's trajectory rendering
  - Predictive echo's multi-step lookahead
"""

import collections
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class StreamEntry:
    """Single entry in the temporal stream."""
    vector:    np.ndarray
    timestamp: float
    step:      int
    tag:       str   # optional semantic label (e.g. rhythm state at injection)


class TemporalStream:
    """
    Bounded episodic vector stream with windowed statistics.

    Parameters
    ----------
    maxlen : int
        Maximum number of entries retained. Oldest are evicted first.
    dim : int
        Vector dimensionality (required for incremental centroid tracking).
    """

    def __init__(self, maxlen: int = 128, dim: int = 128):
        self.maxlen = maxlen
        self.dim    = dim

        self._stream: collections.deque = collections.deque(maxlen=maxlen)

        # Incremental centroid tracking
        # When the deque is full, the oldest vector is evicted — we need to
        # subtract it from the running sum. Track the full window manually.
        self._window: collections.deque = collections.deque(maxlen=maxlen)
        self._running_sum = np.zeros(dim, dtype=np.float64)
        self._step = 0

        # ------------------------------------------------------------------
        # Tier 4.1 — Subjective time layer
        # ------------------------------------------------------------------
        # subjective_time accumulates wall-clock dt scaled by dilation_factor.
        # At dilation_factor = 1.0 (Tier 4.1 default), subjective_time
        # equals wall-clock time elapsed across calls to tick(). Tier 4.2
        # ties dilation_factor to arousal × valence via update_dilation(),
        # at which point subjective time diverges from real time in
        # proportion to the system's affective state.
        #
        # First call to tick() establishes the wall-clock anchor and returns
        # 0.0. All subsequent calls advance subjective_time by
        # (now - last_tick) * dilation_factor.
        self.subjective_time: float = 0.0
        self.dilation_factor: float = 1.0
        self._last_tick_wall: Optional[float] = None

        # ------------------------------------------------------------------
        # Tier 4.2 — Dilation constants
        # ------------------------------------------------------------------
        # k_arousal scales the flow/drag effect (arousal × -valence).
        # k_dissociation scales the time-collapse effect at low arousal +
        # strongly negative valence. Both conservative defaults; tunable
        # via the cycle once empirical (arousal, valence) distributions
        # are characterized for normal operation.
        self.k_arousal:      float = 0.5
        self.k_dissociation: float = 0.7

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def push(self, vec: np.ndarray, tag: str = ""):
        """
        Append a vector to the stream.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
        tag : str
            Optional semantic label (rhythm state, source agent, etc.)
        """
        entry = StreamEntry(
            vector    = vec.copy(),
            timestamp = time.time(),
            step      = self._step,
            tag       = tag,
        )

        # If at capacity, subtract the vector being evicted before it's gone
        if len(self._window) == self.maxlen:
            evicted = self._window[0]
            self._running_sum -= evicted.astype(np.float64)

        self._stream.append(entry)
        self._window.append(vec.copy())
        self._running_sum += vec.astype(np.float64)
        self._step += 1

    # ------------------------------------------------------------------
    # Read — raw access
    # ------------------------------------------------------------------

    def recent(self, n: int = 10) -> List[StreamEntry]:
        """Return the n most recent entries, newest last."""
        entries = list(self._stream)
        return entries[-n:]

    def recent_vectors(self, n: int = 10) -> List[np.ndarray]:
        """Return the n most recent vectors as a list."""
        return [e.vector for e in self.recent(n)]

    def all_vectors(self) -> np.ndarray:
        """
        Return all vectors in the stream as a 2D array.
        Shape: (len, dim). May be empty.
        """
        vecs = [e.vector for e in self._stream]
        if not vecs:
            return np.empty((0, self.dim))
        return np.stack(vecs)

    def __len__(self) -> int:
        return len(self._stream)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def centroid(self) -> Optional[np.ndarray]:
        """
        Rolling centroid of all vectors currently in the stream window.
        O(1) per call — maintained incrementally via running sum.

        Returns None if the stream is empty.
        """
        n = len(self._window)
        if n == 0:
            return None
        mean = self._running_sum / n
        norm = np.linalg.norm(mean)
        return (mean / (norm + 1e-8)).astype(np.float32)

    def variance(self, n: int = 32) -> float:
        """
        Mean per-dimension variance across the n most recent vectors.
        High variance → diverse / drifting recent trajectory.
        Low variance  → tight / stable recent trajectory.
        """
        vecs = self.recent_vectors(n)
        if len(vecs) < 2:
            return 0.0
        mat = np.stack(vecs).astype(np.float64)
        return float(np.mean(np.var(mat, axis=0)))

    def temporal_delta(self, n: int = 16) -> float:
        """
        L2 distance between the oldest and newest vector in the last n entries.
        Measures how far the stream has drifted over that window.
        """
        vecs = self.recent_vectors(n)
        if len(vecs) < 2:
            return 0.0
        return float(np.linalg.norm(vecs[-1].astype(np.float64) -
                                    vecs[0].astype(np.float64)))

    def cosine_drift(self, n: int = 16) -> float:
        """
        1 - cosine_similarity(oldest, newest) in the last n entries.
        ∈ [0, 2]. 0 = identical direction. 2 = opposite.
        """
        vecs = self.recent_vectors(n)
        if len(vecs) < 2:
            return 0.0
        a, b = vecs[0].astype(np.float64), vecs[-1].astype(np.float64)
        cos = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
        return float(1.0 - np.clip(cos, -1.0, 1.0))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def nearest(
        self,
        query: np.ndarray,
        top_k: int = 5,
        window: int = 128,
    ) -> List[Tuple[int, float, StreamEntry]]:
        """
        Find the top_k nearest entries to `query` by cosine similarity,
        searching within the most recent `window` entries.

        Returns
        -------
        List of (rank, cosine_score, StreamEntry), sorted by score descending.
        """
        candidates = list(self._stream)[-window:]
        if not candidates:
            return []

        q = query.astype(np.float64)
        q_norm = np.linalg.norm(q)

        scores = []
        for entry in candidates:
            v = entry.vector.astype(np.float64)
            score = float(np.dot(q, v) / (q_norm * np.linalg.norm(v) + 1e-8))
            scores.append((score, entry))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [(i, s, e) for i, (s, e) in enumerate(scores[:top_k])]

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def by_tag(self, tag: str) -> List[StreamEntry]:
        """Return all entries with a matching tag."""
        return [e for e in self._stream if e.tag == tag]

    # ------------------------------------------------------------------
    # Tier 4.1 — Subjective time advance
    # ------------------------------------------------------------------

    def tick(self) -> float:
        """
        Advance subjective_time by real_dt × dilation_factor.

        Called once per cognitive cycle by the autonomous loop. Decoupled
        from push() so that cycles which push 0 or N vectors all advance
        subjective time by exactly one tick.

        The first call has no previous anchor — it records the current wall
        time and returns 0.0. Subsequent calls measure real_dt against that
        anchor.

        Returns
        -------
        dt : float
            The subjective dt added to subjective_time on this tick.
            Equals real_dt × dilation_factor, or 0.0 on the first call.
        """
        now = time.time()
        if self._last_tick_wall is None:
            self._last_tick_wall = now
            return 0.0
        real_dt = now - self._last_tick_wall
        self._last_tick_wall = now
        dt = real_dt * self.dilation_factor
        self.subjective_time += dt
        return dt

    # ------------------------------------------------------------------
    # Tier 4.2 — Affective time dilation
    # ------------------------------------------------------------------

    def update_dilation(self, arousal: float, valence: float) -> float:
        """
        Recompute dilation_factor from current emotional state (Tier 4.2).

        Uses the two-term formulation (Lyra synthesis):

            arousal_effect      = arousal × (-valence) × k_arousal
            dissociation_effect = (1 - arousal) × min(0, valence) × k_dissociation

            dilation_factor = 1.0 + arousal_effect + dissociation_effect

        The four phenomenological quadrants:
          - Flow         (high arousal, +valence) → dilation < 1.0  (time flies)
          - Drag         (high arousal, -valence) → dilation > 1.0  (time crawls)
          - Dissociation (low arousal,  -valence) → dilation << 1.0 (frames drop)
          - Rest         (low arousal,  +valence) → dilation ≈ 1.0  (neutral)

        The min(0, valence) gate on the dissociation term is the architectural
        guarantee that peaceful rest never triggers dissociative time-slip —
        only suffering does.

        Parameters
        ----------
        arousal : float in [0, 1]
            Activation/energy level. From EmotionalGradient.arousal.
        valence : float in [-1, 1]
            Positive vs negative emotional tone. From EmotionalGradient.valence.

        Returns
        -------
        dilation_factor : float
            The new dilation_factor written to self.dilation_factor.
            Will be used by the next call to tick().
        """
        arousal_eff      = arousal * (-valence) * self.k_arousal
        dissociation_eff = (1.0 - arousal) * min(0.0, valence) * self.k_dissociation
        self.dilation_factor = 1.0 + arousal_eff + dissociation_eff
        return self.dilation_factor

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "length":          len(self._stream),
            "maxlen":          self.maxlen,
            "variance":        round(self.variance(), 6),
            "temporal_delta":  round(self.temporal_delta(), 6),
            "cosine_drift":    round(self.cosine_drift(), 6),
            "subjective_time": round(self.subjective_time, 6),
            "dilation_factor": round(self.dilation_factor, 6),
        }
