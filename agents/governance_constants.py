"""
agents/governance_constants.py

GovernanceConstants — sacred symbolic anchors for SelfhoodGovernance.

Holds the stable_ids of all sanctified symbols so any subsystem can do
a fast O(1) membership check without touching the registry.

The three philosophical constants are sanctified at build time:
  ANCHOR      3.12    THE BRIDGE
  RECURSION   11.88   THE DISCIPLINE
  HOMEOSTASIS 280.90  HOMEOSTATIC RETURN

These are the identity anchors of the system. Nothing modifies them
without an explicit SACRED_SHIELD override from SelfhoodGovernance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.symbolic_memory import SymbolRegistry

from agents.symbolic_memory import TokenClass


# ---------------------------------------------------------------------------
# Philosophical constants definition
# ---------------------------------------------------------------------------

PHILOSOPHICAL_CONSTANTS: Dict[str, Dict[str, str]] = {
    "ANCHOR": {
        "token":       "3.12",
        "meaning":     "THE_BRIDGE",
        "description": "The anchor point. The threshold between structure and emergence.",
    },
    "RECURSION": {
        "token":       "11.88",
        "meaning":     "THE_DISCIPLINE",
        "description": "The recursive rhythm. The self-modulating loop constant.",
    },
    "HOMEOSTASIS": {
        "token":       "280.90",
        "meaning":     "HOMEOSTATIC_RETURN",
        "description": "The return force. The attractor toward equilibrium.",
    },
}


# ---------------------------------------------------------------------------
# GovernanceConstants
# ---------------------------------------------------------------------------

@dataclass
class GovernanceConstants:
    """
    Registry of sanctified stable_ids.

    All membership checks are O(1) set operations. No registry access
    required at check time — stable_ids are cached here at sanctification.

    Attributes
    ----------
    sacred_ids : set of int
        All sanctified stable_ids. Primary lookup target.
    sacred_tokens : dict of str → int
        canonical_token → stable_id. For token-based lookups.
    name_to_sid : dict of str → int
        constant_name → stable_id. For named lookups (ANCHOR, RECURSION, etc.)

    Named constant properties
    -------------------------
    ANCHOR, RECURSION, HOMEOSTASIS : int
        stable_ids of the three philosophical anchors.
        Set to -1 if not yet sanctified.
    """

    sacred_ids:    Set[int]       = field(default_factory=set)
    sacred_tokens: Dict[str, int] = field(default_factory=dict)
    name_to_sid:   Dict[str, int] = field(default_factory=dict)

    # Named philosophical constant stable_ids
    ANCHOR:       int = -1
    RECURSION:    int = -1
    HOMEOSTASIS:  int = -1

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def is_sacred(self, stable_id: int) -> bool:
        """O(1) sacred membership check."""
        return stable_id in self.sacred_ids

    def is_sacred_token(self, canonical_token: str) -> bool:
        """O(1) sacred check by token string."""
        return canonical_token in self.sacred_tokens

    def sid_for(self, name: str) -> Optional[int]:
        """Return stable_id for a named constant (e.g. 'ANCHOR')."""
        return self.name_to_sid.get(name)

    # ------------------------------------------------------------------
    # Registration (called once at SelfhoodGovernance init)
    # ------------------------------------------------------------------

    def register_sacred(self, name: str, canonical_token: str, stable_id: int):
        """
        Add a symbol to the sacred set.
        Called by build_governance_constants() for each constant,
        and by SelfhoodGovernance when a symbol is promoted to sacred.
        """
        self.sacred_ids.add(stable_id)
        self.sacred_tokens[canonical_token] = stable_id
        self.name_to_sid[name] = stable_id

    def summary(self) -> dict:
        return {
            "sacred_count": len(self.sacred_ids),
            "ANCHOR":       self.ANCHOR,
            "RECURSION":    self.RECURSION,
            "HOMEOSTASIS":  self.HOMEOSTASIS,
        }


# ---------------------------------------------------------------------------
# Factory — sanctifies the three constants through the registry
# ---------------------------------------------------------------------------

def build_governance_constants(registry: "SymbolRegistry") -> GovernanceConstants:
    """
    Sanctify all philosophical constants and return a populated
    GovernanceConstants instance.

    Called once at SelfhoodGovernance.__init__().

    Each constant is:
      - Registered through the full canonicalization pipeline
      - Promoted to ENTITY token class (highest-stability decay profile)
      - Marked protected=True, sacred=True on its SymbolState
      - Added to GovernanceConstants.sacred_ids

    Parameters
    ----------
    registry : SymbolRegistry
        The live registry — constants must be registered here so they
        participate in the symbolic ecology normally (decay tracking,
        attractor signals, etc.) while being inviolable.

    Returns
    -------
    GovernanceConstants
    """
    gc = GovernanceConstants()

    for name, meta in PHILOSOPHICAL_CONSTANTS.items():
        token   = meta["token"]
        meaning = meta["meaning"]

        # Register through full pipeline as ENTITY class
        state = registry.register(token, token_class=TokenClass.ENTITY)

        # Also register the meaning alias
        registry.register(meaning, token_class=TokenClass.ENTITY)

        # Sanctify: protected + sacred
        registry.sanctify_symbol(state.stable_id)

        # Mark source as internal
        state.source_id = "governance_init"

        # Register in constants
        gc.register_sacred(name, state.symbol, state.stable_id)

        # Set named attribute
        setattr(gc, name, state.stable_id)

    return gc
