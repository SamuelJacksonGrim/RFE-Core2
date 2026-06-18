"""
tools/ignition/gate.py — the Ignition Threshold Gate (ITG), action half.

The CII probe (tools/ignition/probe.py) is the SENSOR. This is the ACTUATOR:
a closed-loop controller that reads the expression-stream regime state each
cycle and, when it reads `locked`, raises RecursiveAttention.diversity_blend to
push the generator's real metastability through stage C — then relaxes it once
the expression is metastable again. A thermostat on ignition.

ARCHITECTURAL NOTE — this deliberately crosses the "metastability monitors are
observe-only terminal sinks" invariant (CLAUDE.md). It is the first component
that lets a monitor feed back into the cognitive loop. It is therefore OPT-IN:
nothing attaches it by default, so the invariant holds untouched unless a caller
chooses to run the gate. Same discipline as ReflectiveLoop.novelty_attenuation.

STATUS — scaffold; this downstream-gate approach does not lift the
low-differentiation state, and that is itself the useful result: it LOCATED the
lever upstream. Two actuator knobs were tested (diversity_blend here; loop
attenuation in a paired seeded A/B); neither reliably differentiates a collapsed
expression, because the binding constraint on stage-C metastability is the
GENERATOR (its representational room — see dimensionality), not a late-stage knob.
A downstream gate cannot manufacture differentiation the generator did not present.
See docs/findings/2026-06-15-cii-ignition-decomposition.md "ITG follow-up".
Retained as the ITG scaffold for when the generator is TRAINED to present
reliable diversity (the upstream lever); not wired into anything yet.

Usage:
    gate = IgnitionGate(cycle)
    for ...:
        cycle.step(tokens, ...)
        gate.after_step()          # read ignition state, act on the blend
"""
from __future__ import annotations


class IgnitionGate:
    """Thermostat on expression metastability via the diversity-blend knob.

    Parameters
    ----------
    cycle : AutonomousCycle
        Must have `expression_metastability` and `rec_attn`.
    locked_blend : float
        diversity_blend to apply when the expression reads `locked` (more raw
        generator signal preserved). Kept < 1.0 so refinement is not bypassed.
    interval : int
        Act every `interval` cycles (the forced metastability read is the cost).
    """

    def __init__(self, cycle, locked_blend: float = 0.90, interval: int = 4):
        self.cycle        = cycle
        self.locked_blend = float(locked_blend)
        self.default_blend = float(getattr(cycle.rec_attn, "diversity_blend", 0.60))
        self.interval     = max(1, int(interval))
        self._n           = 0
        self.engaged      = 0          # cycles spent loosening (locked)
        self.relaxed      = 0          # cycles spent at default (healthy)
        self.last_state   = "unknown"

    def after_step(self) -> str:
        """Read the expression regime state and set diversity_blend accordingly.
        Returns the regime state read this call (or the carried last state)."""
        self._n += 1
        if self.cycle.expression_metastability is None:
            return self.last_state
        if self._n % self.interval != 0:
            return self.last_state

        state = self.cycle.expression_metastability.compute_now().regime_state
        self.last_state = state
        if state == "locked":
            self.cycle.rec_attn.diversity_blend = self.locked_blend
            self.engaged += 1
        else:
            self.cycle.rec_attn.diversity_blend = self.default_blend
            self.relaxed += 1
        return state

    def restore(self) -> None:
        """Return the blend to its original value (detach the gate)."""
        self.cycle.rec_attn.diversity_blend = self.default_blend
