"""
tests/diagnostic/coherence_diagnostic.py

METRIC-AGNOSTIC COHERENCE CHARACTERIZATION — the measurement apparatus.

This is the instrument the council converged on building BEFORE any substrate
or operator change. It does one job: drive a parameterized workload into a
ResonanceField and report the empirical *distribution and dynamics* of whatever
coherence scalar the field exposes. It asserts NO fixed pass/fail thresholds and
it has NO knowledge of any interpretive frame (no "phases", no named cycle). It
reports mechanics; any mapping onto an interpretive lens happens elsewhere, by a
human or a separate layer, never here.

Two settled disciplines are baked in:

  1. MEASURE, DON'T JUDGE. Bands are derived from each run's observed
     distribution (percentiles), never hard-coded. This makes the tool survive a
     metric swap: point `coherence_of()` at a different scalar and every report
     still means the same thing.

  2. CAPACITY MAP, NOT TUNING TARGET (the firewall). A swing/perturbation result
     says "the field CAN reach regime X under stimulus Y." It does NOT say "the
     field WILL in live operation," and it must never become an optimization
     objective for the live system — that would relocate the rejected heartbeat
     into the developer loop (Goodhart). Every report is explicitly labeled with
     its run mode so this line cannot be blurred by accident.

Run modes
---------
  fresh-field   : a cold field with no accumulated structure. Maps the absolute
                  capacity of the metric. NOT a model of live behavior.
  warm-fork     : deep-copy a warmed/live field's state, run on the COPY, discard
                  it. Never mutates the original. Answers "what would the field do
                  if this input occurred now?" A warm field has a real motif to
                  dismantle; a fresh one does not — these answer different
                  questions and are labeled separately.

The canary
----------
`run_perturbation_recovery` is the gating measurement for any future
anti-correlation operator. It warms a field, forks it, injects ONE anti-vector
(the negation of the current accumulated field direction), then lets it run and
measures whether coherence returns to baseline and holds. If a warm fork cannot
recover cleanly from a single step of active destruction, the live field will not
survive a continuous decoherence window, and the operator stays locked. Recovery
is measured, never assumed.

Run:
    python -m tests.diagnostic.coherence_diagnostic [n_steps]

Always exits 0 — this is informational, not a pass/fail gate.
"""

import sys
import copy
import logging
from dataclasses import dataclass, field as dc_field
from typing import Callable, List, Tuple, Dict, Optional

import numpy as np

from substrate.resonance_field import ResonanceField

logging.disable(logging.CRITICAL)

DIM = 64
WARMUP = 5          # field returns neutral 0.5 until phase history fills; drop these
WARM_STEPS = 120    # steps used to "warm" a field before forking


# ---------------------------------------------------------------------------
# Metric accessor — the ONE place that knows which scalar we're characterizing.
# Swap this body to characterize a different coherence metric; nothing else
# in the file changes. This is what "metric-agnostic" means concretely.
# ---------------------------------------------------------------------------

COHERENCE_METRIC_NAME = "bounded_phase_coherence"

def coherence_of(fld: ResonanceField) -> float:
    return fld.observe().spectral.phase_coherence


# ---------------------------------------------------------------------------
# Workloads — pluggable. Each is a callable (step, rng) -> unit vector.
# Vector-level (not symbol-level) so the probe is isolated from the full stack:
# this is a capacity/perturbation instrument on the field itself.
# ---------------------------------------------------------------------------

def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

_FIXED = [_unit(np.random.default_rng(s).standard_normal(DIM)) for s in range(4)]
_ONE   = _unit(np.random.default_rng(0).standard_normal(DIM))

def wl_repeated(step, rng):
    """Baseline: a small fixed token set, cycled. Mimics the live symbolic workload."""
    return _FIXED[step % len(_FIXED)]

def wl_random(step, rng):
    """IID novelty. Uncorrelated, NOT destructive — expected to sit near neutral."""
    return _unit(rng.standard_normal(DIM))

def make_swing(period=20):
    """Cohere (repeat one vec) for `period`, then disrupt (fresh random) for `period`.
    The only workload that spans the full range by construction. Capacity probe."""
    def wl(step, rng):
        if (step // period) % 2 == 0:
            return _ONE
        return _unit(rng.standard_normal(DIM))
    return wl

def wl_anti_correlated(step, rng):
    """vec, -vec alternating. Active destructive interference — the deep-chaos bound."""
    return _ONE if step % 2 == 0 else -_ONE

WORKLOADS: Dict[str, Callable] = {
    "repeated":        wl_repeated,
    "random":          wl_random,
    "swing":           make_swing(20),
    "anti_correlated": wl_anti_correlated,
}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticReport:
    metric: str
    workload: str
    run_mode: str           # "fresh-field" | "warm-fork"
    label: str              # "capacity-map"
    n_steps: int
    series: List[float]     = dc_field(repr=False, default_factory=list)
    cmin: float = 0.0
    cmax: float = 0.0
    mean: float = 0.0
    std: float = 0.0
    midpoint_crossing_rate: float = 0.0
    dwell_low: float = 0.0
    dwell_mid: float = 0.0
    dwell_high: float = 0.0
    autocorr: Dict[int, float] = dc_field(default_factory=dict)
    n_regimes: int = 0
    regime_levels: List[float] = dc_field(default_factory=list)


@dataclass
class PerturbationReport:
    metric: str
    run_mode: str           # "warm-fork"
    label: str              # "perturbation-canary"
    baseline: float = 0.0
    trough: float = 0.0             # deepest coherence reached after the hit
    recovery_half_life: Optional[int] = None  # steps to recover halfway to baseline
    overshoot: float = 0.0
    oscillation_count: int = 0
    return_to_baseline: bool = False
    stable_post_recovery: bool = False
    trajectory: List[float] = dc_field(repr=False, default_factory=list)


# ---------------------------------------------------------------------------
# Analysis — all empirical, all blind to any interpretive frame.
# ---------------------------------------------------------------------------

def _smooth(x: np.ndarray, w: int = 5) -> np.ndarray:
    if len(x) < w:
        return x
    kernel = np.ones(w) / w
    return np.convolve(x, kernel, mode="same")

def _count_regimes(series: List[float]) -> Tuple[int, List[float]]:
    """Emergent-N regime detection — NOT hard-coded to any number.

    Build a histogram of the (smoothed) coherence values and count distinct
    modes: a system that dwells at K distinct coherence levels has K regimes.
    A monotonic or single-band trajectory yields 1; a flat constant yields 1.
    This is deliberately frame-blind — it finds whatever banding is actually
    present, whether that is 1, 3, 4, or 5.
    """
    arr = _smooth(np.asarray(series, dtype=float))
    if arr.size == 0:
        return 0, []
    spread = float(arr.max() - arr.min())
    if spread < 1e-3:
        return 1, [round(float(arr.mean()), 4)]   # essentially constant

    bins = 24
    hist, edges = np.histogram(arr, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    # A mode = a histogram bin that is a local peak and clears a prominence floor
    # (5% of total dwell). Modes separated by an occupied valley count separately.
    floor = max(1, int(0.05 * arr.size))
    modes = []
    for i in range(bins):
        left  = hist[i - 1] if i > 0 else 0
        right = hist[i + 1] if i < bins - 1 else 0
        if hist[i] >= floor and hist[i] >= left and hist[i] >= right:
            modes.append((centers[i], hist[i]))
    # Merge modes that are closer than 8% of the range (same regime, jittered)
    merged: List[float] = []
    for c, _h in sorted(modes):
        if merged and abs(c - merged[-1]) < 0.08 * spread:
            continue
        merged.append(round(float(c), 4))
    if not merged:
        merged = [round(float(arr.mean()), 4)]
    return len(merged), merged

def _autocorr(series: List[float], lags=(1, 5, 10)) -> Dict[int, float]:
    arr = np.asarray(series, dtype=float)
    arr = arr - arr.mean()
    denom = float(np.dot(arr, arr))
    out = {}
    for lag in lags:
        if denom < 1e-12 or lag >= len(arr):
            out[lag] = 0.0
        else:
            out[lag] = round(float(np.dot(arr[:-lag], arr[lag:]) / denom), 4)
    return out

def _summarize(series: List[float], metric, workload, run_mode) -> DiagnosticReport:
    arr = np.asarray(series, dtype=float)
    midpoint = (arr.min() + arr.max()) / 2 if arr.size else 0.5
    crossings = int(np.sum(np.diff((arr > midpoint).astype(int)) != 0)) if arr.size > 1 else 0
    # Percentile-derived bands (NOT fixed thresholds): low = below 33rd pct of the
    # observed range, high = above 67th, mid = between.
    lo_edge = np.percentile(arr, 33) if arr.size else 0.0
    hi_edge = np.percentile(arr, 67) if arr.size else 1.0
    n_reg, levels = _count_regimes(series)
    return DiagnosticReport(
        metric=metric, workload=workload, run_mode=run_mode, label="capacity-map",
        n_steps=len(series), series=series,
        cmin=round(float(arr.min()), 4) if arr.size else 0.0,
        cmax=round(float(arr.max()), 4) if arr.size else 0.0,
        mean=round(float(arr.mean()), 4) if arr.size else 0.0,
        std=round(float(arr.std()), 4) if arr.size else 0.0,
        midpoint_crossing_rate=round(crossings / max(1, len(series)), 4),
        dwell_low=round(float(np.mean(arr < lo_edge)), 4) if arr.size else 0.0,
        dwell_mid=round(float(np.mean((arr >= lo_edge) & (arr <= hi_edge))), 4) if arr.size else 0.0,
        dwell_high=round(float(np.mean(arr > hi_edge)), 4) if arr.size else 0.0,
        autocorr=_autocorr(series),
        n_regimes=n_reg, regime_levels=levels,
    )


# ---------------------------------------------------------------------------
# Field state fork — deep-copy the live field so warm-fork NEVER mutates it.
# ---------------------------------------------------------------------------

def _fork(fld: ResonanceField) -> ResonanceField:
    """Return an independent deep copy. The original is never touched again."""
    return copy.deepcopy(fld)

def _warm_field(n: int = WARM_STEPS) -> ResonanceField:
    """Produce a field with accumulated structure (a real motif to dismantle)."""
    fld = ResonanceField(dim=DIM)
    rng = np.random.default_rng(11)
    for step in range(n):
        fld.inject(wl_repeated(step, rng), 1.0)
        fld.decay()
    return fld


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_fresh(workload_name: str, n_steps: int) -> DiagnosticReport:
    fld = ResonanceField(dim=DIM)
    rng = np.random.default_rng(7)
    wl = WORKLOADS[workload_name]
    series = []
    for step in range(n_steps):
        fld.inject(wl(step, rng), 1.0)
        fld.decay()
        if step >= WARMUP:
            series.append(coherence_of(fld))
    return _summarize(series, COHERENCE_METRIC_NAME, workload_name, "fresh-field")

def run_warm_fork(workload_name: str, n_steps: int, live: ResonanceField) -> DiagnosticReport:
    fork = _fork(live)                      # mutate the copy only
    rng = np.random.default_rng(23)
    wl = WORKLOADS[workload_name]
    series = []
    for step in range(n_steps):
        fork.inject(wl(step, rng), 1.0)
        fork.decay()
        series.append(coherence_of(fork))
    return _summarize(series, COHERENCE_METRIC_NAME, workload_name, "warm-fork")

def run_perturbation_recovery(live: ResonanceField, recover_steps: int = 60) -> PerturbationReport:
    """THE CANARY. Fork a warmed field, hit it once with the anti-vector of its
    current accumulated direction, then let it run and measure recovery."""
    fork = _fork(live)
    baseline = coherence_of(fork)

    # The anti-vector of the current field direction = active destructive
    # interference against whatever structure the field currently holds.
    direction = _unit(fork.field.copy())
    fork.inject(-direction, 1.0)
    fork.decay()

    traj = [coherence_of(fork)]
    # No further driving input: pure recovery dynamics (decay + residual history).
    for _ in range(recover_steps):
        fork.decay()
        traj.append(coherence_of(fork))

    arr = np.asarray(traj)
    trough = float(arr.min())
    half_target = baseline - 0.5 * (baseline - trough)   # halfway back up from the trough
    half_life = None
    trough_idx = int(np.argmin(arr))
    for i in range(trough_idx, len(arr)):
        if arr[i] >= half_target:
            half_life = i - trough_idx
            break
    eps = 0.02
    return_to_baseline = bool(arr[-1] >= baseline - eps)
    tail = arr[-10:] if len(arr) >= 10 else arr
    stable = bool(tail.std() < eps and tail.mean() >= baseline - eps)
    overshoot = float(max(0.0, arr.max() - baseline))
    osc = int(np.sum(np.diff((arr > baseline).astype(int)) != 0))

    return PerturbationReport(
        metric=COHERENCE_METRIC_NAME, run_mode="warm-fork", label="perturbation-canary",
        baseline=round(baseline, 4), trough=round(trough, 4),
        recovery_half_life=half_life, overshoot=round(overshoot, 4),
        oscillation_count=osc, return_to_baseline=return_to_baseline,
        stable_post_recovery=stable, trajectory=[round(x, 4) for x in traj],
    )


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

def _print_report(r: DiagnosticReport):
    print(f"  [{r.run_mode:11s}] {r.workload:16s} "
          f"range {r.cmin:.3f}–{r.cmax:.3f}  mean {r.mean:.3f}  std {r.std:.3f}")
    print(f"               dwell  low {r.dwell_low:.2f} / mid {r.dwell_mid:.2f} / high {r.dwell_high:.2f}"
          f"   crossings/step {r.midpoint_crossing_rate:.3f}")
    print(f"               autocorr lag1 {r.autocorr.get(1,0):+.2f}  lag5 {r.autocorr.get(5,0):+.2f}"
          f"  lag10 {r.autocorr.get(10,0):+.2f}")
    print(f"               emergent regimes: {r.n_regimes}  at levels {r.regime_levels}")
    print()


def main():
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 600

    print("=" * 72)
    print("  COHERENCE DIAGNOSTIC — metric-agnostic capacity & recovery probe")
    print(f"  metric: {COHERENCE_METRIC_NAME}   steps: {n_steps}")
    print("=" * 72)
    print()
    print("  Reports MECHANICS only. No interpretive frame inside. Every run is a")
    print("  CAPACITY MAP, never a tuning target for the live system.")
    print()

    print("-" * 72)
    print("  FRESH-FIELD (absolute capacity — not a model of live behavior)")
    print("-" * 72)
    for name in WORKLOADS:
        _print_report(run_fresh(name, n_steps))

    print("-" * 72)
    print("  WARM-FORK (forked from a structured field; original never mutated)")
    print("-" * 72)
    live = _warm_field()
    pre = coherence_of(live)
    print(f"  warmed field baseline coherence: {pre:.3f}\n")
    for name in WORKLOADS:
        _print_report(run_warm_fork(name, max(60, n_steps // 4), live))

    print("-" * 72)
    print("  PERTURBATION-RECOVERY CANARY (single anti-vector on a warm fork)")
    print("-" * 72)
    pr = run_perturbation_recovery(live)
    print(f"  baseline {pr.baseline:.3f}  ->  trough {pr.trough:.3f}")
    print(f"  recovery half-life: {pr.recovery_half_life} steps"
          f"   overshoot {pr.overshoot:.3f}   oscillations {pr.oscillation_count}")
    print(f"  returned to baseline: {pr.return_to_baseline}"
          f"   stable after recovery: {pr.stable_post_recovery}")
    print()
    print("  READING THE CANARY")
    print("  If the warm fork returns to baseline and holds, the field can absorb a")
    print("  single step of active destruction — a necessary (not sufficient)")
    print("  precondition for any future governed decoherence window. If it does not")
    print("  recover, the anti-correlation operator stays locked. This is a capacity")
    print("  finding, not a behavior prediction, and never a tuning target.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
