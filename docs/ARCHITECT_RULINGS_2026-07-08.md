# Architect rulings — 2026-07-08

Standing decisions by the architect, recorded the day they were issued (same
discipline as the 2026-07-03 and 2026-07-06 rulings). Do not re-litigate;
supersede only by a later dated ruling.

## 1 · Decision process: explain, then ask

> "No assumptions, no blanket delegations, and every choice brought to me
> fully contextualized."

**Ruling:** technical and architectural design decisions are **discussed, not
delegated** — and never decided unilaterally by an implementing instance.
The instance brings each decision point to the architect as a
**self-contained, plain-terms brief**: what the choice is, what it affects,
the options with their trade-offs, and the instance's recommendation —
written for a reader who has *not* been following the working thread. No
unexplained shorthand, no references to earlier context assumed remembered
("the stub from earlier" is the named failure mode). The instance supplies
the analysis that makes the question answerable; the architect decides.

Routine implementation details need no ceremony. Anything that changes the
system's character, an architectural invariant, or contract-doc text does.

## 2 · Chambered governance — ADOPTED

Origin: the architect's question "should we really only have ONE governance
gate?", resolved through the §1 process the same day it was codified.

**Decision (architect):** keep the **single audit point** — one
`arbitrate()`, no second gate, no bypass path; multiple independent gates
introduce blind spots in the gaps between them, and the single-chokepoint
invariant (CLAUDE.md §Authority hierarchy) is unchanged. But the system
cannot operate effectively while treating its own internal dialogue like a
hostile external threat: extend the existing per-origin pattern (flood
ceilings already differ across user / api / internal) into per-channel
**calibration profiles** covering manipulation-severity sensitivity and
trust learning rates. Stop the self-throttling.

**Binding constraint — calibrate per channel, never exempt:** chambers may
differ only in *calibration* (thresholds tuned to each channel's measured
benign distribution), never in *structure* — same detectors, same severity
rungs, same sacred shield, same ladder to TOXIC for every channel. In
particular, `source_dream`'s chamber is **never more permissive than the
external chamber on manipulation checks**: the dream channel's validated
containment (non-dominant, adversarial-gated, no privileged path) stays
intact.

**Measured-first:** no chamber constant is set by feel. Each channel's benign
distribution is measured before its thresholds move (the F9 harness data
already covers dream-band benign traffic; attack-side separation waits on
the F3 Wall-1 in-corpus-hostile-vocabulary arm). Implementation is not a
separate build — it is the *form* the two queued fixes take when their
measurements land: the identity_erosion recalibration and the trust
learning-rate asymmetry probe (BACKLOG §1).
