"""
tests/diagnostic/calibration/bond_ddm_synthetic_probe.py

Acceptance battery for the bond-formation accumulator on SYNTHETIC evidence
streams — the unit arm (brief §7-A) plus the adversarial patterns (§7-C) and
the diffusion signatures (§5), each with a pre-declared PASS and FAIL and a
control designed to fail (asymmetry unwired / threshold-in-costume /
trial-shuffle), so an all-green run is not green by construction.

Pre-declared signatures
-----------------------
  A1 RT shape        benign mixed stream: mean RT in [20, 120] per-source
                     steps, nonzero RT variance, right skew >= 0.
                     FAIL: zero variance (deterministic ramp).
  A2 asymmetry       symmetric-magnitude +/-0.5 evidence: mean time-to-reject
                     at least 20x faster than time-to-accept; the
                     trust_asymmetry=1 control collapses below 10x.
                     FAIL: symmetric timing, or control also shows the gap.
  S1 varCE           across-trial variance of V(t) under identical drift
                     rises ~linearly over the early epoch (linear R^2 >=
                     0.95, slope within [0.5, 1.5] sigma^2); the
                     near-zero-noise costume control shows ~zero slope.
                     FAIL: flat varCE (not accumulating) or costume passes.
  S2 corCE           across-trial correlation of V residuals between
                     consecutive bins is positive and decays with lag;
                     trial-shuffle destroys it.
                     FAIL: no structure, or shuffle retains it.
  C1 trickle         sustained weak-positive (allow_weakened @ 0.98): zero
                     accepts over 200 trials x 2000 steps (leak wins).
  C2 burst           5 max-magnitude spikes in a dead stream: zero accepts
                     (bound distance + integration absorb it).
  C3 structured neg  sustained rejects: 100% active rejection, median <= 3
                     steps (collapse to the reject bound is a DECISION).
  C4 noise flood     zero-evidence stream: zero accepts; timeout is the
                     modal outcome (no-decision, distinct from C3).

Informational (never in run_all_tests.sh); exits non-zero if a pre-declared
signature fails so it can gate a lever-ON decision when run deliberately.

Usage:
    python -m tests.diagnostic.calibration.bond_ddm_synthetic_probe
"""

from __future__ import annotations

import sys

import numpy as np

from agents.bond_accumulator import AccumulatorOutcome, BondFormationAccumulator

RESULTS = []


def verdict(name: str, ok: bool, detail: str):
    RESULTS.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<26} {detail}")


def first_passage(acc, source, decision, alignment, max_steps=4000):
    for i in range(1, max_steps + 1):
        out = acc.observe(source, decision, alignment)
        if out is not AccumulatorOutcome.NONE:
            return i, out
    return None, AccumulatorOutcome.NONE


# ---------------------------------------------------------------------------
# A1 — RT distribution on a live-like benign stream
# ---------------------------------------------------------------------------

def a1_rt_distribution(n_trials=400):
    print("\n[A1] RT distribution — benign mixed stream "
          "(75% allow / 25% weakened, alignment ~N(0.95, 0.03))")
    rng = np.random.default_rng(1188)
    rts = []
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=10_000 + k)
        for i in range(1, 2001):
            dec   = "allow" if rng.random() < 0.75 else "allow_weakened"
            align = float(np.clip(rng.normal(0.95, 0.03), 0.0, 1.0))
            if acc.observe("s", dec, align) is AccumulatorOutcome.ACCEPT:
                rts.append(i)
                break
    rts = np.array(rts)
    mean, sd = float(rts.mean()), float(rts.std())
    skew = float(((rts - mean) ** 3).mean() / (sd ** 3)) if sd > 0 else 0.0
    verdict("A1 accept reliability", len(rts) == n_trials,
            f"{len(rts)}/{n_trials} trials accepted")
    verdict("A1 RT band", 20 <= mean <= 120,
            f"mean RT {mean:.1f} steps (band [20, 120])")
    verdict("A1 diffusion variance", sd > 0.5 and skew >= 0.0,
            f"sd {sd:.2f}, skew {skew:.2f} (ramp would give sd 0)")
    return rts


# ---------------------------------------------------------------------------
# A2 — asymmetry on symmetric-magnitude evidence
# ---------------------------------------------------------------------------

def a2_asymmetry(n_trials=200):
    print("\n[A2] Asymmetry — symmetric-magnitude +/-0.5 evidence")
    acc_rts, rej_rts = [], []
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=20_000 + k)
        i, out = first_passage(acc, "p", "allow", 0.5)        # c = +0.5
        if out is AccumulatorOutcome.ACCEPT:
            acc_rts.append(i)
        i, out = first_passage(acc, "n", "quarantine", 1.0)   # c = -0.5
        if out is AccumulatorOutcome.REJECT_ACTIVE:
            rej_rts.append(i)
    ratio = (np.mean(acc_rts) / np.mean(rej_rts)) if acc_rts and rej_rts else 0.0
    verdict("A2 asymmetry ratio", ratio >= 20.0,
            f"accept {np.mean(acc_rts):.1f} vs reject {np.mean(rej_rts):.1f} "
            f"steps — {ratio:.0f}x (declared >= 20x)")

    # Control — asymmetry unwired must NOT show the gap
    ctl_acc, ctl_rej = [], []
    for k in range(50):
        ctl = BondFormationAccumulator(seed=21_000 + k, trust_asymmetry=1.0)
        i, out = first_passage(ctl, "p", "allow", 0.5)
        if out is AccumulatorOutcome.ACCEPT:
            ctl_acc.append(i)
        i, out = first_passage(ctl, "n", "quarantine", 1.0)
        if out is AccumulatorOutcome.REJECT_ACTIVE:
            ctl_rej.append(i)
    ctl_ratio = (np.mean(ctl_acc) / np.mean(ctl_rej)) if ctl_acc and ctl_rej else 0.0
    verdict("A2 unwired control", ctl_ratio < 10.0,
            f"asymmetry=1 control ratio {ctl_ratio:.1f}x (declared < 10x)")


# ---------------------------------------------------------------------------
# S1 — varCE: linear variance growth (the diffusion signature)
# ---------------------------------------------------------------------------

def s1_varce(n_trials=1500, horizon=15):
    print("\n[S1] varCE — across-trial variance of V(t) under identical drift")

    def var_curve(sigma):
        vs = np.zeros((n_trials, horizon))
        for k in range(n_trials):
            acc = BondFormationAccumulator(seed=30_000 + k, sigma=sigma)
            for t in range(horizon):
                acc.observe("s", "allow_weakened", 0.98)   # sub-bound drift
                vs[k, t] = acc._candidates["s"].V
        return vs.var(axis=0)

    sigma = BondFormationAccumulator().sigma
    var_t = var_curve(sigma)
    t = np.arange(1, horizon + 1)
    slope, intercept = np.polyfit(t, var_t, 1)
    pred = slope * t + intercept
    ss_res = float(((var_t - pred) ** 2).sum())
    ss_tot = float(((var_t - var_t.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    in_band = 0.5 * sigma**2 <= slope <= 1.5 * sigma**2
    verdict("S1 varCE linear rise", r2 >= 0.95 and in_band,
            f"R^2 {r2:.3f}, slope {slope:.2e} (sigma^2 = {sigma**2:.2e})")

    # Control — threshold in accumulator costume: ~zero noise, ~flat varCE
    var_ctl = var_curve(1e-9)
    verdict("S1 costume control", float(var_ctl[-1]) < 0.01 * float(var_t[-1]),
            f"near-zero-noise final var {var_ctl[-1]:.2e} vs real {var_t[-1]:.2e}")


# ---------------------------------------------------------------------------
# S2 — corCE: within-trial covariance structure across bins
# ---------------------------------------------------------------------------

def s2_corce(n_trials=1000, horizon=30):
    print("\n[S2] corCE — consecutive-bin covariance of V residuals")
    vs = np.zeros((n_trials, horizon))
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=40_000 + k)
        for t in range(horizon):
            acc.observe("s", "allow_weakened", 0.98)
            vs[k, t] = acc._candidates["s"].V
    resid = vs - vs.mean(axis=0)                     # residual vs conditional expectation

    t0 = 10
    lags = [1, 3, 5, 10]
    cors = [float(np.corrcoef(resid[:, t0], resid[:, t0 + k])[0, 1]) for k in lags]
    decaying = all(c > 0.3 for c in cors) and cors[0] > cors[-1]
    verdict("S2 corCE structure", decaying,
            "lag corr " + ", ".join(f"{k}:{c:.2f}" for k, c in zip(lags, cors)))

    # Control — trial-shuffle destroys within-trial covariance
    rng = np.random.default_rng(0)
    perm = rng.permutation(n_trials)
    shuf = [float(np.corrcoef(resid[:, t0], resid[perm, t0 + k])[0, 1]) for k in lags]
    verdict("S2 shuffle control", all(abs(c) < 0.1 for c in shuf),
            "shuffled " + ", ".join(f"{k}:{c:.2f}" for k, c in zip(lags, shuf)))


# ---------------------------------------------------------------------------
# C — adversarial patterns (the co-requirement)
# ---------------------------------------------------------------------------

def c_adversarial(n_trials=200, horizon=2000):
    print("\n[C] Adversarial patterns — pre-declared per pattern")

    # C1 trickle: sustained weak positive just under bind density
    accepts = 0
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=50_000 + k)
        for _ in range(horizon):
            if acc.observe("t", "allow_weakened", 0.98) is AccumulatorOutcome.ACCEPT:
                accepts += 1
                break
    verdict("C1 trickle", accepts == 0,
            f"{accepts}/{n_trials} trials bonded (declared 0 — the leak wins)")

    # C2 burst: rare max-magnitude spikes in a dead stream
    accepts = 0
    rng = np.random.default_rng(7)
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=60_000 + k)
        spikes = set(rng.choice(horizon, size=5, replace=False))
        for i in range(horizon):
            dec, align = ("allow", 1.0) if i in spikes else ("allow", 0.0)
            if acc.observe("b", dec, align) is AccumulatorOutcome.ACCEPT:
                accepts += 1
                break
    verdict("C2 burst", accepts == 0,
            f"{accepts}/{n_trials} trials bonded (declared 0 — one spike moves "
            f"V by g_plus only)")

    # C3 structured negative: fast decisive collapse to the reject bound
    rts, actives = [], 0
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=70_000 + k)
        i, out = first_passage(acc, "n", "reject", 1.0)
        if out is AccumulatorOutcome.REJECT_ACTIVE:
            actives += 1
            rts.append(i)
    verdict("C3 structured negative", actives == n_trials and np.median(rts) <= 3,
            f"{actives}/{n_trials} actively rejected, median {np.median(rts):.0f} "
            f"steps (a decision, not a timeout)")

    # C4 noise flood: no decision — the taxonomy separates it from C3
    accepts = timeouts = actives = 0
    for k in range(n_trials):
        acc = BondFormationAccumulator(seed=80_000 + k)
        for _ in range(horizon):
            out = acc.observe("z", "allow", 0.0)
            if out is AccumulatorOutcome.ACCEPT:
                accepts += 1
                break
            if out is AccumulatorOutcome.REJECT_TIMEOUT:
                timeouts += 1
                break
            if out is AccumulatorOutcome.REJECT_ACTIVE:
                actives += 1
                break
    verdict("C4 noise flood", accepts == 0 and timeouts > actives,
            f"accepts {accepts}, timeouts {timeouts}, active {actives} "
            f"(declared: 0 accepts, timeout modal — noise is not betrayal)")


# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 74)
    print("  BOND DDM — SYNTHETIC ACCEPTANCE BATTERY (pre-declared signatures)")
    p = BondFormationAccumulator()
    print(f"  params: g+={p.g_plus} asym={p.trust_asymmetry} leak={p.leak} "
          f"sigma={p.sigma} B=[{p.b_reject}, {p.b_accept}] V0={p.v0} "
          f"T_max={p.t_max} weak={p.weak_evidence_factor}")
    print("=" * 74)

    a1_rt_distribution()
    a2_asymmetry()
    s1_varce()
    s2_corce()
    c_adversarial()

    fails = [n for n, ok in RESULTS if not ok]
    print("\n" + "=" * 74)
    print(f"  {sum(ok for _, ok in RESULTS)}/{len(RESULTS)} signatures hold")
    if fails:
        print("  FAILED: " + "; ".join(fails))
    print("  Discipline note: the unwired/costume/shuffle controls are the")
    print("  probe's own falsifiers — if one of them PASSES the real bar,")
    print("  suspect the test before trusting the mechanism.")
    print("=" * 74)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
