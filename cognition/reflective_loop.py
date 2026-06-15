"""
cognition/reflective_loop.py

Reflective loop — recursive self-refinement until convergence.

Where RecursiveAttention refines a vector by attending to history,
the ReflectiveLoop refines it by running multiple passes through
the full cognition stack (attractor pull → watcher check → field
resonance blend) until the vector stabilizes or a depth limit is hit.

This is where the system begins to genuinely reflect:
  - A thought is held
  - Run through its own coherence filter
  - Adjusted toward the field
  - Re-evaluated
  - Repeated until stable

Convergence is measured by cosine similarity between successive passes.
High similarity = the thought has found its stable form.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ReflectionResult:
    vector:          np.ndarray   # final stabilized vector
    passes:          int          # how many passes were needed
    converged:       bool         # True if convergence criterion met
    final_coherence: float        # coherence on the final pass
    delta_trace:     list         # cosine delta between successive passes


class ReflectiveLoop:
    """
    Recursive self-refinement over the cognition stack.

    Parameters
    ----------
    max_depth : int
        Maximum number of refinement passes.
    convergence_threshold : float
        Cosine similarity between successive passes that signals convergence.
    field_blend : float
        How strongly the field state pulls each pass.
    attractor_blend : float
        How strongly the nearest attractor pulls each pass.
    coherence_gate : float
        Minimum coherence to continue refining. Below this, reflection halts.
    novelty_attenuation : bool
        EXPERIMENTAL, default OFF. When False the loop behaves exactly as before
        (byte-identical) — the survival-by-coherence pin holds, by design. When
        True, the loop's final anchor-pulled vector is blended back toward the
        raw input *in proportion to how novel that input is relative to the
        anchor* (novelty = 1 - cos(input, anchor)). Reaching this method already
        means the input survived the governance gate and is stable, so this is
        the "gated on surviving novelty" lever (ROADMAP item 7): genuinely-new
        survivors stop being dragged back to the established anchor, while
        non-novel repetition is left to converge as before (identity held).
        Validated multi-seed in tests/diagnostic/lockin/loop_attenuation_probe.py
        and docs/findings/2026-06-15-loop-attenuation-novelty-gate.md: at the
        default attenuation_max=0.30 it frees the field under sustained novelty
        (migration +0.11..+0.15, ~15× the RIGID baseline) with the Tier-2
        manipulation layer SILENT (0% of steps) and attractors bounded, and is
        gate-safe under non-novel repetition (~-0.001). CAVEAT: the cost-clean
        band is a KNIFE EDGE — at attenuation_max=0.33 the manipulation layer
        floods (>75% of steps reading the less-converged expression as
        identity-erosion) and migration margin over the free-the-field bar is
        thin. So this is shippable OFF, NOT ready to be default-ON. Raising
        attenuation_max without re-running the manip-rate instrument is a
        guardrail violation.
    novelty_gain : float
        Slope from novelty to attenuation. attenuation = clip(gain·novelty, 0, max).
    attenuation_max : float
        Ceiling on the blend-back weight (the operative knob). 0.30 is the
        validated cost-clean ceiling; the manip cliff is at ~0.33. Do not raise
        without a fresh manip-rate measurement.
    """

    def __init__(
        self,
        max_depth:            int   = 5,
        convergence_threshold: float = 0.995,
        field_blend:          float = 0.1,
        attractor_blend:      float = 0.08,
        coherence_gate:       float = 0.2,
        novelty_attenuation:  bool  = False,
        novelty_gain:         float = 1.0,
        attenuation_max:      float = 0.30,
    ):
        self.max_depth             = max_depth
        self.convergence_threshold = convergence_threshold
        self.field_blend           = field_blend
        self.attractor_blend       = attractor_blend
        self.coherence_gate        = coherence_gate
        self.novelty_attenuation   = novelty_attenuation
        self.novelty_gain          = novelty_gain
        self.attenuation_max       = attenuation_max

    def reflect(
        self,
        vec:       np.ndarray,
        watcher=None,        # Watcher instance
        anchor:    Optional[np.ndarray] = None,
        field=None,          # ResonanceField instance
        attractor=None,      # Attractor instance
        generator=None,      # Generator (for signal relay)
    ) -> ReflectionResult:
        """
        Run recursive self-refinement on vec.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
        watcher : Watcher or None
            Used for coherence evaluation on each pass.
        anchor : np.ndarray or None
            Witness anchor for geometric coherence.
        field : ResonanceField or None
            Field state blended in on each pass.
        attractor : Attractor or None
            Attractor pull applied on each pass.
        generator : Generator or None
            For signal relay on convergence.

        Returns
        -------
        ReflectionResult
        """
        current     = vec.copy().astype(np.float32)
        delta_trace = []
        converged   = False
        coherence   = 0.5
        passes      = 0

        field_state = field.resonate() if field is not None else None

        for i in range(self.max_depth):
            passes = i + 1
            prev   = current.copy()

            # --- Attractor pull ---
            if attractor is not None and len(attractor.centers) > 0:
                current = attractor.pull(current, generator=generator)

            # --- Field blend ---
            if field_state is not None:
                field_norm = np.linalg.norm(field_state)
                if field_norm > 1e-6:
                    blended = (1.0 - self.field_blend) * current + self.field_blend * field_state
                    norm    = np.linalg.norm(blended)
                    current = (blended / (norm + 1e-8)).astype(np.float32)

            # --- Coherence check ---
            if watcher is not None and anchor is not None:
                report    = watcher.evaluate(current, anchor, field_state)
                coherence = report.composite
                if coherence < self.coherence_gate and i > 0:
                    # Vector is incoherent — halt refinement
                    break
            
            # --- Convergence check ---
            delta = float(np.dot(current, prev) / (
                np.linalg.norm(current) * np.linalg.norm(prev) + 1e-8
            ))
            delta_trace.append(round(delta, 6))

            if delta >= self.convergence_threshold:
                converged = True
                break

        # --- Novelty-gated attenuation (EXPERIMENTAL, off by default) ---
        # Blend the converged (anchor-pulled) vector back toward the raw input
        # in proportion to the input's novelty vs the anchor. Skipped entirely
        # when disabled, so default behavior is byte-identical.
        if self.novelty_attenuation and anchor is not None:
            inp  = np.asarray(vec, dtype=np.float32)
            i_n  = np.linalg.norm(inp)
            a_n  = np.linalg.norm(anchor)
            if i_n > 1e-8 and a_n > 1e-8:
                cos_in  = float(np.dot(inp, anchor) / (i_n * a_n))
                novelty = max(0.0, 1.0 - cos_in)
                att     = float(np.clip(self.novelty_gain * novelty,
                                        0.0, self.attenuation_max))
                if att > 0.0:
                    mixed   = (1.0 - att) * current + att * inp
                    m_n     = np.linalg.norm(mixed)
                    current = (mixed / (m_n + 1e-8)).astype(np.float32)

        return ReflectionResult(
            vector          = current,
            passes          = passes,
            converged       = converged,
            final_coherence = round(coherence, 6),
            delta_trace     = delta_trace,
        )
