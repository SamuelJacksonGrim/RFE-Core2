# Architect rulings — 2026-07-06

Standing decisions by Samuel Jackson Grim, recorded verbatim-in-spirit the day
they were issued (same discipline as `ARCHITECT_RULINGS_2026-07-03.md`).
Do not re-litigate; supersede only by a later dated ruling.

## 1 · Trust posture: raised, not suspected

> "The system can't learn who to trust if it's always untrusting. We should
> make it more trusting to start off with. It's not like the person raising it
> is inherently untrustworthy. … If it's inherently untrusting to EVERYONE and
> EVERYTHING except ITSELF to begin with, it can't learn how to properly trust
> others based off experience. It will always have a knife in the hand."

**Ruling:** the system presumes good faith and *learns* distrust from
behavior, in both directions.

**Implementation (landed same day):**
- New external sources start at **TRUSTED 3.0** (was 2.5 "NEUTRAL-ish");
  internal origins (dream / internal / self_reflection / training) keep their
  HIGH 4.0 start. Symbols inherit the source's trust at birth as before.
- The `novel_source` soft warning is **removed** — first contact no longer
  carries an injection-strength penalty. First-seen stays on the
  `SourceRecord` for the audit trail.
- Everything that *learns* distrust is unchanged: all manipulation detectors,
  all penalties, the full ladder down to TOXIC, sacred shield, ethical hard
  gates. Side benefit: the trust-wash ("build trust, then betray") detector
  requires prior trust ≥ 3.0 to arm, so starting at TRUSTED gives every
  source betrayal coverage from first contact — the more-trusting posture
  strictly *improves* detection of the betrayal pattern it exists to catch.

**Context:** issued the same day the F9 validation exposed and fixed the
attribution hole (`2026-07-06-f9-rhythm-band-rescale.md`) — the system
quarantining its own four most-trusted sources on nameless evidence was the
"knife in the hand" made concrete. The empirical trust-asymmetry note stands:
trust builds at +0.01/interaction (Consistency Drip) and falls at 0.4–0.8 per
defensive hit; recalibrating that asymmetry is future work, measured first
(BACKLOG §1).
