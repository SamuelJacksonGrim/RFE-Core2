# RFE-Core2 — Findings

Empirical findings from probing the live system. This is the lab notebook: what
we measured, with a control, and what it actually showed — including (especially)
the times the result contradicted what we expected or hoped.

**Start at [`INDEX.md`](INDEX.md)** — one line per finding (verdict + whether it
is still the authoritative read), CI-enforced complete by `verify_docs`. Two
standing conventions live there: resolved Open-items get stamped inline
(`→ DONE (date) — pointer`) in the same commit that resolves them, and raw run
data over ~100 KB is gzipped in place (never committed raw — see §Raw-data
convention).

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
4. **Findings are dated; overturns are recorded, not erased.** When a later run changes
   an earlier finding's status, record the successor and update the old one's status —
   never silently flip a conclusion. **Consolidation is allowed (2026-08-05, architect):**
   once a finding is `superseded` / `resolved` / `historical`, its sprawling body may be
   compressed to a stub — verdict, why it is no longer the live read, successor pointer —
   and any measurement that still stands is carried into the stub. Standing findings keep
   their result + control; trim the prose, never the numbers. The overturn survives; the
   sprawl does not. This is a system record now, not only a lab notebook.
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

The one-line-per-finding map (verdict + current status, CI-enforced complete) lives in
**[`INDEX.md`](INDEX.md)** — the single source. This file holds the **discipline + schema**
only; it no longer maintains a second index (the table that used to live here drifted stale
and incomplete — exactly the duplication INDEX.md exists to prevent).
