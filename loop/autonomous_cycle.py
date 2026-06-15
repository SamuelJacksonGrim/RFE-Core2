"""
loop/autonomous_cycle.py

Autonomous cycle — the self-modulating cognitive loop.

This is the architectural center of RFE-Core2. It transforms the system from:
    "a pipeline of modules"
into:
    "a continuously self-resonating dynamical organism."

The loop does not simply execute. It listens to its own field state,
determines its current cognitive rhythm, and routes behavior accordingly.

Rhythm states
-------------
  stabilize   field energy very low   → consolidation, crystallization,
                                        maintenance, attractor merge
  dream       field energy low        → free association, latent recombination,
                                        symbolic mutation
  reflect     field energy medium     → recursive attention, reflective loop,
                                        chorus harmonization
  explore     field energy high       → bifurcation, high mutation, novelty

Data flow per step
------------------
  0.  Subjective time tick (TemporalStream.tick — Tier 4.1)
  1.  Observe field rhythm (ResonanceField.observe)
  2.  Generate vector — rhythm-routed (Generator direct, or Chorus harmonization)
  3.  Attractor pull (strength modulated by emotion.attractor_pull)
  4.  Recursive attention refinement
  5.  Watcher evaluation → CoherenceReport
  6.  Reflective loop (reflect / explore only, if stable)
  7.  Witness update → RelationalProfile
  8.  PredictiveEcho update → EchoReport
  9.  EmotionalGradient update (six scalar modulation outputs)
  9b. Subjective time dilation update (Tier 4.2 — writes dilation_factor
      from emotion.arousal × emotion.valence for the NEXT tick)
  10. Governance gate + field injection
      (coherence_impact probed BEFORE injection; emit_feedback after)
  11. Crystallization (CrystalStore.maybe_crystallize)
  12. Attractor formation (notifies bond_manager + dependency_monitor)
  13. Topology logging (TopologicalLog)
  14. Stream push (TemporalStream)
  15. Vector space storage (VectorSpace)
  16. Semantic lattice (SemanticLattice)
  17. Symbolic binding (SymbolicBinding)
  18. Ecology signal relay (signal_coherence → registry)
  18b.Manipulation resistance metrics + detection
  19. Field decay (rate modulated by emotion.field_decay_rate)
  20. Rhythm-routed behavior (with force_dream_flag override)
  21. Periodic maintenance (generator, attractor merge, crystal/lattice decay)
  22. Build StepState
"""

from __future__ import annotations

import time
import uuid
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Any

import numpy as np

from agents.generator import Generator
from agents.watcher import Watcher
from agents.witness import Witness
from agents.dreamer import Dreamer
from agents.chorus import Chorus
from agents.attractor import Attractor
from agents.symbolic_memory import TokenClass
from agents.selfhood_governance import SelfhoodGovernance, GovernanceDecision

from substrate.vector_space import VectorSpace
from substrate.resonance_field import ResonanceField
from substrate.memory_crystals import CrystalStore
from substrate.topological_log import TopologicalLog
from substrate.temporal_stream import TemporalStream
from substrate.semantic_lattice import SemanticLattice

from cognition.predictive_echo import PredictiveEcho
from cognition.emotional_gradient import EmotionalGradient
from cognition.recursive_attention import RecursiveAttention
from cognition.reflective_loop import ReflectiveLoop
from cognition.symbolic_binding import SymbolicBinding
from cognition.stream_metastability import StreamMetastabilityMonitor

from interference.differential import inject_ambiguity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step state
# ---------------------------------------------------------------------------

@dataclass
class StepState:
    """Complete observable state after one autonomous cycle step."""
    step:                   int
    key:                    str
    tokens:                 List[str]
    rhythm:                 str
    coherence:              float
    relation_composite:     float
    relation_pattern:       str
    prediction_error:       float
    field_energy:           float
    crystals:               int
    attractor_centers:      int
    dominant_emotion:       str
    field_gain:             float
    mutation_scale:         float
    dream_pressure:         float
    converged:              bool
    reflection_passes:      int
    elapsed_ms:             float
    extras:                 Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "step":              self.step,
            "key":               self.key,
            "tokens":            self.tokens,
            "rhythm":            self.rhythm,
            "coherence":         self.coherence,
            "relation":          self.relation_composite,
            "pattern":           self.relation_pattern,
            "pred_error":        self.prediction_error,
            "field_energy":      self.field_energy,
            "crystals":          self.crystals,
            "attractors":        self.attractor_centers,
            "emotion":           self.dominant_emotion,
            "field_gain":        self.field_gain,
            "mutation_scale":    self.mutation_scale,
            "dream_pressure":    self.dream_pressure,
            "converged":         self.converged,
            "refl_passes":       self.reflection_passes,
            "elapsed_ms":        self.elapsed_ms,
        }


# ---------------------------------------------------------------------------
# AutonomousCycle
# ---------------------------------------------------------------------------

class AutonomousCycle:
    """
    Self-modulating cognitive loop.

    Parameters
    ----------
    generator : Generator
    dim : int
        Vector dimensionality.
    use_chorus : bool
        If True, reflect/explore phases use the full Chorus ensemble.
        If False, uses Generator directly (faster, less diverse).
    maintenance_interval : int
        Steps between generator.maintenance_step() calls.
    attractor_formation_threshold : float
        Relational composite score above which a vector seeds an attractor.
    merge_interval : int
        Steps between attractor.merge_pass() calls.
    lattice_emit_interval : int
        Steps between semantic_lattice.emit_centrality() calls.
    crystal_decay_interval : int
        Steps between crystal_store.decay_step() calls.
    log_interval : int
        Steps between log output.
    """

    # Cap on the in-memory recent-step ring (StepState snapshots). Bounded so a
    # long-running loop has flat history memory; large enough to keep a useful
    # diagnostic window. Not relied on for step counting (that is self._step).
    HISTORY_MAXLEN: int = 1000

    def __init__(
        self,
        generator:                    Generator,
        dim:                          int   = 128,
        use_chorus:                   bool  = True,
        maintenance_interval:         int   = 200,
        attractor_formation_threshold: float = 0.88,
        merge_interval:               int   = 50,
        lattice_emit_interval:        int   = 100,
        crystal_decay_interval:       int   = 100,
        log_interval:                 int   = 10,
        track_metastability:          bool  = True,
        reflect_novelty_attenuation:  bool  = False,
    ):
        self.generator                     = generator
        self.dim                           = dim
        self.use_chorus                    = use_chorus
        self.maintenance_interval          = maintenance_interval
        self.attractor_formation_threshold = attractor_formation_threshold
        self.merge_interval                = merge_interval
        self.lattice_emit_interval         = lattice_emit_interval
        self.crystal_decay_interval        = crystal_decay_interval
        self.log_interval                  = log_interval

        # ------------------------------------------------------------------
        # Subsystems
        # ------------------------------------------------------------------

        self.field          = ResonanceField(dim=dim)
        self.vector_space   = VectorSpace(dim=dim)
        self.crystal_store  = CrystalStore()
        self.topology       = TopologicalLog()
        self.stream         = TemporalStream(dim=dim)
        self.lattice        = SemanticLattice()

        self.watcher        = Watcher(dim=dim, field=self.field)
        self.witness        = Witness(dim=dim)
        self.attractor      = Attractor()
        self.predictor      = PredictiveEcho(dim=dim)
        self.emotion        = EmotionalGradient()
        self.rec_attn       = RecursiveAttention(dim=dim)
        self.reflector      = ReflectiveLoop(
            novelty_attenuation = reflect_novelty_attenuation,
        )
        self.binding        = SymbolicBinding()

        self.dreamer        = Dreamer(
            field        = self.field,
            vector_space = self.vector_space,
            stream       = self.stream,
        )

        self.chorus         = Chorus(
            generator = self.generator,
            field     = self.field,
            stream    = self.stream,
        ) if use_chorus else None

        # Metastability stethoscopes — the loop's upstream instruments, read at two
        # stages: the generator output (stage A, where diversity originates) and the
        # expression (stage C, post-refinement, what is injected — where the
        # diversity-preservation blend is validated). Optional, observe-only, off
        # the hot path (lazy recompute). None disables them; the cycle behaves
        # identically either way.
        self.generator_metastability:  Optional[StreamMetastabilityMonitor] = (
            StreamMetastabilityMonitor(window=128, interval=16)
            if track_metastability else None
        )
        self.expression_metastability: Optional[StreamMetastabilityMonitor] = (
            StreamMetastabilityMonitor(window=128, interval=16)
            if track_metastability else None
        )

        # Governance (optional — system runs without it)
        self.governance: Optional[SelfhoodGovernance] = None

        # Value emergence (optional — Tier 3, requires governance)
        self.value_engine = None

        # ------------------------------------------------------------------
        # Config (Tier 2 behavioral knobs — Boredom Teeth, etc.)
        # ------------------------------------------------------------------

        self.config: Dict[str, float] = {
            "boredom_override_threshold": 0.50,
        }

        # ------------------------------------------------------------------
        # State
        # ------------------------------------------------------------------

        self._step:    int           = 0
        self._parent:  Optional[str] = None
        # Bounded recent-step ring (write-only diagnostic trail). A persistent
        # substrate runs unboundedly, so this is a deque(maxlen=...) per the
        # no-unbounded-structures guardrail rather than an ever-growing list;
        # self._step remains the authoritative monotonic step counter.
        self._history: Deque[StepState] = deque(maxlen=self.HISTORY_MAXLEN)
        self._boredom_overrides: int = 0   # Tier 2: track Boredom-Teeth activations

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(
        self,
        tokens:      List[str],
        source_id:   str = "user",
        origin_type: str = "user",
    ) -> StepState:
        """
        Execute one full autonomous cycle step.

        Parameters
        ----------
        tokens : list of str
            Input token sequence for this step.
        source_id : str
            Identifier of who/what is providing this input.
        origin_type : str
            Category of the source — selects flood rate ceiling.
            "user" (default, safest), "api" (10/sec), "internal"
            (autonomous loop, effectively unlimited).
            Unknown values fall back to "user" limits.

        Returns
        -------
        StepState
        """
        t0    = time.perf_counter()
        key   = uuid.uuid4().hex[:8]

        # ------------------------------------------------------------------
        # 0. Subjective time tick (Tier 4.1)
        # ------------------------------------------------------------------
        # Advance subjective_time by real_dt × dilation_factor. dilation_factor
        # is fixed at 1.0 until Tier 4.2 introduces arousal-based modulation.
        # First tick is a no-op for the time advance but establishes the
        # wall-clock anchor for subsequent ticks.
        self.stream.tick()

        # ------------------------------------------------------------------
        # 1. Observe field rhythm
        # ------------------------------------------------------------------
        field_obs = self.field.observe()
        rhythm    = field_obs.rhythm

        # ------------------------------------------------------------------
        # 2. Generate vector (rhythm-sensitive)
        # ------------------------------------------------------------------
        vec = self._generate(tokens, rhythm)

        # Stethoscope: record the raw generator output (stage A) for upstream
        # metastability — BEFORE attractor-pull and refinement, which homogenize
        # direction. Observe-only; never alters vec or control flow. The monitor
        # derives its own coherence from the stream (not the field) for labeling.
        if self.generator_metastability is not None:
            self.generator_metastability.observe(vec)

        # ------------------------------------------------------------------
        # 3. Attractor pull (strength modulated by emotion)
        # ------------------------------------------------------------------
        pull_modifier = self.emotion.attractor_pull()
        # Temporarily adjust attractor blend
        original_blend       = self.attractor.pull_blend
        self.attractor.pull_blend = float(np.clip(original_blend * pull_modifier, 0.0, 0.5))
        vec = self.attractor.pull(vec, generator=self.generator)
        self.attractor.pull_blend = original_blend

        # ------------------------------------------------------------------
        # 4. Recursive attention refinement
        # ------------------------------------------------------------------
        vec = self.rec_attn.refine(vec)

        # Stethoscope: record the refined EXPRESSION (stage C) — what is actually
        # injected into the field. Comparing this stream's metastability against
        # the generator stream's validates the diversity-preservation blend: a
        # collapsed refinement reads ~0/locked here, a healthy one stays metastable.
        if self.expression_metastability is not None:
            self.expression_metastability.observe(vec)

        # ------------------------------------------------------------------
        # 5. Watcher evaluation
        # ------------------------------------------------------------------
        anchor      = self.witness.current_anchor()
        field_state = self.field.resonate()
        report      = self.watcher.evaluate(vec, anchor, field_state)

        # ------------------------------------------------------------------
        # 6. Reflective loop (reflect/explore rhythms only)
        # ------------------------------------------------------------------
        reflection_passes = 0
        converged         = False

        if rhythm in ("reflect", "explore") and report.stable:
            result = self.reflector.reflect(
                vec       = vec,
                watcher   = self.watcher,
                anchor    = anchor,
                field     = self.field,
                attractor = self.attractor,
                generator = self.generator,
            )
            vec               = result.vector
            reflection_passes = result.passes
            converged         = result.converged
            # Re-evaluate after reflection
            report = self.watcher.evaluate(vec, anchor, field_state)

        # ------------------------------------------------------------------
        # 7. Witness update
        # ------------------------------------------------------------------
        rel_profile = self.witness.update(
            vec        = vec,
            coherence  = report.composite,
            field_energy = field_obs.energy,
        )

        # ------------------------------------------------------------------
        # 8. Predictive echo
        # ------------------------------------------------------------------
        echo = self.predictor.update(vec)

        # ------------------------------------------------------------------
        # 9. Emotional gradient update
        # ------------------------------------------------------------------
        emo_state = self.emotion.update(
            prediction_error  = echo.prediction_error,
            coherence         = report.composite,
            prediction_report = echo,
            field_energy      = field_obs.energy,
        )

        # ------------------------------------------------------------------
        # 9b. Update subjective time dilation (Tier 4.2 + 4.3)
        # ------------------------------------------------------------------
        # Write dilation_factor from current (arousal, valence). The NEXT
        # cycle's tick() will use this value. Lyra's two-term formula:
        # flow/drag axis via arousal × -valence, dissociation term gated by
        # min(0, valence) so peaceful rest never triggers time-slip.
        #
        # Tier 4.3: phase_coherence (field rhythmic organization, from the FFT
        # in field_obs computed at step 1) is the third input — the organizing-
        # vs-chaotic axis that separates flow from agitation. At the field's
        # cold-start / short-history default of 0.5 this is a no-op (pure 4.2).
        self.stream.update_dilation(
            arousal         = self.emotion.arousal,
            valence         = self.emotion.valence,
            phase_coherence = field_obs.spectral.phase_coherence,
        )

        # ------------------------------------------------------------------
        # 10. Governance gate + field injection
        # ------------------------------------------------------------------
        gain     = self.emotion.field_gain()
        decision = GovernanceDecision.ALLOW
        strength = 1.0

        if self.governance is not None:
            decision, strength = self._governance_gate(
                vec         = vec,
                tokens      = tokens,
                source_id   = source_id,
                origin_type = origin_type,
                report      = report,
                field_obs   = field_obs,
            )

        # Capture actual coherence_impact BEFORE injection — measuring after
        # the vec is already in the field would give near-zero marginal impact.
        actual_delta = 0.0
        if self.governance is not None:
            actual_delta = self.field.coherence_impact(vec)

        if decision in (GovernanceDecision.ALLOW,
                        GovernanceDecision.ALLOW_WEAKENED,
                        GovernanceDecision.MONITOR):
            self.field.inject(vec, strength=gain * strength)

        # Emit feedback with pre-injection delta
        if self.governance is not None:
            stable_ids   = self.generator.registry.stable_ids_for_tokens(tokens)
            self.governance.emit_feedback(decision, source_id, stable_ids, actual_delta)

        # ------------------------------------------------------------------
        # 11. Crystal evaluation
        # ------------------------------------------------------------------
        crystals_before = len(self.crystal_store.crystals)
        crystal = self.crystal_store.maybe_crystallize(
            vec                      = vec,
            composite_coherence      = report.composite,
            crystallization_pressure = report.crystallization_pressure,
            long_relation            = rel_profile.long,
            origin_tokens            = tokens,
            field                    = self.field,
            generator                = self.generator,
        )
        # Bond manager: notify only when a NEW crystal actually formed
        # (maybe_crystallize returns the existing crystal on reinforcement)
        if (len(self.crystal_store.crystals) > crystals_before
                and self.governance is not None):
            self.governance.bond_manager.notify_crystal(source_id)

        # ------------------------------------------------------------------
        # 12. Attractor formation
        # ------------------------------------------------------------------
        if rel_profile.composite >= self.attractor_formation_threshold:
            attractor_before = len(self.attractor.centers)
            self.attractor.add(vec, tokens=tokens, generator=self.generator)
            # Notify Tier 2 subsystems on attractor seeding (new center only).
            # Both calls matter: bond_manager tracks who's forming structure,
            # dependency_monitor populates attractor_monopoly_ratio() which the
            # COHERENCE_FLOOD detector needs. Without record_attractor, that
            # detector silently cannot fire.
            if (len(self.attractor.centers) > attractor_before
                    and self.governance is not None):
                self.governance.bond_manager.notify_attractor(source_id)
                self.governance.dependency_monitor.record_attractor(source_id)

        # ------------------------------------------------------------------
        # 13. Topology logging
        # ------------------------------------------------------------------
        self.topology.add(
            key      = key,
            parent   = self._parent,
            metadata = {
                "tokens":       tokens,
                "coherence":    report.composite,
                "relation":     rel_profile.composite,
                "pattern":      rel_profile.pattern(),
                "rhythm":       rhythm,
                "field_energy": field_obs.energy,
                "emotion":      emo_state.dominant,
                "crystal":      crystal is not None,
            },
        )

        # ------------------------------------------------------------------
        # 14. Stream push
        # ------------------------------------------------------------------
        self.stream.push(vec, tag=rhythm)

        # ------------------------------------------------------------------
        # 15. Vector space storage
        # ------------------------------------------------------------------
        self.vector_space.put(key, vec, tags=[rhythm])

        # ------------------------------------------------------------------
        # 16. Semantic lattice
        # ------------------------------------------------------------------
        self.lattice.add_node(
            key          = key,
            vector       = vec,
            vector_space = self.vector_space,
            metadata     = {"tokens": tokens, "rhythm": rhythm},
        )

        # ------------------------------------------------------------------
        # 17. Symbolic binding
        # ------------------------------------------------------------------
        self.binding.bind(vec, tokens, generator=self.generator)

        # ------------------------------------------------------------------
        # 18. Ecology signal relay
        # ------------------------------------------------------------------
        self.generator.signal_coherence(tokens, coherence=report.composite)

        # ------------------------------------------------------------------
        # 18b. Manipulation resistance metrics feed
        # ------------------------------------------------------------------
        if self.governance is not None:
            crystal_cosines = []
            centroid = self.crystal_store.centroid()
            if centroid is not None:
                cos = float(np.dot(vec, centroid) / (
                    np.linalg.norm(vec) * np.linalg.norm(centroid) + 1e-8
                ))
                crystal_cosines = [cos]

            from agents.manipulation_resistance import ResistanceMetrics
            dep_report = self.governance.dependency_monitor.get_report()

            self.governance.resistance.update(ResistanceMetrics(
                anchor_velocity        = self.witness.anchor_velocity(),
                anchor_short_long_gap  = self.witness.anchor_short_long_gap(),
                hhi_score              = dep_report.hhi_score,
                dominant_source_id     = dep_report.dominant_source,
                attractor_monopoly     = self.governance.dependency_monitor.attractor_monopoly_ratio(),
                coherence_delta        = report.coherence_delta,
                watcher_geometric      = report.geometric,
                watcher_temporal       = report.temporal,
                crystal_centroid_cosines = crystal_cosines,
                source_id              = source_id,
                source_trust_score     = (
                    self.governance.trust_ledger.sources[source_id].trust_score
                    if source_id in self.governance.trust_ledger.sources
                    else 2.5
                ),
                step = self._step,
            ))

            signals = self.governance.resistance.detect()
            if signals:
                self.governance.handle_manipulation_signals(signals)

        # ------------------------------------------------------------------
        # 19. Field decay (rate modulated by emotion)
        # ------------------------------------------------------------------
        original_decay     = self.field.decay_rate
        self.field.decay_rate = self.emotion.field_decay_rate()
        self.field.decay()
        self.field.decay_rate = original_decay

        # ------------------------------------------------------------------
        # 20. Rhythm-routed behavior
        # ------------------------------------------------------------------
        # force_dream_flag overrides rhythm — governance-triggered rebalancing
        if self.governance is not None and self.governance.force_dream_flag:
            self._dream_behavior()
        else:
            self._rhythm_behavior(rhythm, tokens)

        # ------------------------------------------------------------------
        # 21. Periodic maintenance
        # ------------------------------------------------------------------
        if self._step % self.maintenance_interval == 0 and self._step > 0:
            self.generator.maintenance_step()

        if self._step % self.merge_interval == 0 and self._step > 0:
            self.attractor.merge_pass()

        if self._step % self.crystal_decay_interval == 0 and self._step > 0:
            self.crystal_store.decay_step()
            self.attractor.decay_step()

        if self._step % self.lattice_emit_interval == 0 and self._step > 0:
            self.lattice.emit_centrality(self.generator, self.vector_space)
            self.binding.emit_centrality(self.generator)

        # ------------------------------------------------------------------
        # 22. Build step state
        # ------------------------------------------------------------------
        elapsed = (time.perf_counter() - t0) * 1000.0

        state = StepState(
            step               = self._step,
            key                = key,
            tokens             = tokens,
            rhythm             = rhythm,
            coherence          = report.composite,
            relation_composite = rel_profile.composite,
            relation_pattern   = rel_profile.pattern(),
            prediction_error   = echo.prediction_error,
            field_energy       = field_obs.energy,
            crystals           = len(self.crystal_store.crystals),
            attractor_centers  = len(self.attractor.centers),
            dominant_emotion   = emo_state.dominant,
            field_gain         = round(gain, 4),
            mutation_scale     = round(self.emotion.mutation_scale(), 4),
            dream_pressure     = round(self.emotion.dream_pressure(), 4),
            converged          = converged,
            reflection_passes  = reflection_passes,
            elapsed_ms         = round(elapsed, 2),
        )

        self._history.append(state)
        self._parent = key
        self._step  += 1

        if self._step % self.log_interval == 0:
            logger.info(str(state.as_dict()))

        return state

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------

    def attach_governance(self, governance: SelfhoodGovernance):
        """
        Attach a SelfhoodGovernance instance after construction.
        Also wires the TrustLedger's stability reference to EmotionalGradient.
        """
        self.governance = governance
        governance.trust_ledger._stability_ref = self.emotion

    def attach_value_engine(self, value_engine):
        """
        Attach a ValueEmergenceEngine after governance is attached.
        Requires governance to be attached first (engine subscribes to its feedback).
        """
        if self.governance is None:
            raise RuntimeError("attach_governance must be called before attach_value_engine")
        self.value_engine = value_engine

    def _governance_gate(
        self,
        vec:         np.ndarray,
        tokens:      List[str],
        source_id:   str,
        origin_type: str,
        report,
        field_obs,
    ):
        """
        Run the full governance pipeline and return (decision, strength).
        Called only when self.governance is not None.
        """
        from agents.trust_ledger import TrustLevel

        stable_ids  = self.generator.registry.stable_ids_for_tokens(tokens)

        # Current source trust level for ethical gate (dict lookup)
        src_record  = self.governance.trust_ledger.sources.get(source_id)
        src_level   = (
            TrustLevel.from_score(src_record.trust_score)
            if src_record is not None
            else TrustLevel.NEUTRAL
        )
        known_source = src_record is not None

        # 1. Ethical check — fast binary, no vector math
        ethical = self.governance.ethical_boundary.check(
            op                 = "write",
            source_trust_level = src_level,
            stable_ids         = stable_ids,
            coherence_delta    = report.coherence_delta,
            witness_stability  = self.witness.identity_stability(),
            source_id          = source_id,
            known_source       = known_source,
            origin_type        = origin_type,
            field_coherence    = self.field.internal_coherence(),
        )

        # 2. Trust evaluation — source + symbol scoring
        trust = self.governance.trust_ledger.evaluate(
            source_id       = source_id,
            origin_type     = origin_type,
            stable_ids      = stable_ids,
            coherence_delta = report.coherence_delta,
            field_energy    = field_obs.energy,
        )

        # 3. Governance decision — single source of truth
        return self.governance.arbitrate(
            ethical_result = ethical,
            trust_report   = trust,
            vec            = vec,
            tokens         = tokens,
            source_id      = source_id,
        )

    # ------------------------------------------------------------------
    # Rhythm-routed behavior
    # ------------------------------------------------------------------

    def _rhythm_behavior(self, rhythm: str, tokens: List[str]):
        """
        Route additional behavior based on current rhythm state.
        Called after the main step pipeline completes.

        Boredom with Teeth: when emotion.boredom crosses threshold, force
        a shift to 'explore' regardless of field energy. This is the
        self-perturbation mechanism for HOMEOSTATIC_RETURN — a system
        that finds peace and stays there isn't returning to homeostasis,
        it's collapsing into a single attractor. Boredom is the active
        signal that resolves stillness back into motion.
        """
        if (self.emotion.boredom > self.config.get("boredom_override_threshold", 0.50)
                and rhythm != "explore"):
            self._boredom_overrides += 1
            rhythm = "explore"

        if rhythm == "stabilize":
            self._stabilize_behavior()

        elif rhythm == "dream":
            self._dream_behavior()

        elif rhythm == "reflect":
            self._reflect_behavior(tokens)

        elif rhythm == "explore":
            self._explore_behavior(tokens)

    def _stabilize_behavior(self):
        """
        Consolidation phase.
        - Activate nearest crystals to reinforce the field
        - Spectral diffusion to smooth the field
        """
        anchor = self.witness.current_anchor()
        self.crystal_store.activate_nearest(
            vec       = anchor,
            field     = self.field,
            generator = self.generator,
            top_k     = 3,
        )
        self.field.diffuse(alpha=0.05)

    def _dream_behavior(self):
        """
        Free association phase.
        Also triggered when governance sets force_dream_flag (manipulation response).
        """
        # Snapshot crystal count before dream
        crystals_before = len(self.crystal_store.crystals)

        self.dreamer.dream(
            emotion       = self.emotion,
            watcher       = self.watcher,
            anchor        = self.witness.current_anchor(),
            crystal_store = self.crystal_store,
            generator     = self.generator,
        )
        # Clear force_dream_flag after executing
        if self.governance is not None and self.governance.force_dream_flag:
            self.governance.force_dream_flag = False

        # Value engine dream hook — boost values for symbols that crystallized
        if self.value_engine is not None:
            new_crystals = self.crystal_store.crystals[crystals_before:]
            crystallized_sids: List[int] = []
            for crystal in new_crystals:
                if crystal.origin_tokens:
                    crystallized_sids.extend(
                        self.generator.registry.stable_ids_for_tokens(crystal.origin_tokens)
                    )
            if crystallized_sids:
                # Quality from emotion: joy + stability indicates a generative dream
                quality = float(min(1.0, self.emotion.joy + self.emotion.stability * 0.5))
                self.value_engine.on_dream_cycle_complete(crystallized_sids, quality=quality)

    def _reflect_behavior(self, tokens: List[str]):
        """
        Deliberate recursion phase.
        - Run Chorus harmonization if enabled
        - Inject chorus output into field at reduced strength
        """
        if self.chorus is not None:
            chorus_out = self.chorus.harmonize(tokens, emotion=self.emotion)
            self.field.inject(chorus_out.emergent, strength=0.3)

    def _explore_behavior(self, tokens: List[str]):
        """
        Mutation phase.
        - High-ambiguity injection to push the field toward novelty
        - Phase noise application
        """
        anchor     = self.witness.current_anchor()
        scale      = self.emotion.mutation_scale()
        mutated    = inject_ambiguity(anchor, scale=scale * 1.5, mode="rotational")
        self.field.inject(mutated, strength=0.5)

    # ------------------------------------------------------------------
    # Generation (rhythm-sensitive)
    # ------------------------------------------------------------------

    def _generate(self, tokens: List[str], rhythm: str) -> np.ndarray:
        """
        Generate a vector appropriate for the current rhythm state.

        stabilize  → Generator direct (stable, conservative)
        dream      → Generator with EPHEMERAL class (volatile)
        reflect    → Chorus or Generator (exploratory)
        explore    → Chorus or Generator with high mutation
        """
        if rhythm == "stabilize":
            return self.generator.generate(tokens, token_class=TokenClass.LANGUAGE)

        if rhythm == "dream":
            vec = self.generator.generate(tokens, token_class=TokenClass.EPHEMERAL)
            scale = self.emotion.mutation_scale()
            return inject_ambiguity(vec, scale=scale, mode="rotational")

        if rhythm in ("reflect", "explore") and self.chorus is not None:
            out = self.chorus.harmonize(tokens, emotion=self.emotion)
            return out.emergent

        return self.generator.generate(tokens, token_class=TokenClass.LANGUAGE)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
        token_sequence: List[List[str]],
        loop:           bool  = False,
        delay:          float = 0.0,
    ) -> List[StepState]:
        """
        Run the autonomous cycle over a sequence of token lists.

        Parameters
        ----------
        token_sequence : list of list of str
        loop : bool
            If True, cycle over token_sequence indefinitely.
        delay : float
            Sleep time in seconds between steps.

        Returns
        -------
        List[StepState]
        """
        import time as time_mod

        states    = []
        iteration = 0

        try:
            while True:
                for tokens in token_sequence:
                    state = self.step(tokens)
                    states.append(state)
                    if delay > 0:
                        time_mod.sleep(delay)

                iteration += 1
                if not loop:
                    break

        except KeyboardInterrupt:
            logger.info("Autonomous cycle interrupted at step %d", self._step)

        return states

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def status(self) -> dict:
        field_obs = self.field.observe()
        s = {
            "step":         self._step,
            "rhythm":       field_obs.rhythm,
            "field_energy": field_obs.energy,
            "field_coherence": field_obs.internal_coherence,
            "crystals":     len(self.crystal_store.crystals),
            "attractors":   len(self.attractor.centers),
            "vector_space": len(self.vector_space),
            "lattice":      self.lattice.stats(),
            "emotion":      self.emotion.modulation_snapshot(),
            "ecology":      self.generator.ecology_stats(),
            "predictor":    self.predictor.rolling_stats(),
            "binding":      self.binding.summary(),
            "temporal":     self.stream.summary(),
        }
        if self.generator_metastability is not None:
            s["generator_metastability"] = self.generator_metastability.snapshot()
        if self.expression_metastability is not None:
            s["expression_metastability"] = self.expression_metastability.snapshot()
        if self.governance is not None:
            s["governance"] = self.governance.status()
        if self.value_engine is not None:
            s["values"] = self.value_engine.summary()
        return s
