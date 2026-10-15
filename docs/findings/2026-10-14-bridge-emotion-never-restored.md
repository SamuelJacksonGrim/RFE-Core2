# The speech bridge never restored emotion across a restart (ported fix)

**Date:** 2026-10-14 · **Status:** resolved (same commit) · **Found by:** Grok's architecture read in Rubedo,
confirmed and fixed by Ember; port approved by Samuel (with GPT/Raphael's review).

## Question
Does the live speech bridge (`tools/voice/repl_qwen.py`) carry the emotional state across a restart?

## Control
1. Read-only check on the unmodified live tree: 40 real steps (all six scalars move), `save_checkpoint`, fresh
   stack, `load_checkpoint`, compare.
2. Same check after the port, plus the regression test `tests/smoke/emotion_checkpoint_roundtrip.py`.
3. Backward compatibility: load a **copy** of the real bridge checkpoint
   (`~/.rfe-speech-cortex/substrate-checkpoint.json`, saved 2026-09-22) with the ported loader; original hash
   checked unchanged.

## Result
- **Live code before the port: emotion lost.** Before save: curiosity 0.736, wonder 0.562, joy 0.781, tension
  0.416, boredom 0.118, stability 0.158. After load: 0.3 / 0.2 / 0.5 / 0.1 / 0.0 / 0.7, the newborn defaults.
  Cause: the checkpoint saved only `arousal` and `valence`, which are read-only properties derived from the six
  scalars; the loader's assignment raised inside a swallowed `except`, so `"emotion"` never restored and the six
  scalars were never saved at all.
- **After the port: emotion restored exactly** (all six to 3 decimals; arousal/valence recompute identically).
  `EmotionalGradient.snapshot()` / `restore()` persist the six scalars + step; arousal/valence still go into the
  file as a record of the affective position at save time and are ignored on load. The invariant that
  arousal/valence are never stored state is untouched.
- **Old checkpoints fail cleanly into today's behavior.** The real 2026-09-22 checkpoint (emotion block
  `{arousal 0.532, valence 0.397, step 9}`) restores step, field, values and registry; its emotion is refused
  without touching state, so emotion starts at the defaults exactly as it did before the fix. From the first save
  after this commit on, emotion carries over.
- Live gate: `run_all_tests.sh` 20/20 including the new regression test. Diff = the two code edits (31 + 9 lines),
  the test, and its two registrations; identical to the Rubedo commit `cfc0995`.

## Scope note
This restores the emotional state the system actually represents. It is an engineering fix to persistence and
makes no claim about experience either way.

## Open items
- The bridge checkpoint still omits bonds, trust, crystals, attractors and the temporal stream (Rubedo
  ARCHITECTURE.md § Speech-cortex bridge, FLOW.md state inventory).
