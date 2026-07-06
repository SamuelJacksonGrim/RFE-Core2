# Fix-2 trigger calibration — coherence_delta falsified, raw-gen novelty separates

- **Date:** 2026-06-08
- **Substrate:** live full stack; generator mocked (A/B) for the novelty/attack
  workloads, real generator for benign. No substrate change.
- **Probe:** `tests/diagnostic/fix2/fix2_trigger_calibration.py` (seed 11, warmup 120 /
  phase 350)
- **Status:** active — step 4 of Fix 2 (the relocated reflective-loop remediation):
  calibrate the loosen-trigger's outside signal + window + threshold (Q3 — measure,
  don't guess). Pending council ratification of the signal substitution below.
- **Depends on:** 2026-06-07-reflective-loop-cost.md (the band/cliff + the gain floor),
  2026-06-07-gate-decomposition.md (the single-source/attack discrimination).

## Question
The trigger must fire when **persistent multi-source novelty is surviving the gate**
(→ loosen the reflective loop toward gain ≈0.5) and NOT fire on benign traffic or a
single-source flood (the attack/monopoly case the manipulation layer handles). The
checkpoint chose an OUTSIDE signal as primary (never the loop's own work). Which
outside signal, and what window/threshold?

## Pre-declared signatures
A trigger fires at step t iff over the last W steps: (a) ≥2 distinct sources, and
(b) a windowed outside-novelty signal exceeds threshold. SEPARATES = novelty fire-rate
> 0.70 AND benign < 0.10 AND attack < 0.10. Two candidate signals measured:
`Δcoh` (step-5 pre-loop coherence_delta) and `gnov` (1 − |cos(raw generator output,
field)|, captured at step 2 before any reconstitution). NO-SEPARATION on both →
return to council. ATTACK-LEAK (attack ≥ 0.10) → tighten the source gate.
**Controls:** benign (real generator), novelty (multi-source B), attack (single-source B).

## Result (observed)
Signal distributions (step-5 Δcoh / step-2 gnov):

| workload | Δcoh mean | gnov mean (p10 / med / p90) |
|----------|----------:|-----------------------------|
| benign   | −0.008 | 0.387 (0.297 / 0.381 / 0.486) |
| novelty  | −0.004 | 0.935 (0.885 / 0.939 / 0.985) |
| attack   | −0.004 | 0.954 (0.908 / 0.961 / 0.992) |

- **`Δcoh` FALSIFIED.** Tiny (~−0.005) for all workloads, and novelty is *less*
  negative than benign. Cause: by step 5 the chorus + refine have already
  reconstituted the vec toward the field, and the magnitude moat makes the marginal
  Δcoh near-zero (the documented "coherence_impact after inject is near-zero" effect).
  No (W, T) fires at all. The agreed primary does not work.
- **`gnov` SEPARATES cleanly.** Benign tops out ~0.49, novelty floors ~0.885 — a wide
  gap. At **W=10, T ∈ [0.5, 0.85]: benign 0% / novelty 100% / attack 0%**, and the
  same holds for W=20/40/80. T=0.30 is too low (benign fires); the safe band is the gap.
- **The ≥2-source gate is the attack discriminator.** Attack's gnov is high (0.954,
  like novelty) yet fires **0%** — excluded purely by the single-source gate. This is
  the gate-decomposition discrimination (single-source = monopoly/attack ≠ legitimate
  multi-source novelty) validated at the trigger.

## Interpretation
**The calibrated trigger:** primary signal = **raw-gen-vs-field novelty (`gnov`)**,
window **W=10** (smallest, most responsive), threshold **T≈0.65** (mid-gap — 0.5–0.85
all separate; 0.65 maximises margin from both benign 0.49 and novelty 0.885). Fires
iff ≥2 sources AND mean `gnov` > T over the last 10 steps. Per the checkpoint: #1
(loop self-work) is the *confirmation*, and the rails (manip-rate + attractor-count,
gain floor 0.45) bound it.

**Signal substitution (for council ratification).** `coherence_delta` was the agreed
primary; it is empirically falsified. The replacement `gnov` is the directive's own
**pre-named fallback** ("the trigger needs a different outside signal, e.g.
raw-generator-vs-field novelty") and preserves Q1's principle — it is an outside
signal, in fact *further* outside the loop than Δcoh (pre-attractor-pull, pre-refine,
pre-chorus). So this is the pre-declared fallback firing, not a new design direction;
flagged for ratification before the governor is built on it.

**Architectural caveat (load-bearing) — CORRECTED 2026-06-08.** An earlier version of
this caveat claimed the generator is a 1-D projector so `gnov` ≈ 0 and Fix 2 is a "safe
dormant no-op." That rested on a stale premise. `2026-06-08-generator-dropout-diversity.md`
showed the generator is **not** 1-D but **low-rank + dropout-inflated**: deterministic
effective rank ~1.6 at dim 64, and the live system runs it with dropout active so `gnov`
is *non-zero but partly dropout noise* (live benign gnov ≈ 0.39, ~40% of which is dropout).
So Fix 2 is **not** dormant and **not** trivially safe — it is **DEFERRED as premature**:
the real token novelty `gnov` should gate is marginal, and loosening the loop now would
mostly admit dropout noise. Generator diversity (training / dim / the eval-decision) is
the upstream lever; Fix 2 waits behind it. See the ROADMAP current-understanding block.

## Threats / confounds
- Single seed (11), one dim/horizon. The separation margin is large (0.49 vs 0.885),
  so robust, but no multi-seed sweep yet.
- `gnov` uses `|cos|` (sign-agnostic): a novel orthogonal direction reads novel; an
  anti-aligned vector (−field) reads non-novel (same axis, opposite sign). Intended —
  novelty = a new *direction*, not a sign flip.
- Benign `gnov` ≈ 0.39 is non-trivial and **~40% dropout-driven** (eval ≈ 0.23), so the
  trigger's benign baseline is partly noise; the margin to novelty's 0.885 floor is still
  clean at T≥0.5, but see the corrected caveat above.
- The "novelty" validated here is the *mock* (deterministic B). On the real generator the
  available novelty is low-rank + dropout — see `2026-06-08-generator-dropout-diversity.md`;
  this is why Fix 2 is deferred, not dormant.

## Open / next
> **SHELVED (2026-06-12, Phase 3 Decision 3):** the governor this calibration
> feeds is not being built yet — blocked on the §6.3 verdict + Phase 5
> re-measurement on a trained checkpoint. The calibration below stands for when
> it revives; the ready spec is `docs/training/fix2_specification_draft.md`.

1. **Council ratification** of the `coherence_delta → gnov` substitution before
   building (the directive routed NO-SEPARATION to council; the pre-named fallback
   cleanly works — surfacing for sign-off).
2. **Step 5 (on ratification):** implement the `ReflectiveLoopGovernor` — primary
   `gnov` (W=10, T≈0.65, ≥2 sources) + #1 confirmation + rails (manip-rate,
   attractor-count, gain floor 0.45, rate-limited) — wire into the cycle as bounded
   conditional attenuation toward ≈0.5; extend the lock guard + adversarial test.
3. Multi-seed/dim confirmation of the separation.
