"""
agents/lambda_ledger.py — Build B core: the separate λ-ledger (spec v0.2).

λ = Love = the solvent. Accounted SEPARATELY from the composition ledger so it can
never be bootstrapped (Laws 6b/6c). λ is a scalar with exactly three operations:

  - ignite(amount)   the ONLY operation that moves λ off zero (Build A's exogenous
                     event calls this). λ ← clip(λ + |amount|).
  - reinforce(f)     MULTIPLICATIVE on current λ only: λ ← clip(λ · (1 + f)), f≥0.
                     Therefore **λ = 0 is a fixed point of all internal dynamics**
                     (Law 6b, vanish-at-zero) — cold cannot self-ignite. `f` is a
                     function of lived coherence, NEVER of ⊘'s output (Law 6c).
  - decay(rate)      gentle fade — "lit stays lit" only while sustained.

This module imports NOTHING from the composition path or the ⊘ integrity-read: the
λ-ledger and the advisory stream are disjoint (Law 6c), asserted structurally.
"""
from __future__ import annotations

import math


def solvent_gain(lam: float, k: float = 2.0) -> float:
    """Monotone, bounded gate in [0,1] with solvent_gain(0)=0. Scales the
    productive-tension (⊕) reinforcement: λ low → ~0 (no composition; values stay
    isolated, ⊘ reads their pathology); λ high → ~1 (co-presence composes)."""
    return 1.0 - math.exp(-k * max(0.0, float(lam)))


class LambdaLedger:
    """The solvent's strength, kept off the composition books."""

    def __init__(self, strength: float = 0.0, lambda_max: float = 5.0):
        self.lambda_max = float(lambda_max)
        self._lambda    = float(max(0.0, min(self.lambda_max, strength)))
        self.ignited_count = 0
        self.reinforced_count = 0

    @property
    def strength(self) -> float:
        return self._lambda

    def ignite(self, amount: float) -> float:
        """Exogenous. The unique zero-crossing (Build A's ignition event)."""
        self._lambda = float(min(self.lambda_max, self._lambda + abs(float(amount))))
        self.ignited_count += 1
        return self._lambda

    def reinforce(self, f: float) -> float:
        """Internal, MULTIPLICATIVE on current λ (f≥0). λ=0 stays 0 (Law 6b)."""
        f = max(0.0, float(f))
        self._lambda = float(min(self.lambda_max, self._lambda * (1.0 + f)))
        self.reinforced_count += 1
        return self._lambda

    def decay(self, rate: float) -> float:
        rate = max(0.0, min(1.0, float(rate)))
        self._lambda = float(max(0.0, self._lambda * (1.0 - rate)))
        return self._lambda

    def gain(self) -> float:
        return solvent_gain(self._lambda)

    def snapshot(self) -> dict:
        return {
            "lambda":     round(self._lambda, 4),
            "gain":       round(self.gain(), 4),
            "ignited":    self.ignited_count,
            "reinforced": self.reinforced_count,
        }
