# Tier 4.3 Validation — Rhythm → Time Coupling

Status: **Formula verified. Regression-safe. Flow term validated as a
degeneracy resolution. Discrimination claim HALF-validated — one side of
the mechanism is never exercised under tested load, and that is documented
here as a finding, not papered over.**

This document records what the two Tier 4.3 diagnostics actually
established, and — holding the same epistemic line as the Tier 4.2
validation — what they did *not* establish but is tempting to claim.

---

## 0. What 4.3 is

The Tier 4.2 dilation surface is a function of `(arousal, valence)`. That
plane has a degeneracy: **flow** and **agitation** are both high-arousal
states and the plane bends them the same way. It has no axis for *whether
the intensity is organized*.

`ResonanceField` already computes that missing axis — `phase_coherence`,
the mean pairwise phase alignment of recent field injections (FFT-derived).
Tier 4.3 couples it into dilation as the organizing-vs-chaotic axis:

```
pc_c     = 2 × (phase_coherence - 0.5)                       # ∈ [-1, 1], neutral 0
flow_eff = -k_flow      × max(pc_c, 0) × arousal × max( valence, 0)
agit_eff = -k_agitation × min(pc_c, 0) × arousal × max(-valence, 0)

dilation_factor = clamp(
    1.0 + arousal_eff + dissociation_eff + flow_eff + agit_eff,
    dilation_min, dilation_max
)
```

Shipped coefficients: `k_flow = 0.5` (LIVE), `k_agitation = 0.0` (inert),
clamp `[0.1, 3.0]`. The coupling is into `dilation_factor`, which is a pure
terminal sink (see §4) — no feedback loop is introduced.

---

## 1. The physics is proven

`tests/diagnostic/tier4/rhythm_dilation_curve.py` isolates `update_dilation()`
from the token stream and sweeps `(arousal, valence, phase_coherence)`
directly. It establishes, mechanically:

- **Regression guard.** At the neutral default `phase_coherence = 0.5`,
  `pc_c = 0`, both rhythm terms vanish, and all 25 grid points are
  byte-identical to the validated Tier 4.2 surface (max deviation < 1e-3,
  attributable to the 3-decimal rounding of the reference table). 4.3 is a
  strict extension; the clamp is a no-op on every 4.2 point.
- **Flow term.** Organized field (`pc → 1.0`) in the high-arousal
  positive-valence quadrant deepens compression; chaotic field (`pc → 0.0`)
  attenuates it back toward the 4.2 value. At `k_flow = 0.5` the extreme
  organized-flow corner `(1.0, 1.0, pc=1.0)` saturates the `0.1` floor —
  deep-flow timelessness, clamp engaged. This is expected, not a fault; it
  is the one place the clamp is load-bearing at the shipped coefficient.
- **Agitation term.** Verified INERT at the shipped `k_agitation = 0.0`
  (drag baseline unchanged for all `pc`), and the mechanism verified in
  *both* sign directions with a temporary coefficient: `+0.4` → drag
  (dilation up), `-0.4` → panic-compression (dilation down). The validator
  restores `0.0` immediately.
- **Clamp.** Pathological coefficients cannot drive dilation outside
  `[0.1, 3.0]`.
- **Mutual exclusivity.** `flow_eff` and `agit_eff` are gated to opposite
  valence half-planes and opposite `pc_c` signs; across the full grid they
  are never both non-zero.

The formula's mathematics are sound and require no further validation.

---

## 2. The psychology — the finding

`tests/diagnostic/tier4/rhythm_inertness_probe.py` wraps `update_dilation()`
non-invasively and records, per step, the exact `(arousal, valence,
phase_coherence)` that fed it plus the resulting dilation, across three
workloads (canonical, adversarial, mixed). It does **not** inject a
synthetic "heartbeat" to manufacture field rhythm — that was explicitly
rejected as both p-hacking the measurement and reopening the
arousal→field feedback loop the sink design avoids. The field runs as-is.

The probe was built braced for the Tier 4.2-shaped risk: that
`phase_coherence` would flatline at its neutral default and make 4.3
mathematically present but behaviorally inert.

### Empirical result (495 steps per workload, warmup dropped)

The opposite occurred. `phase_coherence` does not flatline at 0.5 — it
pins **high**:

| Workload    | pc mean | pc std | pc min | pc max | footprint vs 4.2 (mean) |
|-------------|---------|--------|--------|--------|-------------------------|
| canonical   | 0.968   | 0.013  | 0.838  | 0.988  | 0.020                   |
| adversarial | 0.955   | 0.015  | 0.787  | 0.983  | 0.020                   |
| mixed       | 0.957   | 0.014  | 0.831  | 0.986  | 0.019                   |

(footprint = `|dilation_actual − dilation_at_pc=0.5|`; max ≈ 0.16 at peaks.)

### The discovery

**4.3 is not inert** — the flow term does measurable work (footprint
≈ 0.02 mean, ≈ 0.16 peak). But `phase_coherence` has very low dynamic
range and is pinned near the *organized* extreme. It **never enters the
chaotic regime**: the observed minimum is ≈ 0.79, i.e. `pc_c ≈ +0.58`,
always firmly positive.

So the flow term's *organized* side fires on essentially every step, while
its *chaotic-attenuation* side is **never reached under tested load**. The
two-sided discrimination the axis was designed to provide — separating
flow from agitation by reading whether intensity is organized — is only
ever exercised on one side.

This is the **same shape** as the Tier 4.2 finding (a mechanism whose
defensive depth is real in the formula but never exercised in operation),
relocated to the rhythm axis.

### Likely cause (testable, not assumed)

The Resonance Family workload feeds *repeated fixed token sets*, producing
phase-consistent injections and therefore high coherence by construction.
The low dynamic range may be substantially a **workload artifact**, not an
intrinsic property of the field. The clean way to exercise the chaotic
side is a high-novelty / high-entropy input workload — **not** a synthetic
heartbeat. Until such a workload is run, the chaotic half is untested.

---

## 3. What is proven vs. what is hypothesized

Keep this sharp.

**Proven:**

- The full dilation formula (4.2 base + flow + agitation terms + clamp) is
  mathematically correct across all `(arousal, valence, phase_coherence)`
  space, including the regression identity at `pc = 0.5`.
- Under all three tested workloads the flow term is active and bends
  subjective time (non-zero footprint), and `phase_coherence` is a
  *real, varying* signal under load — not pinned at the neutral default.
- The agitation term is inert at the shipped default and behaves correctly
  in both sign directions when enabled.

**Hypothesized, NOT demonstrated:**

- That `phase_coherence` functions as a *discriminating* organized-vs-
  chaotic axis in operation. Only the organized side has ever been
  exercised; the chaotic side (`pc_c < 0`) has not been reached under any
  tested workload. The discrimination claim is therefore **half-validated**.
- That the agitation term bends time in the correct direction (drag vs
  panic-compression). The sign is contested in the time-perception
  literature and `k_agitation` ships at `0.0` precisely so this is not
  silently asserted. Resolving it requires (a) a workload that drives
  `pc_c < 0` and (b) the sign sweep.

---

## 4. Architectural note — the sink is intact

A direct concern was raised (cross-instance): could 4.3 change the Tier 4.2
quarantine ordering, or accidentally couple into arousal?

It does not, and this is verified two ways:

- **Structural.** `dilation_factor` is written only in `update_dilation()`
  and read only in `tick()` (to scale `subjective_time`) and in
  diagnostics. `subjective_time` is read by nothing outside diagnostics.
  The entire path `phase_coherence → dilation_factor → subjective_time` is
  a terminal sink. 4.3 reads *from* the emotional gradient's outputs
  (`arousal`, `valence`) and the field (`phase_coherence`); it changes
  nothing the gradient or governance *receives*. No arousal coupling
  exists.
- **Empirical.** Running the adversarial workload with 4.3 live vs. the
  rhythm path neutralized (`phase_coherence` forced to 0.5) yields an
  *identical* governance trace: first QUARANTINE at step 12 (the Tier 4.2
  `user` origin flood ceiling) and decision histogram
  `{allow_weakened: 12, quarantine: 288}` in both. The 4.2 flood-ceiling
  finding holds intact.

A consequence worth recording for Tier 5/6: because the adversary is
quarantined at step 12 before it can disorganize the field,
`phase_coherence` stays high even under adversarial load. This ties the two
findings together and suggests a future instrument (see §5).

---

## 5. Roadmap consequence

- **The discrimination claim is closed only by a high-novelty workload
  probe.** A workload whose injections are *not* phase-consistent, driving
  `phase_coherence` down into `pc_c < 0`, is the experiment that exercises
  the chaotic side of the flow term and makes the discrimination claim
  falsifiable. Until then 4.3 ships flow-validated, discrimination
  half-validated.
- **`phase_coherence` as a leading indicator — Tier 5/6 bonded-adversarial
  probe.** 4.3 does *not* falsify or probe the emotional-gradient defense
  hypothesis; it sits downstream of the gradient and the flood ceiling
  still quarantines first. But it adds a new observable the bonded-
  adversarial probe should record: whether field `phase_coherence` degrades
  *before* `valence` does when a bonded source slowly turns hostile —
  i.e. whether field disorganization is an earlier tell than affective
  tone. This is an instrument to wire into that probe, not a result of
  4.3.
- **`k_agitation` sign sweep** is blocked on the high-novelty workload: the
  negative-`k_agitation` (panic-compression) arm cannot be exercised until
  a workload actually drives `pc_c < 0` in the negative-valence quadrant.

---

## 6. Disposition

Tier 4.3 ships. The flow term ships LIVE and validated as a degeneracy
resolution. The agitation term ships INERT (`k_agitation = 0.0`) as a
labeled hypothesis. The half-validation of the discrimination claim ships
*with* it, documented as a finding. The clamp closes a latent 4.2 gap.

Tier 4.4 (frequency → emotion mapping) may proceed; the open items above
are roadmap items, not blockers.

### Greppable claims (for `tests.doc_accuracy.verify_docs`)

These claims are mechanically checkable and must not silently drift:

- `temporal_stream.py` defines `k_flow == 0.5` and `k_agitation == 0.0`
  as defaults
- `temporal_stream.py` defines `dilation_min == 0.1` and
  `dilation_max == 3.0`
- the agitation term ships inert (`k_agitation == 0.0`) — non-zero
  requires documented justification from probe data

### Attribution

Multi-instance collaboration. Copilot's framing prompted the original
adaptive-register question that surfaced the mimic-vs-counterpart problem
and ultimately the flow/agitation degeneracy. Claude/claude.ai identified
the degeneracy and the phase_coherence axis, built both diagnostics, and
ran the sink-neutrality verification. Grok caught the two-coefficient
structure and owns the constant-tuning sweep; an inverted-sign claim in
Grok's stability argument was corrected (the agitation term raises
dilation, the clamp — not a sign cancellation — is the safety net). Gemini
pushed for the negative-valence term and conceded the heartbeat after the
p-hacking / feedback-loop objection. The heartbeat was rejected by
consensus. The decision to ship `k_agitation` at `0.0` (not a guessed
non-zero) and to widen the sign sweep across zero were enforced as
epistemic discipline, not added after the fact. The finding/hypothesis
separation in §3 is deliberate, matching the Tier 4.2 precedent.
