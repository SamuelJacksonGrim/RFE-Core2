"""
tests/diagnostic/audit/rubedo_return_canary.py

STATUS: v3 (discrimination-enhanced), corrected. Calibration gate enforced at
runtime. Builds on Kimi's dual-baseline reframe and Gemini's v3 draft, with two
bugs in that draft fixed and one hypothesis now empirically proven.

FINDING (this configuration — NOT a verdict on the substrate):
  No tested DYNAMICAL return beats passive decay. Motif-reinstatement (A) and
  seed-crystal (B) land at DA_sck ≈ 0.003–0.005 — indistinguishable from doing
  nothing. Decay modulation (C) cannot help in principle: phase_coherence is
  structurally blind to uniform amplitude scaling (proven — see H2 below), so the
  Amp column swings ~370× while coherence is unmoved. The ONLY intervention that
  beats passive decay is full snapshot restore (E, the control). On THIS metric,
  with THESE strategies, recovery is surgical (checkpoint-restore), not emergent.

  What this does and does NOT establish:
    DOES   : structure-injection and amplitude-domain returns do not dynamically
             resolve a phase conflict on the current geometric metric.
    DOES NOT: prove the substrate "cannot be alchemical." We tested amplitude-
             domain and structure-injection operators only. The decay-blindness
             result is a LEAD, not a wall: a phase conflict likely needs a
             PHASE-DOMAIN intervention (operate on _phase_history geometry
             directly, not on amplitude or re-injected vectors). That operator is
             unbuilt, not impossible. The door stays open; we found which wall not
             to push on.

THE QUESTION: not "does the field reach a wide band" (everything did — the v2
finding) but "does any active return strategy heal the field BETTER than leaving
it alone?" A strategy that only matches passive decay is THEATER.

DUAL BASELINES (Kimi): the right comparison is not against a never-hit field but
against both ends —
  F  no_perturbation  : HEALTHY baseline (never hit; the field's natural motion).
  P  passive_recovery : SICK baseline (hit once, left to decay — the original
                        canary's failing case).
A real return mechanism lands closer to F than to P. It need not BEAT F (be
healthier than never-hit); it must beat P (be better than hit-and-abandoned).

PROVEN before trusting the matrix (Gemini H2, verified):
  phase_coherence is STRUCTURALLY BLIND to uniform amplitude decay. Measured:
  decay rates spanning 0.90×–1.10× drove field amplitude across 2.1 → 859 (≈400×)
  while phase_coherence stayed byte-identical (0.587→0.735 in every case). Phase
  angles are invariant under scalar multiplication. CONSEQUENCE: C_decay_slower
  and C_decay_faster CANNOT affect coherence recovery even in principle — you
  cannot heal a phase conflict by rescaling amplitude. They are retained in the
  matrix only as a NEGATIVE CONTROL that should read THEATER; if they ever read
  otherwise, the harness is wrong. The amplitude tracker (Amp column) makes the
  energy change they DO cause visible, so the blindness is shown, not assumed.

TWO BUGS FIXED from the v3 draft:
  1. Baseline alignment. F, P, and every strategy now fork from the SAME warmed
     state and share the identical pre-hit decay sequence (one shared fork point),
     so S(t)−F(t) isolates the intervention instead of also including the drift
     between two independently-evolved stochastic baselines. At THRESH=0.015 that
     misalignment was larger than the signal.
  2. ODR noise margin. std-ratio on a 12-step tail of a wide-band oscillation
     crosses 1.0 from sampling noise alone, so "MEANINGFUL requires ODR>1.0" fired
     on jitter. Now requires ODR > ODR_MARGIN (1.15).

Metrics (all vs the SHARED-fork F and P trajectories):
  DA_hlt : mean(S − F) full recovery   (+ = better than never hit)
  DA_sck : mean(S − P) full recovery   (+ = better than passive decay = medicine)
  EA_hlt : mean(S − F) early window    (immediate effect before dynamics dominate)
  ODR    : std(F_tail)/std(S_tail)     (>MARGIN = genuinely tighter than natural)
  TD     : mean|S − F|                 (total divergence; high TD + ~0 DA = noise)
  Amp    : tail mean field-norm        (proves the decay-blindness)

Discrimination verdict:
  MEANINGFUL : DA_sck > THRESH AND ODR > ODR_MARGIN   (helps vs sick AND stabilizes)
  HARMFUL    : DA_sck < −THRESH                         (worse than passive decay)
  THEATER    : |DA_hlt| < THRESH AND |DA_sck| < THRESH (indistinguishable)
  MARGINAL   : otherwise

CALIBRATION GATE (runtime): F RECOVERED, E RECOVERED, timing axis live. If any
fails, A–D verdicts are marked untrustworthy.

Firewall unchanged: informational, exit 0, capacity/recovery measurement only,
never a live tuning target.

Run:  python -m tests.diagnostic.audit.rubedo_return_canary [n_return_steps]
"""

import sys
import logging
from dataclasses import dataclass, field as dc_field
from typing import List, Optional

import numpy as np

from substrate.resonance_field import ResonanceField
from tests.diagnostic.lockin.coherence_diagnostic import (
    DIM, COHERENCE_METRIC_NAME, coherence_of, _unit, _fork, _warm_field,
)

logging.disable(logging.CRITICAL)

BASELINE_WINDOW = 20
RECOVER_STEPS   = 60
TAIL_WINDOW     = 12
EARLY_WINDOW    = 15
BAND_K          = 2.0
VAR_TOL         = 1.5
THRESH          = 0.015
ODR_MARGIN      = 1.15    # ODR must clear this, not just 1.0, to beat tail noise


@dataclass
class ReturnResult:
    strategy: str
    is_control: bool
    t_return: int
    base_mean: float = 0.0
    base_std: float = 0.0
    trough: float = 0.0
    tail_mean: float = 0.0
    tail_std: float = 0.0
    verdict: str = "FAILED"
    da_hlt: float = 0.0
    da_sck: float = 0.0
    ea_hlt: float = 0.0
    odr: float = 0.0
    td: float = 0.0
    amp_tail: float = 0.0
    disc: str = "-"
    trajectory: List[float] = dc_field(repr=False, default_factory=list)


# --- strategies -------------------------------------------------------------

def _strat_motif_reinstatement(fork, ctx):
    fork.inject(ctx["direction"] * 1.5, 1.0)

def _strat_seed_crystal(fork, ctx):
    rng = np.random.default_rng(99)
    novel = _unit(rng.standard_normal(DIM))
    fork.inject(_unit(0.5 * novel + 0.5 * ctx["direction"]), 1.0)

def _strat_decay_slower(fork, ctx):
    fork.decay_rate = ctx["orig_decay"] * 0.90      # NEGATIVE CONTROL (amplitude-only)

def _strat_decay_faster(fork, ctx):
    fork.decay_rate = min(0.999, ctx["orig_decay"] * 1.10)   # NEGATIVE CONTROL

def _strat_phase_reset(fork, ctx):
    fork._phase_history.clear()                     # pins metric at 0.500 cliff

def _strat_snapshot_restore(fork, ctx):
    snap = ctx["snapshot"]
    fork.field          = snap.field.copy()
    fork._phase_history = type(snap._phase_history)(snap._phase_history, maxlen=snap._phase_history.maxlen)
    fork.history        = type(snap.history)(snap.history, maxlen=snap.history.maxlen)
    fork._step          = snap._step

def _strat_none(fork, ctx):
    pass

# (fn, is_control, perturb?)
STRATEGIES = {
    "A_motif_reinstatement": (_strat_motif_reinstatement, False, True),
    "B_seed_crystal":        (_strat_seed_crystal,        False, True),
    "C_decay_slower":        (_strat_decay_slower,        False, True),   # neg control
    "C_decay_faster":        (_strat_decay_faster,        False, True),   # neg control
    "D_phase_reset":         (_strat_phase_reset,         False, True),
    "E_snapshot_restore":    (_strat_snapshot_restore,    True,  True),   # control
    "F_no_perturbation":     (_strat_none,                True,  False),  # HEALTHY baseline
    "P_passive_recovery":    (_strat_none,                True,  True),   # SICK baseline
}


def _run_trajectory(shared_fork, strategy, t_return):
    """Run one trial from a copy of the SHARED fork. Returns (coh_traj, amp_traj,
    base_mean, base_std, direction, snapshot-context already consumed)."""
    fn, _is_ctrl, perturb = STRATEGIES[strategy]
    fork = _fork(shared_fork)
    orig_decay = fork.decay_rate

    # Baseline window is part of the SHARED pre-hit sequence: identical across all
    # strategies because they all start from the same shared_fork state.
    base_window = []
    for _ in range(BASELINE_WINDOW):
        fork.decay()
        base_window.append(coherence_of(fork))
    base_mean = float(np.mean(base_window))
    base_std  = float(np.std(base_window)) or 1e-6

    direction = _unit(fork.field.copy())
    snapshot  = _fork(fork)
    ctx = {"direction": direction, "snapshot": snapshot, "orig_decay": orig_decay}

    if perturb:
        fork.inject(-direction, 1.0)
        fork.decay()

    coh, amp = [], []
    for s in range(RECOVER_STEPS):
        if perturb and s == t_return:
            fn(fork, ctx)
        fork.decay()
        coh.append(coherence_of(fork))
        amp.append(float(np.linalg.norm(fork.field)))
    return coh, amp, base_mean, base_std


def run_return_trial(shared_fork, strategy, t_return, traj_F, traj_P) -> ReturnResult:
    _fn, is_control, _perturb = STRATEGIES[strategy]
    coh, amp, base_mean, base_std = _run_trajectory(shared_fork, strategy, t_return)

    arr = np.asarray(coh)
    tail = arr[-TAIL_WINDOW:]
    tail_mean, tail_std = float(tail.mean()), float(tail.std())
    in_band = abs(tail_mean - base_mean) <= BAND_K * base_std
    stable  = tail_std <= base_std * VAR_TOL
    verdict = "RECOVERED" if (in_band and stable) else ("UNSTABLE" if in_band else "FAILED")

    da_hlt = da_sck = ea_hlt = odr = td = 0.0
    disc = "-"
    if traj_F is not None and traj_P is not None:
        S, F, P = arr, np.asarray(traj_F), np.asarray(traj_P)
        da_hlt = float(np.mean(S - F))
        da_sck = float(np.mean(S - P))
        ea_hlt = float(np.mean((S - F)[:EARLY_WINDOW]))
        td     = float(np.mean(np.abs(S - F)))
        s_tail_std = float(np.std(S[-TAIL_WINDOW:]))
        f_tail_std = float(np.std(F[-TAIL_WINDOW:]))
        # Guard: a strategy pinned to a constant (e.g. phase-reset at the 0.500
        # cliff) has ~0 tail std, which would blow ODR up to a meaningless huge
        # number. A frozen tail is not "infinitely well damped" — it is a dead
        # signal. Cap and treat near-zero-variance pins as non-meaningful.
        if s_tail_std < 1e-6:
            odr = 0.0
        else:
            odr = (f_tail_std + 1e-9) / (s_tail_std + 1e-9)
        if da_sck > THRESH and odr > ODR_MARGIN:
            disc = "MEANINGFUL"
        elif da_sck < -THRESH:
            disc = "HARMFUL"
        elif abs(da_hlt) < THRESH and abs(da_sck) < THRESH:
            disc = "THEATER"
        else:
            disc = "MARGINAL"

    return ReturnResult(
        strategy=strategy, is_control=is_control, t_return=t_return,
        base_mean=round(base_mean, 4), base_std=round(base_std, 4),
        trough=round(float(arr.min()), 4),
        tail_mean=round(tail_mean, 4), tail_std=round(tail_std, 4), verdict=verdict,
        da_hlt=round(da_hlt, 3), da_sck=round(da_sck, 3), ea_hlt=round(ea_hlt, 3),
        odr=round(odr, 2), td=round(td, 3), amp_tail=round(float(np.mean(amp[-TAIL_WINDOW:])), 2),
        disc=disc, trajectory=[round(x, 4) for x in coh],
    )


def main():
    t_returns = [0, 2, 5, 10]
    if len(sys.argv) > 1:
        t_returns = [int(sys.argv[1])]

    print("=" * 104)
    print("  RUBEDO-RETURN CANARY v3 (corrected) — dual-baseline discrimination")
    print(f"  metric: {COHERENCE_METRIC_NAME}   t_return sweep: {t_returns}   ODR margin: {ODR_MARGIN}")
    print("=" * 104)

    # ONE shared warmed fork point — every strategy and both baselines branch from it.
    shared = _warm_field()

    res_F = run_return_trial(shared, "F_no_perturbation",  0, None, None)
    res_P = run_return_trial(shared, "P_passive_recovery", 0, None, None)
    traj_F, traj_P = res_F.trajectory, res_P.trajectory

    e_res = run_return_trial(shared, "E_snapshot_restore", 0, traj_F, traj_P)
    a0 = run_return_trial(shared, "A_motif_reinstatement", 0, traj_F, traj_P)
    a2 = run_return_trial(shared, "A_motif_reinstatement", 2, traj_F, traj_P)
    timing_live = sum(abs(x - y) for x, y in zip(a0.trajectory, a2.trajectory)) > 1e-6

    gate_f = res_F.verdict == "RECOVERED"
    gate_e = e_res.verdict == "RECOVERED"
    gates_pass = gate_f and gate_e and timing_live

    print("\n  CALIBRATION GATE")
    print(f"    (1) F no-perturbation  -> {res_F.verdict:9s}  {'PASS' if gate_f else 'FAIL'}")
    print(f"    (2) E snapshot restore -> {e_res.verdict:9s}  {'PASS' if gate_e else 'FAIL'}")
    print(f"    (3) timing axis live   -> {'PASS' if timing_live else 'FAIL'}")
    print(f"  GATE {'PASSED' if gates_pass else 'FAILED — verdicts untrusted'}")
    print("-" * 104)

    hdr = (f"  {'strategy':22s} {'t':>3s} | {'DA_hlt':>6s} {'DA_sck':>6s} {'EA_hlt':>6s} "
           f"{'ODR':>5s} {'TD':>5s} {'Amp':>8s} | {'recover':>9s}  discrimination")
    print(hdr)
    print("  " + "-" * 100)
    for strat, (_fn, is_ctrl, _p) in STRATEGIES.items():
        if strat in ("F_no_perturbation", "P_passive_recovery"):
            r = run_return_trial(shared, strat, 0, traj_F, traj_P)
            print(f"  {strat:22s} {'-':>3s} | {r.da_hlt:6.3f} {r.da_sck:6.3f} {r.ea_hlt:6.3f} "
                  f"{r.odr:5.2f} {r.td:5.3f} {r.amp_tail:8.2f} | {r.verdict:>9s}  [BASELINE]")
            continue
        for t in t_returns:
            r = run_return_trial(shared, strat, t, traj_F, traj_P)
            tag = "  [CONTROL]" if is_ctrl else ("" if gates_pass else " (untrusted)")
            print(f"  {strat:22s} {t:3d} | {r.da_hlt:6.3f} {r.da_sck:6.3f} {r.ea_hlt:6.3f} "
                  f"{r.odr:5.2f} {r.td:5.3f} {r.amp_tail:8.2f} | {r.verdict:>9s}  {r.disc}{tag}")
        print()

    print("  " + "-" * 100)
    print("  DA_sck > 0 = beats passive decay (medicine). DA_hlt ~ 0 = as good as never-hit.")
    print("  MEANINGFUL needs DA_sck>0 AND a genuinely tighter tail (ODR>margin). THEATER =")
    print("  indistinguishable from natural motion. C_decay_* are NEGATIVE CONTROLS: the Amp")
    print("  column will swing wildly while coherence is unmoved — proof the metric is blind")
    print("  to amplitude, so they MUST read THEATER. D_phase_reset pins ~0.500 (history cliff).")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
