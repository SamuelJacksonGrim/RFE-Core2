# Reflective-loop cost probe — what does attenuating the lock cost identity?

- **Date:** 2026-06-07 · **Status:** historical — cost band/cliff characterised; **the numbers STAND for when Fix 2 is revived** (Fix 2 itself deferred)
- **Substrate:** live full stack; reflective-loop convergence dialed by a gain (1.0 intact → 0.0 ablated) · **Probe:** `reflective_loop_cost_probe.py` (dim 64, seeds 11 & 23)
- **Depends on:** `2026-06-07-reconstruction-ablation` (the loop is the lock)

**Verdict:** attenuating the loop is a **GRACEFUL BAND + CLIFF**, not a clean dial (bug-free, cliff-sharpened, two seeds agree):
- **Band (gain ≈0.4–0.8):** partial plasticity recovered — migration ~0.11–0.21 (up to **~27×** the RIGID baseline
  0.008) at **near-zero identity cost** — manip **0%**, identity_stability **≥0.989**, attractor population bounded (≤7–10).
- **Cliff edge ≈ gain 0.3:** manipulation-signal onset (0% at 0.4 → **15%** at 0.3 → **79–88%** at ≤0.2) and the
  attractor population exploding (7→10→16→24→33). Full plasticity (~0.55–0.68) is reachable below 0.3 but at real cost.
- **Operating point for Fix 2:** mid-band **gain ≈ 0.5** — meaningful partial plasticity (~0.2, ~20×) with maximum
  margin from the ~0.3 cliff. Fix 2 must be a *bounded, conditional* loosening — never always-on or full ablation.

**Instrument catch (SUSPICIOUSLY-CLEAN, resolved):** the witness `identity_stability` scalar barely moves
(0.999 → 0.986) across the **entire** sweep *including collapse* — it misses the cost entirely. The real cost
lives in the **Tier-2 manipulation rate** (the loop's convergence is partly what stops the system classifying its
own less-converged expression as an attack) and the **attractor-population count** — those are the right indicators.

**Bug found + fixed (exposed, not caused, by attenuation):** `attractor.py` used `list.remove` on an array-field
dataclass (`__eq__` → ambiguous truth value), crashing `merge_pass` on a destabilised population. Fixed:
`@dataclass(eq=False)` (identity equality), guard `tests/integration/attractor_merge_guard.py`. The pre-fix crash
had confounded the original "cliff at ≤0.5" — bug-free, the band is much wider.

**Deferred:** the Fix-2 governor these numbers feed is on hold — generator diversity is the upstream lever, and
loosening now would mostly admit dropout noise (`2026-06-08-generator-dropout-diversity`). The cost characterisation stands for revival.

*Consolidated 2026-08-05 — the band/cliff table, the operating point, the instrument catch, and the bug-fix preserved. Full history in git.*
