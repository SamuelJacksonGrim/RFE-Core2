"""
RFE-Core2 - TrustEngine
Tier 1 Selfhood Governance Foundation
"""

from __future__ import annotations
import time
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import torch
import uuid

from .symbolic_memory import SymbolRegistry, SymbolState, TokenClass
from ..substrate.resonance_field import ResonanceField
from ..cognition.emotional_gradient import EmotionalGradient


class TrustLevel(Enum):
    SACRED = 5.0      # Core self / unalterable anchors
    HIGH = 4.0
    TRUSTED = 3.0
    NEUTRAL = 2.0
    SKEPTICAL = 1.0
    UNTRUSTED = 0.5
    TOXIC = 0.0       # Quarantine / rejection


@dataclass
class SourceProvenance:
    source_id: str
    origin_type: str                    # "user", "external_api", "internal_dream", "training", etc.
    timestamp: float
    reliability_history: List[float] = field(default_factory=list)
    interaction_count: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class TrustMetadata:
    stable_id: str
    current_trust: float = 2.5
    max_trust: float = 5.0
    trust_level: TrustLevel = TrustLevel.NEUTRAL
    provenance: SourceProvenance | None = None
    ethical_violation_count: int = 0
    coherence_impact: float = 0.0          # How this symbol affects field coherence
    last_evaluated: float = field(default_factory=time.time)


class TrustEngine:
    """
    Core Tier 1 component responsible for evaluating, tracking, and governing 
    trust across the entire symbolic ecology.
    Works in tight integration with SymbolRegistry, ResonanceField, and SelfhoodGovernor.
    """

    def __init__(self, symbol_registry: SymbolRegistry, resonance_field: ResonanceField,
                 emotional_gradient: EmotionalGradient, config: dict | None = None):
        
        self.symbol_registry = symbol_registry
        self.resonance_field = resonance_field
        self.emotional_gradient = emotional_gradient
        
        self.config = config or {
            "decay_rate": 0.003,           # Trust decay per cycle
            "coherence_weight": 0.45,
            "provenance_weight": 0.25,
            "emotional_weight": 0.20,
            "historical_weight": 0.10,
            "quarantine_threshold": 0.3,
            "sacred_protection_threshold": 4.7
        }
        
        self.sources: Dict[str, SourceProvenance] = {}
        self.trust_map: Dict[str, TrustMetadata] = {}   # stable_id -> TrustMetadata
        
        # Self-trust (meta)
        self.self_trust = 4.8
        self.trust_history: List[float] = []

    def evaluate_incoming(self, content: Any, source_id: str, origin_type: str = "user") -> TrustMetadata:
        """Main entry point for new information/symbols."""
        # 1. Get or create provenance
        provenance = self._get_or_create_provenance(source_id, origin_type)
        provenance.interaction_count += 1
        provenance.last_updated = time.time()

        # 2. Generate or retrieve stable symbol
        symbol = self.symbol_registry.register_symbol(content)
        stable_id = symbol.stable_id

        # 3. Compute multi-factor trust score
        trust_score = self._compute_trust_score(symbol, provenance, content)

        # 4. Create or update metadata
        if stable_id not in self.trust_map:
            metadata = TrustMetadata(
                stable_id=stable_id,
                current_trust=trust_score,
                provenance=provenance
            )
            self.trust_map[stable_id] = metadata
        else:
            metadata = self.trust_map[stable_id]
            metadata.current_trust = self._apply_decay(metadata.current_trust) 
            metadata.current_trust = max(0.0, min(metadata.max_trust,
                metadata.current_trust * 0.6 + trust_score * 0.4))
            metadata.provenance = provenance
            metadata.last_evaluated = time.time()

        metadata.trust_level = self._score_to_level(metadata.current_trust)
        
        # 5. Apply governance actions
        self._apply_governance_actions(metadata, symbol)

        return metadata

    def _compute_trust_score(self, symbol, provenance: SourceProvenance, content: Any) -> float:
        """Multi-dimensional trust calculation."""
        scores = []

        # Provenance score
        prov_score = min(5.0, 1.0 + math.log1p(provenance.interaction_count) * 0.8)
        if provenance.origin_type in ["internal_dream", "self_reflection"]:
            prov_score = 4.8
        scores.append(prov_score * self.config["provenance_weight"])

        # Coherence with current field
        coherence = self.resonance_field.evaluate_coherence_impact(symbol.embedding)
        scores.append(coherence * self.config["coherence_weight"])

        # Emotional resonance
        emotional_fit = self.emotional_gradient.evaluate_emotional_compatibility(symbol)
        scores.append(emotional_fit * self.config["emotional_weight"])

        # Historical reliability
        if provenance.reliability_history:
            hist_avg = sum(provenance.reliability_history[-20:]) / len(provenance.reliability_history[-20:])
            scores.append(hist_avg * self.config["historical_weight"])

        final_score = sum(scores)
        # Apply slight emotional modulation
        final_score *= (1.0 + self.emotional_gradient.curiosity * 0.08)

        return max(0.1, min(5.0, final_score))

    def _apply_decay(self, trust: float) -> float:
        decay = self.config["decay_rate"] * (1.0 - self.emotional_gradient.stability)
        return max(0.1, trust - decay)

    def _score_to_level(self, score: float) -> TrustLevel:
        for level in sorted(TrustLevel, key=lambda x: x.value, reverse=True):
            if score >= level.value:
                return level
        return TrustLevel.TOXIC

    def _apply_governance_actions(self, metadata: TrustMetadata, symbol):
        """Critical integration with Selfhood & Ethical boundaries."""
        if metadata.current_trust <= self.config["quarantine_threshold"]:
            self.symbol_registry.apply_state(symbol.stable_id, SymbolState.COLD)
            # TODO: Notify EthicalBoundarySystem & SelfhoodGovernor
            metadata.ethical_violation_count += 1

        # Protect sacred symbols
        if metadata.current_trust >= self.config["sacred_protection_threshold"]:
            self.symbol_registry.protect_symbol(symbol.stable_id)  # Make harder to reap

    def _get_or_create_provenance(self, source_id: str, origin_type: str) -> SourceProvenance:
        if source_id not in self.sources:
            self.sources[source_id] = SourceProvenance(
                source_id=source_id,
                origin_type=origin_type,
                timestamp=time.time()
            )
        return self.sources[source_id]

    def update_from_feedback(self, stable_id: str, positive: bool, magnitude: float = 1.0):
        """Reinforcement from outcomes, dreams, or self-reflection."""
        if stable_id not in self.trust_map:
            return
            
        meta = self.trust_map[stable_id]
        delta = magnitude * (1.0 if positive else -1.0)
        meta.current_trust = max(0.1, min(meta.max_trust, meta.current_trust + delta))
        
        if meta.provenance:
            meta.provenance.reliability_history.append(meta.current_trust)

    def get_trust_report(self, stable_id: str) -> Optional[TrustMetadata]:
        return self.trust_map.get(stable_id)

    def get_field_trust_summary(self) -> Dict[str, Any]:
        """Used by Witness / AutonomousCycle for global state awareness."""
        if not self.trust_map:
            return {"average_trust": 2.5, "low_trust_symbols": 0}
            
        trusts = [m.current_trust for m in self.trust_map.values()]
        return {
            "average_trust": sum(trusts) / len(trusts),
            "low_trust_symbols": sum(1 for t in trusts if t < 1.2),
            "sacred_symbols": sum(1 for t in trusts if t >= 4.7),
            "quarantined": sum(1 for m in self.trust_map.values() 
                              if m.trust_level == TrustLevel.TOXIC)
        }

    # ============== Integration Hooks ==============
    def on_dream_cycle_complete(self):
        """Called after dream_cycle.py finishes — allows trust re-evaluation of crystallized symbols."""
        for meta in list(self.trust_map.values()):
            if meta.trust_level == TrustLevel.TOXIC:
                # Possible redemption through dreaming
                meta.current_trust = max(meta.current_trust, 0.8)
