# Fix-2 trigger calibration — coherence_delta falsified, raw-gen novelty separates

- **Date:** 2026-06-08 · **Status:** shelved with Fix 2 (calibration stands for revival; spec `docs/training/fix2_specification_draft.md`)
- **Substrate:** live full stack, generator mocked (A/B) for novelty/attack · **Probe:** `fix2_trigger_calibration.py` (seed 11)
- **Depends on:** `2026-06-07-reflective-loop-cost` (band/cliff + gain floor), `2026-06-07-gate-decomposition`

**Verdict:** the agreed primary trigger signal **`coherence_delta` is FALSIFIED** — tiny (~−0.005) for every
workload, and novelty reads *less* negative than benign (the magnitude moat makes the marginal Δcoh ~0); no
(W,T) fires. The pre-named fallback **`gnov`** (= 1 − |cos(raw generator output, field)|, captured at step 2
before reconstitution) **SEPARATES cleanly**: benign tops ~**0.49**, novelty floors ~**0.885**.

**Calibrated trigger:** primary = `gnov`, window **W=10**, threshold **T ≈ 0.65** (mid-gap), fires iff **≥2
distinct sources AND** mean gnov > T. The **≥2-source gate is the attack discriminator** — attack's gnov is high
(0.954, like novelty) yet fires **0%**, excluded purely by the single-source gate (the gate-decomposition
discrimination, validated at the trigger). Signal substitution (Δcoh → gnov) was the directive's own pre-named
fallback, flagged for council ratification.

**Caveat (corrected):** the generator is not 1-D but **low-rank + dropout-inflated** (`generator-dropout-diversity`);
live benign gnov ≈ 0.39, ~40% of which is dropout noise. So Fix 2 is **not** dormant/trivially-safe — it is
**DEFERRED as premature**: the real token novelty it would gate on is marginal, and loosening the loop now would
mostly admit dropout noise. Generator diversity (training / dim / eval) is the upstream lever; Fix 2 waits behind it.

*Consolidated 2026-08-05 — the falsification, the gnov separation, the calibrated (W,T), and the deferral preserved. Full history in git.*
