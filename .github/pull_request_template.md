<!--
RFE-Core2 PRs are experiment reports, not change descriptions. The house style is
measure-first: declare the criteria, run the control, keep the failures on record.

TITLE: what shipped, not what you did to ship it. Findings/§ numbers welcome.
Git operations belong in the body, never the title.
Delete every section that does not apply. Delete these comments.
-->

## What

What this is, where it sits (plan section, BACKLOG entry, the finding it
answers), and whether levers are opt-in or default-ON — with the config key and
how to opt out.

## Root cause <!-- fixes -->

Not "X was broken." When the defect entered, what the earlier code established
that the failing path never mirrored, and why nothing caught it until now. If a
second, quieter failure was hiding beneath the crash, say so — that one is
usually worth more than the crash.

## What's built / The fix

- `path/to/file.py` — real API surface: function names, predicates, default
  constants, so a reviewer can grep the diff for what this claims is in it.
- Equations or update rules inline where the change is mathematical.
- **Rejected alternatives, with the argument.** The fix *not* taken and why —
  precedence it would invert, failure it would mask, gate it would bypass. This
  is what stops the same debate reopening in three weeks.
- Constants ratified under architect delegation: say so, with the date.

## Deviations from the brief <!-- when implementing an architect brief -->

Where the implementation departs from what was asked, and why — a premise
already fixed, a signal named in the brief that is structurally dead, a
placement that had to move to where the evidence actually arrives.

## Test (red → green)

The test must fail on pre-fix code. Name the exact failure it produces there,
then the count after. `tests/...`, wired into `run_all_tests.sh`.

## Validation

- **Pre-declared PASS/FAIL signatures**, and how many held: N/N. Declare bands
  two-sided where a metric can fail by being dead *or* by taking over.
- **Paired control / attribution arm.** Run the control even when you wrote the
  code that morning. If a row fails, prove whether it fails in *both* arms
  before blaming the new lever.
- **Recorded metric corrections.** A criterion you had to re-declare stays
  visible — in the probe docstring and the finding — with the original failure
  on record. Never quietly re-declare and report green.
- Byte-parity on the off-path for opt-in levers.

## Found along the way <!-- the bigger fish -->

Discoveries incidental to this PR that matter more than this PR: coverage that
never ran, an organ dormant at harness scale, a gate measuring the wrong thing.
File in BACKLOG and say so here.

## Honest corrections

Any earlier claim, summary, or doc line this proves wrong — named as wrong, with
the correct version. Any failing check that is **intended state**, said plainly,
so nobody discovers red and has to guess whether the build is broken.

## Status & follow-ups

What stays opt-in pending which gate. What is filed in BACKLOG §N. Anything
where architect override is welcome.

## Merge notes <!-- when it matters -->

Squash recommendation if an intermediate commit is red in isolation; anything a
merger needs that the diff won't say.

---

Finding: `docs/findings/YYYY-MM-DD-slug.md` (+ INDEX row).
Suite **N/N**, doc-accuracy **19/19**.
