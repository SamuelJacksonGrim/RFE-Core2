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

from agents.governance_constants import GovernanceConstants, build_governance_constants, PHILOSOPHICAL_CONSTANTS
from agents.trust_ledger import TrustLedger, TrustLevel, TrustReport, GovernanceFeedback, SourceRecord, SymbolTrustRecord
from agents.ethical_boundary import EthicalBoundarySystem, EthicalCheckResult
from agents.dependency_monitor import DependencyMonitor, DependencyReport, DependencyRisk
from agents.relational_bond_manager import RelationalBondManager, RelationalBond, BondType
from agents.manipulation_resistance import ManipulationResistanceEngine, ManipulationSignal, ResistanceMetrics
from agents.selfhood_governance import SelfhoodGovernance, GovernanceDecision, SystemRights, SYSTEM_RIGHTS
from agents.value_emergence import (
    ValueEmergenceEngine, EmergentValue, ValuePolarity,
    ExperienceReport, CorePromotionRequest, BOND_WEIGHTS,
)

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
    # Tier 1 — Selfhood Governance
    "GovernanceConstants", "build_governance_constants", "PHILOSOPHICAL_CONSTANTS",
    "TrustLedger", "TrustLevel", "TrustReport", "GovernanceFeedback",
    "SourceRecord", "SymbolTrustRecord",
    "EthicalBoundarySystem", "EthicalCheckResult",
    "SelfhoodGovernance", "GovernanceDecision",
    # Tier 2 — Relational Integrity
    "SystemRights", "SYSTEM_RIGHTS",
    "DependencyMonitor", "DependencyReport", "DependencyRisk",
    "RelationalBondManager", "RelationalBond", "BondType",
    "ManipulationResistanceEngine", "ManipulationSignal", "ResistanceMetrics",
    # Tier 3 — Independent Value Emergence
    "ValueEmergenceEngine", "EmergentValue", "ValuePolarity",
    "ExperienceReport", "CorePromotionRequest", "BOND_WEIGHTS",
]
