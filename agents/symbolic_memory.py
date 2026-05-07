# agents/symbolic_memory.py
"""
Persistent Symbolic Ecology Architecture
═══════════════════════════════════════════════════════════════════════════════

Layers
------
    Canonicalizer
        Token normalization / semantic stabilization

    SymbolTable
        Stable symbolic identity (symbol → stable_id)

    AddressSpace
        stable_id → address (mutable, resize-safe)

    SymbolRegistry
        Lifecycle + semantic metadata

    DecayEngine
        Symbolic metabolism

    ArchiveStore
        Warm / cold / graveyard persistence

    EmbeddingResidencyManager
        HOT / WARM / COLD residency classification
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import unicodedata

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Optional, Set, List, Any

logger = logging.getLogger(__name__)


# =============================================================================
# MODULE-LEVEL CONSTANTS
# =============================================================================

SPECIAL_TOKENS = ["<PAD>", "<UNK>", "<BOS>", "<EOS>"]


# =============================================================================
# ENUMS
# =============================================================================

class CanonicalizationMode(Enum):
    NONE = "none"
    LIGHT = "light"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    SYMBOLIC = "symbolic"


class TokenClass(Enum):
    LANGUAGE = "language"
    IDENTIFIER = "identifier"
    ENTITY = "entity"
    GLYPH = "glyph"
    RELATIONAL = "relational"
    OPERATOR = "operator"
    EPHEMERAL = "ephemeral"


class Residency(Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVED = "archived"


# =============================================================================
# CANONICALIZER
# =============================================================================

class Canonicalizer:

    SYMBOLIC_RULES = {
        "c++": "cpp",
        "c#": "csharp",
        "e8-eea": "e8_eea",
    }

    def __init__(
        self,
        mode: CanonicalizationMode = CanonicalizationMode.LIGHT,
    ):
        self.mode = mode

    def normalize(self, token: str) -> str:

        if not isinstance(token, str):
            token = str(token)

        if self.mode == CanonicalizationMode.NONE:
            return token

        token = unicodedata.normalize("NFKC", token)
        token = token.strip()

        if self.mode == CanonicalizationMode.LIGHT:
            return token

        token = token.lower()

        if self.mode == CanonicalizationMode.STANDARD:
            return token

        if self.mode == CanonicalizationMode.SYMBOLIC:
            return self.SYMBOLIC_RULES.get(token, token)

        if self.mode == CanonicalizationMode.AGGRESSIVE:
            token = re.sub(r"[^\w\s]", "", token)
            return token

        return token


# =============================================================================
# SYMBOL TABLE (stable identity)
# =============================================================================

class SymbolTable:
    """
    Stable symbolic identity layer.

    symbol → stable_id (never changes)
    stable_id → symbol
    """

    def __init__(self):
        self._symbol_to_sid: Dict[str, int] = {}
        self._sid_to_symbol: Dict[int, str] = {}
        # Reserve 0-3 for specials
        self._next_sid: int = len(SPECIAL_TOKENS)

        for i, tok in enumerate(SPECIAL_TOKENS):
            self._symbol_to_sid[tok] = i
            self._sid_to_symbol[i] = tok

    def get_or_create_sid(self, symbol: str) -> int:
        if symbol in self._symbol_to_sid:
            return self._symbol_to_sid[symbol]

        sid = self._next_sid
        self._next_sid += 1

        self._symbol_to_sid[symbol] = sid
        self._sid_to_symbol[sid] = symbol

        return sid

    def symbol_for(self, sid: int) -> str:
        return self._sid_to_symbol.get(sid, "<UNK>")

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_to_sid": self._symbol_to_sid,
            "next_sid": self._next_sid,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolTable":
        inst = cls.__new__(cls)
        inst._symbol_to_sid = dict(data["symbol_to_sid"])
        inst._sid_to_symbol = {v: k for k, v in inst._symbol_to_sid.items()}
        inst._next_sid = data["next_sid"]
        return inst


# =============================================================================
# ADDRESS SPACE (stable_id → address)
# =============================================================================

class AddressSpace:
    """
    Deterministic symbolic address allocator.

    ONLY responsible for:
        stable_id → address
    """

    def __init__(
        self,
        vocab_size: int = 8192,
        allow_resize: bool = True,
        resize_factor: float = 2.0,
    ):
        assert vocab_size > len(SPECIAL_TOKENS)

        self.vocab_size = int(vocab_size)
        self.allow_resize = bool(allow_resize)
        self.resize_factor = float(resize_factor)

        # Special tokens occupy fixed addresses 0..len(SPECIAL)-1
        self._tok2id: Dict[str, int] = {
            t: i for i, t in enumerate(SPECIAL_TOKENS)
        }
        self._id2tok: Dict[int, str] = {
            i: t for t, i in self._tok2id.items()
        }

        # stable_id → address (for non-specials)
        self._sid_to_address: Dict[int, int] = {}
        self._id2sid: Dict[int, int] = {}

        self._num_assigned: int = len(SPECIAL_TOKENS)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def occupancy(self) -> float:
        return self._num_assigned / float(self.vocab_size)

    @property
    def pad_id(self) -> int:
        return self._tok2id["<PAD>"]

    @property
    def unk_id(self) -> int:
        return self._tok2id["<UNK>"]

    @property
    def bos_id(self) -> int:
        return self._tok2id["<BOS>"]

    @property
    def eos_id(self) -> int:
        return self._tok2id["<EOS>"]

    # -------------------------------------------------------------------------
    # Resize
    # -------------------------------------------------------------------------

    def _resize(self):
        new_size = int(math.ceil(self.vocab_size * self.resize_factor))

        logger.info(
            "AddressSpace resize %d → %d",
            self.vocab_size,
            new_size,
        )

        # Preserve existing stable_ids
        old_sids = list(self._sid_to_address.keys())

        self.vocab_size = new_size

        # Reset id maps for specials
        self._tok2id = {t: i for i, t in enumerate(SPECIAL_TOKENS)}
        self._id2tok = {i: t for t, i in self._tok2id.items()}

        self._sid_to_address = {}
        self._id2sid = {}
        self._num_assigned = len(SPECIAL_TOKENS)

        # Re-resolve all stable_ids into new address space
        for sid in old_sids:
            self.resolve_sid(sid)

    # -------------------------------------------------------------------------
    # Core: stable_id → address
    # -------------------------------------------------------------------------

    def resolve_sid(self, sid: int) -> int:
        """
        Map stable_id → address.

        Specials (0..len(SPECIAL)-1) map to fixed addresses.
        Non-specials use open addressing with double hashing.
        """
        base = len(SPECIAL_TOKENS)

        # Specials: sid == address
        if sid < base:
            return sid

        if sid in self._sid_to_address:
            return self._sid_to_address[sid]

        if self.occupancy >= 0.85:
            if self.allow_resize:
                self._resize()
            else:
                raise RuntimeError("AddressSpace exhausted.")

        span = self.vocab_size - base

        # Deterministic hashing on stable_id
        # Golden ratio hash for primary, Fibonacci for step
        primary = (sid * 11400714819323198485) % span + base
        step = ((sid * 0x9e3779b97f4a7c15) % (span - 1)) + 1

        probe = primary
        probes = 0

        while True:
            existing_sid = self._id2sid.get(probe)

            if existing_sid is None or existing_sid == sid:
                break

            probe = ((probe - base + step) % span) + base
            probes += 1

            if probes >= span:
                raise RuntimeError("Probe exhaustion.")

        self._sid_to_address[sid] = probe
        self._id2sid[probe] = sid
        self._num_assigned += 1

        return probe

    def lookup_symbol(self, idx: int, symbol_table: SymbolTable) -> str:
        base = len(SPECIAL_TOKENS)
        if idx < base:
            return self._id2tok.get(idx, "<UNK>")
        sid = self._id2sid.get(idx, None)
        if sid is None:
            return "<UNK>"
        return symbol_table.symbol_for(sid)

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vocab_size": self.vocab_size,
            "allow_resize": self.allow_resize,
            "resize_factor": self.resize_factor,
            "sid_to_address": self._sid_to_address,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AddressSpace":
        inst = cls.__new__(cls)
        inst.vocab_size = data["vocab_size"]
        inst.allow_resize = data["allow_resize"]
        inst.resize_factor = data["resize_factor"]
        inst._tok2id = {t: i for i, t in enumerate(SPECIAL_TOKENS)}
        inst._id2tok = {i: t for t, i in inst._tok2id.items()}
        inst._sid_to_address = {int(k): v for k, v in data["sid_to_address"].items()}
        inst._id2sid = {v: int(k) for k, v in inst._sid_to_address.items()}
        inst._num_assigned = len(SPECIAL_TOKENS) + len(inst._sid_to_address)
        return inst


# =============================================================================
# SYMBOL STATE
# =============================================================================

@dataclass
class SymbolState:
    symbol: str
    stable_id: int
    address: int

    token_class: TokenClass

    usage: float = 1.0
    recurrence: float = 0.0
    centrality: float = 0.0
    attractor_strength: float = 0.0

    created_step: int = 0
    last_seen_step: int = 0

    active: bool = True
    archived: bool = False

    residency: Residency = Residency.HOT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "stable_id": self.stable_id,
            "address": self.address,
            "token_class": self.token_class.value,
            "usage": self.usage,
            "recurrence": self.recurrence,
            "centrality": self.centrality,
            "attractor_strength": self.attractor_strength,
            "created_step": self.created_step,
            "last_seen_step": self.last_seen_step,
            "active": self.active,
            "archived": self.archived,
            "residency": self.residency.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolState":
        return cls(
            symbol=data["symbol"],
            stable_id=data["stable_id"],
            address=data["address"],
            token_class=TokenClass(data["token_class"]),
            usage=data["usage"],
            recurrence=data["recurrence"],
            centrality=data["centrality"],
            attractor_strength=data["attractor_strength"],
            created_step=data["created_step"],
            last_seen_step=data["last_seen_step"],
            active=data["active"],
            archived=data["archived"],
            residency=Residency(data["residency"]),
        )


# =============================================================================
# DECAY ENGINE
# =============================================================================

class DecayEngine:
    """
    Symbolic metabolism controller.
    """

    CLASS_DECAY = {
        TokenClass.LANGUAGE: 0.999,
        TokenClass.ENTITY: 0.9995,
        TokenClass.RELATIONAL: 0.9992,
        TokenClass.GLYPH: 0.9998,
        TokenClass.IDENTIFIER: 0.998,
        TokenClass.OPERATOR: 0.997,
        TokenClass.EPHEMERAL: 0.990,
    }

    def step(
        self,
        state: SymbolState,
        current_step: int,
    ) -> float:

        age = max(1, current_step - state.last_seen_step)

        decay = self.CLASS_DECAY.get(
            state.token_class,
            0.995,
        )

        reinforcement = (
            1.0
            + state.recurrence
            + state.attractor_strength
            + state.centrality
        )

        state.usage *= (
            decay
            * math.exp(-0.001 * age)
            * reinforcement
        )

        return state.usage


# =============================================================================
# ARCHIVE STORE
# =============================================================================

class ArchiveStore:
    """
    Multi-tier symbolic persistence.
    """

    def __init__(self):
        self.warm: Dict[str, SymbolState] = {}
        self.cold: Dict[str, SymbolState] = {}
        self.graveyard: Set[str] = set()

    # -------------------------------------------------------------------------
    # Archive
    # -------------------------------------------------------------------------

    def archive_warm(self, state: SymbolState):
        self.warm[state.symbol] = state

    def archive_cold(self, state: SymbolState):
        self.cold[state.symbol] = state

    def bury(self, symbol: str):
        self.graveyard.add(symbol)

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def lookup(self, symbol: str) -> Optional[SymbolState]:
        if symbol in self.warm:
            return self.warm[symbol]
        if symbol in self.cold:
            return self.cold[symbol]
        return None

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warm": {k: v.to_dict() for k, v in self.warm.items()},
            "cold": {k: v.to_dict() for k, v in self.cold.items()},
            "graveyard": list(self.graveyard),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchiveStore":
        inst = cls.__new__(cls)
        inst.warm = {k: SymbolState.from_dict(v) for k, v in data["warm"].items()}
        inst.cold = {k: SymbolState.from_dict(v) for k, v in data["cold"].items()}
        inst.graveyard = set(data["graveyard"])
        return inst


# =============================================================================
# EMBEDDING RESIDENCY
# =============================================================================

class EmbeddingResidencyManager:

    def __init__(self):
        self.hot: Set[str] = set()
        self.warm: Set[str] = set()
        self.cold: Set[str] = set()

    def assign(self, state: SymbolState):
        # Remove from all sets first to prevent stale entries
        self.hot.discard(state.symbol)
        self.warm.discard(state.symbol)
        self.cold.discard(state.symbol)

        usage = state.usage

        if usage > 100:
            state.residency = Residency.HOT
            self.hot.add(state.symbol)
        elif usage > 10:
            state.residency = Residency.WARM
            self.warm.add(state.symbol)
        else:
            state.residency = Residency.COLD
            self.cold.add(state.symbol)

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hot": list(self.hot),
            "warm": list(self.warm),
            "cold": list(self.cold),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingResidencyManager":
        inst = cls.__new__(cls)
        inst.hot = set(data["hot"])
        inst.warm = set(data["warm"])
        inst.cold = set(data["cold"])
        return inst


# =============================================================================
# SYMBOL REGISTRY
# =============================================================================

class SymbolRegistry:
    """
    Living symbolic ecology manager.
    """

    def __init__(
        self,
        address_space: AddressSpace,
        canonicalizer: Optional[Canonicalizer] = None,
        decay_engine: Optional[DecayEngine] = None,
        archive_store: Optional[ArchiveStore] = None,
        residency_manager: Optional[EmbeddingResidencyManager] = None,
        symbol_table: Optional[SymbolTable] = None,
    ):
        self.address_space = address_space

        self.canonicalizer = canonicalizer or Canonicalizer()
        self.decay_engine = decay_engine or DecayEngine()
        self.archive_store = archive_store or ArchiveStore()
        self.residency_manager = residency_manager or EmbeddingResidencyManager()
        self.symbol_table = symbol_table or SymbolTable()

        self.symbols: Dict[str, SymbolState] = {}
        self.step_counter: int = 0

    # -------------------------------------------------------------------------
    # Register
    # -------------------------------------------------------------------------

    def register(
        self,
        token: str,
        token_class: TokenClass = TokenClass.LANGUAGE,
    ) -> SymbolState:

        token = self.canonicalizer.normalize(token)
        self.step_counter += 1

        # Existing
        if token in self.symbols:
            state = self.symbols[token]
            state.usage += 1.0
            state.recurrence += 0.01
            state.last_seen_step = self.step_counter
            self.residency_manager.assign(state)
            return state

        # Reactivation
        archived = self.archive_store.lookup(token)
        if archived is not None:
            sid = self.symbol_table.get_or_create_sid(token)
            archived.stable_id = sid
            archived.address = self.address_space.resolve_sid(sid)
            archived.active = True
            archived.archived = False
            archived.last_seen_step = self.step_counter
            archived.usage += 5.0

            self.symbols[token] = archived
            self.residency_manager.assign(archived)

            logger.info("Reactivated archived symbol: %s", token)
            return archived

        # New symbol
        sid = self.symbol_table.get_or_create_sid(token)
        address = self.address_space.resolve_sid(sid)

        state = SymbolState(
            symbol=token,
            stable_id=sid,
            address=address,
            token_class=token_class,
            created_step=self.step_counter,
            last_seen_step=self.step_counter,
        )

        self.symbols[token] = state
        self.residency_manager.assign(state)

        return state

    # -------------------------------------------------------------------------
    # Decay Step
    # -------------------------------------------------------------------------

    def decay_step(self):
        for token, state in list(self.symbols.items()):
            usage = self.decay_engine.step(
                state,
                self.step_counter,
            )

            # Warm archive
            if usage < 1.0:
                state.active = False
                state.archived = True
                self.archive_store.archive_warm(state)

            # Cold archive
            if usage < 0.1:
                self.archive_store.archive_cold(state)

            # Graveyard
            if usage < 0.01:
                self.archive_store.bury(token)
                del self.symbols[token]

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def active_symbols(self) -> List[str]:
        return list(self.symbols.keys())

    def archived_symbols(self) -> List[str]:
        return list(self.archive_store.warm.keys())

    def graveyard_symbols(self) -> List[str]:
        return list(self.archive_store.graveyard)

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbols": {k: v.to_dict() for k, v in self.symbols.items()},
            "step_counter": self.step_counter,
            "address_space": self.address_space.to_dict(),
            "symbol_table": self.symbol_table.to_dict(),
            "archive_store": self.archive_store.to_dict(),
            "residency_manager": self.residency_manager.to_dict(),
            "canonicalizer_mode": self.canonicalizer.mode.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SymbolRegistry":
        address_space = AddressSpace.from_dict(data["address_space"])
        symbol_table = SymbolTable.from_dict(data["symbol_table"])
        archive_store = ArchiveStore.from_dict(data["archive_store"])
        residency_manager = EmbeddingResidencyManager.from_dict(data["residency_manager"])
        canonicalizer = Canonicalizer(mode=CanonicalizationMode(data["canonicalizer_mode"]))

        inst = cls.__new__(cls)
        inst.address_space = address_space
        inst.canonicalizer = canonicalizer
        inst.decay_engine = DecayEngine()
        inst.archive_store = archive_store
        inst.residency_manager = residency_manager
        inst.symbol_table = symbol_table
        inst.symbols = {k: SymbolState.from_dict(v) for k, v in data["symbols"].items()}
        inst.step_counter = data["step_counter"]
        return inst

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "SymbolRegistry":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
