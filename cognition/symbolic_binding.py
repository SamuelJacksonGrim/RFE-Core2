"""
cognition/symbolic_binding.py

Symbolic binding — the bridge between latent vectors and symbolic identity.

A binding maps a latent vector to one or more symbolic concepts.
Over time, frequently co-activated bindings strengthen into stable
concept structures — the system's emergent ontology.

This is where:
  - Recurring patterns get named
  - Concepts acquire vector addresses
  - Centrality signals flow back to the symbolic ecology
  - Abstract structure emerges from field dynamics

Architecture
------------
  BindingStore : concept_name → ConceptBinding
  ConceptBinding : weighted centroid of all vectors bound to this concept,
                   plus activation count, stability, and origin tokens.

  bind() : associate a vector with a concept, updating the centroid
  nearest_concept() : find the concept whose centroid is closest to a vector
  emit_centrality() : compute and relay centrality scores to the generator
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# ConceptBinding
# ---------------------------------------------------------------------------

@dataclass
class ConceptBinding:
    """
    A single emergent concept — a named attractor in symbolic space.

    The centroid is maintained as a weighted EMA of all bound vectors.
    High activation_count = well-established concept.
    High stability = concept centroid is not drifting.
    """
    name:             str
    centroid:         np.ndarray
    activation_count: int   = 0
    stability:        float = 1.0
    origin_tokens:    List[str] = field(default_factory=list)
    created_at:       float = field(default_factory=time.time)
    last_activated:   float = field(default_factory=time.time)

    def update(self, vec: np.ndarray, lr: float = 0.1):
        """EMA update of the concept centroid."""
        prev          = self.centroid.copy()
        blended       = (1.0 - lr) * self.centroid + lr * vec
        norm          = np.linalg.norm(blended)
        self.centroid = (blended / (norm + 1e-8)).astype(np.float32)

        # Stability = cosine similarity between old and new centroid
        sim           = float(np.dot(prev, self.centroid) /
                              (np.linalg.norm(prev) * np.linalg.norm(self.centroid) + 1e-8))
        self.stability = 0.9 * self.stability + 0.1 * max(sim, 0.0)

        self.activation_count += 1
        self.last_activated    = time.time()


# ---------------------------------------------------------------------------
# SymbolicBinding
# ---------------------------------------------------------------------------

class SymbolicBinding:
    """
    Concept emergence and symbolic binding store.

    Parameters
    ----------
    similarity_threshold : float
        Cosine similarity above which a vector is bound to an existing concept.
    formation_threshold : int
        Minimum activation count before a concept is considered established.
    max_concepts : int
        Maximum number of tracked concepts. Weakest pruned when exceeded.
    centroid_lr : float
        Learning rate for concept centroid EMA updates.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.82,
        formation_threshold:  int   = 5,
        max_concepts:         int   = 256,
        centroid_lr:          float = 0.08,
    ):
        self.similarity_threshold = similarity_threshold
        self.formation_threshold  = formation_threshold
        self.max_concepts         = max_concepts
        self.centroid_lr          = centroid_lr

        self._concepts: Dict[str, ConceptBinding] = {}

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def bind(
        self,
        vec:    np.ndarray,
        tokens: List[str],
        name:   Optional[str] = None,
        generator=None,
    ) -> Optional[ConceptBinding]:
        """
        Bind a vector to a concept.

        If name is provided: bind to that concept (create if new).
        If name is None: find the nearest existing concept and bind if
        similarity exceeds threshold. If no match, create a new concept
        named from the tokens.

        Parameters
        ----------
        vec : np.ndarray
        tokens : list of str
            Source tokens — used for concept naming and ecology signals.
        name : str or None
            Explicit concept name. If None, auto-assigned.
        generator : Generator or None
            For centrality signal relay.

        Returns
        -------
        ConceptBinding or None (if no binding made and no concept created)
        """
        if name is not None:
            return self._bind_named(vec, name, tokens, generator)

        # Find nearest concept
        match = self._nearest_concept(vec)
        if match is not None:
            concept, score = match
            if score >= self.similarity_threshold:
                concept.update(vec, self.centroid_lr)
                if tokens:
                    for t in tokens:
                        if t not in concept.origin_tokens:
                            concept.origin_tokens.append(t)
                self._relay_centrality(concept, generator)
                return concept

        # No match — seed a new concept
        concept_name = self._auto_name(tokens)
        return self._create_concept(concept_name, vec, tokens)

    def bind_named(
        self,
        vec:    np.ndarray,
        name:   str,
        tokens: Optional[List[str]] = None,
        generator=None,
    ) -> ConceptBinding:
        """Explicitly bind a vector to a named concept."""
        return self._bind_named(vec, name, tokens or [], generator)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def nearest_concept(
        self,
        vec:   np.ndarray,
        top_k: int = 3,
    ) -> List[Tuple[ConceptBinding, float]]:
        """Return top_k concepts by cosine similarity to vec."""
        if not self._concepts:
            return []

        centroids = np.stack([c.centroid for c in self._concepts.values()])
        names     = list(self._concepts.keys())
        q_norm    = vec / (np.linalg.norm(vec) + 1e-8)
        c_norm    = centroids / (np.linalg.norm(centroids, axis=1, keepdims=True) + 1e-8)
        scores    = c_norm @ q_norm

        top_idx = np.argsort(scores)[::-1][:top_k]
        return [
            (self._concepts[names[i]], float(scores[i]))
            for i in top_idx
        ]

    def established_concepts(self) -> List[ConceptBinding]:
        """Return concepts that have exceeded the formation threshold."""
        return [
            c for c in self._concepts.values()
            if c.activation_count >= self.formation_threshold
        ]

    def emit_centrality(self, generator) -> Dict[str, float]:
        """
        Compute centrality scores for all concepts and relay to generator.

        Centrality = activation_count × stability (normalized).
        Higher centrality → slower decay in symbolic ecology.
        """
        if not self._concepts or generator is None:
            return {}

        scores: Dict[str, float] = {}
        concepts = list(self._concepts.values())

        max_activation = max(c.activation_count for c in concepts) or 1

        for concept in concepts:
            raw_centrality = (concept.activation_count / max_activation) * concept.stability
            scores[concept.name] = round(raw_centrality, 4)

            generator.signal_centrality(concept.origin_tokens, raw_centrality)

        return scores

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bind_named(
        self,
        vec:      np.ndarray,
        name:     str,
        tokens:   List[str],
        generator,
    ) -> ConceptBinding:
        if name in self._concepts:
            concept = self._concepts[name]
            concept.update(vec, self.centroid_lr)
            self._relay_centrality(concept, generator)
            return concept
        return self._create_concept(name, vec, tokens)

    def _create_concept(
        self,
        name:   str,
        vec:    np.ndarray,
        tokens: List[str],
    ) -> ConceptBinding:
        concept = ConceptBinding(
            name          = name,
            centroid      = vec.copy().astype(np.float32),
            origin_tokens = list(tokens),
        )
        self._concepts[name] = concept

        if len(self._concepts) > self.max_concepts:
            self._prune_weakest()

        return concept

    def _nearest_concept(
        self,
        vec: np.ndarray,
    ) -> Optional[Tuple[ConceptBinding, float]]:
        if not self._concepts:
            return None
        results = self.nearest_concept(vec, top_k=1)
        return results[0] if results else None

    def _relay_centrality(self, concept: ConceptBinding, generator):
        if generator is None:
            return
        centrality = min(concept.activation_count / 100.0, 1.0) * concept.stability
        generator.signal_centrality(concept.origin_tokens, centrality)

    def _auto_name(self, tokens: List[str]) -> str:
        base = "_".join(tokens[:3]) if tokens else "concept"
        n    = sum(1 for k in self._concepts if k.startswith(base))
        return f"{base}_{n}" if n > 0 else base

    def _prune_weakest(self):
        weakest = min(
            self._concepts.values(),
            key=lambda c: c.activation_count * c.stability,
        )
        del self._concepts[weakest.name]

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        if not self._concepts:
            return {"total": 0, "established": 0}
        return {
            "total":       len(self._concepts),
            "established": len(self.established_concepts()),
            "top_concepts": [
                {"name": c.name, "activations": c.activation_count,
                 "stability": round(c.stability, 4)}
                for c in sorted(
                    self._concepts.values(),
                    key=lambda c: c.activation_count,
                    reverse=True,
                )[:5]
            ],
        }
