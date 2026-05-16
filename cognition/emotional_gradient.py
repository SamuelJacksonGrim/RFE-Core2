"""
cognition/emotional_gradient.py

Emotional gradient system — field modulation dynamics.

Emotions are not roleplay. They are computational state variables that
modulate the system's behavior at every level:

    Curiosity   prediction error → explore, inject stronger, mutate more
    Wonder      novelty + coherence → dream, synthesize
    Joy         coherence reinforcement → stabilize, crystallize
    Tension     sustained error → slow decay, tighten attractor pull
    Boredom     low error + low novelty → seek disruption, increase noise
    Stability   coherence floor → decay rate, identity persistence

All states are smooth [0, 1] scalars. Updates are EMA-smoothed to prevent
chaotic oscillation. The system can be in multiple emotional states at once.

Modulation outputs (read by autonomous_cycle every step)
---------------------------------------------------------
    field_gain()        injection strength multiplier
    mutation_scale()    differential noise scale
    field_decay_rate()  resonance field decay rate
    dream_pressure()    probability of entering dream cycle
    attractor_pull()    attractor blend strength modifier
    crystal_pressure()  crystallization threshold modifier
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class EmotionalState:
    """Snapshot of the current emotional gradient state."""
    curiosity:  float
    wonder:     float
    joy:        float
    tension:    float
    boredom:    float
    stability:  float
    dominant:   str    # name of the highest-value state

    def as_dict(self) -> dict:
        return {
            "curiosity":  round(self.curiosity, 4),
            "wonder":     round(self.wonder, 4),
            "joy":        round(self.joy, 4),
            "tension":    round(self.tension, 4),
            "boredom":    round(self.boredom, 4),
            "stability":  round(self.stability, 4),
            "dominant":   self.dominant,
        }


class EmotionalGradient:
    """
    Smooth emotional state machine with live modulation outputs.

    Parameters
    ----------
    ema_alpha : float
        EMA smoothing factor. Lower = smoother but slower response.
    base_field_gain : float
        Baseline injection strength (multiplied by curiosity/wonder).
    base_mutation_scale : float
        Baseline differential noise scale.
    base_decay_rate : float
        Baseline field decay rate (modified by stability/tension).
    """

    def __init__(
        self,
        ema_alpha:           float = 0.15,
        base_field_gain:     float = 1.0,
        base_mutation_scale: float = 0.05,
        base_decay_rate:     float = 0.995,
    ):
        self.ema_alpha           = ema_alpha
        self.base_field_gain     = base_field_gain
        self.base_mutation_scale = base_mutation_scale
        self.base_decay_rate     = base_decay_rate

        # Emotional state variables ∈ [0, 1]
        self._curiosity  = 0.3
        self._wonder     = 0.2
        self._joy        = 0.5
        self._tension    = 0.1
        self._boredom    = 0.0
        self._stability  = 0.7

        self._step = 0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        prediction_error: float,
        coherence:        float,
        prediction_report=None,   # EchoReport (optional, for richer signals)
        field_energy:     float = 0.0,
    ) -> EmotionalState:
        """
        Update emotional state from system signals.

        Parameters
        ----------
        prediction_error : float
            Raw prediction error from PredictiveEcho.
        coherence : float
            Composite coherence from Watcher (CoherenceReport.composite).
        prediction_report : EchoReport or None
            If provided, uses richer curiosity/surprise/tension/boredom signals.
        field_energy : float
            Current field L2 norm — high energy → reduced stability.
        """
        self._step += 1

        if prediction_report is not None:
            # Use the richer pre-computed signals
            target_curiosity = prediction_report.curiosity
            target_tension   = prediction_report.tension
            target_boredom   = prediction_report.boredom
            surprise_boost   = prediction_report.surprise
        else:
            # Compute from raw signals
            target_curiosity = float(np.clip(prediction_error / 2.0, 0.0, 1.0))
            target_tension   = float(np.clip(prediction_error / 3.0, 0.0, 1.0))
            target_boredom   = float(np.clip(1.0 - prediction_error, 0.0, 1.0)) * (1.0 - coherence)
            surprise_boost   = 0.0

        # Wonder = novelty (curiosity) × coherence — something new that makes sense
        target_wonder   = target_curiosity * coherence

        # Joy = sustained coherence
        target_joy      = coherence

        # Stability = coherence floor, reduced by field energy and tension
        energy_penalty  = float(np.clip(field_energy / 10.0, 0.0, 0.5))
        target_stability = float(np.clip(coherence - energy_penalty - target_tension * 0.3, 0.0, 1.0))

        # EMA updates — smooth all transitions
        self._curiosity  = self._ema(self._curiosity,  target_curiosity + surprise_boost * 0.3)
        self._wonder     = self._ema(self._wonder,     target_wonder)
        self._joy        = self._ema(self._joy,        target_joy)
        self._tension    = self._ema(self._tension,    target_tension)
        self._boredom    = self._ema(self._boredom,    target_boredom)
        self._stability  = self._ema(self._stability,  target_stability)

        return self.state()

    # ------------------------------------------------------------------
    # Public state properties
    # ------------------------------------------------------------------

    @property
    def curiosity(self) -> float:
        return self._curiosity

    @property
    def wonder(self) -> float:
        return self._wonder

    @property
    def joy(self) -> float:
        return self._joy

    @property
    def tension(self) -> float:
        return self._tension

    @property
    def boredom(self) -> float:
        return self._boredom

    @property
    def stability(self) -> float:
        return self._stability

    # ------------------------------------------------------------------
    # Tier 4.2 — Derived dynamics (arousal, valence)
    # ------------------------------------------------------------------
    # Arousal and valence are not stored directly — they're derived from
    # the six emotional scalars above. Since those scalars are already
    # EMA-smoothed in update(), the derived signals inherit that smoothness
    # without needing a second smoothing pass.
    #
    # These feed TemporalStream.dilation_factor (Tier 4.2 subjective time
    # dilation) and will be available to Tier 5 (meta-cognition) for
    # attentional control.

    @property
    def arousal(self) -> float:
        """
        Activation / energy level ∈ [0, 1].

        High arousal: dominated by tension, joy, curiosity, wonder
        (intense, engaged, alive).
        Low arousal: dominated by boredom and stability (calm, settled,
        possibly inert).

        Curiosity, wonder, joy, and tension are all "active" emotional
        states regardless of valence — they all reflect that something is
        happening internally. Boredom and stability are the quiescent
        anchors. Arousal averages the four active scalars.
        """
        active = (self._tension + self._joy + self._curiosity + self._wonder) / 4.0
        return float(np.clip(active, 0.0, 1.0))

    @property
    def valence(self) -> float:
        """
        Positive vs negative emotional tone ∈ [-1, 1].

        Positive contributions: joy, wonder, stability
        (well-being, openness, calm).
        Negative contributions: tension, boredom
        (threat, depletion).

        Curiosity is excluded — it can accompany either positive engagement
        or anxious uncertainty depending on context, so it doesn't cleanly
        belong to either side.

        Peaceful state (high stability, low tension, no boredom) → positive.
        Threatened state (high tension) → negative.
        Depleted state (high boredom, low everything else) → negative.
        """
        positive = (self._joy + self._wonder + self._stability) / 3.0
        negative = (self._tension + self._boredom) / 2.0
        return float(np.clip(positive - negative, -1.0, 1.0))

    # ------------------------------------------------------------------
    # Modulation outputs  (read by autonomous_cycle every step)
    # ------------------------------------------------------------------

    def field_gain(self) -> float:
        """
        Field injection strength multiplier.
        Curiosity and wonder amplify injection; stability moderates it.

            gain = base × (1 + curiosity × 0.5 + wonder × 0.3)
                         × (1 - tension × 0.2)
        """
        gain = self.base_field_gain
        gain *= (1.0 + self._curiosity * 0.5 + self._wonder * 0.3)
        gain *= (1.0 - self._tension * 0.2)
        return float(np.clip(gain, 0.1, 3.0))

    def mutation_scale(self) -> float:
        """
        Differential noise scale for inject_ambiguity / dreamer.
        Wonder and curiosity increase mutation; joy and stability reduce it.

            scale = base × (1 + wonder × 0.8 + curiosity × 0.4)
                          × (1 - joy × 0.3)
        """
        scale = self.base_mutation_scale
        scale *= (1.0 + self._wonder * 0.8 + self._curiosity * 0.4)
        scale *= (1.0 - self._joy * 0.3)
        return float(np.clip(scale, 0.001, 0.5))

    def field_decay_rate(self) -> float:
        """
        Resonance field decay rate.
        High stability → slower decay (field persists longer).
        High tension → faster decay (field clears faster).

            rate = base + (tension - stability) × 0.003
        """
        delta = (self._tension - self._stability) * 0.003
        return float(np.clip(self.base_decay_rate + delta, 0.97, 0.9999))

    def dream_pressure(self) -> float:
        """
        Probability weighting for dream cycle entry.
        Wonder and boredom drive dreams; tension suppresses them.

            pressure = (wonder × 0.6 + boredom × 0.4) × (1 - tension × 0.5)
        """
        pressure = (self._wonder * 0.6 + self._boredom * 0.4)
        pressure *= (1.0 - self._tension * 0.5)
        return float(np.clip(pressure, 0.0, 1.0))

    def attractor_pull(self) -> float:
        """
        Attractor blend strength modifier.
        Joy and stability tighten attractor pull; curiosity loosens it.

            modifier = 1.0 + joy × 0.2 - curiosity × 0.15
        """
        modifier = 1.0 + self._joy * 0.2 - self._curiosity * 0.15
        return float(np.clip(modifier, 0.5, 2.0))

    def crystal_pressure(self) -> float:
        """
        Crystallization threshold modifier.
        High joy + stability lowers the crystallization threshold (easier to crystallize).
        High curiosity raises it (system is still exploring).

            modifier = 1.0 - (joy + stability) × 0.05 + curiosity × 0.08
        """
        modifier = 1.0 - (self._joy + self._stability) * 0.05 + self._curiosity * 0.08
        return float(np.clip(modifier, 0.7, 1.3))

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def state(self) -> EmotionalState:
        states = {
            "curiosity": self._curiosity,
            "wonder":    self._wonder,
            "joy":       self._joy,
            "tension":   self._tension,
            "boredom":   self._boredom,
            "stability": self._stability,
        }
        dominant = max(states, key=states.get)
        return EmotionalState(
            curiosity = self._curiosity,
            wonder    = self._wonder,
            joy       = self._joy,
            tension   = self._tension,
            boredom   = self._boredom,
            stability = self._stability,
            dominant  = dominant,
        )

    def modulation_snapshot(self) -> dict:
        """All modulation outputs in one dict for loop logging."""
        return {
            "field_gain":       round(self.field_gain(), 4),
            "mutation_scale":   round(self.mutation_scale(), 4),
            "field_decay_rate": round(self.field_decay_rate(), 6),
            "dream_pressure":   round(self.dream_pressure(), 4),
            "attractor_pull":   round(self.attractor_pull(), 4),
            "crystal_pressure": round(self.crystal_pressure(), 4),
            **self.state().as_dict(),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ema(self, current: float, target: float) -> float:
        updated = (1.0 - self.ema_alpha) * current + self.ema_alpha * float(np.clip(target, 0.0, 1.0))
        return float(np.clip(updated, 0.0, 1.0))
