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
