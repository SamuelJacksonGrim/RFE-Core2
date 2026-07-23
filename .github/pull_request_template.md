<!--
TITLE: what shipped, not what you did to ship it.
  yes -> "Reward engine (§5), drifting world + recovery, and the architecture tree"
  no  -> "Merge the phone branch and reconcile the backlogs"
Git operations belong in the body, never the title.
Delete any section below that does not apply. Delete these comments.
-->

Scope in one sentence. Then the diff size: `N files, +X / -Y`.

## 1. <the change>  (`<sha>` if this PR spans several commits)

- `path/to/file.py` (+N) — what it now does
- Real API surface: actual function names, predicates, default constants, so a
  reviewer can grep the diff for what this claims is in it
- **Load-bearing:** what breaks or never works without this. One or two
  sentences. This is the only thing a diff cannot tell the reader.

## Triage <!-- only when this PR reconciles competing or queued work -->

- **kept** — and the forcing function that keeps it
- **deferred** — and why there is no forcing function yet
- **folded** — merged into an existing item rather than standing alone
- **shelved** — decided against, with the argument, so it is not re-litigated

## Honest corrections

- Any earlier claim, summary, or doc line this proves wrong — named as wrong.
- **Any failing check that is intended state**, said plainly, so nobody
  discovers red and has to guess whether the build is broken.

## Verified

Exact commands and their real output. Not "tests pass" — `pytest -q` → **N
passed**. If you did not run it, say what you skipped.
