"""
tests/diagnostic/sidecar/sidecar_harness.py

Observe-only adapters wiring two external measurement engines around an
AutonomousCycle:

  - LAE (Liminal Anchor Engine)   — structures *transitions*: reads the
    rhythm-hypothesis profile each cycle and activates when the system is
    between rhythm bands (confidence collapse / hypothesis conflict /
    frame oscillation).
  - PLE (Paradox Lattice Engine)  — structures *contradictions*: reads the
    per-cycle evaluator opinions (watcher components, field delta, emotion,
    rhythm router, governance, resistance) and activates when they disagree.

Both engines are terminal sinks in the dilation_factor /
StreamMetastabilityMonitor sense: they read host telemetry after each step
and never feed anything back into the cognitive or governance loop. The
host cycle is NOT modified — capture is done with the non-invasive wrapper
pattern established by the lockin probes (wrap, latch, restore), plus
post-step attribute reads.

Sidecar repos are expected as installed packages (pip install -e of
sibling checkouts); a sys.path fallback covers a bare sibling layout.
All rolling buffers are bounded (deque maxlen) per the repo guardrail.

Mapping v1 (LAE rhythm hypotheses): soft confidences over the four rhythm
bands from log-energy distance to the sacred band boundaries
(stabilize < 0.5 / dream 0.5–2.0 / reflect 2.0–5.0 / explore >= 5.0),
exp(-d/tau) normalized. Sidecar sensitivity knob only — never read by the
host. Timestamps are fed as step_index * LAE_TICK_SECONDS so the detector's
wall-clock 1500 ms oscillation window deterministically spans the last 4
cycles (wall time would make the window hardware-dependent; subjective_time
is wall-clock-noisy by construction).
"""

from __future__ import annotations

import logging
import math
import sys
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

from loop.autonomous_cycle import AutonomousCycle, StepState
from agents.selfhood_governance import SelfhoodGovernance

# -- sidecar imports (installed packages, sibling-checkout fallback) --------
_REPO_PARENT = Path(__file__).resolve().parents[3].parent
for _sibling in ("Liminal-Anchor-Engine", "Paradox-Lattice-Engine"):
    _p = _REPO_PARENT / _sibling
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from lae.detectors.transition_detector import TransitionDetector
from lae.integration.external_api import LAE
from ple.core.paradox_pipeline import ParadoxLatticeEngine
from ple.integration import external_api as ple_api
from ple.integration import rfecore2hook

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping v1 — rhythm-hypothesis confidences from field energy
# ---------------------------------------------------------------------------

# Sacred rhythm bands (configs/field.yaml) — read-only here, never altered.
RHYTHM_BANDS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "stabilize": (None, 0.5),
    "dream":     (0.5,  2.0),
    "reflect":   (2.0,  5.0),
    "explore":   (5.0,  None),
}
HYPOTHESES_TAU   = 0.4    # mapping v1 — sidecar sensitivity only
ENERGY_FLOOR     = 1e-3   # log-space floor for near-zero field energy
LAE_TICK_SECONDS = 0.5    # 1500 ms oscillation window == last 4 cycles


def rhythm_hypotheses(field_energy: float) -> Dict[str, float]:
    """Soft rhythm-band confidences from field energy (mapping v1).

    Distance to each band is measured in log-energy space (the bands are
    multiplicative), confidence = exp(-d/tau), normalized to sum 1. Deep
    in-band the top confidence is ~0.73 with a ~0.60 gap (LAE stays
    dormant — correct); exactly at a band boundary the top two tie at
    ~0.47 (hypothesis_conflict fires, confidence_collapse does not).
    """
    x = math.log(max(field_energy, ENERGY_FLOOR))
    conf: Dict[str, float] = {}
    for rhythm, (lo, hi) in RHYTHM_BANDS.items():
        edges = [math.log(b) for b in (lo, hi) if b is not None]
        inside = ((lo is None or field_energy >= lo)
                  and (hi is None or field_energy < hi))
        d = 0.0 if inside else min(abs(x - e) for e in edges)
        conf[rhythm] = math.exp(-d / HYPOTHESES_TAU)
    total = sum(conf.values())
    return {r: c / total for r, c in conf.items()}


# ---------------------------------------------------------------------------
# CycleTap — capture-only wrappers + post-step reads
# ---------------------------------------------------------------------------

@dataclass
class CycleCapture:
    """One step's evaluator opinions, assembled after cycle.step() returns."""
    watcher_geometric:     float
    watcher_temporal:      float
    watcher_resonance:     float
    coherence_composite:   float
    coherence_delta:       float
    decision:              str
    manipulation_severity: float
    phase_coherence:       float
    arousal:               float
    valence:               float
    identity_stability:    float
    anchor_velocity:       float
    dilation_factor:       float


class CycleTap:
    """Latch the per-step values that StepState does not carry.

    Wraps watcher.evaluate (keeps the LAST report per step — the
    reflective loop re-evaluates, and the last call is what feeds
    witness/crystals downstream), governance.arbitrate, resistance.detect,
    and stream.update_dilation. Pure capture: every wrapper calls the
    original and latches the return — no RNG, no mutation, no branching
    on host state. install()/uninstall() restore the originals.
    """

    def __init__(self, cycle: AutonomousCycle, governance: SelfhoodGovernance):
        self.cycle      = cycle
        self.governance = governance
        self._report          = None
        self._decision        = None
        self._severity        = 0.0
        self._phase_coherence = 0.5
        self._originals: Dict[str, Any] = {}
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        watcher, gov, stream = self.cycle.watcher, self.governance, self.cycle.stream

        orig_eval = watcher.evaluate
        def latched_eval(*a, **k):
            report = orig_eval(*a, **k)
            self._report = report
            return report

        orig_arb = gov.arbitrate
        def latched_arb(*a, **k):
            dec, strength = orig_arb(*a, **k)
            self._decision = dec.value
            return dec, strength

        orig_detect = gov.resistance.detect
        def latched_detect(*a, **k):
            signals = orig_detect(*a, **k)
            self._severity = float(sum(s.severity for s in signals))
            return signals

        orig_dil = stream.update_dilation
        def latched_dil(*a, **k):
            pc = k.get("phase_coherence", a[2] if len(a) > 2 else 0.5)
            self._phase_coherence = float(pc)
            return orig_dil(*a, **k)

        self._originals = {
            "evaluate": orig_eval, "arbitrate": orig_arb,
            "detect": orig_detect, "update_dilation": orig_dil,
        }
        watcher.evaluate       = latched_eval
        gov.arbitrate          = latched_arb
        gov.resistance.detect  = latched_detect
        stream.update_dilation = latched_dil
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        self.cycle.watcher.evaluate            = self._originals["evaluate"]
        self.governance.arbitrate              = self._originals["arbitrate"]
        self.governance.resistance.detect      = self._originals["detect"]
        self.cycle.stream.update_dilation      = self._originals["update_dilation"]
        self._originals = {}
        self._installed = False

    def read(self, state: StepState) -> CycleCapture:
        """Assemble this step's capture. Call once, after cycle.step()."""
        report = self._report
        capture = CycleCapture(
            watcher_geometric     = float(report.geometric)  if report else 0.0,
            watcher_temporal      = float(report.temporal)   if report else 0.0,
            watcher_resonance     = float(report.resonance)  if report else 0.0,
            coherence_composite   = float(report.composite)  if report else state.coherence,
            coherence_delta       = float(report.coherence_delta) if report else 0.0,
            decision              = self._decision or "allow",
            manipulation_severity = self._severity,
            phase_coherence       = self._phase_coherence,
            arousal               = float(self.cycle.emotion.arousal),
            valence               = float(self.cycle.emotion.valence),
            identity_stability    = float(self.cycle.witness.identity_stability()),
            anchor_velocity       = float(self.cycle.witness.anchor_velocity()),
            dilation_factor       = float(self.cycle.stream.dilation_factor),
        )
        # Clear latches so a step that skipped a call can't read stale data.
        self._report, self._decision, self._severity = None, None, 0.0
        return capture


# ---------------------------------------------------------------------------
# LAE sidecar
# ---------------------------------------------------------------------------

class LAESidecar:
    """Feeds the rhythm-hypothesis profile to a fresh LAE each cycle.

    Trigger types are re-derived locally with the detector's own constants
    (TransitionEvent does not carry them); the histogram of per-cycle top
    confidences keeps dormancy interpretable — a dormant run with all mass
    deep in-band is a finding, not a malfunction.
    """

    def __init__(self, maxlog: int = 2048):
        self.lae = LAE()   # hermetic: no persist_path, no autosave target
        self._conf_threshold = float(self.lae.config.confidence_threshold)
        self._conflict_band  = float(TransitionDetector.CONFLICT_BAND)
        self._window_s = float(self.lae.config.oscillation_window_ms) / 1000.0
        self._top_history: Deque[Tuple[float, str]] = deque(maxlen=64)
        self.trigger_counts: Counter = Counter()
        self.top_conf_hist:  Counter = Counter()   # 0.05-wide bins, bounded
        self.boundary_adjacent_cycles = 0
        self.activation_log: Deque[dict] = deque(maxlen=maxlog)

    def _derive_triggers(self, hypotheses: Dict[str, float], ts: float) -> List[str]:
        top_id, top_conf = max(hypotheses.items(), key=lambda kv: kv[1])
        self._top_history.append((ts, top_id))
        ranked = sorted(hypotheses.values(), reverse=True)
        fired = []
        if top_conf < self._conf_threshold:
            fired.append("confidence_collapse")
        if len(ranked) >= 2 and (ranked[0] - ranked[1]) < self._conflict_band:
            fired.append("hypothesis_conflict")
        recent = [h for t, h in self._top_history if ts - t <= self._window_s]
        if len(recent) >= 3:
            flips = sum(1 for a, b in zip(recent, recent[1:]) if a != b)
            if flips >= 2:
                fired.append("frame_oscillation")
        return fired

    def after_step(self, state: StepState) -> None:
        hypotheses = rhythm_hypotheses(state.field_energy)
        ts = state.step * LAE_TICK_SECONDS
        triggers = self._derive_triggers(hypotheses, ts)

        ranked = sorted(hypotheses.items(), key=lambda kv: -kv[1])
        self.top_conf_hist[round(ranked[0][1] // 0.05 * 0.05, 2)] += 1
        if ranked[0][1] - ranked[1][1] < self._conflict_band:
            self.boundary_adjacent_cycles += 1

        outcome = self.lae.observe({
            "state_id":   f"rhythm::{state.rhythm}",
            "hypotheses": hypotheses,
            "timestamp":  ts,
        })
        if outcome.activated:
            self.trigger_counts.update(triggers)
            intent = outcome.result.intent
            self.activation_log.append({
                "cycle":          state.step,
                "rhythm":         state.rhythm,
                "field_energy":   round(state.field_energy, 4),
                "triggers":       triggers,
                "conflict_score": round(outcome.result.event.conflict_score, 4),
                "top2":           [(r, round(c, 4)) for r, c in ranked[:2]],
                "intent_stability": round(float(intent.stability_score), 4),
                "anchors":        len(outcome.result.anchors),
            })

    def summary(self) -> dict:
        return {
            "diagnostics":              self.lae.diagnostics.snapshot(),
            "trigger_counts":           dict(self.trigger_counts),
            "boundary_adjacent_cycles": self.boundary_adjacent_cycles,
            "top_confidence_histogram": {str(k): v for k, v in
                                         sorted(self.top_conf_hist.items())},
            "activation_log":           list(self.activation_log),
        }


# ---------------------------------------------------------------------------
# PLE sidecar
# ---------------------------------------------------------------------------

class PLESidecar:
    """Feeds each cycle's evaluator opinions through ple rfecore2hook."""

    def __init__(self):
        self.engine = ParadoxLatticeEngine()
        self.triggered_cycles = 0
        self.contradictions_by_claim: Counter = Counter()   # 4 claim keys

    def after_step(self, state: StepState, cap: CycleCapture, arm: str) -> None:
        telemetry = {
            "watcher_geometric":     cap.watcher_geometric,
            "watcher_temporal":      cap.watcher_temporal,
            "watcher_resonance":     cap.watcher_resonance,
            "coherence_delta":       cap.coherence_delta,
            "valence":               cap.valence,
            "dominant_emotion":      state.dominant_emotion,
            "decision":              cap.decision,
            "manipulation_severity": cap.manipulation_severity,
            "rhythm":                state.rhythm,
        }
        result = rfecore2hook.submit_cycle(self.engine, telemetry, context={
            "host": "rfe-core2", "cycle": state.step,
            "rhythm": state.rhythm, "arm": arm,
        })
        if result.triggered:
            self.triggered_cycles += 1
            for node in result.paradox_nodes:
                key = node.context_window.get("claim_key", "unknown")
                self.contradictions_by_claim[key] += 1

    def summary(self) -> dict:
        return {
            "ecology":                 ple_api.ecology_report(self.engine),
            "findings":                ple_api.get_findings(self.engine,
                                                            validated_only=False),
            "validated_findings":      len(ple_api.get_findings(self.engine)),
            "triggered_cycles":        self.triggered_cycles,
            "contradictions_by_claim": dict(self.contradictions_by_claim),
        }
