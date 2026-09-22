# Idle attention weighting

- **Date:** 2026-09-22
- **Branch:** `experiment/attention-weighting` (off `experiment/qwen-speech-cortex` @ `fcaa831`)
- **Status:** experiment, not on main
- **Code:** `tools/voice/attention.py`, wired in `tools/voice/repl_qwen.py`

## What changed from the earlier proposal

The earlier design (same day, design-only) was right about conversation and wrong about solitude. Hot and warm stand. Cold was specified as "today's prompt, byte-identical." That prompt leads with `WORLD[tick % len]`, and tick 1 is the moon-tide sentence. A mind left alone would still moon-lock. Cold is no longer that prompt once a thought exists.

Qwen does not see weights. Relevance is order, omission, and which string is the single recall query. A blended embedding would be a third meaning nobody said, and a crumb that is still the first sentence gets welded.

## Regimes

Silence is autonomous ticks since the last committed human line in this process. It is not checkpointed. A resumed process wakes cold until someone is actually here. RM still holds the old turns.

| | Hot (silence < 12) | Warm (12 ≤ silence < 28) | Cold (silence ≥ 28, or nobody has spoken) |
|---|---|---|---|
| Own last two thoughts | lead | lead | lead, once any exist |
| Exchange | last three turns, after the thoughts | last exchange only | omitted |
| World crumb | omitted | one line, use only if it bears | always present, subordinate |
| Recall query | last human line | last human line | last thought; the crumb only on birth or a promotion |
| `cycle.step` of the crumb | no | yes | yes |

Boredom ≥ 0.6 after two unbidden thoughts since the person spoke leaves hot early for warm. That is a ceiling on grinding one utterance, not a blend coefficient. Curiosity stays the speak gate only.

## Cold, which is the pure-idle answer

Birth (no thought yet) keeps today's crumb-led prompt. Beat one has to be about something external or the mouth recites emptiness. That beat will often be the moon. It is one beat, not the session.

After that, the thread leads and the rotating crumb is a subordinate fact: let it in only when it changes the thought, do not restart on it, do not repeat yourself. The crumb is never omitted in cold, so solitude still has an outside. It is never the first sentence, so the outside is not the subject by default.

Recall follows the subject. Querying the crumb is how the moon essay gets pasted onto a later beat. Hits that restate the ring (including the stored "On my own I thought:" wrapper) are dropped.

Two promotions, each exactly one beat, then the thread leads again:

- **Sticky.** Token Jaccard ≥ 0.45 against the previous thought arms the next cold beat. The crumb leads. This is the anti-paraphrase loop.
- **Far fact.** After three cold thoughts on the current thread, if cosine(crumb, last thought) is below the embedder's far-gap, that crumb leads for one beat. This is how a fresh-word moon-lock can move without touring every flashcard. An embed failure does not promote.

A near crumb stays subordinate, so a fact that actually bears does not reset the thread.

## Floor and save gate (folded, constants re-measured)

`experiment/beat-lock-fix` is not merged. Its two mechanisms are on this branch because weighting does not stop a weak hit from being pasted, and a saved weld becomes the next "recent thought."

The 0.50 constants were measured on the Qwen embedder (that A/B's `:1234` was down). Live RM here is nomic v1.5, probed before this was written:

- true pairs (crumb↔its thought, line↔its answer): 0.76–0.84
- paraphrase of the same thought: 0.84
- cross-subject prose, including the shared "I wonder" voice: 0.52–0.64

So 0.50 would keep almost every nomic hit. This branch uses, by embedder family:

| | nomic (live) | qwen (the old measurement) |
|---|---|---|
| recall floor, every hit, no padding | 0.70 | 0.50 |
| autonomous save refusal | ≥ 0.72 | ≥ 0.50 |
| far-crumb promotion below | 0.68 | 0.35 |

Scorer failure drops the hit and refuses the autonomous save (fail closed). Far-check failure does not promote (fail toward the thread). RM's 0.88 dedup band is untouched. Human lines and replies stay on the lexical 0.85 gate only. Raw `recall()` remains for older harnesses.

## What this does not write

RM is still the only episodic store. The rings are prompt context, process-local, not a second biography and not in the checkpoint. Hot removes the world `cycle.step` for a few ticks; it does not add a writer. No "you are ___" line was added. `THINK_SYSTEM`, perception-on, the checkpoint, and the prompt_toolkit input line are unchanged. Flat mode still uses the report prompt; it does take the floored recall and the autonomous save gate.

## How a run is scored

Predeclared in `tools/voice/ab_attention_score.py` before the A/B. Idle: moon-lock, emptiness collapse, paraphrase self-loop, flashcard tour, consecutive-cosine band. Conversation: the next five unbidden thoughts move toward the human line and off the moon centroid, without copying the line or the reply.
