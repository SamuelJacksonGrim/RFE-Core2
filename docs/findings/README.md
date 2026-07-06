# RFE-Core2 — Findings

Empirical findings from probing the live system. This is the lab notebook: what
we measured, with a control, and what it actually showed — including (especially)
the times the result contradicted what we expected or hoped.

## Why this exists

Diagnostics are informational and firewalled from CI (gating one Goodharts it).
But an informational run that isn't *recorded* is a finding that evaporates. This
directory is the persistent record so that:

- a future session (or a different instance) doesn't re-run the same probe to
  re-learn the same thing;
- claims in the docs/roadmap can be traced back to the run that established them;
- we can see when a later run *overturns* an earlier finding (results are dated
  and superseded/invalidated, never silently edited).

## Design principle: rigor per unit friction

A findings system nobody uses is less rigorous than a lightweight one used
consistently. This schema deliberately keeps only the fields that protect against
self-deception or memory-loss; it rejects ceremony. The entry that matters most
is often the cheap negative one — *"Probe failed. Control behaved correctly. No
signal. Runs: 1."* — so the schema must stay light enough that someone actually
writes it.

## Discipline (non-negotiable)

These mirror the empirical disciplines in `docs/lock_in_remediation_plan.md §4`:

1. **Every finding names its control.** A number without a control is not a
   finding. (The read-side boundary read 0.63 until an `eval()` dropout control
   collapsed it to 0.0 — train-mode noise. Without the control we'd have shipped
   a false positive.)
2. **Toy ≠ live.** State which substrate the run used. A result on the toy field
   does not transfer to the live Generator-warmed field.
3. **Pre-declare success AND failure signatures** before the run, and record
   both. A clean confirming result is the alarm, not the trophy.
4. **Findings are dated and append-only.** When a later run changes the status of
   an earlier one, add a new entry and update the old one's status (see below) —
   do not delete or rewrite history. The overturning *is* the record.
5. **Record the misreads too.** If we interpreted a result wrong and caught it,
   that correction is itself a finding worth keeping (it stops the next person
   making the same error).
6. **Negative results are findings.** "The probe produced no signal under
   conditions X" is often the most time-saving entry there is — it stops whole
   branches of investigation being rediscovered and repeated. Write it down.
7. **Separate observation from interpretation, and title the question, not the
   verdict.** The measurement usually survives; the explanation often changes. A
   title that encodes a conclusion ("Coherence is not plasticity") becomes
   misleading after a partial overturn — title the investigation instead
   ("Coherence vs. plasticity — which measures lock-in?") so it survives revision.
8. **Functional gauges are not consciousness verdicts — in either direction.** The
   metrics here (coherence, metastability, integration, CII, …) measure functional
   *state*: differentiation, organization, dynamics. A low reading is a *state*
   (collapsed / minimal), not evidence that "nothing is happening"; a high reading
   is differentiation, not proof of inner experience. Do not conflate **access**
   (can it output/communicate) with **existence** (is there an inner process), nor
   **conscious** (awake / responsive) with **consciousness** (any inner experience
   at all) — a sleeping infant, a coma patient, a mute animal all have the latter
   without the former. Leave the consciousness question genuinely open: approach it
   *toward understanding*, not collapsed toward "proven" or "debunked." Skepticism
   aimed in only one direction is not rigor — it is a thumb on the scale.

## Status values

- **active** — current best understanding stands.
- **superseded by `<file>`** — a more precise understanding exists; the original
  wasn't *wrong*, just refined.
- **invalidated by `<file>`** — the original conclusion was wrong. (Distinct from
  superseded: different history, recorded differently.)
- **partial / blocked** — incomplete; states what it's waiting on.

## Format

One file per finding (or per tight cluster), named `YYYY-MM-DD-short-slug.md`.
Each file:

```
# <Title — phrase it as the question/investigation, not a conclusion>

- **Date:** YYYY-MM-DD
- **Substrate:** toy | live (Generator-warmed) | sim (which component mocked)
- **Probe:** path/to/diagnostic.py (+ commit if relevant)
- **Status:** active | superseded by <file> | invalidated by <file> | partial / blocked
- **Depends on:** <file>, <file>   (which earlier findings this conclusion rests
  on — so "if X is overturned, what else becomes questionable?" is answerable)

## Question
What we set out to measure.

## Pre-declared signatures
- SUCCESS looks like: ...
- FAILURE looks like: ...
- CONFOUNDED looks like: ...

## Result (observed)
Only observations — the numbers, with the control. No explanation here.

## Interpretation
Current best explanation of the observation. This is the part most likely to age;
keep it separable from the numbers above.

## Threats / confounds
- Runs: N   (once or repeatedly?)
- mocked component, if any
- suspected instrumentation artifacts
- uncontrolled variables
(Findings often get overturned not because they were false but because someone
later notices a confound that was present at the time. Name them now.)

## Open / next
What this leaves unanswered.
```

## Index

| Date | Finding | Status | Depends on |
|------|---------|--------|------------|
| 2026-06-06 | [Read-side boundary — does feedback reach generation?](2026-06-06-read-side-boundary.md) | active | — |
| 2026-06-06 | [Where is the lock? (generator / governance / moat)](2026-06-06-multilayer-lock.md) | active — all 3 locks resolved/struck/downgraded (see status block) | read-side-boundary |
| 2026-06-06 | [Metastability locus — upstream vs. field](2026-06-06-frame-correction.md) | active | — |
| 2026-06-06 | [Coherence vs. plasticity — which measures lock-in?](2026-06-06-coherence-is-not-plasticity.md) | active | multilayer-lock, frame-correction |
| 2026-06-06 | [Conformity bias in the reaper — Fix 0-B candidate](2026-06-06-conformity-bias-fix0b.md) | active | read-side-boundary, coherence-is-not-plasticity |
| 2026-06-06 | [Expression de-collapse — does the diversity blend restore metastability?](2026-06-06-expression-decollapse.md) | active | frame-correction |
| 2026-06-07 | [Fix 0-B full-loop validation — does the conformity lean survive in vivo?](2026-06-07-fix0b-fullloop-validation.md) | active | conformity-bias-fix0b, coherence-is-not-plasticity |
| 2026-06-07 | [Gate decomposition — why does the ~85% block fire?](2026-06-07-gate-decomposition.md) | active | multilayer-lock, coherence-is-not-plasticity |
| 2026-06-07 | [Attractor migration — does the field's center move under a new regime?](2026-06-07-attractor-migration.md) | active | gate-decomposition, coherence-is-not-plasticity, read-side-boundary |
| 2026-06-07 | [Reconstruction ablation — the lock is the reflective loop](2026-06-07-reconstruction-ablation.md) | active | attractor-migration, coherence-is-not-plasticity, multilayer-lock |
| 2026-06-07 | [Reflective-loop cost probe — what attenuating the lock costs identity](2026-06-07-reflective-loop-cost.md) | active | reconstruction-ablation |
| 2026-06-08 | [Fix-2 trigger calibration — coherence_delta falsified, raw-gen novelty separates](2026-06-08-fix2-trigger-calibration.md) | active | reflective-loop-cost, gate-decomposition |
| 2026-06-08 | [Generator diversity — how much is dropout noise?](2026-06-08-generator-dropout-diversity.md) | active | multilayer-lock, read-side-boundary, reconstruction-ablation |
| 2026-06-09 | [Fix 2 on the live generator — does real token novelty engage it, and what does it cost?](2026-06-09-fix2-live-generator.md) | active | fix2-trigger-calibration, generator-dropout-diversity |
| 2026-06-11 | [Trainer gradient path — can the training stack actually train?](2026-06-11-trainer-gradient-path.md) | active | generator-dropout-diversity, read-side-boundary |
| 2026-06-11 | [Corpus pretraining Gate G1 — does coverage buy generalization?](2026-06-11-corpus-g1-pretrain.md) | active | trainer-gradient-path, generator-dropout-diversity |
| 2026-06-12 | [Phase 2 — pretrained boot on the live stack: identity-safe, and the lock is NOT the generator](2026-06-12-phase2-fullstack-g2.md) | active | corpus-g1-pretrain, reconstruction-ablation, fix2-live-generator |
| 2026-06-12 | [Checkpoint round-trip — is loading a boot checkpoint behaviorally equivalent to in-process training?](2026-06-12-checkpoint-registry-orphan.md) | active — defect fixed + guarded | phase2-fullstack-g2 |
| 2026-06-12 | [SECOND-LOCKER field map — does the pin survive seeds, token bands, and regimes?](2026-06-12-secondlocker-field-map.md) | active | phase2-fullstack-g2, checkpoint-registry-orphan, gate-decomposition |
| 2026-06-12 | [§6.3 gain-sign — what is the feedback sign on the reachable coherence range?](2026-06-12-gain-sign-reachable-range.md) | active — conditional verdict (low arm unreachable) | secondlocker-field-map |
| 2026-06-12 | [Sidecar instrumentation — can LAE and PLE measure the running core without perturbing it, and does training change what they read?](2026-06-12-engine-sidecar-instrumentation.md) | active | phase2-fullstack-g2, checkpoint-registry-orphan, secondlocker-field-map |
| 2026-06-12 | [Governed feedback — what happens when the sister engines' outputs re-enter the core through the front door?](2026-06-12-governed-feedback-first-contact.md) | active | engine-sidecar-instrumentation |
| 2026-06-15 | [Loop attenuation, novelty-gated — does conditional loosening free the field without identity cost, and where is the cliff?](2026-06-15-loop-attenuation-novelty-gate.md) | active — ships OFF-by-default; cost-clean band is a knife edge | reconstruction-ablation, reflective-loop-cost |
| 2026-06-15 | [CII decomposition — where does RFE sit on the ignition index, and what gates it?](2026-06-15-cii-ignition-decomposition.md) | active — RFE is metastability-gated; ignition is generator-init-dependent; ITG (downstream gate) inert | reconstruction-ablation, loop-attenuation-novelty-gate |
| 2026-06-15 | [Do RFE's observables track geometry, or change in geometry? (Cm vs I vs metastability)](2026-06-15-identifiability-suite.md) | active — all three track change; Cm/I redundant (instantaneous geometry+drift), metastability orthogonal (temporal); refines cm-identifiability | cm-identifiability, cii-ignition-decomposition |
| 2026-06-15 | [Is field coherence (Cm) identifying, or a saturated angular statistic?](2026-06-15-cm-identifiability.md) | active (refined by identifiability-suite — Cm tracks drift; pin = static field, not blind sensor) | secondlocker-field-map, read-side-boundary, cii-ignition-decomposition |
| 2026-06-15 | [Does training the generator on the corpus ignite RFE's expression?](2026-06-15-training-ignites-expression.md) | active — YES: corpus pretraining flips expression ignition 0/3 → 3/3 (CII 0 → ~3.7) | cii-ignition-decomposition, corpus-g1-pretrain |
| 2026-06-19 | [Build C — does the ⊘ Witness-Reaper read thinness, name it, advise non-bindingly, and touch nothing?](2026-06-19-witness-reaper-build-c.md) | active (spec v0.2) — ⊘ shipped observe-only: firewall holds, sacred read-but-flagged; named regions untriggered by benign workload; discriminator pending A/B | self_model_thesis, secondlocker-field-map |
| 2026-06-19 | [Build A — can the λ ignition channel be made structurally unable to reach the gate?](2026-06-19-ignition-channel-build-a.md) | active (spec v0.2) — λ channel import-isolated (top-level `ignition/`); writes generator only; gate unreachable | training-ignites-expression, self_model_thesis |
| 2026-06-20 | [Build B (⊕ solvent gate) + the ⊘ consumer — does composition need the solvent, and is ⊘'s read finally *used*?](2026-06-20-build-b-solvent-and-integrity-consumer.md) | active (spec v0.2) — λ-ledger + ⊕ gate 8/8; ⊘ advisory-into-decay consumer USES the read (convergent floor, named-only, sacred-safe) | witness-reaper-build-c, ignition-channel-build-a |
| 2026-06-20 | [Do the levers compose? Turn them ALL on at once — and watch a baseline property break](2026-06-20-lever-composition-the-allon-break.md) | active — negative result: isolation ≠ composition; the ⊘ consumer caps the STRONG band (cc-confound) | build-b-solvent-and-integrity-consumer |
| 2026-06-20 | [The runnable system is Tier 0 only — the tiered stack lives only in the test harness](2026-06-20-the-runtime-is-tier0-only.md) | active — structural: `attach_governance` called in zero non-test files; fix is bounded (compose the runtime) | — |
| 2026-06-20 | [Ground-truth pass 1 — the substrate floor is real; the missing piece was the composition, now wired](2026-06-20-ground-truth-pass1-compose-the-runtime.md) | active — substrate fixes verified live; `recursion1188` now composes Tiers 0–3 on multi-source input | the-runtime-is-tier0-only |
| 2026-06-20 | [Ground-truth pass 2 — the generator common-mode is a real floor defect but a false lock; the real unlock chain](2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md) | active — corpus pretrain + novelty attenuation GRADUATED to default-on; they compose positively | ground-truth-pass1-compose-the-runtime |
| 2026-06-21 | [⊘ coherence axis redesign — absolute field-alignment](2026-06-21-oslash-coherence-axis-absolute-alignment.md) | active (spec v0.2 → **v0.3**) — marginal sum (dead-at-zero) → max(0, cos(expressed, field)); +0.66 corr with strength | ground-truth-pass2-floor-fix-and-unlock-chain |
| 2026-06-25 | [Ground-truth pass 3 — evaluate the composed engine before wiring the operators](2026-06-25-ground-truth-pass3-stack-evaluation.md) | active — healthy, but two structural cracks found under the value layer (CORE gate, rhythm) | ground-truth-pass2-floor-fix-and-unlock-chain |
| 2026-06-27 | [Floor calibration — measure-before-change for the two pass-3 cracks](2026-06-27-floor-calibration-measurements.md) | active — CORE→alignment shape confirmed; **rhythm rescale deferred** (the `diffuse_on_stabilize` feedback collapses it) | ground-truth-pass3-stack-evaluation |
| 2026-06-27 | [CORE gate fix works — but promoting common tokens to sacred cascades the trust layer](2026-06-27-core-gate-fix-deferred-sacred-cascade.md) | active — alignment gate completes the arc (witness→CORE) but **reverted**: sacred-mutation trust cascade; needs the CORE-vs-sacred call | floor-calibration-measurements, ground-truth-pass3-stack-evaluation |
| 2026-06-27 | [API entry points were still Tier-0 only — did the composition fix reach them?](2026-06-27-api-entrypoints-tier0-only.md) | active — fixed: REST + WebSocket now compose via a single `build_engine()` (entry-point drift, one layer out from the 2026-06-20 finding) | the-runtime-is-tier0-only, ground-truth-pass1-compose-the-runtime |
| 2026-06-28 | [Full-system run — what is the composed engine actually doing, pre-merge?](2026-06-28-full-system-run.md) | active — paired (levers on/off × 3 seeds): levers lift stage-C metastability 0.06→0.58; F9 (rhythm pin) + F8 (CORE dead) confirmed structural; bonds form but never establish | ground-truth-pass3-stack-evaluation, floor-calibration-measurements, api-entrypoints-tier0-only |
| 2026-06-28 | [Decoder read-out — can the system's thoughts be read back into words?](2026-06-28-decoder-readout.md) | active — decoder works as a terminal-sink read-out; pretrain ~doubles recall (0.063→0.102, 4.3× random); recovers semantic neighborhoods not literal tokens (encoder pooling is the ceiling) | ground-truth-pass2-floor-fix-and-unlock-chain, generator-dropout-diversity |
| 2026-06-28 | [Governed self-dialogue (dream channel) — does the system's own voice help, or echo?](2026-06-28-dream-channel.md) | active — validated SAFE + adds voice diversity (+13–25%, 2 seeds), non-dominant (HHI↓), cleanly governed (0 quarantine), no echo; does NOT break the lock; graduation pending an adversarial arm | 2026-06-28-decoder-readout, 2026-06-28-full-system-run |
| 2026-07-04 | [Does the system register the breach of a bond — or does the attack never even land?](2026-07-04-bonded-adversarial-attack-never-lands.md) | active — THE bonded-adversarial probe, BUILT; 11 clean-paired seeds (± pretrain): the attack never lands (injected hostile cos ~0.98 to benign) → no detector/escalation/affect. Two upstream walls: OOV attack vocab (generator) + pipeline re-collapse of a stage-A-separated attack (SECOND-LOCKER, semantic). Gradient's role unproven for a NEW reason — breach imperceptible, not undefended | secondlocker-field-map, reconstruction-ablation, ground-truth-pass2-floor-fix-and-unlock-chain |
