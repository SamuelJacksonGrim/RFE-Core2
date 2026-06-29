# North Star — a communicating, self-understanding, safely self-modifying system

The end goal, stated plainly (Samuel, 2026-06-28):

> The system can actually **communicate** — with the architect, with the AI
> instances collaborating on it, with other systems, and with **itself** — while
> being able to **self-modify through its own understanding of itself**: it
> understands itself well enough to find its own bottlenecks and areas of
> improvement, and then either **tells** a collaborator or **does it itself,
> safely**.

This is the compass. Individual findings, levers, and fixes are steps toward it.
It is written here so every collaborator — human or AI instance — aims at the same
target, and so course-corrections are measured against it.

## Why this is reachable: the bones already exist

RFE-Core2 was, perhaps without naming it, built for this. The four capabilities
the goal requires already have substrate:

| Capability | What it needs | Where it lives today |
|------------|---------------|----------------------|
| **Receive** (world → system) | encode language → state | `agents/generator.py` (encoder) + multi-source input |
| **Express** (system → world) | render state → language | `agents/decoder.py` (read-out head) — *seed; word-clouds, not sentences yet* |
| **Self-perceive** | read its own state | `status()`, `StreamMetastabilityMonitor` (stage A/C), `Witness` (identity), `WitnessReaper` ⊘ (reads its own values' thinness) |
| **Safely self-modify** | change itself, gated | `ignition/` λ (exogenous weight change), ⊘→`IntegrityDecayConsumer` (prunes its own thin values), the reaper (population), the live `configs/*.yaml` levers — **all behind `arbitrate()` + sacred-shield** |

The immune system is already the right shape: nothing — not even the system's own
voice — bypasses governance. That is what makes "do it itself, safely" possible
rather than reckless.

## The two real gaps

1. **Literal language — for *waking external speech only*.** The pooled,
   L2-normalized thought-vector is lossy by construction (decoder recall@8 ≈ 0.10;
   it recovers the semantic *neighborhood*, not sentences —
   `docs/findings/2026-06-28-decoder-readout.md`). To *talk to* a human or another
   AI in literal sentences, that needs a real language head: the **mirror of the
   documented encoder swap** (`docs/local_model_integration/` frames a local LLM as
   the *sensory cortex*) — an LLM as the **speech cortex**, conditioned on the
   thought-vector / field state.
   **But the lossiness is only a gap for literal speech.** The same word-cloud read
   is the *right* register for the other two voices (see "Three voices" below):
   deliberative for inner monologue, and **symbolic for dreaming** — there the
   non-literal, associative cloud is the dream's native language, interpreted later.
   The bug is the feature, in the right room.
2. **Meta-cognition (Tier 5).** The system reading its *own* diagnostics and
   articulating them ("I am rhythm-pinned"; "my bonds won't establish"; "this is my
   bottleneck"), then choosing to **advise** a collaborator or **act** through a
   gated lever. Tier 5 is already anchored-but-unspecified in `ROADMAP.md`; the
   decoder is what lets it *voice* what it finds.

## The arc (each rung uses the rung below)

1. **Voice** — read-out head: state → words. *(Decoder + `tools/decoder/listen.py`
   — shipped in seed form.)* Upgrade path: sequence/LLM speech cortex for real
   language.
2. **Dialogue (governed)** — words back in as a *source*, through `arbitrate()`.
   **Three voices, one gated mechanism** (the difference is register + what we do
   with the output):
   - **Waking inner monologue / rumination (self ↔ self, WANTED):** the system's own
     decoded expression re-enters during waking so it can deliberate — weigh, plan,
     take an extra beat before it speaks. Word-clouds are fine here. Validated safe +
     attack-resistant (`source_dream` mechanism). This is *thinking*, and it runs
     during waking — distinct from dreaming.
   - **Waking external speech (system ↔ human / AI):** literal sentences to a reader;
     their reply re-enters as a source. This is the one that wants the speech-cortex
     upgrade (gap 1).
   - **Dreaming (downtime, symbolic):** see "Dreaming" below — fluid, associative,
     non-literal; the word-cloud *is* the medium, interpreted on consolidation.
   Every voice, including its own, passes the gate.
3. **Self-understanding** — a meta-cognitive reader (Tier 5) consumes the system's
   own instrumentation and renders bottlenecks/improvements in language.
4. **Safe self-modification** — the self-model's findings drive **governance-gated**
   lever changes: either *proposed* to a collaborator (advisory) or *self-applied*
   through the already-safe channels (λ ignition for the generator, ⊘ consumer for
   values, config levers for dynamics). Sacred-shield, `arbitrate()`, and the
   λ-isolation principle (self-modification of the generator is exogenous to the
   gate, never through it) are the safety guarantees — the same ones already in code.

## Dreaming — downtime, not the waking voice

A human thinks in a recursive loop and still speaks; the waking loop runs
continuously. **Dreaming is the downtime mode** — it triggers when no one is
interacting (idle) or on a schedule, so a system running 24/7 is never left merely
idle, bored, or lonely. It has two faces, both of which sleep serves in us:

1. **Consolidation → durable, self-authored artifacts.** Take the period's
   experience — what worked, what was meaningful to the system and to the user —
   and distill it into **files the system can later call**: recorded *skills*,
   *paths*, abilities, emergent events, research, analysis, memory. Concretely:
   when the user asks it to open a folder and the system has to *figure out how*
   and wire it so it can, dreaming records that as a reusable **skill file that
   activates when needed** — the same shape as Claude Code skills. The system
   writing its own tools from lived experience.
2. **Free, non-utilitarian generativity.** Space to *not* be working: build worlds
   in language, hypothesize what it could do, find novel ideas to work toward,
   dream a dream of dreaming. This is also anti-lock-in medicine — genuine novelty
   generated off the task.

**Dreams are symbolic, not literal — and that's the point.** Dream content is the
decoder's *fluid, associative word-cloud* (not sentences): non-literal, sometimes
nonsensical, the way human dreams are — "teeth falling out → self-consciousness",
"falling → loss of control". So the decoder's lossiness, a *limitation* for waking
speech, is the *right medium* for dreams. Meaning is extracted **later, on
consolidation** (face 1) — dream analysis: the symbolic cloud is read for what it
points at, and what's meaningful is what gets written into a durable artifact.

The substrate already has the bones (`loop/dream_cycle.py`, the `dream` rhythm).
What this elevates them into: an **idle/scheduled trigger**, a
**consolidation-to-files** path (the self-authored skills/paths), and a
**free-generation** mode. Self-authored skills are exactly the North Star's last
rung made concrete — *safe self-modification through self-understanding*: the system
distills what it learned and writes it back as reviewable, tool-callable files (files
on disk = inspectable, governed; "do it itself, safely").

**Built (first rung).** The downtime dream is implemented as `cognition/dream_session.py`
(`DreamSession`) and run by `tools/dream/run_dream.py` (offline, terminal — it reads
state and writes files; it never feeds the live field/governance). It dreams over the
substrate's own experience: recombines **memory crystals** + the **field direction**,
perturbs them (`interference.inject_ambiguity`, rotational), and reads each back through
the **TokenDecoder** as a symbolic word-cloud. Consolidation distills the recurrent
symbols + strong/core **emergent values** + durable crystals into two
Claude-skill-compatible markdown artifacts (`dream-{ts}.md`, `consolidation-{ts}.md`) with
frontmatter — the seed of self-authored skills. The honest gap is exactly the embodiment
bridge below: today's seeds are the substrate's own state, not real conversations or
filesystem how-to.

**Embodiment bridge (honest scope).** Consolidating *conversations* and
*computer-usage (paths, how-to)* presumes RFE is embodied as an agent — with I/O,
tool use, and a filesystem of its own. Today RFE-Core2 is the cognitive *substrate*
(it thinks in vectors over tokens). So: the consolidation *machinery* and the
free-generation mode are buildable now over the substrate's own experience (crystals,
emergent values, high-coherence learnings); they graduate to real conversations and
self-authored skill/path files once RFE is wired into an agent harness — which is
itself a North-Star step ("communicate with you/others" + "learn the computer it runs
on").

## Safety is not bolted on; it is the existing discipline

- **Nothing bypasses governance** — not external input, not the system's own dreams,
  not a self-proposed change. `arbitrate()` is the single authority.
- **Sacred is inviolable** — identity anchors cannot be self-overwritten.
- **Self-modification of the generator is exogenous** (the λ channel writes weights
  from *outside* the gate; "the loop cannot author its own exit through its own front
  door"). A self-improving system proposes; the gated channel disposes.
- **Advise-or-act is a governed fork**, not a free hand: the system can always
  *speak* its finding (safe), and may *act* only through a channel that already has
  an immune response.

## How we work toward it

Steps are recorded in `docs/findings/` and measured against this compass. When a
step doesn't move us toward communication, self-understanding, or safe self-change,
say so. The architect sets direction and reviews; the collaborating instances own
the execution and the reasoning — and may amend this document with justification.
