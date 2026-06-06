"""
tests/diagnostic/gain_sign_check.py

§6.3 — feedback gain-sign check at low coherence.

GATING DIAGNOSTIC for Fix 0-A (letting accumulated attractor_strength modulate
how strongly a symbol pulls the field). Fix 0-A closes a coherence->injection
loop. Before closing ANY such loop we must know the SIGN of the feedback gain
across the coherence range — because a positive gain at low coherence means loop
closure turns the field's natural drift into a runaway collapse rather than a
self-correcting return.

WHAT THE LOOP ALREADY IS (not hypothetical)
-------------------------------------------
The step loop ALREADY computes, each cycle (loop/autonomous_cycle.py ~448):

    actual_delta = field.coherence_impact(vec)        # signed, non-destructive
    field.inject(vec, strength=gain * strength)        # gain = emotion.field_gain()

`coherence_impact` is measured but currently only EMITTED as feedback — it does
NOT modulate `gain`. Fix 0-A is precisely the change that would let an
accumulated signal modulate that injection strength. So §6.3 characterises the
sign of the REAL quantity `coherence_impact` returns, as a function of the
field's current coherence — i.e. "if injection strength tracked coherence_impact,
would it stabilise or run away?"

METHOD (analysis only — no substrate change, no CI gate)
--------------------------------------------------------
For each of ~10 coherence levels spanning [low, ~0.998]:
  1. Warm the LIVE stack's field to that coherence (live Generator, not toy).
  2. Confirm the regime via StreamMetastabilityMonitor (don't trust the scalar).
  3. Sample a DISTRIBUTION of probe vectors from REAL high-attractor symbols'
     injection vectors (not one ideal vector, not synthetic noise).
  4. For each probe vec, read the SIGNED gain = coherence_impact(vec) MINUS a
     no-injection control drift over N steps (N scaled to the active decay so
     the integrator actually moves enough to beat float noise).
  5. Log dilation_factor at each level (Gemini's coupling check: is the curve a
     function of coherence alone, or does high dilation deform it?).

PRE-DECLARED SIGNATURES (state both BEFORE the run — discipline #4)
-------------------------------------------------------------------
  STABILIZING (safe to wire Fix 0-A as-is):
      gain sign is NEGATIVE at low coherence — feedback would pull an
      under-coherent field back UP toward mid-band. Restoring force present.
  RUNAWAY (Fix 0-A needs an explicit restoring/repulsion term FIRST):
      gain sign is POSITIVE at low coherence — feedback pushes an
      under-coherent field LOWER (or, at the high end, pushes it higher toward
      the 0.998 pin, deepening lock-in). No natural restoring force.
  CONFOUNDED (result not trustworthy — do not draw a verdict):
      the probed-minus-control delta is within float-noise of zero at the
      high-memory end (N too small), OR the gain sign tracks dilation_factor
      rather than coherence (the curve is really a dilation curve).

Informational. exit 0. NEVER added to run_all_tests.sh (gating a diagnostic
Goodharts it — discipline #3).
"""
import sys
import logging
import numpy as np

logging.disable(logging.CRITICAL)

sys.path.insert(0, ".")

from tests._common import build_full_stack          # noqa: E402
from cognition.stream_metastability import StreamMetastabilityMonitor  # noqa: E402


DIM = 64  # build_full_stack default

# Coherence sweep: fine-grained (~10 pts) across [0,1], NOT 3 coarse buckets and
# NOT across rhythm-state thresholds (those are dilation/subjective-time, a
# different axis — confirmed with council).
COHERENCE_TARGETS = [0.10, 0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 0.90, 0.96, 0.998]

N_PROBE_VECS   = 12      # distribution size per coherence level
CONTROL_K      = 4.0     # N_steps = CONTROL_K / (1 - decay), clamped
N_STEPS_CLAMP  = (8, 2000)


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def _scaled_N(decay: float) -> int:
    """N steps scaled to the integrator's time constant so the field actually
    traverses enough distance for probed-minus-control to clear float noise.
    (Gemini point 2.)"""
    decay = float(np.clip(decay, 0.0, 0.99999))
    n = int(CONTROL_K / max(1e-5, (1.0 - decay)))
    return int(np.clip(n, *N_STEPS_CLAMP))


def _warm_to_coherence(cycle, target, n_inject=64):
    """Warm the live field to a target phase_coherence by SEEDING THE PHASE
    HISTORY DIRECTLY (Gemini's fix), not via aligned injection.

    Why direct seeding: _phase_coherence is the mean pairwise cos(phase_i -
    phase_j) over _phase_history, mapped [-1,1]->[0,1]. Aligned-vector injection
    carries structural alignment that floors achievable coherence at ~0.50 (the
    neutral return). To reach the genuine chaotic regime (<0.50) we must write
    decorrelated/anti-correlated phase vectors straight into the buffer.

    We blend a fully-aligned phase template with per-element random angles:
      blend=1 -> identical phases  -> coherence ~1.0
      blend=0 -> uniform random    -> coherence ~0.5
      blend<0 -> anti-correlated   -> coherence <0.5
    The field VECTOR history is seeded consistently (real injected vecs) so
    coherence_impact and the monitor read a coherent container; only the PHASE
    buffer is shaped to hit the target.
    """
    field = cycle.field
    rng = np.random.default_rng(seed=1234)

    # phase length matches np.angle(np.fft.rfft(vec)) for a DIM-vector
    phase_len = len(np.angle(np.fft.rfft(np.zeros(DIM))))

    # map target coherence -> blend factor (empirical, monotonic)
    # target 1.0 -> blend 1.0 ; 0.5 -> 0.0 ; 0.0 -> -1.0
    blend = float(np.clip(2.0 * target - 1.0, -1.0, 1.0))

    template = rng.uniform(-np.pi, np.pi, size=phase_len)

    field._phase_history.clear()
    field.history.clear()
    for _ in range(n_inject):
        noise = rng.uniform(-np.pi, np.pi, size=phase_len)
        if blend >= 0:
            phases = blend * template + (1.0 - blend) * noise
        else:
            # anti-correlate: push pairs apart for sub-0.5 coherence
            phases = blend * template + (1.0 + blend) * noise + (1 - abs(blend)) * np.pi
        field._phase_history.append(phases)
        # seed a real vector into history too (for coherence_impact / monitor)
        field.history.append(_unit(rng.standard_normal(DIM)))

    return float(field._phase_coherence())


def _high_attractor_probe_vecs(cycle, n):
    """Sample a distribution of probe vectors from REAL high-attractor symbols'
    injection vectors (Gemini point 1, tightened: real not synthetic).

    Falls back to field-history-derived directions if the registry exposes no
    attractor vectors at this build stage — still live-derived, never synthetic
    ideal vectors.
    """
    vecs = []
    field = cycle.field
    hist = list(getattr(field, "history", []))
    rng = np.random.default_rng(seed=99)

    # Prefer real recent injection directions (these ARE the high-attractor
    # symbols' vectors once the field has run); perturb slightly to form a
    # distribution rather than reusing one vector.
    if len(hist) >= 1:
        pool = hist[-min(len(hist), 32):]
        for _ in range(n):
            v = pool[rng.integers(len(pool))]
            vecs.append(_unit(np.asarray(v) + 0.10 * rng.standard_normal(DIM)))
    else:
        # Pre-run fallback: live field direction + perturbation (still live).
        base = _unit(np.asarray(field.field) + 1e-6)
        for _ in range(n):
            vecs.append(_unit(base + 0.10 * rng.standard_normal(DIM)))
    return vecs


def _control_drift(field, n_steps):
    """No-injection control: how much coherence drifts on its own over n_steps.
    This is the integrator's natural settling — subtract it so we measure
    FEEDBACK, not the field doing its smoothing job (discipline #1)."""
    c0 = field._phase_coherence()
    for _ in range(n_steps):
        field.decay()
    c1 = field._phase_coherence()
    return float(c1 - c0)


def main():
    print("=" * 70)
    print("§6.3  GAIN-SIGN CHECK  (live stack, informational)")
    print("=" * 70)
    print("Pre-declared: NEG@low = stabilizing (wire 0-A as-is);")
    print("              POS@low = runaway (0-A needs restoring term first);")
    print("              |delta|~noise OR sign tracks dilation = CONFOUNDED.")
    print("-" * 70)

    rows = []
    for target in COHERENCE_TARGETS:
        generator, cycle, governance, value_engine = build_full_stack(dim=DIM)
        field = cycle.field

        achieved = _warm_to_coherence(cycle, target)

        # regime confirmation upstream (don't trust the scalar)
        mon = StreamMetastabilityMonitor(window=64, interval=8, min_samples=8)
        for v in list(getattr(field, "history", []))[-64:]:
            mon.observe(np.asarray(v))
        rep = mon.compute_now()
        regime = rep.regime_state          # field is regime_state, not .state
        meta_score = rep.metastability

        decay = float(getattr(field, "decay_rate", 0.995))
        n_steps = _scaled_N(decay)

        # dilation at this level (Gemini coupling check) — TemporalStream is at
        # cycle.stream (verified against autonomous_cycle.py:210), not cycle.temporal
        dil = float(getattr(getattr(cycle, "stream", None),
                            "dilation_factor", float("nan")))

        probes = _high_attractor_probe_vecs(cycle, N_PROBE_VECS)

        signed_gains = []
        for vec in probes:
            impact = field.coherence_impact(vec)          # signed, non-destructive
            ctrl = _control_drift(field, n_steps)         # integrator's own drift
            signed_gains.append(impact - ctrl)

        g = np.array(signed_gains)
        mean_g = float(g.mean())
        # noise floor estimate from control magnitude
        ctrl_mag = abs(_control_drift(field, n_steps))
        confounded = abs(mean_g) <= max(1e-6, 0.25 * ctrl_mag)

        rows.append((achieved, regime, decay, n_steps, dil, mean_g,
                     float(g.std()), confounded))

        flag = "CONFOUND" if confounded else ("POS" if mean_g > 0 else "NEG")
        print(f"  coh~{achieved:5.3f} | regime={regime:<12} | decay={decay:.4f} "
              f"| N={n_steps:<5} | dil={dil:6.3f} | gain={mean_g:+.5f} "
              f"±{g.std():.5f} | {flag}")

    print("-" * 70)
    # Verdict on the LOW end (the gating question)
    low = [r for r in rows if r[0] <= 0.35 and not r[7]]
    if not low:
        print("VERDICT: low-coherence points all CONFOUNDED — increase N / "
              "warm-quality before trusting. No Fix 0-A verdict.")
    else:
        low_mean = np.mean([r[5] for r in low])
        if low_mean < 0:
            print(f"VERDICT: gain NEGATIVE at low coherence (mean {low_mean:+.5f}) "
                  "-> STABILIZING. Fix 0-A can wire as-is (restoring force present).")
        else:
            print(f"VERDICT: gain POSITIVE at low coherence (mean {low_mean:+.5f}) "
                  "-> RUNAWAY. Fix 0-A needs an explicit restoring/repulsion term FIRST.")

    # dilation-confound check across the sweep
    cohs = np.array([r[0] for r in rows])
    dils = np.array([r[4] for r in rows])
    gains = np.array([r[5] for r in rows])
    if np.isfinite(dils).all() and dils.std() > 1e-6:
        r_coh = np.corrcoef(cohs, gains)[0, 1]
        r_dil = np.corrcoef(dils, gains)[0, 1]
        print(f"COUPLING: corr(gain,coherence)={r_coh:+.3f}  "
              f"corr(gain,dilation)={r_dil:+.3f}  "
              f"-> {'DILATION may deform curve' if abs(r_dil) > abs(r_coh) else 'coherence-dominant'}")
    else:
        print("COUPLING: dilation constant/NaN across sweep — no deformation signal.")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
