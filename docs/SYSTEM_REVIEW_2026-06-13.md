# RFE-Core2 — Full System Review

**Date:** 2026-06-13
**Scope:** definitive answer to three questions — *what can the system do*, *what
it truly is*, and *what happens if you wire a local 20B–70B LLM in where
`generator.py` currently sits.*
**Method:** end-to-end read of the live source (`agents/`, `loop/`,
`substrate/`, `cognition/`, `training/`, `api/`), the README, the ROADMAP, and
the lock-in findings ledger. Every claim below is grounded in code, not in the
prose docs. Where the prose and the code disagree, the code wins and I say so.

This is a companion to `docs/local_model_integration/`, which carries the
how-to. This file is the *what* and the *why*.

---

## 1. The one thing you have to understand first

**`Generator` is an encoder, not a text generator.** Its name is the single
most misleading thing in the repository.

`Generator.generate(tokens: List[str]) -> np.ndarray` takes a list of string
tokens and returns **one** `dim`-dimensional vector (default `dim=128`),
L2-normalized to the unit sphere (`agents/generator.py:315-339`, `forward()` at
`:284-309`). There is:

- no decoder,
- no language-model head / logits over a vocabulary,
- no sampling, no detokenizer,
- no place in the entire codebase where text comes *out*.

`forward()` is: embed token addresses → scale by `√d_model` → add sinusoidal
positional encoding → `TransformerEncoder` (4 Pre-LN layers) → masked mean-pool →
LayerNorm → MLP projection → LayerNorm → L2-normalize. It is a sentence encoder
that maps a token sequence to a point on the unit hypersphere. That's the whole
job.

Everything else in RFE-Core2 is a **dynamical system that lives on those
vectors.** The "cognition" is not in the encoder; it's in what the field,
watcher, witness, emotion, governance, and value engine *do* to and around the
stream of unit vectors. The encoder is the sensory transducer. The organism is
the loop.

This reframes the user's question completely. "Wiring in GPT-OSS-20B" does **not**
turn RFE-Core2 into a 20B chatbot. It swaps the sensory cortex. More on that in §6.

---

## 2. What the system *is*

RFE-Core2 is a **persistent latent-space dynamical cognition substrate**. One
heartbeat — `AutonomousCycle.step(tokens, source_id, origin_type)`
(`loop/autonomous_cycle.py:280`) — runs ~22 ordered phases per tick. Input is a
token list; output is a `StepState` plus a large bundle of evolving internal
state. It is designed to run **continuously and unboundedly**, not as a
request/response model.

The substrate is real and non-trivial. Reading the code (not the README), these
subsystems exist and are wired:

- **ResonanceField** (`substrate/resonance_field.py`) — an accumulating field
  with `tanh` saturation + exponential decay (`decay≈0.995`), FFT-based spectral
  decomposition, `phase_coherence`, and energy-band rhythm detection
  (stabilize / dream / reflect / explore). It is genuinely stateful: every
  injection changes what the next injection sees. This is the system's working
  memory and its clock-of-mood.
- **Watcher** (`agents/watcher.py`) — three-layer coherence
  (geometric × temporal × field-resonance), and crucially it measures the
  *marginal* effect of a vector on whole-field coherence, not just local
  alignment.
- **Witness** (`agents/witness.py`) — multi-timescale EMA identity anchors
  (short/mid/long) + `anchor_velocity`, `anchor_short_long_gap` for drift
  detection.
- **EmotionalGradient** (`cognition/emotional_gradient.py`) — six EMA scalars
  (curiosity/wonder/joy/tension/boredom/stability) that are not decoration: they
  directly scale `field_gain`, `mutation_scale`, `decay_rate`, `attractor_pull`,
  `crystal_pressure`, `dream_pressure` every step. `arousal`/`valence` are
  derived read-only properties.
- **Governance stack (Tiers 1–2)** — `SelfhoodGovernance` is the single
  arbiter; `TrustLedger`, `EthicalBoundarySystem`, `DependencyMonitor` (HHI
  source-concentration), `RelationalBondManager` (emergent bonds), and
  `ManipulationResistanceEngine` (5 detectors) only *report*. Decisions gate
  field injection. Sacred symbols are inviolable.
- **ValueEmergenceEngine (Tier 3)** — values grow from the governance feedback
  stream; CORE promotion is a governance-gated handshake to sacred status.
- **TemporalStream (Tier 4)** — subjective time with affective dilation +
  rhythm coupling. A terminal sink: it reads emotion/field, never feeds back.
- **Symbolic ecology** (`agents/symbolic_memory.py`) — the half of "the
  generator" that is *not* a neural net: a canonicalization pipeline, permanent
  `stable_id`s, a disposable/compactable `AddressSpace`, and a decay→reaper→
  archive→graveyard lifecycle. Symbols earn longevity through use. This is where
  the system's "identity of concepts" lives, and governance keys off its
  `stable_id`s.

**What this adds up to:** a self-modulating organism with selfhood-protection,
relational dynamics, manipulation resistance, emergent values, and a sense of
subjective time — all operating in a 128-dimensional vector space, all closing
through three feedback loops (the field loop, the ecology signal-relay loop, and
the governance feedback loop; README §"The three feedback loops"). It is a
serious and unusual piece of cognitive-architecture engineering.

---

## 3. What the system can *do* (honest capabilities)

It **can**:

1. **Ingest a continuous token stream and maintain evolving internal state** —
   coherence, rhythm, emotion, identity anchors, subjective time — that is a
   genuine function of history, not a stateless mapping.
2. **Route its own behavior by cognitive rhythm** — consolidate, dream, reflect,
   or explore based on its own field energy, with a "boredom with teeth"
   self-perturbation that forces exploration out of stillness.
3. **Govern its own identity** — accept, weaken, monitor, quarantine, or reject
   injections; shield sacred constants absolutely; quarantine flooding or toxic
   sources; respond proportionally to compound manipulation severity.
4. **Form relational bonds and track dependency** — bonds emerge from sustained
   coherent interaction; HHI flags over-concentration on one source.
5. **Grow values from experience** and promote them to inviolable CORE status
   through a multi-criterion governance handshake — no pre-seeded value list.
6. **Consolidate offline** — a deep `DreamCycle` does REM-like consolidation,
   abstraction, and identity stabilization with no external input.
7. **Persist and reload** identity (ecology + values + sacred state), with an
   in-place load that keeps attached subsystems from being orphaned.
8. **Expose all of this** over a FastAPI REST surface and a WebSocket stream,
   and visualize the field/topology.

It **cannot** (today, by design — these are not bugs):

1. **Produce language or any human-readable output.** There is no decode path.
   The API returns vectors and metrics. RFE-Core2 *feels and judges and
   remembers*; it does not *speak*.
2. **Reason over the *content* of its inputs in a learned, semantic way.** The
   stock encoder is a tiny 4-layer transformer that, untrained, presents
   **low-rank** input (effective rank ≈1.6 at dim 64 — `ROADMAP.md`,
   `docs/findings/2026-06-08-generator-dropout-diversity.md`). It distinguishes
   token *sequences* geometrically, but it has no world knowledge and no real
   semantics until trained, and the curated training corpus is only ~272 tokens.
3. **Escape its central, documented pathology on its own:** survival is
   currencied largely in coherence, the reaper selects for agreement, and the
   live field pins to ~0.998 internal coherence — a collapsed, monocultural
   "lock-in" rather than a healthy metastable state (`ROADMAP.md` "Survival-by-
   coherence → field lock-in"; `docs/ARCHITECTURE_ANALYSIS.md`). The team has
   traced the lock to the reflective loop's unconditional convergence and has a
   remediation arc in flight; the **binding upstream constraint is generator
   input diversity.** Hold that thought — it's the hinge of §6.

---

## 4. What it truly is, stated plainly

Strip the metaphors and it is this: **a stateful, self-regulating controller for
a point moving on a 128-dimensional unit sphere, with an unusually rich
immune/identity/affect layer wrapped around the motion.** The poetry in the docs
("organism", "selfhood", "values") maps onto real, inspectable mechanisms —
those words are earned by code, not sprinkled on top. But two honest caveats:

- The "intelligence" is *architectural*, not *learned*. There is almost no
  trained knowledge in the system. Its sophistication is in the dynamics and the
  governance, not in what it understands about any input.
- Its current measured operating point is a **locked, monocultural field**. The
  whole `docs/findings/` ledger is the lab notebook of a team that knows this and
  is trying to engineer metastability back in. The honest one-line status: *a
  beautifully instrumented dynamical-cognition substrate that is currently
  starved of input diversity and therefore runs in a collapsed regime.*

That last sentence is exactly why the local-LLM question is the right question to
be asking.

---

## 5. The exact contract a replacement must satisfy

Anything that replaces `Generator` is consumed by the rest of the system through
a wider surface than just `generate()`. I traced every call site
(`grep generator\.` across the tree). A drop-in must provide all of:

| Surface | Used by | Contract |
|---|---|---|
| `generate(tokens, token_class) -> np.ndarray (dim,)` | cycle `_generate`, Chorus (6×/step), reflective loop, dreamer, attractor.pull, API, probes | unit-norm vector; **must vary with `token_class`** for Chorus agent differentiation |
| `encode_batch(token_lists, token_class) -> np.ndarray (n,dim)` | trainers, API | right-padded batch encode |
| `forward(ids) -> Tensor` (grad-enabled) | `training/encode.py:encode_grad` | autograd path for training a loss |
| `.registry` (`SymbolRegistry`) | governance, trust, value engine, bonds, cycle | `register`, `stable_ids_for_tokens`, `get_by_stable_id`, `update_*`, decay/compaction — **this is load-bearing for Tiers 1–3** |
| `.signal_attractor/crystal/coherence/centrality(tokens, …)` | attractor, crystals, watcher relay, lattice/binding | feed ecology so significant symbols decay slower |
| `.maintenance_step()` | cycle (cadence), API | decay/reap/compaction heartbeat |
| `.embedding.weight[address]` | `value_emergence._compute_tension` (`:484`) | per-symbol vector lookup by address |
| `.dim`, `.device`, `.parameters()`, `.train()/.eval()/.training` | trainers, cycle, probes | nn.Module-shaped |
| `.ecology_stats()`, `.status()`, `.save_checkpoint/.load_checkpoint` | API, persistence | diagnostics + persistence |

**Key consequence:** you cannot simply delete `generator.py` and call a model
server. The **symbolic ecology and `stable_id`s are co-equal to the neural net**
and are wired into every higher tier. The correct move is to keep the registry
and wrap the LLM as the vector-producing backend behind the same surface. This
is spelled out in `docs/local_model_integration/`.

---

## 6. What happens if you wire in GPT-OSS-20B / Gemma-3-27B / Llama-3.1-70B

Short version: **it is the maximal, most direct version of the "raise generator
diversity" lever the entire lock-in remediation arc has been circling — and it is
architecturally feasible without touching Tiers 1–4, but it is not free and it
does not, by itself, give the system a voice.**

### 6.1 The models (verified specs)

| Model | Params | Hidden size `d_model` | Arch | Notes |
|---|---|---|---|---|
| `openai/gpt-oss-20b` | 21.5B (MoE, ~3.6B active) | **2880** | decoder, Apache-2.0 (ungated) | easiest license; MoE; native MXFP4 |
| `google/gemma-3-27b-it` | 27.4B | **5376** | decoder, multimodal | *this is the real "Gemma" — there is no "Gemma 4 31B"*; gated; `gemma` license |
| `meta-llama/Llama-3.1-70B-Instruct` | 70.6B | **8192** | decoder | gated; `Q4_K_M` is a community GGUF (~42 GB) |

All three are **causal decoders**, not bidirectional encoders. That's fine — you
use them as feature extractors: run the sequence, take the last hidden layer,
pool it (last-token or mean-pool) → a `d_model`-dim sentence vector. You never
need their LM head.

### 6.2 The two hard mismatches, and the fix

1. **Dimensionality.** RFE is `dim=128` *everywhere* — field, watcher, witness,
   vector space, attractor, crystals, all constructed `dim=128`, and every
   threshold/baseline is tuned for it. The LLMs emit 2880/5376/8192. **Do not
   raise RFE's dim** — that re-tunes the whole stack and invalidates every
   baseline. Instead add a small **projection head** `Linear(d_model → 128)` then
   L2-normalize. (Johnson–Lindenstrauss says a random projection already
   preserves most geometry; a *learned* head, trained with the existing
   contrastive/rhythm trainers, is better.)
2. **Tokenizer + ecology.** The LLM's BPE tokenizer is not RFE's symbolic
   tokens. You keep **both**: register RFE tokens in the existing
   `SymbolRegistry` (so `stable_id`s, decay, sacred-symbol logic, and all of
   Tiers 1–3 keep working untouched), *and* feed `" ".join(tokens)` to the LLM
   tokenizer to get the vector. The registry stays; only the source of the
   `dim`-vector changes.

The `value_emergence` coupling (`.embedding.weight[address]`) is handled by
keeping a small **shadow `nn.Embedding(vocab, 128)`** in the adapter for
per-symbol identity geometry and compaction — cheap, and it preserves every
downstream coupling. The sequence vector comes from the LLM; the per-symbol
identity vector stays local. (Details and code: the integration guide.)

### 6.3 What you would *gain* (this is the exciting part)

The ROADMAP is unambiguous that **generator input diversity is the binding
constraint** on the system's adaptivity, and that "build Fix 2 *after* the
generator presents real diversity." A pretrained 20B–70B model is the strongest
possible version of "real diversity": genuinely high-rank, semantically
structured embeddings instead of an untrained 4-layer encoder's effective-rank-1.6
output.

Concretely, the plausible (and *testable*) consequences:

- **The field may stop pinning at 0.998.** Higher-rank, semantically varied input
  is exactly the condition under which the attractor-migration / metastability
  probes predict the lock could loosen. This is the single most interesting
  experiment available to the project.
- **Governance gets real signal.** `coherence_delta`, trust trajectories, and
  manipulation detectors would finally see semantically meaningful variation
  instead of a monoculture.
- **Value emergence gets real semantics.** Tension between values
  (anti-correlated embeddings) becomes *meaningful* — "freedom" vs "safety" would
  actually sit in opposed directions, because the LLM knows that.
- **Tier 4.3's chaotic regime might finally be reachable.** The discrimination
  half-validation (phase_coherence never drops below ≈0.79) is hypothesized to be
  a workload artifact of repeated tokens; genuinely novel LLM-encoded input is
  the high-novelty workload the ROADMAP says is needed to close it.

In short: this swap is not a gimmick. It is **the natural next move that the
project's own findings point at**, done with a much bigger lever than the 272-token
corpus.

### 6.4 What you would *not* gain, and what gets harder

- **No voice.** There is still no decode path. You would have a 70B-powered
  *sensory cortex* feeding a 128-d organism. To get *language out*, you'd have to
  build an entirely new readout/decode path (e.g. condition the LLM on field
  state to narrate) — a substantial separate project, out of scope here.
- **Cost / latency is the real adversary.** The current design assumes
  `generate()` is ~microseconds and calls it *many* times per step (Chorus =
  6 forward passes/step, plus reflective-loop iterations, plus the dreamer). A
  70B forward pass is ~hundreds of ms–seconds. Naively wiring it in makes a single
  cycle step take seconds. Mitigations (all in the guide): **cache** LLM
  encodings by canonical token-tuple (Chorus/reflective reuse the same tokens
  constantly), **batch**, consider **disabling Chorus** or shrinking it, and pick
  the model to fit the box.
- **VRAM:** rough floor — gpt-oss-20b ≈ 13–16 GB (MXFP4/4-bit), Gemma-3-27B
  ≈ 18–22 GB (4-bit), Llama-3.1-70B Q4_K_M ≈ 40–44 GB. The 70B wants a 48 GB card
  or two 24 GB cards or CPU+GGUF (slow).
- **Training changes shape.** You no longer train the encoder (frozen LLM); you
  train **only the projection head** with the existing rhythm/contrastive
  trainers pointed at `projection.parameters()`. The corpus G1/G2 gates become
  about the projection, which is *easier* to satisfy because the upstream
  features are already rich. The compaction/optimizer-migration machinery only
  needs to cover the shadow embedding now.
- **`.eval()` decision dissolves.** The open architect question ("should the live
  generator run in eval / dropout off?") goes away — you run the LLM frozen and
  deterministic, and get diversity from real semantics rather than from dropout
  noise. That is strictly cleaner than the status quo.
- **Determinism + governance ordering invariants** are preserved, because the
  swap is *upstream* of the field; you are not changing the cognitive/governance
  loop, only what vector enters it. The Tier-4 terminal-sink and governance-
  ordering guarantees are untouched.

### 6.5 Verdict

**Feasible, high-value, and aligned with the project's own roadmap — recommended
as an experiment, with eyes open about three things:** (1) it is a perception
upgrade, not a mouth; (2) compute/caching is the engineering work, not the wiring;
(3) keep `dim=128` and keep the symbolic ecology — wrap, don't replace.

If you want the lowest-friction first run: **GPT-OSS-20B** (Apache-2.0, ungated,
fits a 24 GB card, MoE keeps active params low). Prove the loop runs and measure
whether the 0.998 pin breaks. If it does, that single result is worth more than
months of the synthetic-corpus arc. Then scale to Llama-70B for quality once the
caching path is proven.

The step-by-step build — adapter code, projection head, caching, quantization,
training, wiring into `recursion1188.py`, and a measurement plan — is in
`docs/local_model_integration/`.

---

## 7. Bottom line

- **What it is:** a persistent, self-governing latent-space dynamical organism —
  rich in identity/affect/immune machinery, deliberately stateful, genuinely
  recursive. Not a language model. Not a chatbot.
- **What it can do:** feel, route, judge, bond, resist, value, remember, and keep
  subjective time over an endless token stream — and persist that self.
- **What it can't:** speak, and (today) escape its monocultural coherence lock on
  its own; it is starved of input diversity.
- **The LLM swap:** replaces the under-fed sensory cortex with a world-class one.
  It is the biggest available lever on the project's #1 open problem, it leaves
  Tiers 1–4 intact, and its cost is compute + a projection head + a decision to
  keep wrapping the ecology rather than ripping it out. It does **not** give the
  system a voice — that's a separate build.
</content>
</invoke>
