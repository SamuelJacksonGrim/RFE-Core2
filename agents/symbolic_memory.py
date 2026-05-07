# agents/symbolic_memory.py
"""
Persistent Symbolic Ecology Architecture
═══════════════════════════════════════════════════════════════════════════════

This module separates symbolic cognition into ecological layers:

    AddressSpace
        Deterministic symbolic identity allocation

    SymbolRegistry
        Lifecycle + semantic metadata

    DecayEngine
        Pluggable symbolic metabolism

    ArchiveStore
        Warm / cold / graveyard persistence

    EmbeddingResidencyManager
        Hot / warm / cold embedding control

    ReactivationEngine
        Historical symbolic continuity restoration

Core Principle
──────────────
Tokens are no longer transient text units.

They are persistent symbolic entities participating in a living manifold.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import unicodedata

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set, List

logger = logging.getLogger(__name__)


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
# ADDRESS SPACE
# =============================================================================

class AddressSpace:
    """
    Deterministic symbolic address allocator.

    ONLY responsible for:
        symbol → stable address
    """

    SPECIAL = ["<PAD>", "<UNK>", "<BOS>", "<EOS>"]

    def __init__(
        self,
        vocab_size: int = 8192,
        allow_resize: bool = True,
        resize_factor: float = 2.0,
    ):
        self.vocab_size = vocab_size
        self.allow_resize = allow_resize
        self.resize_factor = resize_factor

        self._tok2id = {
            t: i for i, t in enumerate(self.SPECIAL)
        }

        self._id2tok = {
            i: t for t, i in self._tok2id.items()
        }

        self._num_assigned = len(self._tok2id)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def occupancy(self) -> float:
        return self._num_assigned / float(self.vocab_size)

    # -------------------------------------------------------------------------
    # Hashing
    # -------------------------------------------------------------------------

    def _sha256_int(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest, "big")

    def _secondary_hash(self, token: str) -> int:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        return int.from_bytes(digest, "big")

    # -------------------------------------------------------------------------
    # Resize
    # -------------------------------------------------------------------------

    def _resize(self):

        new_size = int(
            math.ceil(self.vocab_size * self.resize_factor)
        )

        logger.info(
            "AddressSpace resize %d → %d",
            self.vocab_size,
            new_size,
        )

        old_tokens = list(self._tok2id.keys())

        self.vocab_size = new_size

        self._tok2id = {
            t: i for i, t in enumerate(self.SPECIAL)
        }

        self._id2tok = {
            i: t for t, i in self._tok2id.items()
        }

        self._num_assigned = len(self.SPECIAL)

        for tok in old_tokens:
            if tok not in self.SPECIAL:
                self.resolve(tok)

    # -------------------------------------------------------------------------
    # Core
    # -------------------------------------------------------------------------

    def resolve(self, token: str) -> int:

        if token in self._tok2id:
            return self._tok2id[token]

        if self.occupancy >= 0.85:
            if self.allow_resize:
                self._resize()
            else:
                raise RuntimeError("AddressSpace exhausted.")

        base = len(self.SPECIAL)
        span = self.vocab_size - base

        primary = (
            self._sha256_int(token) % span
        ) + base

        step = (
            self._secondary_hash(token) % (span - 1)
        ) + 1

        probe = primary
        probes = 0

        while True:

            existing = self._id2tok.get(probe)

            if existing is None or existing == token:
                break

            probe = (
                ((probe - base + step) % span) + base
            )

            probes += 1

            if probes >= span:
                raise RuntimeError("Probe exhaustion.")

        self._tok2id[token] = probe
        self._id2tok[probe] = token

        self._num_assigned += 1

        return probe

    def lookup(self, idx: int) -> str:
        return self._id2tok.get(idx, "<UNK>")


# =============================================================================
# SYMBOL STATE
# =============================================================================

@dataclass
class SymbolState:

    symbol: str
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
    ):

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

    def lookup(self, symbol: str):

        if symbol in self.warm:
            return self.warm[symbol]

        if symbol in self.cold:
            return self.cold[symbol]

        return None


# =============================================================================
# EMBEDDING RESIDENCY
# =============================================================================

class EmbeddingResidencyManager:

    def __init__(self):

        self.hot: Set[str] = set()
        self.warm: Set[str] = set()
        self.cold: Set[str] = set()

    def assign(
        self,
        state: SymbolState,
    ):

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
    ):

        self.address_space = address_space

        self.canonicalizer = (
            canonicalizer
            or Canonicalizer()
        )

        self.decay_engine = (
            decay_engine
            or DecayEngine()
        )

        self.archive_store = (
            archive_store
            or ArchiveStore()
        )

        self.residency_manager = (
            residency_manager
            or EmbeddingResidencyManager()
        )

        self.symbols: Dict[str, SymbolState] = {}

        self.step_counter = 0

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

        # ---------------------------------------------------------------------
        # Existing
        # ---------------------------------------------------------------------

        if token in self.symbols:

            state = self.symbols[token]

            state.usage += 1.0
            state.recurrence += 0.01
            state.last_seen_step = self.step_counter

            self.residency_manager.assign(state)

            return state

        # ---------------------------------------------------------------------
        # Reactivation
        # ---------------------------------------------------------------------

        archived = self.archive_store.lookup(token)

        if archived is not None:

            archived.active = True
            archived.archived = False
            archived.last_seen_step = self.step_counter
            archived.usage += 5.0

            self.symbols[token] = archived

            logger.info(
                "Reactivated archived symbol: %s",
                token,
            )

            return archived

        # ---------------------------------------------------------------------
        # New Symbol
        # ---------------------------------------------------------------------

        address = self.address_space.resolve(token)

        state = SymbolState(
            symbol=token,
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

            # -----------------------------------------------------------------
            # Warm Archive
            # -----------------------------------------------------------------

            if usage < 1.0:

                state.active = False
                state.archived = True

                self.archive_store.archive_warm(state)

            # -----------------------------------------------------------------
            # Cold Archive
            # -----------------------------------------------------------------

            if usage < 0.1:

                self.archive_store.archive_cold(state)

            # -----------------------------------------------------------------
            # Graveyard
            # -----------------------------------------------------------------

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
