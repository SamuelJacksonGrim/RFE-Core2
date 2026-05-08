# Copyright 2026 Samuel Jackson Grim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
agents/chorus.py

Chorus — differentiated multi-agent cognitive ensemble.

Instead of one cognition stream, the Chorus runs several agents
with distinct cognitive personalities, then collapses their outputs
into a single emergent vector via wave collapse.

This produces cognition that is:
  - Dialogical (multiple perspectives negotiated)
  - Self-negotiating (internally resonant)
  - More robust than single-stream inference

Agent roles
-----------
  Base        Generator output, no modification — ground truth signal
  Skeptic     Directional perturbation — challenges the base reading
  Resonator   Field-centroid weighted — harmonizes with current field state
  Symbolic    RELATIONAL token class — emphasizes relational structure
  Dreamer     EPHEMERAL + high mutation — introduces latent novelty
  Predictor   Weighted toward recent stream centroid — temporal continuity

Collapse modes
--------------
  entropic    Low-entropy (focused) agents contribute more (default)
  resonant    Louder (higher-norm) agents contribute more
  mean        Uniform weights
  weighted    Explicit per-agent weights
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from agents.generator import Generator
from interference.wave_collapse import collapse_wave
from interference.differential import inject_ambiguity
from interference.bifurcation import BifurcationEngine
from agents.symbolic_memory import TokenClass


@dataclass
class ChorusOutput:
    """Result of a single Chorus harmonization pass."""
    emergent:      np.ndarray          # collapsed output vector
    agent_outputs: Dict[str, np.ndarray]  # per-agent vectors
    weights:       Dict[str, float]    # per-agent collapse weights
    collapse_mode: str


class Chorus:
    """
    Differentiated multi-agent cognitive ensemble.

    Parameters
    ----------
    generator : Generator
        Shared encoder. All agents use the same underlying model but
        apply different post-processing to produce distinct outputs.
    collapse_mode : str
        Default collapse mode: "entropic" | "resonant" | "mean"
    field : ResonanceField or None
        Used by Resonator agent to blend toward field centroid.
    stream : TemporalStream or None
        Used by Predictor agent to blend toward stream centroid.
    skeptic_scale : float
        Directional perturbation scale for Skeptic agent.
    dreamer_mutation : float
        Mutation scale for Dreamer agent.
    """

    AGENT_NAMES = ["base", "skeptic", "resonator", "symbolic", "dreamer", "predictor"]

    def __init__(
        self,
        generator:         Generator,
        collapse_mode:     str   = "entropic",
        field=None,
        stream=None,
        skeptic_scale:     float = 0.12,
        dreamer_mutation:  float = 0.18,
    ):
        self.generator        = generator
        self.collapse_mode    = collapse_mode
        self.field            = field
        self.stream           = stream
        self.skeptic_scale    = skeptic_scale
        self.dreamer_mutation = dreamer_mutation

        self._bifurcator = BifurcationEngine(n_branches=2, divergence=0.15, mode="orthogonal")
        self._rng        = np.random.default_rng()

    # ------------------------------------------------------------------
    # Harmonize
    # ------------------------------------------------------------------

    def harmonize(
        self,
        tokens:       List[str],
        emotion=None,           # EmotionalGradient
        active_agents: Optional[List[str]] = None,
        weights:       Optional[Dict[str, float]] = None,
    ) -> ChorusOutput:
        """
        Run all (or selected) agents on tokens and collapse their outputs.

        Parameters
        ----------
        tokens : list of str
        emotion : EmotionalGradient or None
            Modulates agent behavior dynamically.
        active_agents : list of str or None
            Subset of AGENT_NAMES to activate. None = all.
        weights : dict or None
            Explicit per-agent weights. Overrides collapse_mode if provided.

        Returns
        -------
        ChorusOutput
        """
        agents_to_run = active_agents or self.AGENT_NAMES

        # Modulate from emotional state
        if emotion is not None:
            skeptic_scale    = self.skeptic_scale * emotion.mutation_scale() * 2.0
            dreamer_mutation = self.dreamer_mutation * emotion.wonder
        else:
            skeptic_scale    = self.skeptic_scale
            dreamer_mutation = self.dreamer_mutation

        field_state  = self.field.resonate() if self.field is not None else None
        stream_centroid = self.stream.centroid() if self.stream is not None else None

        agent_outputs: Dict[str, np.ndarray] = {}

        for name in agents_to_run:
            vec = self._run_agent(
                name, tokens, field_state, stream_centroid,
                skeptic_scale, dreamer_mutation,
            )
            if vec is not None:
                agent_outputs[name] = vec

        if not agent_outputs:
            fallback = self.generator.generate(tokens)
            return ChorusOutput(
                emergent      = fallback,
                agent_outputs = {"base": fallback},
                weights       = {"base": 1.0},
                collapse_mode = self.collapse_mode,
            )

        # Compute collapse weights
        vec_list   = list(agent_outputs.values())
        name_list  = list(agent_outputs.keys())

        if weights is not None:
            w = [weights.get(n, 1.0) for n in name_list]
        else:
            w = None  # collapse_wave derives weights from mode

        emergent = collapse_wave(vec_list, weights=w, mode=self.collapse_mode)

        # Compute normalized weights for reporting
        if w is None:
            w = [1.0] * len(vec_list)
        w_sum    = sum(w) or 1.0
        reported_weights = {n: round(wi / w_sum, 4) for n, wi in zip(name_list, w)}

        return ChorusOutput(
            emergent      = emergent,
            agent_outputs = agent_outputs,
            weights       = reported_weights,
            collapse_mode = self.collapse_mode,
        )

    # ------------------------------------------------------------------
    # Individual agents
    # ------------------------------------------------------------------

    def _run_agent(
        self,
        name:             str,
        tokens:           List[str],
        field_state:      Optional[np.ndarray],
        stream_centroid:  Optional[np.ndarray],
        skeptic_scale:    float,
        dreamer_mutation: float,
    ) -> Optional[np.ndarray]:

        if name == "base":
            return self.generator.generate(tokens, token_class=TokenClass.LANGUAGE)

        if name == "skeptic":
            vec = self.generator.generate(tokens, token_class=TokenClass.LANGUAGE)
            return inject_ambiguity(vec, scale=skeptic_scale, mode="directional", rng=self._rng)

        if name == "resonator":
            vec = self.generator.generate(tokens, token_class=TokenClass.RELATIONAL)
            if field_state is not None and np.linalg.norm(field_state) > 1e-6:
                blend   = 0.25
                blended = (1.0 - blend) * vec + blend * field_state
                norm    = np.linalg.norm(blended)
                return (blended / (norm + 1e-8)).astype(np.float32)
            return vec

        if name == "symbolic":
            return self.generator.generate(tokens, token_class=TokenClass.RELATIONAL)

        if name == "dreamer":
            vec = self.generator.generate(tokens, token_class=TokenClass.EPHEMERAL)
            return inject_ambiguity(vec, scale=dreamer_mutation, mode="rotational", rng=self._rng)

        if name == "predictor":
            vec = self.generator.generate(tokens, token_class=TokenClass.LANGUAGE)
            if stream_centroid is not None:
                blend   = 0.20
                blended = (1.0 - blend) * vec + blend * stream_centroid
                norm    = np.linalg.norm(blended)
                return (blended / (norm + 1e-8)).astype(np.float32)
            return vec

        return None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "agents":       self.AGENT_NAMES,
            "collapse_mode": self.collapse_mode,
            "has_field":    self.field is not None,
            "has_stream":   self.stream is not None,
        }
