"""
agents — Cognitive agent layer for RFE-Core2.
"""

from agents.symbolic_memory import (
    SymbolRegistry,
    SymbolTable,
    AddressSpace,
    SymbolState,
    TokenClass,
    Residency,
    ReaperDecision,
    CanonicalizationPipeline,
    CanonicalizationTier,
    DecayProfile,
    DECAY_PROFILES,
    ReaperEngine,
    ReaperConfig,
    CompactionManager,
    CompactionReport,
    ArchiveStore,
    ColdStoragePolicy,
    EmbeddingResidencyManager,
)

from agents.generator import Generator
from agents.watcher import Watcher, CoherenceReport
from agents.witness import Witness, RelationalProfile, EpisodicSnapshot, CrystallizationCandidate
from agents.attractor import Attractor, AttractorCenter
from agents.dreamer import Dreamer, DreamProduct
from agents.chorus import Chorus, ChorusOutput

__all__ = [
    # Symbolic ecology
    "SymbolRegistry", "SymbolTable", "AddressSpace", "SymbolState",
    "TokenClass", "Residency", "ReaperDecision",
    "CanonicalizationPipeline", "CanonicalizationTier",
    "DecayProfile", "DECAY_PROFILES",
    "ReaperEngine", "ReaperConfig",
    "CompactionManager", "CompactionReport",
    "ArchiveStore", "ColdStoragePolicy", "EmbeddingResidencyManager",
    # Core agents
    "Generator",
    "Watcher", "CoherenceReport",
    "Witness", "RelationalProfile", "EpisodicSnapshot", "CrystallizationCandidate",
    "Attractor", "AttractorCenter",
    "Dreamer", "DreamProduct",
    "Chorus", "ChorusOutput",
]
