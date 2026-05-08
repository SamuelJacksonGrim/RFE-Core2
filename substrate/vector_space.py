"""
substrate/vector_space.py

Semantic vector memory store.

Beyond flat key→vector storage:
  - Cosine nearest-neighbor search (vectorized, O(n) but fast in numpy)
  - Batch put / batch get
  - Semantic clustering: group vectors by centroid proximity
  - Staleness tracking: vectors age and can be evicted
  - Integration hooks for TopologicalLog centrality signals
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

@dataclass
class VectorEntry:
    key:       str
    vector:    np.ndarray
    timestamp: float
    access_count: int = 0
    tags:      List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def touch(self):
        self.access_count += 1
        self.timestamp = time.time()


# ---------------------------------------------------------------------------
# VectorSpace
# ---------------------------------------------------------------------------

class VectorSpace:
    """
    Semantic vector memory store.

    Parameters
    ----------
    dim : int
        Vector dimensionality. Enforced on put().
    max_size : int or None
        Maximum number of entries. LRU eviction when exceeded.
    """

    def __init__(self, dim: int = 128, max_size: Optional[int] = None):
        self.dim      = dim
        self.max_size = max_size
        self._store:  Dict[str, VectorEntry] = {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(self, key: str, vector: np.ndarray, tags: Optional[List[str]] = None):
        """Store a vector. Overwrites existing entry for the same key."""
        if vector.shape[0] != self.dim:
            raise ValueError(
                f"Vector dim {vector.shape[0]} != space dim {self.dim}"
            )
        entry = VectorEntry(
            key       = key,
            vector    = vector.astype(np.float32).copy(),
            timestamp = time.time(),
            tags      = tags or [],
        )
        self._store[key] = entry

        if self.max_size and len(self._store) > self.max_size:
            self._evict_lru()

    def put_batch(self, pairs: List[Tuple[str, np.ndarray]]):
        """Store multiple vectors at once."""
        for key, vec in pairs:
            self.put(key, vec)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[np.ndarray]:
        entry = self._store.get(key)
        if entry is None:
            return None
        entry.touch()
        return entry.vector.copy()

    def get_entry(self, key: str) -> Optional[VectorEntry]:
        return self._store.get(key)

    def get_batch(self, keys: List[str]) -> Dict[str, Optional[np.ndarray]]:
        return {k: self.get(k) for k in keys}

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)

    def keys(self) -> List[str]:
        return list(self._store.keys())

    # ------------------------------------------------------------------
    # Nearest neighbor
    # ------------------------------------------------------------------

    def nearest(
        self,
        query:   np.ndarray,
        top_k:   int = 5,
        exclude: Optional[List[str]] = None,
        tag_filter: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Cosine nearest-neighbor search.

        Parameters
        ----------
        query : np.ndarray, shape (dim,)
        top_k : int
        exclude : list of str or None
            Keys to exclude from results.
        tag_filter : str or None
            Only consider entries with this tag.

        Returns
        -------
        List of (key, cosine_score) sorted by score descending.
        """
        if not self._store:
            return []

        exclude_set = set(exclude or [])

        candidates = [
            e for e in self._store.values()
            if e.key not in exclude_set
            and (tag_filter is None or tag_filter in e.tags)
        ]

        if not candidates:
            return []

        # Vectorized cosine similarity
        matrix = np.stack([e.vector for e in candidates])  # (n, dim)
        q_norm = query / (np.linalg.norm(query) + 1e-8)
        m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8)
        scores = m_norm @ q_norm  # (n,)

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(candidates[i].key, float(scores[i])) for i in top_indices]

    def nearest_vectors(
        self,
        query:  np.ndarray,
        top_k:  int = 5,
    ) -> List[Tuple[str, float, np.ndarray]]:
        """Like nearest() but also returns the vectors."""
        results = self.nearest(query, top_k)
        return [
            (key, score, self._store[key].vector.copy())
            for key, score in results
            if key in self._store
        ]

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def cluster_centroid(self, keys: Optional[List[str]] = None) -> Optional[np.ndarray]:
        """
        Compute the normalized centroid of a subset (or all) stored vectors.
        Returns None if the store is empty.
        """
        entries = (
            [self._store[k] for k in keys if k in self._store]
            if keys is not None
            else list(self._store.values())
        )
        if not entries:
            return None

        centroid = np.mean([e.vector for e in entries], axis=0)
        norm     = np.linalg.norm(centroid)
        return (centroid / (norm + 1e-8)).astype(np.float32)

    def semantic_clusters(
        self,
        n_clusters: int = 5,
        max_iter:   int = 20,
    ) -> Dict[int, List[str]]:
        """
        Simple k-means clustering over stored vectors.
        Returns {cluster_id: [key, ...]} mapping.
        """
        if len(self._store) < n_clusters:
            return {0: list(self._store.keys())}

        keys    = list(self._store.keys())
        vectors = np.stack([self._store[k].vector for k in keys])

        # Random init
        rng      = np.random.default_rng()
        centers  = vectors[rng.choice(len(vectors), n_clusters, replace=False)]

        labels = np.zeros(len(vectors), dtype=int)

        for _ in range(max_iter):
            # Assign
            c_norm = centers / (np.linalg.norm(centers, axis=1, keepdims=True) + 1e-8)
            v_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8)
            sims   = v_norm @ c_norm.T  # (n, k)
            new_labels = np.argmax(sims, axis=1)

            if np.array_equal(new_labels, labels):
                break
            labels = new_labels

            # Update centers
            for c in range(n_clusters):
                mask = labels == c
                if mask.any():
                    centers[c] = vectors[mask].mean(axis=0)

        clusters: Dict[int, List[str]] = {i: [] for i in range(n_clusters)}
        for i, key in enumerate(keys):
            clusters[int(labels[i])].append(key)
        return clusters

    # ------------------------------------------------------------------
    # Eviction
    # ------------------------------------------------------------------

    def evict(self, key: str) -> bool:
        """Remove a single entry. Returns True if it existed."""
        return self._store.pop(key, None) is not None

    def evict_oldest(self, n: int = 10):
        """Evict the n least recently accessed entries."""
        if len(self._store) <= n:
            return
        sorted_entries = sorted(
            self._store.values(), key=lambda e: e.timestamp
        )
        for e in sorted_entries[:n]:
            del self._store[e.key]

    def _evict_lru(self):
        """Evict the single least recently accessed entry."""
        lru_key = min(self._store, key=lambda k: self._store[k].timestamp)
        del self._store[lru_key]

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        if not self._store:
            return {"size": 0, "dim": self.dim}
        timestamps = [e.timestamp for e in self._store.values()]
        return {
            "size":       len(self._store),
            "dim":        self.dim,
            "oldest_age": round(time.time() - min(timestamps), 2),
            "newest_age": round(time.time() - max(timestamps), 2),
        }
