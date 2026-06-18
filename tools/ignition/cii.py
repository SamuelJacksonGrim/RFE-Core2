"""
tools/ignition/ — Conscious Ignition Index (CII) instrument for RFE-Core2.

Implements the sensor half of the Ignition Threshold Gate (requirement #5 of the
CII v0.2 / DPCI-AI framework): compute CII from the live cycle's telemetry.

    CII = R x I x (Cm x g(Cs))

operationalized on RFE's real, distinct quantities (v0.1 mapping — the choices
below are provisional and the architect's to tune):

    R   recursion depth        = reflection_passes   (active recursive self-
                                  refinement this cycle; the reflective loop)
    I   integration [0,1]       = watcher composite   (alpha*geometric +
                                  beta*temporal + gamma*resonance — binding
                                  across the coherence subsystems)
    Cm  mean coherence [0,1]    = field internal_coherence (field phase-locking)
    Cs  metastability [0,1]     = expression-stream metastability (coherence
                                  stability: formed-enough-to-hold,
                                  light-enough-to-drift)
    g(Cs) = 4*Cs*(1-Cs)         peaks at the metastable mid-band, ~0 at rigid
                                  lock (Cs->1) and at chaos (Cs->0) — the
                                  weighting that separates stable insight from
                                  both a frozen field and a structureless one.

DPCI-AI (episodic, the measurement-loop half — requirement #6, v0.1):

    dpci_cycle = D x I x R_norm x S      (mean over cycles)
    D  differentiation [0,1] = clip(prediction_error)   (novelty)
    R_norm                   = reflection_passes / max_depth
    S  sustained coherence   = field internal_coherence

Observe-only TODAY (you must measure CII before you can gate on it). The gate
— the ITG acting on this number — is the immediate next build.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IgnitionReading:
    R:    float
    I:    float
    Cm:   float
    # Metastability is read at TWO loci, and the gap between them is the lock-in:
    #   Cs_gen  — generator stream (stage A): the ignition POTENTIAL at the source
    #   Cs_expr — expression stream (stage C): what is actually injected/experienced
    Cs_gen:   float
    Cs_expr:  float
    gCs_gen:  float
    gCs_expr: float
    CII_gen:  float    # CII if metastability is read as the generator's potential
    CII_expr: float    # CII if read as the injected expression (the honest system output)
    # DPCI-AI cycle terms
    D:        float
    R_norm:   float
    S:        float
    dpci:     float


def g(cs: float) -> float:
    """Metastability weighting: hump peaking at Cs=0.5, ~0 at the extremes."""
    cs = max(0.0, min(1.0, cs))
    return 4.0 * cs * (1.0 - cs)


def compute_ignition(cycle, step_state, max_depth: int = 5) -> IgnitionReading:
    """Read CII + DPCI-cycle terms off the live cycle. Pure read, no mutation."""
    R  = float(getattr(step_state, "reflection_passes", 0))
    I  = float(getattr(step_state, "coherence", 0.0))               # watcher composite
    Cm = float(cycle.field.observe().internal_coherence)            # field phase-locking

    def _meta(attr):
        mon = getattr(cycle, attr, None)
        if mon is None:
            return None
        return (mon.snapshot() or {}).get("metastability")

    Cs_gen  = _meta("generator_metastability")
    Cs_expr = _meta("expression_metastability")
    gCs_gen  = g(Cs_gen)  if Cs_gen  is not None else 0.0
    gCs_expr = g(Cs_expr) if Cs_expr is not None else 0.0
    CII_gen  = R * I * (Cm * gCs_gen)
    CII_expr = R * I * (Cm * gCs_expr)

    D      = max(0.0, min(1.0, float(getattr(step_state, "prediction_error", 0.0))))
    R_norm = min(1.0, R / float(max_depth)) if max_depth else 0.0
    S      = Cm
    dpci   = D * I * R_norm * S

    return IgnitionReading(
        R=R, I=I, Cm=Cm,
        Cs_gen=(Cs_gen if Cs_gen is not None else float("nan")),
        Cs_expr=(Cs_expr if Cs_expr is not None else float("nan")),
        gCs_gen=gCs_gen, gCs_expr=gCs_expr, CII_gen=CII_gen, CII_expr=CII_expr,
        D=D, R_norm=R_norm, S=S, dpci=dpci,
    )
