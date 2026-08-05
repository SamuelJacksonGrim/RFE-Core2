# Fix 0-B full-loop validation — does the conformity lean survive in vivo, and does the symmetric gate fix it?

- **Date:** 2026-06-07 · **Status:** historical — split verdict; closes the owed full-loop run for `conformity-bias-fix0b`
- **Substrate:** live (Generator-warmed full stack), reaper formula varied probe-side · **Probe:** `fix0b_fullloop_probe.py` (seed 42, dim 64, 600 steps)
- **Depends on:** `2026-06-06-conformity-bias-fix0b`, `2026-06-06-coherence-is-not-plasticity`, `2026-06-06-multilayer-lock`

**Verdict (split):** the **direct** conformity term is real, small, cleanly gateable; an in-vivo **coherence-only**
lean is **not observationally separable**; the dominant survival/coherence link is **binding magnitude**.

**Numbers:** correlation structure coh×attractor ≈ +0.92, ×crystal ≈ +0.92, ×centrality **+1.00**, ×recurrence
≈ +0.64 (shuffle control collapses to max |corr| ≈ 0.13 ✓ — real, not artifact). Same-symbol counterfactual
(clean control): asymmetric **+1.16%/lap** (2× in 60 laps), symmetric & universal **+0.00%**. Magnitude: coherence
term ≈ **0.047** vs binding (att+cry+cen) ≈ **2.19** → binding is **~47×** larger. Baselines all pass (allow 0.992,
HHI 0.264, 46 values). Low-coherence cohort (n=6) reads 0.000 on every channel = brand-new arrivals, not recurring
dissenters — so coherence/recurrence/binding entangle 0.92–1.0 and only the same-symbol counterfactual is clean.

**Misread caught:** the first in-vivo measure used the retention **multiplier** (decay × reinforcement); `decay`
is age-dominated (step_counter ~10,800), returning a spurious partial-r ≈ −0.98 **identical across all three
formulas** (a false "conservative-enough"). The formulas being *indistinguishable* was the alarm; excluding the
age-driven decay channel fixed it.

**Decision:** keep the shipped **asymmetric** patch; symmetric is a safe minor direct-term upgrade, **not** the
lock-in fix; universal gating not warranted (doesn't decorrelate binding from coherence). The real lever is
upstream **attractor migration**, not the reaper's survival math.

*Consolidated 2026-08-05 — correlations, the 47× scale, the clean control, and the misread preserved. Full history in git.*
