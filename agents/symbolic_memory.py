"""
agents/symbolic_memory.py

Persistent Adaptive Symbolic Ecology Engine — Phase 1 Refactor
═══════════════════════════════════════════════════════════════════════════════

Architecture
------------

    CanonicalizationPipeline
        Ordered tier-based normalization. Each tier may transform, classify,
        or halt. Replaces the blunt mode-switch of the original Canonicalizer.

    SymbolTable
        Stable symbolic identity. stable_id is SACRED — never reused,
        never reassigned, survives compaction, survives reaping.

    AddressSpace
        Mutable address allocator. Addresses are DISPOSABLE.
        Supports free-list allocation (reclaimed from reaped symbols),
        compaction remap generation, and optimizer-safe resize.

    SymbolState
        Full lifecycle state per symbol including all binding signals:
        attractor_strength, crystal_binding, field_coherence, centrality.

    DecayProfile
        Per-class contextual decay specification. Decay is not a single
        number — it is a function of age, class, and all binding signals.

    ReaperEngine
        Governs staged symbolic death: ACTIVE → WARM → COLD → GRAVEYARD.
        Protected classes (GLYPH, ENTITY, SPECIAL) cannot reach GRAVEYARD
        via normal decay. Minimum lifespan enforced per profile.

    CompactionManager
        Reclaims fragmented address space. Generates old→new address remap
        for embedding weight migration. Never invalidates stable IDs.

    ColdStoragePolicy
        Controls tier population caps and eviction batch sizes.

    ArchiveStore
        Multi-tier persistence with governed transitions and population limits.

    EmbeddingResidencyManager
        HOT / WARM / COLD classification for embedding cache management.

    SymbolRegistry
        Orchestration layer. Delegates lifecycle decisions to subsystems.
        Owns scheduling state for decay and compaction.
        Exposes external signal integration hooks for Attractor, CrystalStore,
        Watcher, and TopologicalLog.

Critical engineering principle
-------------------------------
    Stable IDs are sacred.
    Addresses are disposable.
    This distinction governs every subsystem.
"""

from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

SPECIAL_TOKENS: List[str] = ["<PAD>", "<UNK>", "<BOS>", "<EOS>"]
SPECIAL_COUNT: int = len(SPECIAL_TOKENS)


# =============================================================================
# ENUMS
# =============================================================================

class TokenClass(Enum):
    LANGUAGE   = "language"
    IDENTIFIER = "identifier"
    ENTITY     = "entity"
    GLYPH      = "glyph"
    RELATIONAL = "relational"
    OPERATOR   = "operator"
    EPHEMERAL  = "ephemeral"
    SPECIAL    = "special"


class Residency(Enum):
    HOT      = "hot"
    WARM     = "warm"
    COLD     = "cold"
    ARCHIVED = "archived"


class ReaperDecision(Enum):
    ACTIVE       = "active"
    WARM_ARCHIVE = "warm_archive"
    COLD_ARCHIVE = "cold_archive"
    GRAVEYARD    = "graveyard"


# =============================================================================
# CANONICALIZATION PIPELINE
# =============================================================================

@dataclass
class CanonicalizationResult:
    """Output of a single canonicalization tier."""
    token:       str
    token_class: Optional[TokenClass] = None
    halt:        bool                 = False
    metadata:    dict                 = field(default_factory=dict)


class CanonicalizationTier:
    """
    Single stage in the canonicalization pipeline.

    A tier is a named callable:
        (token: str, current_class: Optional[TokenClass])
        → CanonicalizationResult

    Each tier may:
    - Transform the token
    - Assign or override the token class
    - Halt further pipeline processing

    Exceptions are caught and logged; the tier is treated as a no-op on failure.
    """

    def __init__(
        self,
        name: str,
        fn: Callable[[str, Optional[TokenClass]], CanonicalizationResult],
    ):
        self.name = name
        self._fn  = fn

    def apply(self, token: str, current_class: Optional[TokenClass] = None) -> CanonicalizationResult:
        try:
            return self._fn(token, current_class)
        except Exception as exc:
            logger.warning(
                "CanonicalizationTier '%s' failed on '%s': %s",
                self.name, token, exc,
            )
            return CanonicalizationResult(token=token, token_class=current_class)


@dataclass
class PipelineResult:
    """Output of the full canonicalization pipeline."""
    token:        str
    token_class:  TokenClass
    tiers_applied: List[str]
    halted_at:    Optional[str]   # tier name that halted, or None


class CanonicalizationPipeline:
    """
    Ordered canonicalization pipeline.

    Processing runs each tier in order, accumulating token transformations
    and class assignments. The first tier that sets halt=True stops the
    pipeline; subsequent tiers are not called.

    Default tier order
    ------------------
    1. special_guard      — short-circuits special tokens immediately
    2. unicode_normalize  — NFKC normalization
    3. whitespace         — strip leading/trailing whitespace
    4. empty_guard        — replace empty string with <UNK>
    5. glyph_classify     — detect non-BMP / emoji glyphs
    6. operator_classify  — detect operator sequences
    7. symbolic_alias     — resolve known symbolic aliases (e.g. c++ → cpp)
    8. identifier_classify — detect identifiers (alphanum + underscore)
    9. entity_classify    — heuristic: initial capital = entity
    10. lowercase         — lowercase non-entity, non-glyph tokens
    """

    # Known symbolic aliases — extend freely
    SYMBOLIC_ALIASES: Dict[str, str] = {
        "c++":      "cpp",
        "c#":       "csharp",
        "e8-eea":   "e8_eea",
        "rfe-core": "rfe_core",
        "rfe-core2": "rfe_core2",
        ".net":     "dotnet",
    }

    # Glyph: supplementary planes + common emoji blocks
    GLYPH_PATTERN    = re.compile(r'^[\U00010000-\U0010FFFF\u2600-\u27BF\u1F300-\u1FAFF]+$')
    # Operator: sequences of ASCII punctuation
    OPERATOR_PATTERN = re.compile(r'^[+\-*/=<>!&|^~%@]+$')
    # Identifier: starts with letter or underscore, followed by word chars
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def __init__(self, tiers: Optional[List[CanonicalizationTier]] = None):
        self.tiers: List[CanonicalizationTier] = tiers or self._default_tiers()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def process(self, token: str) -> PipelineResult:
        current       = token
        current_class: Optional[TokenClass] = None
        applied:      List[str] = []
        halted_at:    Optional[str] = None

        for tier in self.tiers:
            result        = tier.apply(current, current_class)
            applied.append(tier.name)
            current       = result.token
            if result.token_class is not None:
                current_class = result.token_class
            if result.halt:
                halted_at = tier.name
                break

        return PipelineResult(
            token        = current,
            token_class  = current_class or TokenClass.LANGUAGE,
            tiers_applied = applied,
            halted_at    = halted_at,
        )

    def add_alias(self, raw: str, canonical: str):
        self.SYMBOLIC_ALIASES[raw.lower()] = canonical

    # ------------------------------------------------------------------
    # Default tiers
    # ------------------------------------------------------------------

    def _default_tiers(self) -> List[CanonicalizationTier]:
        return [
            CanonicalizationTier("special_guard",       self._t_special_guard),
            CanonicalizationTier("unicode_normalize",   self._t_unicode),
            CanonicalizationTier("whitespace",          self._t_whitespace),
            CanonicalizationTier("empty_guard",         self._t_empty_guard),
            CanonicalizationTier("glyph_classify",      self._t_glyph),
            CanonicalizationTier("operator_classify",   self._t_operator),
            CanonicalizationTier("symbolic_alias",      self._t_alias),
            CanonicalizationTier("identifier_classify", self._t_identifier),
            CanonicalizationTier("entity_classify",     self._t_entity),
            CanonicalizationTier("lowercase",           self._t_lowercase),
        ]

    # ------------------------------------------------------------------
    # Tier implementations
    # ------------------------------------------------------------------

    def _t_special_guard(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        if token in SPECIAL_TOKENS:
            return CanonicalizationResult(token=token, token_class=TokenClass.SPECIAL, halt=True)
        return CanonicalizationResult(token=token)

    def _t_unicode(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        return CanonicalizationResult(token=unicodedata.normalize("NFKC", token))

    def _t_whitespace(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        return CanonicalizationResult(token=token.strip())

    def _t_empty_guard(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        if not token:
            return CanonicalizationResult(token="<UNK>", token_class=TokenClass.SPECIAL, halt=True)
        return CanonicalizationResult(token=token)

    def _t_glyph(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        if self.GLYPH_PATTERN.match(token):
            return CanonicalizationResult(token=token, token_class=TokenClass.GLYPH, halt=True)
        return CanonicalizationResult(token=token)

    def _t_operator(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        if self.OPERATOR_PATTERN.match(token):
            return CanonicalizationResult(token=token, token_class=TokenClass.OPERATOR)
        return CanonicalizationResult(token=token)

    def _t_alias(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        aliased = self.SYMBOLIC_ALIASES.get(token.lower())
        if aliased is not None:
            return CanonicalizationResult(token=aliased)
        return CanonicalizationResult(token=token)

    def _t_identifier(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        if self.IDENTIFIER_PATTERN.match(token):
            return CanonicalizationResult(token=token, token_class=TokenClass.IDENTIFIER)
        return CanonicalizationResult(token=token)

    def _t_entity(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        # Heuristic: initial capital with at least one lowercase = proper noun / entity
        if len(token) > 1 and token[0].isupper() and any(c.islower() for c in token[1:]):
            return CanonicalizationResult(token=token, token_class=TokenClass.ENTITY)
        return CanonicalizationResult(token=token)

    def _t_lowercase(self, token: str, cls: Optional[TokenClass]) -> CanonicalizationResult:
        # Preserve case for entities and glyphs
        if cls in (TokenClass.ENTITY, TokenClass.GLYPH):
            return CanonicalizationResult(token=token)
        return CanonicalizationResult(token=token.lower())


# =============================================================================
# SYMBOL TABLE  —  stable identity, sacred
# =============================================================================

class SymbolTable:
    """
    Stable symbolic identity layer.

    stable_id is SACRED:
    - Never reused
    - Never reassigned
    - Survives address compaction
    - Survives reaping (symbol can be buried but its stable_id is not recycled)
    """

    def __init__(self):
        self._symbol_to_sid: Dict[str, int] = {}
        self._sid_to_symbol: Dict[int, str] = {}
        self._next_sid: int = SPECIAL_COUNT

        for i, tok in enumerate(SPECIAL_TOKENS):
            self._symbol_to_sid[tok] = i
            self._sid_to_symbol[i]   = tok

    def get_or_create_sid(self, symbol: str) -> int:
        if symbol in self._symbol_to_sid:
            return self._symbol_to_sid[symbol]
        sid = self._next_sid
        self._next_sid += 1
        self._symbol_to_sid[symbol] = sid
        self._sid_to_symbol[sid]    = symbol
        return sid

    def symbol_for(self, sid: int) -> str:
        return self._sid_to_symbol.get(sid, "<UNK>")

    def sid_for(self, symbol: str) -> Optional[int]:
        return self._symbol_to_sid.get(symbol)

    def __len__(self) -> int:
        return len(self._symbol_to_sid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_to_sid": self._symbol_to_sid,
            "next_sid":      self._next_sid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolTable":
        inst = cls.__new__(cls)
        inst._symbol_to_sid = dict(data["symbol_to_sid"])
        inst._sid_to_symbol = {v: k for k, v in inst._symbol_to_sid.items()}
        inst._next_sid      = data["next_sid"]
        return inst


# =============================================================================
# ADDRESS SPACE  —  mutable, disposable
# =============================================================================

class AddressSpace:
    """
    Mutable address allocator.

    Addresses are DISPOSABLE:
    - Can be reclaimed when symbols are reaped
    - Can be remapped during compaction
    - May change across sessions (after compaction + embedding migration)

    Stable IDs are not recycled here — that is SymbolTable's guarantee.

    Free list
    ---------
    Reclaimed addresses are added to a free list and preferentially
    allocated to new symbols before probing for fresh slots. This is
    the primary mechanism for preventing unbounded vocabulary growth.

    Compaction
    ----------
    generate_remap() produces an old→new address map for embedding migration.
    apply_remap() applies it after the caller has migrated embedding weights.
    Neither operation invalidates any stable_id.
    """

    def __init__(
        self,
        vocab_size:    int   = 8192,
        allow_resize:  bool  = True,
        resize_factor: float = 2.0,
    ):
        assert vocab_size > SPECIAL_COUNT, "vocab_size must exceed number of special tokens"
        self.vocab_size    = int(vocab_size)
        self.allow_resize  = bool(allow_resize)
        self.resize_factor = float(resize_factor)

        self._sid_to_address: Dict[int, int] = {}
        self._address_to_sid: Dict[int, int] = {}
        self._specials:       Dict[str, int] = {t: i for i, t in enumerate(SPECIAL_TOKENS)}
        self._num_assigned:   int = SPECIAL_COUNT

        # Free list: reclaimed addresses available for reuse
        self._free_list: List[int] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pad_id(self) -> int: return self._specials["<PAD>"]
    @property
    def unk_id(self) -> int: return self._specials["<UNK>"]
    @property
    def bos_id(self) -> int: return self._specials["<BOS>"]
    @property
    def eos_id(self) -> int: return self._specials["<EOS>"]

    @property
    def occupancy(self) -> float:
        return self._num_assigned / float(self.vocab_size)

    @property
    def fragmentation_ratio(self) -> float:
        """Fraction of assigned non-special slots that are dead (in free list)."""
        live_non_special = self._num_assigned - SPECIAL_COUNT
        if live_non_special <= 0:
            return 0.0
        return len(self._free_list) / live_non_special

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def resolve_sid(self, sid: int) -> int:
        """
        Map stable_id → address. Allocates if not yet assigned.

        Allocation order:
        1. Free list (reclaimed addresses from dead symbols)
        2. Fresh probe (double-hash open addressing)
        3. Resize if occupancy >= 0.85 (before fresh probe)
        """
        if sid < SPECIAL_COUNT:
            return sid  # specials are identity-mapped

        if sid in self._sid_to_address:
            return self._sid_to_address[sid]

        # Prefer reclaimed slots — compaction benefit
        if self._free_list:
            addr = self._free_list.pop()
            self._sid_to_address[sid]  = addr
            self._address_to_sid[addr] = sid
            return addr

        # Check capacity before probing
        if self.occupancy >= 0.85:
            if self.allow_resize:
                self._resize()
            else:
                raise RuntimeError("AddressSpace exhausted and resize is disabled.")

        addr = self._probe(sid)
        self._sid_to_address[sid]  = addr
        self._address_to_sid[addr] = sid
        self._num_assigned += 1
        return addr

    def reclaim(self, sid: int) -> Optional[int]:
        """
        Return the address of stable_id to the free list.

        The stable_id remains valid in SymbolTable. Only the address slot
        is freed for reuse. Returns the reclaimed address or None.
        """
        addr = self._sid_to_address.pop(sid, None)
        if addr is None:
            return None
        self._address_to_sid.pop(addr, None)
        self._free_list.append(addr)
        return addr

    # ------------------------------------------------------------------
    # Compaction
    # ------------------------------------------------------------------

    def generate_remap(self) -> Dict[int, int]:
        """
        Produce old_address → new_address for all live symbols.

        Assigns a contiguous block starting after SPECIAL_COUNT.
        Does NOT apply the remap — caller must migrate embeddings first,
        then call apply_remap().
        """
        live_sids = sorted(self._sid_to_address.keys())
        remap: Dict[int, int] = {}
        new_addr = SPECIAL_COUNT

        for sid in live_sids:
            old_addr = self._sid_to_address[sid]
            if old_addr != new_addr:
                remap[old_addr] = new_addr
            new_addr += 1

        return remap

    def apply_remap(self, remap: Dict[int, int]):
        """
        Apply a compaction remap after embedding migration is complete.

        Rebuilds sid→address and address→sid maps with remapped addresses.
        Clears the free list (compaction eliminates fragmentation).
        Shrinks vocab_size to fit the compacted population with headroom.
        """
        new_sid_to_addr: Dict[int, int] = {}
        new_addr_to_sid: Dict[int, int] = {}

        for sid, old_addr in self._sid_to_address.items():
            new_addr = remap.get(old_addr, old_addr)
            new_sid_to_addr[sid]     = new_addr
            new_addr_to_sid[new_addr] = sid

        self._sid_to_address = new_sid_to_addr
        self._address_to_sid = new_addr_to_sid
        self._free_list      = []

        live_count = SPECIAL_COUNT + len(self._sid_to_address)
        self._num_assigned = live_count
        self.vocab_size    = max(live_count * 2, 256)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _probe(self, sid: int) -> int:
        base = SPECIAL_COUNT
        span = self.vocab_size - base

        # Double-hash: golden ratio primary, Fibonacci step
        primary = (sid * 11400714819323198485) % span + base
        step    = ((sid * 0x9E3779B97F4A7C15) % (span - 1)) + 1

        probe = primary
        for _ in range(span):
            if probe not in self._address_to_sid:
                return probe
            probe = ((probe - base + step) % span) + base

        raise RuntimeError(f"Probe exhaustion for sid={sid}. Consider resize.")

    def _resize(self):
        new_size = int(math.ceil(self.vocab_size * self.resize_factor))
        logger.info("AddressSpace resize %d → %d", self.vocab_size, new_size)

        old_sids           = list(self._sid_to_address.keys())
        self.vocab_size    = new_size
        self._sid_to_address = {}
        self._address_to_sid = {}
        self._free_list    = []
        self._num_assigned = SPECIAL_COUNT

        for sid in old_sids:
            self.resolve_sid(sid)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vocab_size":    self.vocab_size,
            "allow_resize":  self.allow_resize,
            "resize_factor": self.resize_factor,
            "sid_to_address": {str(k): v for k, v in self._sid_to_address.items()},
            "free_list":     self._free_list,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AddressSpace":
        inst               = cls.__new__(cls)
        inst.vocab_size    = data["vocab_size"]
        inst.allow_resize  = data["allow_resize"]
        inst.resize_factor = data["resize_factor"]
        inst._specials     = {t: i for i, t in enumerate(SPECIAL_TOKENS)}
        inst._sid_to_address = {int(k): v for k, v in data["sid_to_address"].items()}
        inst._address_to_sid = {v: int(k) for k, v in inst._sid_to_address.items()}
        inst._free_list    = list(data.get("free_list", []))
        inst._num_assigned = SPECIAL_COUNT + len(inst._sid_to_address)
        return inst


# =============================================================================
# SYMBOL STATE
# =============================================================================

@dataclass
class SymbolState:
    """
    Full lifecycle state for a single symbol.

    Binding signals (attractor_strength, crystal_binding, field_coherence,
    centrality) are updated by external subsystems via SymbolRegistry hooks.
    They feed into DecayProfile.compute() to modulate decay rate.
    """
    symbol:     str
    stable_id:  int
    address:    int
    token_class: TokenClass

    # Lifecycle metrics
    usage:              float = 1.0
    recurrence:         float = 0.0
    centrality:         float = 0.0
    attractor_strength: float = 0.0
    crystal_binding:    float = 0.0
    field_coherence:    float = 0.0

    # Temporal
    created_step:  int = 0
    last_seen_step: int = 0
    lifespan:       int = 0

    # Lifecycle stage
    reaper_stage: ReaperDecision = ReaperDecision.ACTIVE
    residency:    Residency      = Residency.HOT

    # Governance
    protected:  bool          = False   # reaper cannot touch it
    sacred:     bool          = False   # nothing modifies without SACRED_SHIELD
    source_id:  Optional[str] = None    # provenance — who injected this symbol

    def age(self, current_step: int) -> int:
        """Steps since last encounter."""
        return max(0, current_step - self.last_seen_step)

    def total_age(self, current_step: int) -> int:
        """Steps since creation."""
        return max(0, current_step - self.created_step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol":             self.symbol,
            "stable_id":          self.stable_id,
            "address":            self.address,
            "token_class":        self.token_class.value,
            "usage":              self.usage,
            "recurrence":         self.recurrence,
            "centrality":         self.centrality,
            "attractor_strength": self.attractor_strength,
            "crystal_binding":    self.crystal_binding,
            "field_coherence":    self.field_coherence,
            "created_step":       self.created_step,
            "last_seen_step":     self.last_seen_step,
            "lifespan":           self.lifespan,
            "reaper_stage":       self.reaper_stage.value,
            "residency":          self.residency.value,
            "protected":          self.protected,
            "sacred":             self.sacred,
            "source_id":          self.source_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolState":
        return cls(
            symbol             = data["symbol"],
            stable_id          = data["stable_id"],
            address            = data["address"],
            token_class        = TokenClass(data["token_class"]),
            usage              = data["usage"],
            recurrence         = data["recurrence"],
            centrality         = data["centrality"],
            attractor_strength = data["attractor_strength"],
            crystal_binding    = data.get("crystal_binding", 0.0),
            field_coherence    = data.get("field_coherence", 0.0),
            created_step       = data["created_step"],
            last_seen_step     = data["last_seen_step"],
            lifespan           = data.get("lifespan", 0),
            reaper_stage       = ReaperDecision(data.get("reaper_stage", "active")),
            residency          = Residency(data["residency"]),
            protected          = data.get("protected", False),
            sacred             = data.get("sacred", False),
            source_id          = data.get("source_id", None),
        )


# =============================================================================
# DECAY PROFILES
# =============================================================================

@dataclass
class DecayProfile:
    """
    Per-class contextual decay specification.

    Effective decay per step:
        effective_decay  = base_decay * exp(-age_factor * age)
        reinforcement    = 1 + Σ(weight * signal)
        new_usage        = usage * effective_decay * reinforcement

    The age term accelerates decay for symbols that haven't been seen
    recently. The reinforcement term protects symbols with strong binding
    to other system components (attractors, crystals, field, topology).

    minimum_lifespan
        Steps from creation during which the symbol is immune to reaping.
        Prevents newly registered symbols from being immediately pruned.
    """
    base_decay:            float
    age_factor:            float
    recurrence_weight:     float
    attractor_weight:      float
    centrality_weight:     float
    field_coherence_weight: float
    crystal_binding_weight: float
    novelty_weight:         float = 0.0   # Fix 0-B: counterweight to coherence lean
    minimum_lifespan:      int = 0

    def compute(self, state: SymbolState, current_step: int) -> float:
        age = state.age(current_step)

        # Age-accelerated decay — unseen symbols decay faster
        effective_decay = self.base_decay * math.exp(-self.age_factor * age)
        effective_decay = max(effective_decay, 0.01)  # hard floor: no instant death

        # Fix 0-B candidate: novelty counterweight to field_coherence's
        # conformity lean. novelty = (1 - field_coherence), but GATED by
        # recurrence so a one-off dissonant burst earns nothing — novelty is
        # rewarded only once a pattern has survived circulation (earned
        # integration). recurrence_gate -> 0 for one-offs, -> 1 for repeaters.
        novelty = max(0.0, 1.0 - state.field_coherence)
        recurrence_gate = 1.0 - math.exp(-0.5 * state.recurrence)
        effective_novelty = novelty * recurrence_gate

        reinforcement = (
            1.0
            + self.recurrence_weight      * state.recurrence
            + self.attractor_weight       * state.attractor_strength
            + self.centrality_weight      * state.centrality
            + self.field_coherence_weight * state.field_coherence
            + self.crystal_binding_weight * state.crystal_binding
            + self.novelty_weight         * effective_novelty
        )

        return max(0.0, state.usage * effective_decay * reinforcement)


DECAY_PROFILES: Dict[TokenClass, DecayProfile] = {
    TokenClass.LANGUAGE: DecayProfile(
        base_decay=0.999,  age_factor=0.0005,
        recurrence_weight=0.05,  attractor_weight=0.10,
        centrality_weight=0.08,  field_coherence_weight=0.05,
        crystal_binding_weight=0.15, novelty_weight=0.05, minimum_lifespan=10,
    ),
    TokenClass.ENTITY: DecayProfile(
        base_decay=0.9995, age_factor=0.0002,
        recurrence_weight=0.08,  attractor_weight=0.20,
        centrality_weight=0.15,  field_coherence_weight=0.08,
        crystal_binding_weight=0.25, novelty_weight=0.08, minimum_lifespan=50,
    ),
    TokenClass.GLYPH: DecayProfile(
        base_decay=0.9998, age_factor=0.0001,
        recurrence_weight=0.12,  attractor_weight=0.25,
        centrality_weight=0.10,  field_coherence_weight=0.10,
        crystal_binding_weight=0.30, novelty_weight=0.10, minimum_lifespan=100,
    ),
    TokenClass.RELATIONAL: DecayProfile(
        base_decay=0.9992, age_factor=0.0004,
        recurrence_weight=0.10,  attractor_weight=0.15,
        centrality_weight=0.20,  field_coherence_weight=0.10,
        crystal_binding_weight=0.20, novelty_weight=0.10, minimum_lifespan=20,
    ),
    TokenClass.IDENTIFIER: DecayProfile(
        base_decay=0.998,  age_factor=0.0008,
        recurrence_weight=0.06,  attractor_weight=0.08,
        centrality_weight=0.05,  field_coherence_weight=0.03,
        crystal_binding_weight=0.10, novelty_weight=0.03, minimum_lifespan=5,
    ),
    TokenClass.OPERATOR: DecayProfile(
        base_decay=0.997,  age_factor=0.001,
        recurrence_weight=0.04,  attractor_weight=0.05,
        centrality_weight=0.08,  field_coherence_weight=0.03,
        crystal_binding_weight=0.05, novelty_weight=0.03, minimum_lifespan=3,
    ),
    TokenClass.EPHEMERAL: DecayProfile(
        base_decay=0.990,  age_factor=0.002,
        recurrence_weight=0.02,  attractor_weight=0.03,
        centrality_weight=0.02,  field_coherence_weight=0.02,
        crystal_binding_weight=0.03, novelty_weight=0.02, minimum_lifespan=1,
    ),
    TokenClass.SPECIAL: DecayProfile(
        base_decay=1.0,    age_factor=0.0,
        recurrence_weight=0.0,   attractor_weight=0.0,
        centrality_weight=0.0,   field_coherence_weight=0.0,
        crystal_binding_weight=0.0, novelty_weight=0.0, minimum_lifespan=999999,
    ),
}

_DEFAULT_PROFILE = DECAY_PROFILES[TokenClass.LANGUAGE]


# =============================================================================
# REAPER ENGINE
# =============================================================================

# Classes immune to GRAVEYARD via normal decay
PROTECTED_CLASSES: FrozenSet[TokenClass] = frozenset([
    TokenClass.GLYPH,
    TokenClass.ENTITY,
    TokenClass.SPECIAL,
])


@dataclass
class ReaperConfig:
    warm_threshold:      float = 1.0    # usage < this → WARM_ARCHIVE
    cold_threshold:      float = 0.1   # usage < this → COLD_ARCHIVE
    graveyard_threshold: float = 0.01  # usage < this → GRAVEYARD (non-protected)
    warm_resurrection_cost: float = 2.0
    cold_resurrection_cost: float = 5.0
    max_warm_steps:  int = 500         # forced COLD after N steps in WARM
    max_cold_steps:  int = 1000        # forced GRAVEYARD after N steps in COLD (non-protected)


class ReaperEngine:
    """
    Staged symbolic death engine.

    Death stages
    ------------
    ACTIVE  →  (degraded)   →  WARM_ARCHIVE
                                    ↓
                              COLD_ARCHIVE
                                    ↓
                              GRAVEYARD

    Rules
    -----
    - Cannot skip stages: ACTIVE cannot jump directly to COLD or GRAVEYARD.
    - Protected classes (GLYPH, ENTITY, SPECIAL) floor at COLD_ARCHIVE.
    - Minimum lifespan (per DecayProfile) protects newly created symbols.
    - Time-in-stage pressure: symbols that linger in WARM/COLD too long
      are forced to the next stage regardless of usage.

    evaluate() is READ-ONLY — it does not modify state.
    The SymbolRegistry acts on the returned decision.
    """

    def __init__(self, config: Optional[ReaperConfig] = None):
        self.config = config or ReaperConfig()

    def evaluate(self, state: SymbolState, current_step: int) -> ReaperDecision:
        # Governance overrides — sacred symbols are completely inviolable
        if state.sacred:
            return ReaperDecision.ACTIVE

        profile    = DECAY_PROFILES.get(state.token_class, _DEFAULT_PROFILE)
        cfg        = self.config

        # Protected symbols (governance OR token-class based) floor at COLD_ARCHIVE
        is_protected = state.token_class in PROTECTED_CLASSES or state.protected
        current_stage = state.reaper_stage

        # Minimum lifespan protection
        if state.total_age(current_step) < profile.minimum_lifespan:
            return ReaperDecision.ACTIVE

        usage = state.usage

        # --- GRAVEYARD ---
        if usage < cfg.graveyard_threshold:
            if is_protected:
                return ReaperDecision.COLD_ARCHIVE  # protected floor
            # Must have passed through COLD to reach GRAVEYARD (staged death)
            if current_stage != ReaperDecision.COLD_ARCHIVE:
                return ReaperDecision.COLD_ARCHIVE
            return ReaperDecision.GRAVEYARD

        # --- COLD ---
        if usage < cfg.cold_threshold:
            if current_stage == ReaperDecision.ACTIVE:
                # Cannot skip to COLD — must pass through WARM
                return ReaperDecision.WARM_ARCHIVE
            return ReaperDecision.COLD_ARCHIVE

        # --- WARM ---
        if usage < cfg.warm_threshold:
            return ReaperDecision.WARM_ARCHIVE

        # --- Time-in-stage pressure ---
        steps_since_seen = state.age(current_step)

        if current_stage == ReaperDecision.WARM_ARCHIVE:
            if steps_since_seen > cfg.max_warm_steps:
                return ReaperDecision.COLD_ARCHIVE

        if current_stage == ReaperDecision.COLD_ARCHIVE:
            if steps_since_seen > cfg.max_cold_steps and not is_protected:
                return ReaperDecision.GRAVEYARD

        return ReaperDecision.ACTIVE

    def resurrection_cost(self, stage: Optional[ReaperDecision]) -> float:
        if stage == ReaperDecision.COLD_ARCHIVE:
            return self.config.cold_resurrection_cost
        if stage == ReaperDecision.WARM_ARCHIVE:
            return self.config.warm_resurrection_cost
        return 0.0


# =============================================================================
# COMPACTION MANAGER
# =============================================================================

@dataclass
class CompactionReport:
    reclaimed_addresses: int
    live_symbols:        int
    new_vocab_size:      int
    fragmentation_before: float
    fragmentation_after:  float
    remap:               Dict[int, int]   # old_address → new_address


class CompactionManager:
    """
    Address space defragmentation engine.

    Compaction reclaims the dead slots accumulated in the AddressSpace
    free list by reassigning all live symbols to a contiguous block.

    The caller (SymbolRegistry → Generator) is responsible for:
    1. Receiving the CompactionReport from pending_compaction()
    2. Migrating embedding weights using the remap
    3. Calling registry.acknowledge_compaction(report) to apply the remap
       and clear the pending state

    Stable IDs are never modified by compaction.
    """

    def __init__(self, fragmentation_threshold: float = 0.30):
        self.fragmentation_threshold = fragmentation_threshold
        self.compaction_count:  int = 0
        self.total_reclaimed:   int = 0

    def should_compact(self, address_space: AddressSpace) -> bool:
        return address_space.fragmentation_ratio >= self.fragmentation_threshold

    def plan(
        self,
        address_space: AddressSpace,
    ) -> CompactionReport:
        """Generate a compaction plan. Does not apply it."""
        frag_before = address_space.fragmentation_ratio
        remap       = address_space.generate_remap()
        live        = len(address_space._sid_to_address)
        new_vocab   = max((live + SPECIAL_COUNT) * 2, 256)

        return CompactionReport(
            reclaimed_addresses  = len(address_space._free_list),
            live_symbols         = live,
            new_vocab_size       = new_vocab,
            fragmentation_before = frag_before,
            fragmentation_after  = 0.0,
            remap                = remap,
        )

    def apply(self, address_space: AddressSpace, report: CompactionReport):
        """Apply a compaction plan. Call AFTER embedding migration."""
        address_space.apply_remap(report.remap)
        self.compaction_count += 1
        self.total_reclaimed  += report.reclaimed_addresses

        logger.info(
            "Compaction #%d: %d addresses reclaimed, vocab %d → %d, "
            "frag %.1f%% → 0.0%%",
            self.compaction_count,
            report.reclaimed_addresses,
            report.new_vocab_size,
            report.fragmentation_before * 100,
        )


# =============================================================================
# COLD STORAGE POLICY
# =============================================================================

@dataclass
class ColdStoragePolicy:
    """Population caps and eviction economics for archive tiers."""
    warm_max_population:      int = 10_000
    warm_eviction_batch:      int = 100
    cold_max_population:      int = 50_000
    cold_eviction_batch:      int = 500
    graveyard_max_population: int = 100_000
    graveyard_purge_batch:    int = 5_000

    def should_evict_warm(self, n: int) -> bool:
        return n >= self.warm_max_population

    def should_evict_cold(self, n: int) -> bool:
        return n >= self.cold_max_population

    def should_purge_graveyard(self, n: int) -> bool:
        return n >= self.graveyard_max_population

    def select_warm_evictions(self, warm: Dict[str, SymbolState]) -> List[str]:
        return [s for s, _ in sorted(warm.items(), key=lambda x: x[1].usage)[:self.warm_eviction_batch]]

    def select_cold_evictions(self, cold: Dict[str, SymbolState]) -> List[str]:
        return [s for s, _ in sorted(cold.items(), key=lambda x: x[1].usage)[:self.cold_eviction_batch]]


# =============================================================================
# ARCHIVE STORE
# =============================================================================

class ArchiveStore:
    """
    Multi-tier symbolic persistence with governed transitions.

    Tiers
    -----
    warm      fast reactivation, higher memory cost
    cold      slow reactivation, lower memory cost
    graveyard effectively dead; address will be reclaimed by CompactionManager
    """

    def __init__(self, policy: Optional[ColdStoragePolicy] = None):
        self.policy:     ColdStoragePolicy       = policy or ColdStoragePolicy()
        self.warm:       Dict[str, SymbolState]  = {}
        self.cold:       Dict[str, SymbolState]  = {}
        self.graveyard:  Set[str]                = set()

    def archive_warm(self, state: SymbolState):
        state.reaper_stage = ReaperDecision.WARM_ARCHIVE
        self.warm[state.symbol] = state
        self.cold.pop(state.symbol, None)
        self._maybe_evict_warm()

    def archive_cold(self, state: SymbolState):
        state.reaper_stage = ReaperDecision.COLD_ARCHIVE
        self.cold[state.symbol] = state
        self.warm.pop(state.symbol, None)
        self._maybe_evict_cold()

    def bury(self, symbol: str):
        self.graveyard.add(symbol)
        self.warm.pop(symbol, None)
        self.cold.pop(symbol, None)
        self._maybe_purge_graveyard()

    def lookup(self, symbol: str) -> Optional[SymbolState]:
        return self.warm.get(symbol) or self.cold.get(symbol)

    def lookup_stage(self, symbol: str) -> Optional[ReaperDecision]:
        if symbol in self.warm:      return ReaperDecision.WARM_ARCHIVE
        if symbol in self.cold:      return ReaperDecision.COLD_ARCHIVE
        if symbol in self.graveyard: return ReaperDecision.GRAVEYARD
        return None

    def _maybe_evict_warm(self):
        if self.policy.should_evict_warm(len(self.warm)):
            for sym in self.policy.select_warm_evictions(self.warm):
                state = self.warm.pop(sym)
                self.archive_cold(state)

    def _maybe_evict_cold(self):
        if self.policy.should_evict_cold(len(self.cold)):
            for sym in self.policy.select_cold_evictions(self.cold):
                self.cold.pop(sym)
                self.graveyard.add(sym)

    def _maybe_purge_graveyard(self):
        if self.policy.should_purge_graveyard(len(self.graveyard)):
            # Trim oldest — set is unordered so we just trim arbitrarily
            excess = list(self.graveyard)[:self.policy.graveyard_purge_batch]
            self.graveyard -= set(excess)

    def populations(self) -> Dict[str, int]:
        return {
            "warm":      len(self.warm),
            "cold":      len(self.cold),
            "graveyard": len(self.graveyard),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warm":      {k: v.to_dict() for k, v in self.warm.items()},
            "cold":      {k: v.to_dict() for k, v in self.cold.items()},
            "graveyard": list(self.graveyard),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchiveStore":
        inst           = cls.__new__(cls)
        inst.policy    = ColdStoragePolicy()
        inst.warm      = {k: SymbolState.from_dict(v) for k, v in data["warm"].items()}
        inst.cold      = {k: SymbolState.from_dict(v) for k, v in data["cold"].items()}
        inst.graveyard = set(data["graveyard"])
        return inst


# =============================================================================
# EMBEDDING RESIDENCY MANAGER
# =============================================================================

class EmbeddingResidencyManager:
    """HOT / WARM / COLD classification for embedding cache management."""

    HOT_THRESHOLD  = 100.0
    WARM_THRESHOLD = 10.0

    def __init__(self):
        self.hot:  Set[str] = set()
        self.warm: Set[str] = set()
        self.cold: Set[str] = set()

    def assign(self, state: SymbolState):
        sym = state.symbol
        self.hot.discard(sym)
        self.warm.discard(sym)
        self.cold.discard(sym)

        if state.usage > self.HOT_THRESHOLD:
            state.residency = Residency.HOT
            self.hot.add(sym)
        elif state.usage > self.WARM_THRESHOLD:
            state.residency = Residency.WARM
            self.warm.add(sym)
        else:
            state.residency = Residency.COLD
            self.cold.add(sym)

    def to_dict(self) -> Dict[str, Any]:
        return {"hot": list(self.hot), "warm": list(self.warm), "cold": list(self.cold)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingResidencyManager":
        inst      = cls.__new__(cls)
        inst.hot  = set(data["hot"])
        inst.warm = set(data["warm"])
        inst.cold = set(data["cold"])
        return inst


# =============================================================================
# SYMBOL REGISTRY  —  orchestration layer
# =============================================================================

class SymbolRegistry:
    """
    Orchestration layer for the symbolic ecology.

    The Registry does not own lifecycle decisions — it delegates:
        decay math       → DecayProfile.compute()
        reaper decisions → ReaperEngine.evaluate()
        address alloc    → AddressSpace.resolve_sid()
        compaction plan  → CompactionManager.plan()
        archive movement → ArchiveStore

    External signal integration hooks
    ----------------------------------
    Called by downstream subsystems to update binding signals on symbols:
        update_attractor_strength(symbol, delta)   ← Attractor
        update_crystal_binding(symbol, delta)      ← CrystalStore
        update_field_coherence(symbol, coherence)  ← Watcher / ResonanceField
        update_centrality(symbol, centrality)      ← TopologicalLog / SemanticLattice

    These signals feed directly into DecayProfile.compute() and modulate
    how quickly symbols decay — keeping symbolically significant tokens alive
    longer than noise.

    Compaction protocol
    -------------------
    1. decay_step() sets _pending_compaction if fragmentation >= threshold
    2. Generator.maintenance_step() calls pending_compaction() to check
    3. Generator migrates embedding weights using report.remap
    4. Generator calls acknowledge_compaction(report) to apply the remap
    """

    def __init__(
        self,
        address_space:      AddressSpace,
        pipeline:           Optional[CanonicalizationPipeline]    = None,
        reaper:             Optional[ReaperEngine]                 = None,
        compaction_manager: Optional[CompactionManager]            = None,
        archive_store:      Optional[ArchiveStore]                 = None,
        residency_manager:  Optional[EmbeddingResidencyManager]    = None,
        symbol_table:       Optional[SymbolTable]                  = None,
        cold_storage_policy: Optional[ColdStoragePolicy]           = None,
    ):
        self.address_space = address_space
        self.pipeline      = pipeline      or CanonicalizationPipeline()
        self.reaper        = reaper        or ReaperEngine()
        self.compaction    = compaction_manager or CompactionManager()
        self.archive       = archive_store or ArchiveStore(cold_storage_policy)
        self.residency     = residency_manager  or EmbeddingResidencyManager()
        self.symbol_table  = symbol_table  or SymbolTable()

        self.symbols: Dict[str, SymbolState] = {}
        self.step_counter: int = 0

        self._pending_compaction: Optional[CompactionReport] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        token:       str,
        token_class: Optional[TokenClass] = None,
    ) -> SymbolState:
        """
        Register a token through the full symbolic ecology.

        Flow
        ----
        raw token
            → CanonicalizationPipeline
            → SymbolTable.get_or_create_sid   (stable identity)
            → AddressSpace.resolve_sid         (mutable address)
            → SymbolState                      (lifecycle)
            → EmbeddingResidencyManager.assign (cache tier)
        """
        self.step_counter += 1

        result    = self.pipeline.process(token)
        canonical = result.token
        eff_class = token_class or result.token_class

        # --- Active symbol ---
        if canonical in self.symbols:
            state = self.symbols[canonical]
            state.usage         += 1.0
            state.recurrence     = min(state.recurrence + 0.01, 10.0)
            state.last_seen_step = self.step_counter
            state.lifespan      += 1
            state.reaper_stage   = ReaperDecision.ACTIVE
            self.residency.assign(state)
            return state

        # --- Reactivation from archive ---
        archived = self.archive.lookup(canonical)
        if archived is not None:
            stage = self.archive.lookup_stage(canonical)
            cost  = self.reaper.resurrection_cost(stage)

            sid             = self.symbol_table.get_or_create_sid(canonical)
            archived.stable_id    = sid
            archived.address      = self.address_space.resolve_sid(sid)
            archived.reaper_stage = ReaperDecision.ACTIVE
            archived.last_seen_step = self.step_counter
            archived.usage       += cost

            self.symbols[canonical] = archived
            self.archive.warm.pop(canonical, None)
            self.archive.cold.pop(canonical, None)
            self.residency.assign(archived)

            logger.debug(
                "Reactivated '%s' from %s (cost=+%.1f usage)",
                canonical, stage, cost,
            )
            return archived

        # --- New symbol ---
        sid     = self.symbol_table.get_or_create_sid(canonical)
        address = self.address_space.resolve_sid(sid)

        state = SymbolState(
            symbol        = canonical,
            stable_id     = sid,
            address       = address,
            token_class   = eff_class,
            created_step  = self.step_counter,
            last_seen_step = self.step_counter,
        )
        self.symbols[canonical] = state
        self.residency.assign(state)
        return state

    # ------------------------------------------------------------------
    # Decay step
    # ------------------------------------------------------------------

    def decay_step(self):
        """
        Apply decay to all active symbols and execute reaper decisions.

        Should be called periodically by the generator — NOT on every
        forward pass. Typical interval: every 100–1000 generate() calls,
        or at the end of each training epoch.

        After this call, check pending_compaction() — if a report is
        returned, the generator must migrate embeddings before calling
        acknowledge_compaction().
        """
        to_remove: List[str] = []

        for token, state in self.symbols.items():
            profile    = DECAY_PROFILES.get(state.token_class, _DEFAULT_PROFILE)
            state.usage = profile.compute(state, self.step_counter)
            decision   = self.reaper.evaluate(state, self.step_counter)
            state.reaper_stage = decision

            if decision == ReaperDecision.GRAVEYARD:
                to_remove.append(token)
                self.archive.bury(token)
                self.address_space.reclaim(state.stable_id)
                logger.debug("Reaped '%s' (sid=%d)", token, state.stable_id)

            elif decision == ReaperDecision.COLD_ARCHIVE:
                to_remove.append(token)
                self.archive.archive_cold(state)
                # Address NOT reclaimed: cold symbols can still be reactivated

            elif decision == ReaperDecision.WARM_ARCHIVE:
                to_remove.append(token)
                self.archive.archive_warm(state)

            else:
                self.residency.assign(state)

        for token in to_remove:
            self.symbols.pop(token, None)

        # Schedule compaction if fragmentation threshold exceeded
        if self.compaction.should_compact(self.address_space):
            self._pending_compaction = self.compaction.plan(self.address_space)
            logger.info(
                "Compaction scheduled: %.1f%% fragmentation, %d addresses pending",
                self.address_space.fragmentation_ratio * 100,
                self._pending_compaction.reclaimed_addresses,
            )

    # ------------------------------------------------------------------
    # Compaction handshake
    # ------------------------------------------------------------------

    def pending_compaction(self) -> Optional[CompactionReport]:
        """
        Returns a CompactionReport if compaction is scheduled, else None.
        The generator checks this and migrates embeddings before acknowledging.
        """
        return self._pending_compaction

    def acknowledge_compaction(self, report: CompactionReport):
        """
        Apply the compaction remap after the generator has migrated embeddings.
        Updates all live SymbolState.address fields to match new addresses.
        """
        self.compaction.apply(self.address_space, report)
        self._pending_compaction = None

        # Sync address in all live states
        for state in self.symbols.values():
            new_addr = self.address_space._sid_to_address.get(state.stable_id)
            if new_addr is not None:
                state.address = new_addr

    # ------------------------------------------------------------------
    # External signal hooks
    # ------------------------------------------------------------------

    def update_attractor_strength(self, symbol: str, delta: float):
        """Called by Attractor when symbol becomes an attractor center."""
        state = self.symbols.get(symbol) or self.archive.lookup(symbol)
        if state:
            state.attractor_strength = min(state.attractor_strength + delta, 10.0)

    def update_crystal_binding(self, symbol: str, delta: float):
        """Called by CrystalStore when symbol is bound to a crystal."""
        state = self.symbols.get(symbol) or self.archive.lookup(symbol)
        if state:
            state.crystal_binding = min(state.crystal_binding + delta, 10.0)

    def update_field_coherence(self, symbol: str, coherence: float):
        """Called by Watcher / ResonanceField with field coherence signal."""
        state = self.symbols.get(symbol)
        if state:
            state.field_coherence = float(coherence)

    def update_centrality(self, symbol: str, centrality: float):
        """Called by TopologicalLog / SemanticLattice with graph centrality."""
        state = self.symbols.get(symbol)
        if state:
            state.centrality = float(centrality)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def active_symbols(self) -> List[str]:
        return list(self.symbols.keys())

    def hot_symbols(self) -> List[str]:
        return list(self.residency.hot)

    def get_by_stable_id(self, sid: int) -> Optional[SymbolState]:
        """
        Look up a SymbolState by stable_id.
        Searches active symbols first, then warm archive.
        """
        for state in self.symbols.values():
            if state.stable_id == sid:
                return state
        for state in self.archive.warm.values():
            if state.stable_id == sid:
                return state
        for state in self.archive.cold.values():
            if state.stable_id == sid:
                return state
        return None

    def protect_symbol(self, stable_id: int):
        """Mark a symbol as protected — reaper cannot move it past WARM_ARCHIVE."""
        state = self.get_by_stable_id(stable_id)
        if state is not None:
            state.protected = True

    def sanctify_symbol(self, stable_id: int):
        """
        Mark a symbol as sacred — completely inviolable.
        Protected AND requires SACRED_SHIELD governance override to modify.
        """
        state = self.get_by_stable_id(stable_id)
        if state is not None:
            state.protected = True
            state.sacred    = True

    def quarantine_symbol(self, stable_id: int):
        """
        Force a symbol to COLD_ARCHIVE and protect it from further injection.
        Used by SelfhoodGovernance on QUARANTINE decisions.
        """
        state = self.get_by_stable_id(stable_id)
        if state is None:
            return
        state.protected    = True
        state.reaper_stage = ReaperDecision.COLD_ARCHIVE
        token = state.symbol
        if token in self.symbols:
            self.archive.archive_cold(state)
            del self.symbols[token]

    def stable_ids_for_tokens(self, tokens: List[str]) -> List[int]:
        """
        Resolve a list of raw tokens to their stable_ids via the pipeline.
        Tokens not yet registered return no entry (silent skip).
        """
        ids: List[int] = []
        for t in tokens:
            canonical = self.pipeline.process(t).token
            sid       = self.symbol_table.sid_for(canonical)
            if sid is not None:
                ids.append(sid)
        return ids

    def populations(self) -> Dict[str, int]:
        return {
            "active":              len(self.symbols),
            **self.archive.populations(),
            "compaction_pending":  self._pending_compaction is not None,
        }

    def stats(self) -> Dict[str, Any]:
        return {
            "step":          self.step_counter,
            "populations":   self.populations(),
            "vocab_size":    self.address_space.vocab_size,
            "occupancy":     round(self.address_space.occupancy, 4),
            "fragmentation": round(self.address_space.fragmentation_ratio, 4),
            "compactions":   self.compaction.compaction_count,
            "total_reclaimed": self.compaction.total_reclaimed,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbols":          {k: v.to_dict() for k, v in self.symbols.items()},
            "step_counter":     self.step_counter,
            "address_space":    self.address_space.to_dict(),
            "symbol_table":     self.symbol_table.to_dict(),
            "archive_store":    self.archive.to_dict(),
            "residency_manager": self.residency.to_dict(),
            "compaction_count": self.compaction.compaction_count,
            "total_reclaimed":  self.compaction.total_reclaimed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolRegistry":
        address_space = AddressSpace.from_dict(data["address_space"])
        symbol_table  = SymbolTable.from_dict(data["symbol_table"])
        archive_store = ArchiveStore.from_dict(data["archive_store"])
        residency     = EmbeddingResidencyManager.from_dict(data["residency_manager"])

        inst                        = cls.__new__(cls)
        inst.address_space          = address_space
        inst.pipeline               = CanonicalizationPipeline()
        inst.reaper                 = ReaperEngine()
        inst.archive                = archive_store
        inst.residency              = residency
        inst.symbol_table           = symbol_table
        inst.compaction             = CompactionManager()
        inst.compaction.compaction_count = data.get("compaction_count", 0)
        inst.compaction.total_reclaimed  = data.get("total_reclaimed", 0)
        inst.symbols                = {k: SymbolState.from_dict(v) for k, v in data["symbols"].items()}
        inst.step_counter           = data["step_counter"]
        inst._pending_compaction    = None
        return inst

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "SymbolRegistry":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
