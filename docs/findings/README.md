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
  and superseded, never silently edited).

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
4. **Findings are dated and append-only.** When a later run overturns an earlier
   one, add a new entry and mark the old one `SUPERSEDED by <file>` at its top.
   Do not delete or rewrite history — the overturning *is* the record.
5. **Record the misreads too.** If we interpreted a result wrong and caught it,
   that correction is itself a finding worth keeping (it stops the next person
   making the same error).

## Format

One file per finding (or per tight cluster), named:

    YYYY-MM-DD-short-slug.md

Each file:

```
# <Title>

- **Date:** YYYY-MM-DD
- **Substrate:** toy | live (Generator-warmed) | sim (which component mocked)
- **Probe:** path/to/diagnostic.py (+ commit if relevant)
- **Status:** active | superseded by <file> | partial / blocked

## Question
What we set out to measure.

## Pre-declared signatures
- SUCCESS looks like: ...
- FAILURE looks like: ...
- CONFOUNDED looks like: ...

## Result
The numbers, with the control.

## Read
What it means — and any misread we caught along the way.

## Open / next
What this leaves unanswered.
```

## Index

| Date | Finding | Status |
|------|---------|--------|
| 2026-06-06 | [Read-side boundary: feedback gates survival, not generation](2026-06-06-read-side-boundary.md) | active |
| 2026-06-06 | [The lock is multi-layered (generator + governance + moat)](2026-06-06-multilayer-lock.md) | active |
| 2026-06-06 | [Frame correction: metastable upstream → coherent field](2026-06-06-frame-correction.md) | active |
