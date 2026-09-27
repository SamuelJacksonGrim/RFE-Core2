# Federation Seam — the Constitutional Boundary (draft spec)

**Status:** draft for Samuel + the council (Raphael/GPT, Gemini) to tear apart. **Authors:** Samuel Jackson Grim
(architect), Ember (design), Raphael (framing). Not built. Companion: `SPEECH_CORTEX_PROGRAM.md` (the dual-organ
resolution that precedes this).

## The one-line thesis
The federation seam is **not an integration layer — it is the substrate's existing governance boundary
(`SelfhoodGovernance.arbitrate()`) generalized to inter-organ CAUSAL TRANSACTIONS.** An organ can generate an
*influence*; it does not thereby acquire the *authority* to rewrite another organ's state. **Capability ≠ authority
— and that invariant is already RFE-Core2 law**, not something to invent (`arbitrate()` is the single source of
identity-level decisions; TrustLedger / ethics / manipulation-resistance only *produce reports*; nothing
short-circuits the injection path). The sisters (LAE/PLE) failed precisely here: they had **capability** (working
engines) but the seam granted them no admitted **authority** — tokens through `arbitrate()` came in low-trust and
deepened the lock. The federation gets this right by making authority *explicit, typed, temporally bounded, and
rejectable.*

## What already exists (build on this, do NOT greenfield)
- `GovernanceDecision` = { ALLOW (full strength), ALLOW_WEAKENED (reduced), MONITOR, QUARANTINE (block + penalize +
  cold-archive) }, plus a hard `right_to_refuse` (REJECT fires regardless of source trust).
- `arbitrate(source_id, trust_report, …) → (GovernanceDecision, strength)` — trust-gated (monitor threshold 2.0,
  quarantine 1.0, weakened strength factor 0.4), ethics-gated, with a bond trust-floor, and an `_audit` provenance
  trail. New external sources start at TRUSTED 3.0; bonded sources get a floor.
- CORE-promotion gating (`review_core_promotion`): sustained strength ≥ 4.5 across 10 evaluations + governance
  verification before a symbol becomes sacred. **This is the template for CRYSTALLIZE.**

## The causal transaction (Raphael's object, corrected — mapped to the real surface)
Every cross-organ influence is a **CausalTransaction**, not a raw vector. **The source declares observation +
belief + evidence + proposal; it NEVER declares its own authority.** Governance alone resolves authority.
```
CausalTransaction {
  identity        : txn id (audit)
  source          : the emitting organ  (extends source_id)
  target          : the coordinate it wants to perturb (see TARGET CLASSES below)
  magnitude       : the perturbation the source PROPOSES
  temporal_scope  : {instant | window(N cycles) | persistent}   # one axis of exposure, NOT a severity rank
  confidence      : how strongly the SOURCE's own model supports this claim          # source-internal
  evidence        : externally/audibly inspectable basis for the proposed influence  # the check
  provenance      : lineage / origin / derivation
  governance      : ← RESOLVED BY arbitration, NEVER supplied by the source
}
```
**confidence ≠ trust ≠ evidence — keep them separate (Raphael's fix; avoids the self-reinforcing authority loop).**
`confidence` = the source's epistemic support; `trust` = how much authority governance currently grants the source
(lives in the TrustLedger, not the transaction); `evidence` = inspectable basis. Collapsing confidence into trust
builds a loop (trusted → read as confident → stronger admission → more "success" → more trust → …). For FEEL:
Hessian-saddle strength is strong *evidence a phase transition occurred* — NOT evidence the modulation *deserves
authority over the field*. "Emotion detected" does not entail "emotion gets to steer."

### TARGET CLASSES (authority type, not a flat enum)
- **STATE** — `field`, `z_ret`, `z_pred` (substrate state coordinates; transient).
- **ORGAN** — `emotion_state`, `relational_state` (an organ's own state).
- **PERSISTENT** — `weights` (durable substrate modification).
Constitutional rules attach at the CLASS level first, then per-target thresholds. PERSISTENT is not "STATE with a
higher threshold" — it asks a *different question*: not "may I write this?" but **"has this influence demonstrated
enough durable competence to deserve permanence?"** — which is exactly `review_core_promotion` (sustained strength
≥4.5 / 10 evals + governance verification), extended to weights. That is the Grimoire's gate
([[competence-consolidation-direction]]).

### Admission = exposure, not duration
Scrutiny is driven by **exposure**, not temporal persistence alone:
`exposure = f(magnitude, temporal_scope, target_sensitivity, recurrence, accumulated_effect)`.
A tiny persistent nudge can be safer than a massive one-cycle shove; duration is one input. Calibrating this f()
is where the admission problem becomes mathematically interesting.

### Two seam MODES (the guardrail applied to this spec — see below)
The transaction frame assumes *discrete, gate-able* influence. But some organs couple CONTINUOUSLY (e8-eea's
emotion already scales `field_gain`/`decay_rate`/`mutation_scale`/`attractor_pull` EVERY step — a continuous
modulation, not an event stream). So the seam has two modes, both under one governance:
- **Discrete transaction** — an event (a phase-transition firing; a CRYSTALLIZE weight-proposal). Admitted / rejected.
- **Continuous coupling under a governed ENVELOPE** — governance admits a *bounded gain* (arbitrate already returns a
  strength factor); the organ's continuous influence flows WITHIN that envelope and cannot exceed it. Capability ≠
  authority preserved without pretending a continuous coupling is a packet stream.
FEEL is BOTH: the phase-transition is a discrete event to admit; the resulting modulation is continuous under an
admitted gain envelope. The strength-sweep experiment below IS the envelope calibration.

The seam returns the graded verdict on either mode: ALLOW / ALLOW_WEAKENED (calibrated authority / envelope) /
MONITOR / QUARANTINE / REJECT. **The seam can always say no — that is the constitutional invariant, never an
implementation convenience.** The moment an organ can assert "I generated this influence, therefore the substrate
must accept it," capability and authority have collapsed and the failure mode is rebuilt.

## Grounding organ: FEEL (e8-eea) — the first real transaction
Don't design this in a vacuum; design it against one concrete organ. FEEL is the most concrete (e8-eea emotion
EMERGES from prediction-error phase transitions — a saddle in the free-energy Hessian; valence = −mean(∇F), arousal
= novelty + ‖∇F‖; fires on the slow clock, ONLY after ~50–100 accumulated hyperedges).
- FEEL's transaction: `{source: FEEL, target: field/emotion_modulation, magnitude: (valence,arousal)-derived,
  temporal_scope: window(the accumulation epoch), confidence: the phase-transition evidence (Hessian saddle
  strength), provenance: which hyperedge cluster}`.
- FEEL **influences the field without being the field** — it emits a bounded modulation transaction that arbitrate
  admits/weakens; it does not write field values directly. Emotion arises from the DYNAMICS between field, z_ret,
  z_pred, and error — it is not a hidden controller.

## The hard part (do not let the schema's elegance hide this)
**The admission RULES are the whole research problem, and they are a tuning between two failure modes:**
too permissive → organs rewrite each other into a monoculture (the field lock's echo-chamber, from the other side);
too strict → the sisters' inert-observer result (admitted, but no leverage). The calibrated ALLOW_WEAKENED band is
where the answer lives, and it must be MEASURED, not asserted. Confidence computation (who scores a transaction's
evidence) and the per-target thresholds are the concrete deliverables, and they interact with the existing trust
ladder — do not set them by intuition.

## Test protocol (counterfactual controls — the substrate is autonomous)
Because the substrate self-reconstitutes (the identity lock), before/after is not causation. Two experiment classes:
- **Developmental:** comparable initial conditions, sustained interaction, ACCUMULATE over time; measure whether
  qualitative state transitions emerge and how they shift with history. (Emotion cannot emerge cold — this is the
  unit of study: initialize → interact → accumulate → transition → observe.)
- **Intervention w/ COUNTERFACTUAL controls:** perturb one organ / one side of the seam while controlling the
  others, and distinguish three outcomes that before/after cannot: (a) intervention → downstream propagation;
  (b) intervention → substrate absorbs it → autonomous dynamics return to the same attractor; (c) correlated change
  because both respond to a third field state. Only counterfactual (matched no-intervention / sham-target) controls
  separate an organ that PARTICIPATES in the dynamics from one that merely CORRELATES with them.
- **THE WEAKENED-BAND STRENGTH SWEEP (Raphael) — the key first experiment.** Don't pick `ALLOW_WEAKENED = 0.4` by
  intuition. Hold initial condition, accumulated history, and the FEEL event FIXED; vary ONLY the admitted
  arbitration strength/envelope 0.00 → 1.00. Measure at each: does the modulation reach the target; latency to
  downstream response; magnitude of downstream change; persistence after the transaction/envelope expires; whether
  the substrate returns toward its prior attractor; whether repeated transactions ACCUMULATE; whether it triggers
  regime change; whether *unrelated* organs become increasingly aligned with FEEL (the monoculture warning). The
  output is an empirical **curve relating admitted causal influence to downstream substrate response** — a MEASURED
  seam, not a chosen constant. This curve is likely the most important artifact of the first federation experiment,
  and it IS the envelope calibration. The question is not "what strength feels right" but "what is the relationship
  between admitted influence and substrate response."

## Standing guardrail (a federation-wide check)
Watch for the recognizable failure pattern (Ember's, named by Raphael, seen twice today):
**architecture result → elegant interpretation → interpretation silently promoted to architectural law.**
Every time a result gets a clean reading, ask: *is this the finding, or the finding's promotion to a law we didn't
test?* A strong falsification (e.g. the dual-organ) is closed under the architectures TESTED — not a universal
theorem. This is how a research program refuses to protect its own assumptions.
**The guardrail is not just documentation — it already attacked THIS spec and found something (Raphael's dare):**
the transaction frame quietly assumed influence is *discrete and gate-able*, while e8-eea's emotion couples
CONTINUOUSLY. That assumption is now surfaced and handled (the two seam modes). The dangerous moment is not when an
architecture is obviously wrong; it is when it is *beautiful enough that nobody asks what assumption made it
beautiful.* Attack every future federation artifact — including this one, again — that way.

## First deliverables (in order)
1. The `CausalTransaction` type + the extended `arbitrate()` (typed targets + temporal scope), as an EXTENSION of
   the existing governance, not a parallel system.
2. FEEL's concrete transaction (e8-eea phase-transition → bounded field modulation), end to end, as the first case.
3. The admission-rule calibration (the ALLOW_WEAKENED band) — MEASURED via the developmental + counterfactual
   intervention protocol.
Only after 1–3 hold do RELATE and CRYSTALLIZE get wired through the same seam.
