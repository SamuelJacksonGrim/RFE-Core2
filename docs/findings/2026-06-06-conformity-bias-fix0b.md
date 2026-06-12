# Conformity bias in the reaper — does coherence buy survival, and does a gated novelty term fix it?

- **Date:** 2026-06-06
- **Substrate:** isolated (pure-function `DecayProfile.compute`; the reaper's
  retention math in isolation, NOT the full live loop)
- **Probe:** `tests/diagnostic/lockin/conformity_bias_probe.py`
- **Status:** active — Fix 0-B candidate validated *in isolation only*; full-loop
  validation owed before the strong version ships
- **Depends on:** 2026-06-06-read-side-boundary.md (survival is currencied by
  coherence; this quantifies and fixes that), 2026-06-06-coherence-is-not-plasticity.md
  (the gate question this resolves)

## Question
The reaper's retention (`DecayProfile.compute`) is already a circulation chamber:
staged death ACTIVE→WARM→COLD→GRAVEYARD, `minimum_lifespan` immunity, a decay
floor, and a recurrence-weighted reinforcement sum. But `field_coherence_weight`
is positive in every profile. Does agreeing-with-the-field buy *extra* survival
beyond recurrence (the monoculture pump)? And does a recurrence-gated novelty
counterweight neutralise it?

## Pre-declared signatures
- CONFORMITY BIAS: at matched recurrence/attractor/centrality/crystal, the
  high-coherence state out-survives the low-coherence one → coherence buys
  survival; Fix 0-B needs a counterweight.
- TIE: trajectories within noise → coherence term negligible in practice.
- For the fix (symmetric-gate prototype): lean→~0 across classes; laps-to-2x→∞;
  one-off noise (recurrence=0) gets NO bonus; high-recurrence coherent vs novel
  tie.
- **Control:** the construction itself — two `SymbolState`s identical in every
  field except `field_coherence`. Every other reinforcement signal forced equal
  by hand (so coherence is the *sole* differing term; this is tighter than
  injecting real coherent-vs-novel patterns, which carry correlated
  attractor/crystal binding — the inputCos-style confound).

## Result (observed)

**Headline-artifact caught first:** an early version reported a survival ratio of
~10¹¹×. That was an unnormalised 400-lap compounding of a small per-step edge,
with usage running to ~10⁵⁷ — a measurement artifact, NOT the effect size. The
probe was rebuilt to report the per-step multiplier and laps-to-2× instead.

**Honest baseline (current formula, coherence ungated):** at matched everything-
else, field_coherence gives the coherent state a per-lap reinforcement-multiplier
advantage that scales cleanly with `field_coherence_weight`:

| class | coh_w | per-lap lean | laps until coherent = 2× novel |
|-------|------:|-------------:|-------------------------------:|
| GLYPH | 0.10 | +6.56% | 11 |
| ENTITY | 0.08 | +5.45% | 13 |
| LANGUAGE | 0.05 | +3.72% | 19 |

The lean is small per step but **monotonic and unopposed**, so it compounds:
coherent doubles the survival gap over an equally-recurrent novel pattern every
~11 laps (GLYPH). Insidious attrition, not a crushing force. The cross-class
ordering (lean tracks coh_w across three independent profiles) is the trustworthy
corroboration — the effect follows the knob.

**Fix attempts:**
1. *Mirror the weight* (novelty_weight = field_coherence_weight, novelty gated by
   recurrence): reduced the GLYPH lean +6.56% → +4.29% but did NOT neutralise it.
   Cause: the recurrence gate throttles novelty to ~33% of its weight at
   recurrence=0.8 (`1 - exp(-0.5·0.8) ≈ 0.33`), while coherence is ungated. The
   two terms are asymmetric, so matching weights undershoots.
2. *Symmetric gate* (probe-only prototype — gate BOTH coherence and novelty by
   recurrence): all four target signatures hold —

| class | asymmetric (mirror) | SYMMETRIC | noise (recur=0) | high-recur parity |
|-------|--------------------:|----------:|----------------:|------------------:|
| GLYPH | +4.29%/lap | −0.00%/lap | 1.0000 (no bonus) | 1.0000 (tie) |
| ENTITY | +3.58%/lap | +0.00%/lap | 1.0000 | 1.0000 |
| LANGUAGE | +2.46%/lap | +0.00%/lap | 1.0000 | 1.0000 |

## Interpretation
Conformity bias CONFIRMED, at its true size (~3–7% per lap, class-dependent),
not the artifact magnitude. The reaper is a working circulation chamber with a
thumb on the scale toward agreement.

Symmetric gating is the principled fix and validates cleanly *in isolation*:
recurrence becomes the price of admission, and coherence/novelty only modulate
survival *after* a pattern has recurred. Nothing — neither conformity nor novelty
— earns survival on a snapshot. This is the earned-integration / circulation-
chamber principle implemented faithfully (survive the laps first, then character
matters).

**What shipped vs. what's a candidate:**
- SHIPPED (conservative): `symbolic_memory.py` now has the *asymmetric* gated
  novelty term (novelty_weight mirroring coherence, novelty gated by recurrence).
  It reduces the lean (~6.6%→4.3% GLYPH) without changing how coherence itself is
  rewarded, so it carries no identity-formation risk. Safe interim.
- CANDIDATE (not shipped): *symmetric* gating (gate coherence too). Validated in
  isolation but NOT in the full loop.

## Threats / confounds
- Runs: deterministic pure-function (no seed variance); the per-step lean is exact
  given the profile weights. But this is the **isolated reaper math only.**
- **Correlated-signal leakage (the main unproven risk).** The probe forces
  attractor/centrality/crystal equal. In a live run these correlate with coherence
  (a field-agreeing pattern also binds existing attractors/crystals). Symmetric
  gating gates only coherence+novelty, NOT those three. So coherence's *shadows*
  could still leak a conformity lean through the ungated correlated terms. The
  probe cannot see this by construction. Open question: does the gate need to be
  *universal* (all binding signals), as Copilot argued?
- **Identity-formation impact (second unproven risk).** Gating coherence means a
  freshly-injected coherent pattern (low recurrence) gets *less* survival than
  today. The field's job is to hold identity; slower entrenchment of coherent
  patterns could slow or destabilise early identity formation. Healthy-state
  baselines (allow_rate ≥0.95, trust, HHI 0.20–0.40, bond counts) must still pass.
- Untrained-generator caveat inherited from the substrate's current state.

## Open / next
1. **Full-loop validation (owed before symmetric ships).** Run the full stack
   with the symmetric gate; confirm (a) the lean stays cancelled with correlated
   signals live, (b) healthy-state baselines still pass, (c) identity formation is
   not destabilised. → handed to Claude Code for live run.
   **→ DONE (2026-06-07), see `2026-06-07-fix0b-fullloop-validation.md`:** the
   direct term is small (+1.16%/lap) and symmetric/universal cancel it with
   baselines intact (b ✓); but (a) is **CONFOUNDED in vivo** — low-coherence
   symbols are degenerate brand-new arrivals, and coherence/recurrence/binding are
   entangled (0.92–1.0), so a coherence-only lean is not observationally separable.
   The dominant survival/coherence link is *binding magnitude*, which the reaper
   formula cannot adjudicate. Net: keep asymmetric; symmetric is a safe but minor
   direct-term upgrade, **not** the lock-in lever (that is upstream attractor
   migration).
2. If correlated-signal leakage appears, evaluate the **universal gate** (gate all
   binding signals by recurrence), per Copilot's argument.
   **→ Evaluated (2026-06-07): NOT warranted now.** Recurrence-gating does not
   decorrelate binding magnitudes from coherence, so universal gating is not the
   lever and perturbs binding broadly for a channel not shown harmful.
3. Keep the conservative asymmetric patch in the substrate until 1 passes.
   **→ Confirmed: keep asymmetric.**
