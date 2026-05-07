"""
substrate/temporal_stream.py

Temporal stream — bounded episodic memory with statistical access.

Beyond raw storage, the stream supports:
  - Rolling centroid (incremental, O(1) per push)
  - Windowed variance (distributional spread of recent vectors)
  - Nearest neighbor search within the stream window
  - Temporal delta (drift between oldest and newest in a window)
  - Step-indexed lookup

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
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "length":         len(self._stream),
            "maxlen":         self.maxlen,
            "variance":       round(self.variance(), 6),
            "temporal_delta": round(self.temporal_delta(), 6),
            "cosine_drift":   round(self.cosine_drift(), 6),
        }
