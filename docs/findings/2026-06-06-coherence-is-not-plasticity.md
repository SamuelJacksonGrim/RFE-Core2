# Coherence vs. plasticity — which measures lock-in?

- **Date:** 2026-06-06 · **Status:** historical — a definitional reframe (0 runs); the program it specified was executed 2026-06-07
- **Substrate:** n/a (conceptual reframe; from the multilayer-lock run + external review) · **Probe:** none — this finding *defined* the probes
- **Depends on:** `2026-06-06-multilayer-lock`, `2026-06-06-frame-correction`

**Verdict (definitional, not measured):** retired the "pin vs. band" framing — it conflated **field coherence**
(static phase alignment) with **attractor plasticity** (whether the field's attractor geometry can migrate under
persistent surviving novelty). A 0.998 field may still be adaptive if its attractor migrates; a 0.90 field may
still be rigid. So **lock-in must be assessed by attractor migration, not the coherence value.** Coupling caveat
(Raphael, do not over-clean to "coherence irrelevant"): if the magnitude moat is real and moat depth scales with
coherence, then higher coherence → larger moat → less mobility — coherence as an *input* to plasticity, not the
proxy for it. Kept three states deliberately separate: **Learned** (coherence ≠ plasticity) · **Unknown** (can
the attractor migrate?) · **Investigate first** (the gate, a confounder for any plasticity test).

**Program it specified, since executed (2026-06-07):** gate decomposition → the 85% block was a single-source
HHI artifact, input channel CLEAR (`gate-decomposition`); attractor migration → **RIGID**, the locker is the
reflective loop's active reconstitution upstream of the field (`attractor-migration`, `reconstruction-ablation`).

*Consolidated 2026-08-05 — the reframe, the coupling caveat, and the three-state hygiene preserved. Full history in git.*
