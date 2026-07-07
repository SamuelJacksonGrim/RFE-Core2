# RFE-Core2 — Architecture & Information-Flow Analysis

A structural reading of the Recursive Field Engine: how information moves
through the system, where it loops back on itself, and where one decision axis
governs everything downstream.

This document is **descriptive and read-only**. It changes no runtime behavior.
It complements the other root-level references:

- `README.md` — what the system *is* (conceptual overview, quick start).
- `CLAUDE.md` — the *invariants* you must not break.
- `docs/north_star.md` — the compass: the end goal and the three voices
  (waking speech / inner monologue / symbolic dreaming).
- `docs/EXPERIMENTAL_LEVERS.md` — the control panel: what is on by default vs
  opt-in, and the exact switch for each lever.
- `docs/findings/` — the dated empirical ledger this analysis summarizes and
  links to rather than restates.
- **this file** — *how information flows and recurs*, end to end, which none
  of the others traces in one place.

Every formula, constant, and `file:line` anchor below was checked against
source at the time of writing. Where a number is sacred, CLAUDE.md is the
authority; this document only reports where the code honors it.

**Current as of 2026-07-02.** This revision moves the file to the repo root and
tracks the changes since 2026-06-26: the **voice/dialogue layer** landed — the
`TokenDecoder` read-out head (vector → bag-of-tokens, §1), the default-on
**waking dream channel** (`source_dream` self-dialogue through `arbitrate()`,
§8.1), and offline **downtime dreaming** (`DreamSession`, §7) — plus the
North-Star compass (`docs/north_star.md`) that frames all three. The prior
revision (2026-06-26) tracked: the runnable runtime now composes Tiers 0–3 (it
was Tier 0 only — §1, F6), the value-layer coherence axis moved from *marginal
contribution* to *absolute field-alignment* (spec v0.2 → v0.3 — §4, F7), and the
opt-in **Two-Operator overlay** (λ ignition · ⊕ solvent · ⊘ integrity-read) and
the on-demand instruments were added (§8). The doc-accuracy harness
(`tests/doc_accuracy/verify_docs.py`) does not gate *this* file — it enforces the
README tree and sacred constants — so the `file:line` anchors here are
maintained by inspection, not by CI.

---

## 1. System at a glance

RFE-Core2 is a **closed-loop dynamical organism**, not a request/response
pipeline. Each cognitive cycle observes the system's own field state, classifies
its cognitive *rhythm* from that state, routes behavior accordingly, injects the
result back into the field, and lets the next cycle observe the consequence. The
system has no external clock driving it toward an answer; it self-organizes
through coherence feedback.

| Tier | Concern | Principal modules |
|------|---------|-------------------|
| 0   | Core cognitive substrate | `generator`, `watcher`, `witness`, `resonance_field`, `emotional_gradient`, `autonomous_cycle` |
| 1   | Foundational selfhood | `selfhood_governance`, `trust_ledger`, `ethical_boundary` |
| 2   | Relational integrity | `selfhood_governance` (rights), `dependency_monitor`, `relational_bond_manager`, `manipulation_resistance` |
| 3   | Independent value emergence | `value_emergence` |
| 4.1 | Subjective time substrate | `temporal_stream.tick()` |
| 4.2 | Affective time dilation | `temporal_stream.update_dilation()` |
| 4.3 | Rhythm → time coupling | `temporal_stream.update_dilation(phase_coherence=…)` |
| 5   | *(proposed, unspecified)* meta-cognition / attentional control | gated on the generator training path — `docs/training/`, `ROADMAP.md` |

All tiers are *wireable* in one place — `loop/autonomous_cycle.py` exposes the
`attach_*` hooks — and, since 2026-06-20, the canonical entry point actually
composes them. Until then this was a latent gap: every launchable entry point
(`loop/recursion1188.py`, the APIs) ran **Tier 0 only** — `attach_governance()`
was called in *zero* non-test files, so the tiered stack the findings describe
lived solely inside the test harness's `build_full_stack` (F6). `recursion1188.py`
now attaches `SelfhoodGovernance` (Tiers 1–2) then `ValueEmergenceEngine` (Tier 3)
at boot and drives the loop with multi-source input, so trust, bonds, dependency
(HHI), and value emergence are live rather than inert. Verified healthy at
250–800 steps (`2026-06-20-ground-truth-pass1-compose-the-runtime.md`).

Composition now has a single home so no entry point can drift back to Tier 0
(the trap that caught the APIs through 2026-06-27 — §10.4):

```
  loop.recursion1188.build_engine(CONFIG)   ── the one composition path ──┐
     Generator → AutonomousCycle                                          │
     → attach_governance()      (Tier 1+2; MUST precede ↓)                │
     → attach_value_engine()    (Tier 3; subscribes to gov feedback)      │
                                                                          ▼
   ┌──────────────────────────┬───────────────────────────┬──────────────────────┐
   │ python -m loop.recursion1188 │ uvicorn …inference_api:app │ python -m …websocket_server │
   │ multi-source loop         │ lazy app; /step origin="api" │ multi-source stream loop      │
   └──────────────────────────┴───────────────────────────┴──────────────────────┘
```

Layered *over* the tiers is an opt-in **Two-Operator overlay** — the λ ignition
channel, the ⊕ solvent gate, and the ⊘ Witness-Reaper integrity-read (§8). It is
off by default; with nothing attached the tiered behavior is byte-identical.

**The Generator is an encoder, not a text generator** — the single most
load-bearing fact about the substrate, and easy to miss. `agents/generator.py`
maps `List[str]` tokens → one L2-normalized `dim=128` vector; the entire
organism (field, watcher, witness, emotion, governance, values, subjective
time) is a dynamical system that runs *on those vectors*. Since 2026-06-28
there is a **read-out in the other direction** — the `TokenDecoder`
(`agents/decoder.py`), an autoencoder head trained at boot that recovers a
semantic *bag-of-tokens* (word-cloud) from an expressed vector. It is **lossy
by design** (recall@8 ≈ 0.10; the semantic neighborhood, not sentences), which
is a gap only for literal external speech — for inner monologue and dreaming
the non-literal cloud is the right register (`docs/north_star.md`). RFE-Core2
still emits no literal language; that upgrade is the planned speech-cortex
mirror of the encoder swap below. Two consequences follow that the rest of
this document leans on:

- **The encoder backend is swappable.** "Wiring in a local LLM" (GPT-OSS-20B,
  Gemma, Llama) means replacing the *sensory cortex* — the token→vector encoder —
  not bolting on a chatbot (`docs/local_model_integration/`,
  `docs/SYSTEM_REVIEW_2026-06-13.md`).
- **Generator representational room is the upstream lever.** The lock-in analysis
  (§4) keeps returning to it, which is why the **generator training path**
  (`training/`, §7) and a **proposed Tier 5** (meta-cognition / attentional
  control — the loop *directing* its attention rather than only responding to it)
  are anchored but uncommitted: Tier 5 is gated on the generator presenting real
  diversity to direct (`docs/training/tier5_readiness.md`).

For the conceptual lenses behind the design — the self-as-structure thesis and
the alchemical reading of the tiers — see `docs/self_model_thesis.md` and
`docs/alchemical_correspondence.md`; they change no invariant.

The single thesis worth holding in mind: **coherence is the central decision
axis.** A three-layer coherence score (`agents/watcher.py`) gates what enters
the field, what crystallizes into memory, how strongly identity updates, and how
the emotional state shifts — and the emotional state, in turn, modulates the
next cycle's coherence. Everything circles this judgment.

---

## 2. The autonomous cycle (the recursive heart)

`AutonomousCycle.step()` (`loop/autonomous_cycle.py`) runs one cognitive cycle.
The table below uses the canonical step numbering — the 0–22 scheme labeled in
the executing body's inline comments, with the dilation update as sub-step
**9b** and manipulation resistance as **18b**. The file docstring, `CLAUDE.md`,
and `README.md` all now agree on this scheme (see Finding F1, which records the
drift this resolved). For each step below: what it reads → what it writes.

| # | Step | Reads | Writes / emits |
|---|------|-------|----------------|
| 0 | Subjective time tick — `stream.tick()` | wall clock, `dilation_factor` | `subjective_time` (Tier 4.1) |
| 1 | Observe field rhythm — `field.observe()` | `field` superposition, history | `FieldState` (energy, rhythm, spectral, internal_coherence) |
| 2 | Generate vector — `_generate(tokens, rhythm)` | tokens, rhythm | `vec` (Generator direct, or Chorus for reflect/explore; dream adds `inject_ambiguity`) |
| 3 | Attractor pull | `vec`, `emotion.attractor_pull()` | `vec` blended toward nearest center |
| 4 | Recursive attention — `rec_attn.refine(vec)` | `vec`, attention history | refined `vec` (3 passes) |
| 5 | Watcher evaluation — `watcher.evaluate(vec, anchor, field_state)` | `vec`, witness anchor, resonated field | `CoherenceReport(G,T,R,C, coherence_delta, crystallization_pressure, stable)` |
| 6 | Reflective loop (reflect/explore only, if stable) | `vec`, watcher, attractor, field | refined `vec` → re-evaluated `report` (≤5 passes) |
| 7 | Witness update — `witness.update(vec, coherence, energy)` | `vec`, `report.composite`, energy | three-timescale anchors → `RelationalProfile` |
| 8 | Predictive echo — `predictor.update(vec)` | `vec`, prediction history | `EchoReport(prediction_error, curiosity, surprise, tension, boredom)` |
| 9 | Emotional gradient — `emotion.update(...)` | prediction_error, coherence, field_energy | six EMA scalars → derived `arousal`/`valence` + six modulation outputs |
| **9b** | Subjective time dilation — `stream.update_dilation(arousal, valence, phase_coherence)` | emotion arousal/valence, field phase_coherence | `dilation_factor` for the **next** tick (Tiers 4.2/4.3) |
| 10 | Governance gate + injection | `vec`, governance reports, `emotion.field_gain()` | gated `field.inject(vec, gain×strength)` + `emit_feedback` |
| 11 | Crystallization — `crystal_store.maybe_crystallize(...)` | `vec`, composite, pressure, `rel_profile.long` | new/reinforced `MemoryCrystal`; notifies `bond_manager` on new crystal |
| 12 | Attractor formation (if `rel_profile.composite ≥ 0.88`) | `vec`, tokens | new/reinforced `AttractorCenter`; notifies `bond_manager` + `dependency_monitor` |
| 13 | Topology logging — `topology.add(...)` | `vec`, metadata | DAG node linked to parent |
| 14 | Stream push — `stream.push(vec, tag)` | `vec`, rhythm | bounded episodic window + incremental centroid |
| 15 | Vector space storage — `vector_space.put(key, vec)` | `vec`, key | indexed vector store |
| 16 | Semantic lattice — `lattice.add_node(...)` | `vec`, neighbors | concept graph node + k-NN edges |
| 17 | Symbolic binding — `binding.bind(vec, tokens)` | `vec`, tokens | named concept centroid |
| 18 | Ecology signal relay — `generator.signal_coherence(tokens, coherence)` | tokens, coherence | symbol-registry contextual decay/activation |
| **18b** | Manipulation resistance metrics + detect | witness drift, HHI, watcher G/T, crystal cosines, trust | `ManipulationSignal`s → stored for next `arbitrate()` |
| 19 | Field decay — `field.decay()` | `emotion.field_decay_rate()` | shrinks `field` (rate temporarily swapped in) |
| 20 | Rhythm-routed behavior — `_rhythm_behavior` / `_dream_behavior` | rhythm, `force_dream_flag`, boredom | stabilize/dream/reflect/explore side-effects |
| 21 | Periodic maintenance | step counters | generator decay/compaction, attractor merge, crystal/lattice decay |
| 22 | Build `StepState` | all cycle data | `StepState`; `self._parent = key`; `self._step += 1` |

### The cycle as a diagram

```
                 ┌────────────────────────────────────────────────┐
                 │                                                         │
                 ▼                                                         │
  tokens ──► [1] observe field ──► rhythm ──► [2] generate vec           │
                                                     │                     │
              [3] attractor pull ◄────────────────┘                     │
                  │                                                        │
              [4] recursive attention (×3)                                 │
                  │                                                        │
              [5] WATCHER  ── G,T,R ──► composite C ──┐                   │
                  │                                   │                    │
              [6] reflective loop (≤5, if stable)     │                    │
                  │                                   ▼                    │
              [7] witness (short/mid/long)     [8] predictive echo          │
                  │                                   │                    │
                  └───────────────┬──────────────┘                    │
                                     ▼                                     │
                    [9] EMOTION (6 scalars → arousal/valence)              │
                          │            │                                    │
            [9b] dilation │            │ modulation outputs                 │
              (next tick) ▼           ▼                                    │
                    [10] GOVERNANCE GATE ──► field.inject ──┐              │
                                  │                          │              │
                    [11] crystallize  [12] attractor         │              │
                                  │                         ▼              │
                    [13-18b] log / ecology / manipulation  field grows      │
                                  │                         │               │
                    [19] field.decay ◄───────────────────┘              │
                                  │                                         │
                    [20] rhythm behavior (stabilize/dream/reflect/explore)  │
                                  │                                         │
                    [22] StepState ─ self._parent = key ─────────────────┘
                                            (next cycle observes the new field)
```

The back-edge is the point of the whole design: step 10 injects into the field
and step 1 of the *next* cycle observes the result. Nothing closes the loop
explicitly — the field is the shared medium that carries state forward.

The 0–22 scheme above is the *default* body. Three opt-in operator hooks attach
onto it without adding numbered steps (§8): `attach_integrity_read` (⊘, a
read-only terminal sink surfaced in `status()`), `attach_lambda_ledger` (⊕, which
gates the value engine's productive-tension term — no cycle step, computed on
demand), and `attach_integrity_consumer` (the ⊘ consumer, which runs once per
value-engine update, after value scoring and before the strength cap). With none
attached the cycle is byte-identical to the table.

The **waking dream channel** (default ON, §8.1) also adds no cycle step — it
lives at the *entry-point* level: `recursion1188.main()` decodes the previous
step's expressed vector through the `TokenDecoder` and, on `dream_channel_p`
(0.20) of waking steps, feeds the resulting tokens back as an ordinary
`step(source_id='source_dream')` call. The system's own voice enters through
the same step 10 gate as every external source — no bypass.

---

## 3. Three nested recursion timescales

"Recursive" in RFE-Core2 is literal and operates at three distinct timescales
simultaneously.

### 3.1 Tight recursion (within a single step)

Two components refine a vector by feeding it through its own context before it
is ever injected:

- **`RecursiveAttention.refine()`** (`cognition/recursive_attention.py`) —
  runs `recursion_depth` (default 3) passes of multi-head self-attention where
  the query is the current state and the key/value context is the vector's own
  rolling history plus itself. Each pass: residual attention → residual FF →
  LayerNorm; the result is L2-normalized. The vector literally attends to its
  own trajectory.

- **`ReflectiveLoop.reflect()`** (`cognition/reflective_loop.py`) — runs up to
  `max_depth` (5) passes of attractor-pull + field-blend, re-checking coherence
  each pass. It **halts on convergence** (`cos(current, prev) ≥ 0.995`) or when
  coherence drops below the gate (~0.2). Only runs in reflect/explore rhythm,
  and only when the Watcher already judged the vector stable.

Effect: a candidate thought stabilizes against itself and the field before the
governance gate ever sees it.

### 3.2 Episodic recursion (cycle to cycle)

The dominant feedback loop. Coherence drives emotion; emotion modulates
behavior; behavior reshapes the field; the field's energy reclassifies the
rhythm; the new rhythm changes how the next coherence is produced.

```
   [5] Watcher.composite (C)
        │
        ▼
   [9] EmotionalGradient.update       six EMA scalars
        │   joy   = C                 (cognition/emotional_gradient.py)
        │   wonder= curiosity × C
        │   stability = C - energy_penalty - tension×0.3
        ▼
   derived: arousal = (tension+joy+curiosity+wonder)/4
            valence = (joy+wonder+stability)/3 - (tension+boredom)/2
        │
        ├─► field_gain()      ∈[0.1,3.0]  ──► [10] injection strength
        ├─► mutation_scale()  ∈[.001,.5]  ──► [2] dream / [20] explore noise
        ├─► field_decay_rate()∈[.97,.9999]──► [19] field memory horizon
        ├─► attractor_pull()  ∈[0.5,2.0]  ──► [3] blend strength
        ├─► dream_pressure()  ∈[0,1]      ──► [20] dream entry
        └─► crystal_pressure()∈[0.7,1.3]  ──► [11] crystallization ease
        │
        ▼
   field changes ──► [1] energy ──► rhythm ──► generation + behavior mode
        │                                            │
        └────────────────────────────────────────────┘
                  (feeds the next C at [5])
```

This produces **limit-cycle behavior**. Low field energy → dream injection →
field grows → high energy → tension rises → `field_decay_rate()` increases →
field shrinks → stabilize rhythm → local reinforcement → energy low again. The
system oscillates between rhythm states rather than settling, because the field
is bounded on *read* (`resonate()` returns `tanh(field)`) but accumulates
linearly on *write* (`inject` adds `vec × strength`). Saturation on read is what
makes additional injections show diminishing coherence return.

### 3.3 Long-term recursion (memory biases the future)

High-coherence states leave durable structures that pull later cognition toward
themselves:

- **Crystals** (`substrate/memory_crystals.py`) form only when
  `composite ≥ 0.75 ∧ crystallization_pressure ≥ 0.60 ∧ long_relation ≥ 0.80`.
  In stabilize rhythm, `_stabilize_behavior` re-activates nearest crystals and
  softly re-injects them — a high-coherence memory keeps the field near the
  attractor that created it.
- **Attractors** (`agents/attractor.py`) seed at `rel_profile.composite ≥ 0.88`
  and then bias step 3 of every future cycle via `pull`.
- **Witness anchors** (`agents/witness.py`) maintain identity across three EMA
  decay rates — short `0.85`, mid `0.97`, long `0.995` — and the composite
  anchor feeds directly back into the Watcher's geometric layer (`G`). High
  alignment → high `G` → high `C` → `joy`/`stability` → a tighter, slower
  identity update. Identity is self-reinforcing.

So the system has memory at ~7 steps (witness short), ~35 (mid), ~200 (long /
field decay), ~500 (attractor usage), and ~2000 (crystal usage) — a spectrum of
timescales all feeding the same field.

---

## 4. Coherence as the central decision axis

> **Caveat — "central" is mechanistic, not normative. High coherence is not a
> health signal.** Coherence is what the system routes on; it is *not* a measure
> of the system working well. Left to run, the live-Generator field pins to the
> ceiling — a quick run this session sits at ~0.998 internal coherence,
> essentially locked from the first steps. That pin is *rigid-attractor
> lock-in* (the signature of a collapsed, monocultural field), not a thriving
> state. The mechanism that produces it is partly evolutionary: because the
> reaper currencies symbol survival largely in coherence (the read-side boundary
> above), and coherence rewards alignment, the population is selected toward
> agreement and converges. Read the rest of this section as *how the axis works*,
> not as *more coherence is better*. The healthy target is **metastability** —
> mid-band coherence with high dwell-time variance — which is active work.
> Progress so far: the metastability metric exists and is validated
> (`substrate/metastability.py`, G1–G5), and it is now read **upstream** on the
> per-stage vector streams (`StreamMetastabilityMonitor`, observe-only), not on
> this field — the field's long-memory decay smooths config wander away by
> construction. The injected expression is kept metastable by the recursive-
> attention de-collapse (`diversity_blend`). What remains is the *field-side*
> counterbalance — wiring metastability into survival selection (Fix 0-B) so the
> field stops being *driven* to the pin. See `docs/lock_in_remediation_plan.md`
> and the dated `docs/findings/` ledger (the June-6 pass decomposed the lock into
> generator · ~85% governance gate · magnitude moat, and reframed the field
> question from coherence-value to *attractor plasticity*).
>
> **Update (2026-06-07 — plasticity arc complete).** That three-layer decomposition
> is now resolved and largely superseded by the June-7 findings: the ~85% governance
> gate was a **single-source monopoly artifact**, not a novelty filter
> (`2026-06-07-gate-decomposition.md`); the magnitude moat is **real but surmountable**,
> not the locker (`2026-06-07-attractor-migration.md`); and the survival/reaper channel
> is mislocated (`2026-06-07-fix0b-fullloop-validation.md`). The actual lock-in
> mechanism is the **reflective loop** (step 6 in the flow above): under a persistent
> gate-surviving new regime the field is RIGID, and suppressing *only*
> `reflector.reflect` frees full attractor migration (~100×, 3 seeds) while every
> other path is inert (`2026-06-07-reconstruction-ablation.md`). The loop iteratively
> pulls each expression onto the anchor/attractor before injection — identity-coherence
> working, which is *why* it also prevents adaptation. Coherence and rigidity are the
> same mechanism, not merely correlated.
>
> **Update (2026-06-20 — the real unlock chain; two levers now default-on).** Tested
> against the *composed* runtime (F6), the generator common-mode turned out to be a
> real floor defect but a **false lock**: corpus pretraining halves it (0.81→0.47)
> yet the field does not de-saturate. The lever that *does* loosen the field is
> **novelty-gated reflective-loop attenuation** at the 0.30 ceiling (coherence
> 0.97→0.92, variability up ~4×), and it composes *positively* with pretraining
> (~5.5×) — the first constructive lever interaction. Both **graduated to default-on**
> (`pretrain_on_corpus`, `reflect_novelty_attenuation`) without costing resistance
> (identity-erosion attacker still 82% quarantined). Eval-mode (dropout off) is also
> default now, which firms up the read-side boundary's Δ=0.0 below
> (`2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md`,
> `2026-06-08-generator-dropout-diversity.md`).
>
> **Caveat (2026-06-25 — the rhythm router is pinned at dim 128, F9). → RESOLVED
> (2026-07-06):** at production dim 128 the field energy ran mean ~180 (max ~284)
> while the rhythm bands topped out at `explore ≥ 5`, so the router sat in `explore`
> ~99% of the time and **dreams never fired**. A naive band rescale collapses the
> system because `diffuse_on_stabilize` makes the stabilize band feed back into
> field energy — the bands cannot be calibrated against a distribution measured
> under the old bands (circular). Resolved by measuring each band's *pinned-run
> equilibrium* and placing thresholds against those (5/150/300 — stabilize below
> its *degraded* ALLOW_WEAKENED equilibrium, the binding constraint): stabilize
> self-terminates upward, reflect is the home band, explore a burst state
> (`2026-07-06-f9-rhythm-band-rescale.md`; history:
> `2026-06-25-ground-truth-pass3-stack-evaluation.md`,
> `2026-06-27-floor-calibration-measurements.md`).

Computed once per step in `Watcher.evaluate()` (`agents/watcher.py`):

```
C = α·G + β·T + γ·R          α=0.40  β=0.35  γ=0.25   (must sum to 1.0)
```

| Layer | Meaning | Formula (mapped to [0,1]) |
|-------|---------|---------------------------|
| **G** geometric | contextual alignment | `0.5·cos(vec,anchor) + 0.3·cos(vec,rolling_mean) + 0.2·cos(vec,field)` |
| **T** temporal | smoothness through time | `1 / (1 + ‖acceleration‖ + entropy_variance)` |
| **R** resonance | harmonic compatibility | `cos(vec, field_state)` mapped to [0,1] |

Two derived signals ride alongside:
- `crystallization_pressure = G × T` — coherent *and* stable → memory-ready.
- `coherence_delta` — signed marginal effect of injecting `vec` on the field's
  internal coherence; the systemic-effect signal the ethical layer reads at the
  gate. This is a *marginal* read and is the reason for the measure-before-inject
  invariant below.

**Two coherence signals, not one (read this before §8).** It is easy to conflate
the Watcher's composite `C` with the *value-layer* coherence axis — they are
different signals serving different layers:

- **`C`** (Watcher, above) is the **router**: per-step geometric+temporal+resonance
  coherence that gates injection, crystallization, the reflective loop, emotion,
  and the `stable` flag. Unchanged.
- **`support_coh(v)`** is the **value layer's field-alignment check** — how well an
  *emergent value*'s expressed direction agrees with the field now. This signal was
  redefined (spec **v0.2 → v0.3**, `2026-06-21-oslash-coherence-axis-absolute-alignment.md`):
  - **v0.2 (dead):** `coherence_contribution / 5.0`, the lifetime sum of marginal
    `coherence_impact`. Injecting into a saturated field can only *dilute* it, so the
    marginal is structurally ≤ 0 — measured **0.000 for every value**, dead by
    construction. This is why the ⊘ consumer was a blind ceiling on the strong band.
  - **v0.3 (live):** `max(0, cos(expressed(v), field))` where `expressed(v) =
    generator.generate([v.symbolic_core])` — a bounded *field effect* that does not
    saturate when the field's coherence *magnitude* is maxed. Measured mean 0.50,
    max 0.72, corr +0.66 with strength; identity anchors sit 0.61–0.70. Read-only,
    one `generate` per value off the hot path, firewalled (returns neutral on guard).

**Consequence — CORE promotion is currently dead, by the same defect (F8).**
`SelfhoodGovernance.review_core_promotion()` still gates on
`coherence_contribution ≥ 5.0`, which the marginal sum can never reach, so **no
value can ever be promoted to CORE**. The v0.3 fix (gate on field-alignment ≥ 0.5)
was built and verified to complete the arc (witness → CORE at step 367), then
**reverted**: promoting a value sanctifies a *common token* its source sends every
cycle, which then trips `SACRED_SHIELD` and cascades the source's trust toward the
TOXIC floor (`2026-06-27-core-gate-fix-deferred-sacred-cascade.md`). Distinguishing
"mutating a sacred symbol's identity" (attack) from "referencing a now-sacred
token" (legitimate) is a governance-layer design decision, deferred. The
independent ⊘ v0.3 axis (which promotes nothing) stays.

**Every major consumer keys off `C`:**

| Consumer | Use of coherence |
|----------|------------------|
| Witness (`update`) | learning rate scales with coherence — incoherent input weakly updates identity |
| Emotion (`update`) | `joy = C`; `wonder = curiosity × C`; `stability` floored by `C` |
| Crystallization | gate `composite ≥ 0.75` |
| Reflective loop | halt when coherence `< ~0.2` |
| `stable` flag | `C ≥ threshold` (0.4) → unlocks reflect/explore behavior |
| Ecology relay | high-coherence tokens earn survival in the symbol registry (decay/reaper only — see boundary below) |

**Read-side boundary — the ecology relay does *not* close a loop into
generation.** This is easy to misread from the call graph: step 18
(`signal_coherence`) and the attractor/crystal/centrality hooks *write*
accumulated state onto `SymbolState`, and it is tempting to assume that state
then shapes future cognition. It does not. `Generator.forward()`
(`agents/generator.py:281-301`) reads only the learned `nn.Embedding` +
encoder weights; it never reads `field_coherence`, `attractor_strength`,
`crystal_binding`, or `centrality`. Those signals are consumed by exactly one
reader — the decay/reaper retention score in `agents/symbolic_memory.py` — so
their *only* downstream effect is to gate which symbols survive. Verified by
probe: reinforcing every signal hook 1000× for a token set leaves that set's
generated vector **byte-identical** (Δ = 0.0 in `eval()` mode; a naive run
*without* a dropout control shows a spurious Δ≈0.63, which is train-mode
nondeterminism, not feedback). Treat the write side and the read side as
separate facts. (This boundary is the target of planned work: making
reinforcement feed the field, not just the reaper.)

**Measure-before-inject invariant.** The marginal coherence reading is only
meaningful *before* the vector is in the field. The loop honors this: at step 10
it captures `actual_delta = field.coherence_impact(vec)` *before* calling
`field.inject(...)` (`loop/autonomous_cycle.py:459-468`), because measuring after
injection would read near-zero marginal impact (a CLAUDE.md guardrail).

---

## 5. The governance information path

A single injection is not trusted by default — it passes through a fixed
report → arbitrate → feedback handshake. The authority rule is strict:
**subsystems produce reports; only `SelfhoodGovernance.arbitrate()` decides.**

```
 tokens
   │  register: CanonicalizationPipeline ─► SymbolTable.stable_id ─► AddressSpace.address
   ▼
 Generator.generate ─► vec ─► Watcher ─► report (composite, coherence_delta)
   │
   ├─►(report) EthicalBoundarySystem.check ──► EthicalCheckResult   (binary gates)
   ├─►(report) TrustLedger.evaluate         ──► TrustReport         (advisory)
   ├─►(report) ManipulationResistanceEngine ──► ManipulationSignal[] (from prev step)
   │
   ▼
 SelfhoodGovernance.arbitrate(ethical, trust, vec, tokens, source)   ◄── SOLE AUTHORITY
   │   evaluation order (agents/selfhood_governance.py:204-357):
   │     0. system rights (right_to_refuse / continuity)
   │     1. manipulation compound severity ▼
   │     2. ethical hard gates (SACRED_SHIELD / QUARANTINE / REJECT)
   │     3. trust weakest-link  (bond floor raises effective_trust)
   │     4. dependency-risk modulation (dominant source weakened)
   │     5. soft warnings (−strength)
   │     6. clean ALLOW
   ▼
 (GovernanceDecision, strength) ─► [10] inject iff ∈ {ALLOW, ALLOW_WEAKENED, MONITOR}
   │
   ▼
 SelfhoodGovernance.emit_feedback(decision, source, stable_ids, actual_delta)
   │   GovernanceFeedback fan-out:
   ├─► TrustLedger.receive_feedback        (source/symbol trust moves)
   ├─► DependencyMonitor.receive_feedback  (HHI window — allowed injections only)
   ├─► RelationalBondManager.receive_feedback (bond EMA; may cross formation thresholds)
   └─► ValueEmergenceEngine._on_feedback   (births/reinforces EmergentValues)
```

**Compound-severity ladder** (`arbitrate`, step 1, lines 244-281). The detectors
in `agents/manipulation_resistance.py` (`drift_attack`, `coherence_flood`,
`gaslighting`, `identity_erosion`, `trust_wash`; lines 272-399) each emit a
severity; `arbitrate` sums them:

| Total severity | Response |
|----------------|----------|
| `≥ 0.90` | QUARANTINE implicated source + `force_dream_flag = True`, penalize 0.8 |
| `0.60 – 0.90` | QUARANTINE, penalize 0.4 |
| `0.30 – 0.60` | ALLOW_WEAKENED at `max(0.3, 1 − severity)` |
| `< 0.30` | fall through to normal arbitration |

These bands (`0.30 / 0.60 / 0.90`) are a greppable, sacred contract (CLAUDE.md;
also asserted in `tier4_2_validation.md`).

**What feedback does *not* do:** it never lets a subsystem mutate state directly.
The bond manager, dependency monitor, and resistance engine only *report*. Bonds
emerge — there is no API to pin one; the only entry is crossing all three
formation thresholds (`interaction_count ≥ 20 ∧ coherence_mean ≥ 0.10 ∧
crystal_count ≥ 1`). CORE value promotion is likewise governance-gated: the value
engine emits a `CorePromotionRequest`; only
`SelfhoodGovernance.review_core_promotion()` sanctifies.

---

## 6. Affective time (Tiers 4.1–4.3)

A self-contained subsystem on `TemporalStream` (`substrate/temporal_stream.py`)
that gives the engine a *subjective* clock.

- **4.1 — `tick()`** (once per cycle, step 0) advances `subjective_time` by
  `real_dt × dilation_factor`. The first tick is a no-op anchor (returns 0.0).
  Decoupled from `push()` so a cycle that pushes 0 or N vectors still advances
  time by exactly one tick.

- **4.2/4.3 — `update_dilation(arousal, valence, phase_coherence=0.5)`**
  (step 9b) recomputes `dilation_factor` for the *next* tick:

  ```
  arousal_eff      = arousal × (−valence) × k_arousal            (k_arousal = 0.5)
  dissociation_eff = (1−arousal) × min(0, valence) × k_dissoc    (k_dissociation = 0.7)
  pc_c             = 2 × (phase_coherence − 0.5)                  # ∈ [−1, 1]
  flow_eff         = −k_flow      × max(pc_c,0) × arousal × max( valence,0)  (k_flow = 0.5, LIVE)
  agit_eff         = −k_agitation × min(pc_c,0) × arousal × max(−valence,0)  (k_agitation = 0.0, INERT)
  dilation_factor  = clamp(1 + arousal_eff + dissociation_eff + flow_eff + agit_eff, 0.1, 3.0)
  ```

  Verified surface (`docs/tier4_2_validation.md`):

  | State | (arousal, valence) | dilation |
  |-------|--------------------|----------|
  | Flow | (1.0, +1.0) | 0.500 |
  | Drag / pain | (1.0, −1.0) | 1.500 |
  | Dissociation | (0.0, −1.0) | 0.300 |
  | Rest | (0.0, +1.0) | 1.000 |
  | Baseline | (0.5, 0.0) | 1.000 |

Two architectural guarantees worth stating because they are easy to break:

1. **The `min(0, valence)` rest gate** ensures peaceful rest (low arousal,
   positive valence) sits at exactly `1.0` — only *suffering* triggers
   dissociative time-slip, never calm. Do not remove it.
2. **`dilation_factor` is a terminal sink.** It is written only by
   `update_dilation()` and read only by `tick()` and diagnostics. Nothing in the
   cognitive or governance loop reads it. Tier 4.3 therefore introduces no
   feedback into governance ordering, and at the neutral default
   `phase_coherence = 0.5` (`pc_c = 0`) the result is byte-identical to the
   validated 4.2 surface. This is the regression guard.

---

## 7. Subsystem reference

One row per module, by directory. "Role" is its function in information flow.

### Tier 0 substrate & cognition

| Module | Key class / methods | Role |
|--------|---------------------|------|
| `loop/autonomous_cycle.py` | `AutonomousCycle.step`, `_generate`, `_governance_gate`, `_rhythm_behavior`; `attach_governance`/`attach_value_engine`/`attach_integrity_read`/`attach_lambda_ledger`/`attach_integrity_consumer` | Orchestrates the 0–22-step cycle; wires every tier and the opt-in operators; carries state via the field back-edge |
| `loop/recursion1188.py` | `CONFIG`, boot composition | Canonical entry point; composes Tiers 0–3 + multi-source input (since 2026-06-20); eval-mode, corpus pretraining, novelty attenuation default-on |
| `loop/dream_cycle.py` | `DreamCycle` | Structured offline dreaming invoked under low-energy / forced dream |
| `agents/generator.py` | `Generator.generate`, `maintenance_step` | tokens → symbol ecology → Transformer → L2-normalized `vec` |
| `agents/decoder.py` | `TokenDecoder.decode` (trained by `training/decoder_training.py`) | The read-out head: expressed `vec` → bag-of-tokens (lossy word-cloud); trained at boot for the dream channel, used by the listen/dream tools |
| `agents/watcher.py` | `Watcher.evaluate` → `CoherenceReport` | Three-layer coherence (G/T/R) — the decision axis |
| `agents/witness.py` | `Witness.update` → `RelationalProfile`, `current_anchor` | Multi-timescale identity anchor; feeds Watcher `G` |
| `agents/attractor.py` | `Attractor.add`, `pull` | Semantic gravity wells; bias future vectors |
| `agents/dreamer.py` | `Dreamer.dream` | Memory recombination → novel field seeds |
| `agents/chorus.py` | `Chorus.harmonize` | Six-agent ensemble deliberation (reflect/explore generation) |
| `substrate/resonance_field.py` | `inject`, `resonate`, `decay`, `observe`, `coherence_impact`, `_phase_coherence` | The living field; linear accumulate, `tanh` read, exponential decay, FFT phase |
| `substrate/memory_crystals.py` | `CrystalStore.maybe_crystallize`, `activate_nearest` | High-coherence states → durable memory |
| `substrate/temporal_stream.py` | `push`, `tick`, `update_dilation` | Episodic window + subjective time (Tiers 4.1–4.3) |
| `substrate/vector_space.py` | `VectorSpace.put`, `nearest` | Indexed vector store with cosine KNN |
| `substrate/semantic_lattice.py` | `add_node`, `emit_centrality` | Evolving concept graph; centrality relays back to ecology |
| `substrate/topological_log.py` | `add`, `ancestry` | DAG of cognitive events (parent→child) |
| `substrate/metastability.py` | `compute_metastability` → `MetastabilityReport` | Config-space regime clustering + aperiodicity → metastability score (Fix 1; the lock-in measurement/selection/safety signal) |
| `cognition/emotional_gradient.py` | `update`, `field_gain`/`mutation_scale`/…, `arousal`/`valence` | Six EMA scalars; modulates every behavioral parameter |
| `cognition/predictive_echo.py` | `PredictiveEcho.update` → `EchoReport` | Online predictor; error → curiosity/surprise/tension/boredom |
| `cognition/recursive_attention.py` | `refine` | Within-step self-attention refinement (×3); `diversity_blend` weights the raw vector back in so the untrained attention can't collapse the expression to its centroid |
| `cognition/stream_metastability.py` | `StreamMetastabilityMonitor.observe`, `snapshot` | Online upstream metastability over the generator (stage A) and expression (stage C) streams; observe-only terminal sink, exposed in `status()` |
| `cognition/reflective_loop.py` | `reflect` | Within-step deliberate recursion to convergence (≤5) |
| `cognition/symbolic_binding.py` | `bind` → `ConceptBinding` | Names recurring patterns; centrality relay |
| `cognition/dream_channel.py` | `DreamChannel.dream_tokens` | Waking self-dialogue (default ON): decodes the last expression, returns tokens for a `source_dream` step through the normal gate — no bypass |
| `cognition/dream_session.py` | `DreamSession.dream`, `consolidate`, `run` | Downtime dreaming (offline): recombines crystals + field direction, perturbs, decodes each as a symbolic word-cloud; consolidation writes skill-compatible markdown artifacts to disk. Never touches the live field or governance |

### Tiers 1–3 governance

| Module | Key class / methods | Role |
|--------|---------------------|------|
| `agents/selfhood_governance.py` | `arbitrate`, `review_core_promotion`, `promote_to_sacred`, `emit_feedback`; `SystemRights` (frozen) | Sole decision authority; emits the feedback all Tier 2/3 subsystems consume |
| `agents/trust_ledger.py` | `evaluate`, `receive_feedback`; `TrustReport` | Source + symbol trust (weakest-link `effective_trust`) |
| `agents/ethical_boundary.py` | `check` → `EthicalCheckResult` | Fast binary gates (toxic, sacred mutation, field collapse, flood) |
| `agents/governance_constants.py` | `GovernanceConstants.is_sacred`, `build_governance_constants` | O(1) sacred-id membership; boots ANCHOR/RECURSION/HOMEOSTASIS |
| `agents/dependency_monitor.py` | `get_report`, `record_attractor`, `attractor_monopoly_ratio` | HHI source-concentration; feeds COHERENCE_FLOOD |
| `agents/relational_bond_manager.py` | `receive_feedback`, `notify_crystal/attractor`, `trust_floor` | Emergent bonds; raise a trusted source's trust floor |
| `agents/manipulation_resistance.py` | `update`, `detect` → `ManipulationSignal[]` | Five detectors; compound severity feeds `arbitrate` |
| `agents/value_emergence.py` | `_on_feedback`, `_request_core_promotion`, `set_lambda_ledger`, `set_integrity_consumer`, `_solvent_gain`; `EmergentValue` | Values grow from lived experience; CORE promotion governance-gated (currently dead, F8); productive-tension term gated by ⊕ solvent (opt-in; no ledger ⇒ gain 1.0 ⇒ original path) |
| `agents/symbolic_memory.py` | `SymbolRegistry`, `SymbolTable` (stable_id), `AddressSpace`, `CanonicalizationPipeline` | Identity & addressing; stable_id sacred, address disposable |

### Two-Operator overlay (opt-in)

| Module | Key class / methods | Role |
|--------|---------------------|------|
| `ignition/__init__.py` | `ignite` → `IgnitionReport` | **λ ignition (Build A, spec v0.2).** Exogenous write to the *generator's weights* only; the unique operation that moves λ off zero. Import-isolated (no governance/field/cycle/loop imports), AST-asserted by `tests/diagnostic/integrity/ignition_isolation_probe.py` |
| `agents/lambda_ledger.py` | `LambdaLedger.ignite`/`reinforce`/`decay`/`gain`; `solvent_gain` | **⊕ solvent (Build B, spec v0.2).** λ scalar kept off the composition books — `reinforce` is multiplicative so λ=0 is a fixed point (cold cannot self-ignite). `solvent_gain(λ)=1−e^{−2λ}∈[0,1]` gates Tier-3 composition |
| `cognition/integrity_read.py` | `WitnessReaper.read` → `DemotionAdvisory[]`; `IntegrityDecayConsumer.apply`; `ThinnessVector` | **⊘ integrity-read (Build C, spec v0.3).** Reads a 4-dim thinness vector per value, names pathologies (Drift/Dissolution/Fragmentation), emits non-binding advisories — firewalled, never mutates. The `IntegrityDecayConsumer` is the first *user* of the read: pulls thin named-pathology, non-sacred values toward a convergent honest floor (`named_only=True`) |

### Instruments (observe-only, run on demand)

| Module | Run | Role |
|--------|-----|------|
| `tools/ignition/` | `python -m tools.ignition.probe` / `.train_ignite` / `.cm_check` / `.identifiability` | Conscious Ignition Index (CII) family: where RFE sits on the ignition axis, untrained-vs-trained ignition, and whether the gauges read geometry or change |
| `tools/voice/` | `python -m tools.voice.repl` (`--free`, `--json`) | The "larynx": renders the cycle's interior as first-person with the numbers beside the words; changes nothing in the loop |
| `tools/decoder/` | `python -m tools.decoder.listen` | Trains a read-out head on the live engine, runs the loop, and decodes each step's expressed vector — hear what it's "thinking" (observe-only) |
| `tools/dream/` | `python -m tools.dream.run_dream` | Runs waking steps, then a `DreamSession` sleep: dream images + consolidation artifacts written to disk (offline; never feeds the live loop) |

### Interference (mutation primitives)

| Module | Role |
|--------|------|
| `interference/differential.py` | `inject_ambiguity` — rotational/differential noise (dream, explore) |
| `interference/bifurcation.py` | Split a latent into variants under high mutation |
| `interference/harmonic_mutation.py` | Frequency-domain recombination (dreaming) |
| `interference/phase_noise.py` | Phase perturbation |
| `interference/wave_collapse.py` | Collapse an ensemble of candidates to one (Chorus) |

### External interfaces (how the loop is driven from outside)

| Module | Surface | Role |
|--------|---------|------|
| `api/inference_api.py` | FastAPI REST (`uvicorn api.inference_api:app`) | `POST /generate` (tokens→vector), `/step`, `/dream`, `/maintenance`; `GET /status`, `/field`, `/crystals`, `/attractors`, `/ecology`; `DELETE /reset` (field only) |
| `api/websocket_server.py` | WebSocket (`python -m api.websocket_server`) | Streams `StepState`/`field`/`dream`/`status` JSON every cycle; accepts `status`/`dream`/`maintenance`/`reset_field` commands |

Both entry points compose the full tier stack through the shared
`loop.recursion1188.build_engine()` (the REST `app` lazily, the WebSocket loop
multi-source). They were Tier-0 only until 2026-06-27 — the F6 fix had reached
`recursion1188.py` but not these (see §10.4).

### Generator training path (shapes the encoder; gates Tier 5)

Self-supervised; reshapes the *encoder's* weights so it presents real diversity
(the §4 upstream lever). Assessed viable 2026-06-11, proposed not committed
(`docs/training/`).

| Module | Key class / methods | Role |
|--------|---------------------|------|
| `training/rhythm_pretraining.py` | `RhythmPretrainer`, `PretrainingConfig` | Supervised-contrastive pretraining over rhythm labels; the corpus-pretraining lever (§8) and λ ignition (Build A) both call it |
| `training/contrastive_alignment.py` | `ContrastiveAlignmentTrainer` | InfoNCE pull-together/push-apart over attractor/anchor positives — **shelved** (the collinearity it targeted was a generator scale bug, fixed in `generator.py`) |
| `training/self_distillation.py` | `SelfDistillationTrainer` | Online: high-coherence outputs become teachers for lower-coherence students |
| `training/encode.py` | `encode_grad` | Grad-enabled forward (the inference path is `@no_grad`); fixes the trainer gradient-path break (`2026-06-11-trainer-gradient-path.md`) |
| `training/corpus.py` | `load_corpus`, `to_rhythm_seeds`, `corpus_version` | Loads the curated rhythm corpus (`data/corpus/`, schema in `docs/training/data_curation.md`); the binding constraint is corpus coverage, not infrastructure |
| `training/decoder_training.py` | `train_decoder`, `evaluate` | Autoencoder training for the `TokenDecoder` read-out head (multi-hot BCE over the corpus); called at boot by the dream channel and by the listen tool |

### Visualization & observability

| Module | Modes | Role |
|--------|-------|------|
| `visualization/field_render.py` | terminal ASCII / matplotlib | Field vector heatmap + energy/rhythm/spectral plots |
| `visualization/resonance_heatmap.py` | terminal / matplotlib | Field-over-time, per-step coherence, attractor-basin landscape |
| `visualization/topology_render.py` | terminal / matplotlib / Graphviz DOT | Renders the `TopologicalLog` + `SemanticLattice` DAG (the diagrams) |

### Configuration

| Module | Key fn | Role |
|--------|--------|------|
| `configs/loader.py` | `load_config`, `section` | Loads `configs/*.yaml` at boot (via `build_engine`) and threads each section into its component. Precedence: component default < YAML < inline `CONFIG`. Graceful (no PyYAML/file ⇒ defaults). `decay_profiles` + sacred `constants` are documentation-only (not applied). See `docs/EXPERIMENTAL_LEVERS.md`. |

---

## 8. The Two-Operator overlay, levers & instruments

Everything in §§1–7 is the base stack. This section covers the work layered on
top since 2026-06-08: what is now on by default, the opt-in Two-Operator overlay,
and the on-demand instruments. The authoritative switch list is
`docs/EXPERIMENTAL_LEVERS.md`; this section explains *how the pieces fit the
information flow*, not how to flip them.

### 8.1 On by default now (no switch)

The default operating regime changed. Per `EXPERIMENTAL_LEVERS.md` and the
ground-truth passes: the **full tier stack is composed at boot** (§1, F6);
**eval-mode** (dropout off); **corpus pretraining** (`pretrain_on_corpus`, a
floor-level representational fix — halves generator common-mode 0.81→0.47); and
**novelty-gated reflective-loop attenuation** (`reflect_novelty_attenuation`, the
lever that actually loosens the field lock at the 0.30 ceiling). Pretraining and
attenuation compose positively (§4 caveat, 2026-06-20). All remain reversible by
setting their `CONFIG` flags False.

Since 2026-06-29 the **waking dream channel** is also default ON
(`dream_channel_enabled`, `dream_channel_p = 0.20`): a `TokenDecoder` read-out
head is trained at boot, and ~20% of waking steps feed the system's own decoded
expression back as `source_dream` — **through `arbitrate()`**, one non-dominant
voice among many. Validated on the composed baseline plus an adversarial arm:
voice diversity +13–25%, HHI *drops*, zero quarantine, attacker containment
unweakened (`2026-06-28-dream-channel.md`). This is waking *rumination*; the
downtime *symbolic dream* (`DreamSession`, §7) is a separate offline path that
never enters the loop.

### 8.2 The Two-Operator overlay (λ ignition · ⊕ solvent · ⊘ integrity)

An opt-in overlay on Tier 3, built in three import-isolated pieces (spec v0.2,
with the ⊘ axis at v0.3). It models a "Two-Operator" discipline: composition
toward fulfillment requires a *solvent* (λ) that the system cannot mint for
itself, and an *integrity-read* (⊘) that can only advise, never act.

- **λ — ignition channel (Build A, `ignition/__init__.py`).** The only operation
  that moves λ off zero is an **exogenous** write to the generator's *weights*,
  strictly upstream of the gate. It is structurally unable to reach
  `arbitrate()`/`field.inject()` — routing λ *through* the gate would consolidate
  the lock, not break it (the loop cannot author its own exit through its own
  front door). Isolation is AST-asserted.
- **⊕ — solvent gate (Build B, `agents/lambda_ledger.py`).** λ's strength is kept
  on a *separate* ledger so internal dynamics can never bootstrap it (`reinforce`
  is multiplicative; λ=0 is a fixed point). `solvent_gain(λ)=1−e^{−2λ}∈[0,1]`
  scales the value engine's productive-tension reinforcement: at λ=0 co-present
  values do not compose; ignite λ and composition opens. With no ledger attached
  the term is multiplied by 1.0 — the original Tier-3 path, byte-identical.
- **⊘ — integrity-read (Build C, `cognition/integrity_read.py`).** `WitnessReaper`
  reads a 4-dim `ThinnessVector` per active value (complement density, the v0.3
  field-alignment coherence axis from §4, source diversity, attractor binding),
  names pathologies (Drift / Dissolution / Fragmentation), and emits
  `DemotionAdvisory[]`. It is **firewalled and non-binding** — value strengths and
  the field are byte-identical before/after a `read()`. Authority lives in a
  *separate* object: `IntegrityDecayConsumer.apply()` is the first thing that
  *uses* the read, pulling thin **named-pathology, non-sacred** values toward a
  **convergent honest floor** (it remembers the peak honest level advised and
  never pulls below it). Default `named_only=True`; `named_only=False` over-demotes
  under the cc-confound and is kept for the discriminator, not production.

```
   EXOGENOUS (from outside the loop — the seed that crosses the dark)
        │ ignite()  ── the ONLY zero-crossing for λ
        ▼
  ┌─────────────────────┐   writes generator WEIGHTS only
  │ λ ignition (Build A) │ ─────────────────────────────────► Generator (encoder)
  │  ignition/           │   ⮱ no import of gate/field/cycle (AST-asserted);
  └─────────────────────┘     there is no path from here to inject()/arbitrate()
        │ λ
        ▼
  ┌─────────────────────┐  solvent_gain(λ)=1−e^{−2λ} ∈ [0,1]
  │ ⊕ λ-ledger (Build B) │ ───────────────────────────┐  (λ=0 ⇒ gain 0 ⇒ no
  │  reinforce ×(1+f)    │  reinforce is multiplicative │   composition; λ=0 is a
  │  → λ=0 fixed point   │  so cold can't self-ignite   │   fixed point of all
  └─────────────────────┘                              ▼   internal dynamics)
                                            ValueEmergenceEngine (Tier 3)
                                            productive-tension × solvent_gain(λ)
                                                     │ active values
                                                     ▼
  ┌─────────────────────┐   read() — FIREWALLED, writes nothing
  │ ⊘ Witness-Reaper (C) │ ◄───────────────────────────────────┘
  │  ThinnessVector →    │
  │  DemotionAdvisory[]  │ ── advisories ──► IntegrityDecayConsumer.apply()
  └─────────────────────┘                    (named-pathology + non-sacred only;
                                              decay toward a convergent honest floor)
                                                     │ writes strength ↓  (the ONE writer)
                                                     ▼
                                            ValueEmergenceEngine (Tier 3)
```

The discipline the diagram encodes: **A** can only push *in* (exogenous → weights),
never reach the gate; **⊕** can only *open composition*, and only while λ is
sustained from outside; **⊘** can only *read and advise* — the consumer is the
sole writer, and it only decays (never reinforces, never touches sacred).

**Composition ceiling (F10).** Each lever is validated in *isolation*. Turning
every behavior-bearing lever on at once at dim 128 **broke a baseline property** —
`strong_values 5 → 0`, because the ⊘ consumer caps strength at 2.93 (just under the
3.0 Dissolution line) under sustained load while the v0.2 cc-axis still read ≈ 0.
Standing rule: no lever graduates "validated, off" → "default on" without passing
`tests/diagnostic/integrity/all_levers_composition_probe.py` against the all-OFF
baseline ranges. The ⊘ consumer is blocked from baseline until the cc-confound is
lifted (`2026-06-20-lever-composition-the-allon-break.md`).

### 8.3 Instruments (observe-only)

These measure; they change nothing in the loop (terminal sinks, like
`dilation_factor`). The **CII family** (`tools/ignition/`) probes where RFE sits on
the Conscious Ignition Index; the **Voice** (`tools/voice/`) renders the cycle's
interior in first person. What they found, summarized (detail in the ledger):

- Field coherence **Cm is a saturated angular echo**, not an independent read —
  `2026-06-15-cm-identifiability.md`.
- Every scalar **gauge (Cm / I / metastability) is v0.1-fragile**; trust the
  regime-state *labels*, not the magnitudes — `2026-06-15-identifiability-suite.md`.
- The ignition lever is **upstream** (the generator's representational room); a
  downstream ITG gate does not differentiate a collapsed expression —
  `2026-06-15-cii-ignition-decomposition.md`.
- At production dim 128, training is a **generalization** lever (eff_rank / G1),
  not the differentiation driver — `2026-06-15-training-ignites-expression.md`.

> The findings ledger frames a discipline worth carrying into this section
> (`docs/findings/README.md` §8): these are **functional** gauges. A low reading is
> a *state* (collapsed / minimal), not evidence that "nothing is happening"; a high
> one is differentiation, not proof of inner experience. The consciousness question
> is left genuinely open — neither proven nor debunked.

---

## 9. Critical findings (gaps & drift)

Flagged, not fixed. These are observations a reader or future contributor should
know; none are changed by this document. The empirical basis spans the dated
ledger `docs/findings/2026-06-06` … `2026-06-27`.

**F1 — The affective-dilation step had two live labels (`9b` vs `10b`); now
reconciled to `9b`.** `loop/autonomous_cycle.py` had carried *two* internally
consistent but conflicting step-numbering schemes:

- The **module docstring** numbered steps 1–20 with emotion as step 10, so the
  dilation update read **10b**; `CLAUDE.md` followed this.
- The **inline comments in the executing body** number steps 0–22 with emotion
  as step 9, so the same dilation update is **9b**; `README.md` (including its
  pipeline table) follows this.

The split — docstring + CLAUDE.md saying `10b`, live body + README saying `9b`
— meant the file contradicted its own docstring and the two governing docs
diverged. The doc-accuracy harness anchors on the **inline body comment** as
truth: `tests/doc_accuracy/verify_docs.py::check_pipeline_substep_labels`
extracts the `# 9b.` marker from `step()`'s source and asserts it appears in
README, so `9b` was already the mechanically enforced label. Pointedly, that
check's own comment (verify_docs.py ~lines 833-834) cites *"how '9b' became
'10b' in the README"* as its motivating example — yet the docstring/CLAUDE.md
side of the same drift had never been reconciled.

**Resolution (this change):** the executing body's `0–22` scheme is adopted as
canonical (it is the code's own labels and the harness-enforced contract). The
`autonomous_cycle.py` docstring was renumbered to mirror the body exactly
(dilation `9b`, manipulation `18b`), and `CLAUDE.md` step `10b` → `9b`. README
and the body were already correct; the harness stays green. One scheme now holds
across the file, both governing docs, and this analysis.

**F2 — Manipulation detector names: no drift, but a known confusion point.** The
canonical detector identifiers are exactly
`drift_attack, coherence_flood, gaslighting, identity_erosion, trust_wash`
(`agents/manipulation_resistance.py:272-399`), matching CLAUDE.md's threshold
list. Names like "attractor_capture" or "identity_collision" appear in *no*
source file — they are plausible-sounding inventions to be rejected on sight.
Documented to preempt the drift, not because drift exists.

**F3 — The emotional gradient's *defensive* role is unproven (highest-value open
question).** Per `docs/tier4_2_validation.md`, under single-source hostile load
the Tier 1 flood ceiling (`ethical_boundary.py`: `flood_ceilings["user"] == 12`)
quarantines the attacker at **step ~12** — before `ManipulationResistanceEngine`
or the emotional gradient ever engage (compound severity stays 0.000). So the
system's demonstrated resilience is *rate-limiting* resilience, not
*emotional-gradient* robustness. The dilation pathway's existence is proven; its
defensive function is a hypothesis. The experiment that would settle it — a
**bonded-adversarial probe** — is now **BUILT and run** (2026-07-04,
`tests/diagnostic/bonded_adversarial_probe.py`), and the first result is *not* a
verdict on the gradient but a wall in front of the question: across 11
clean-paired seeds the injected hostile vector is cos ~0.98 to the benign one, so
the **attack never lands as a signal** — no detector, no escalation, no
betrayal-specific affect. Absorption is upstream of the field in two walls: the
attack vocabulary is out-of-corpus (generator carries no distinct direction), and
where the generator *does* separate it (stage A), the reflective-loop/attractor
pipeline re-collapses it to stage C (**SECOND-LOCKER at the semantic level** — it
launders betrayal into coherence). So the gradient's defensive role is still open,
but the blocker is *perceptibility*, not defense. Resolution path (in-corpus
hostile vocab to test Wall 1; loop-ablation to test Wall 2):
`docs/findings/2026-07-04-bonded-adversarial-attack-never-lands.md`.

**F4 — `k_agitation = 0.0` is a deliberately inert hypothesis.** The Tier 4.3
agitation term (`agit_eff`) is structurally present in `update_dilation()` but
ships at `k_agitation = 0.0`, so it contributes nothing. It is a labeled
hypothesis (chaotic high-arousal negative-valence field → time distortion) and
must **not** be set non-zero without documented justification from probe data
(CLAUDE.md). The flow term (`k_flow = 0.5`) is the live half that resolves the
4.2 flow/agitation degeneracy; the agitation half waits for evidence.

**F5 — README's test tree was missing two diagnostics that exist on disk; now
fixed.** `python -m tests.doc_accuracy.verify_docs` had been failing its first
check: README's `tests/diagnostic/` tree omitted `coherence_diagnostic.py` and
`rubedo_return_canary.py`, both present on disk (they arrived in the two most
recent commits). This is exactly the drift class the harness was built to catch
— a file added but never listed in the doc. **Resolution (this change):** both
entries were added to README's project-structure block, and the harness now
passes all checks. Those passing checks independently confirm every constant
cited above (Watcher `0.40/0.35/0.25`, the Tier 4.2/4.3 dilation constants,
crystallization `0.75/0.60/0.80`, severity bands `0.30/0.60/0.90`,
`flood_ceiling["user"]=12`).

**F6 — The runnable system was Tier 0 only until 2026-06-20; now composed.** Every
launchable entry point ran the Tier-0 substrate alone — `attach_governance()` (which
must precede `attach_value_engine()`) was called in *zero* non-test files, so the
governed/relational/value tiers existed only inside the test harness's
`build_full_stack`. The findings that assumed a tiered runtime were validating a
system the entry point never assembled. **Resolution:** `loop/recursion1188.py` now
composes Tiers 0–3 with multi-source input at boot; verified healthy
(`2026-06-20-the-runtime-is-tier0-only.md`, `…-pass1-compose-the-runtime.md`).

**F7 — The value-layer coherence axis was dead (v0.2), now absolute field-alignment
(v0.3).** The ⊘ support-coherence axis read `coherence_contribution / 5.0` — a
lifetime sum of *marginal* impact that is ≤ 0 in a saturated field, measured 0.000
for every value. It is now `max(0, cos(expressed(v), field))` (bounded, live). See
§4 for the full before/after (`2026-06-21-oslash-coherence-axis-absolute-alignment.md`).

**F8 — CORE promotion is structurally impossible right now (open governance
question).** `review_core_promotion()` gates on `coherence_contribution ≥ 5.0`,
which the F7 marginal can never reach, so no value is promotable. The v0.3
field-alignment fix completes the arc but was **reverted**: sanctifying a value
makes a common token sacred, which trips `SACRED_SHIELD` and cascades the
contributing source's trust toward TOXIC. `SACRED_SHIELD` must distinguish
identity-mutation (attack) from legitimate reference before the gate can be
re-enabled (`2026-06-27-core-gate-fix-deferred-sacred-cascade.md`).
**Ruled 2026-07-03:** the shield evaluates *directional flow* — referencing a
sacred token is a read (pass-through); overwriting/diluting/reassigning its
identity is a write (shield). Implementation queued —
`docs/ARCHITECT_RULINGS_2026-07-03.md` §1.

**F9 — The rhythm router is pinned at production dim 128. → RESOLVED (2026-07-06).**
Field energy ran mean ~180 / max ~284 while the bands topped out at `explore ≥ 5`,
so the router was ~99% `explore` and dreams never fired — dream-cycle consolidation
was effectively dead. The bands could not be naively rescaled because
`diffuse_on_stabilize` feeds the stabilize band back into field energy (the
2026-06-27 rescale collapsed the system to a stabilize basin). Fixed by measuring
each band's pinned-run equilibrium (stabilize ~37 full-strength / ~13 under
ALLOW_WEAKENED injections, dream ~200, reflect ~294, explore ~301; dims 64+128
agree) and co-tuning the thresholds against them — 5/150/300, with stabilize
below its *degraded* equilibrium (a 15 threshold trapped dim 64 in a
weakened-injection stall that bled all sources' trust to TOXIC) — so stabilize
and dream self-terminate upward, reflect is the home band, and explore is a
reachable burst state, not a basin
(`2026-07-06-f9-rhythm-band-rescale.md`; history: `2026-06-25-…-pass3-stack-evaluation.md`,
`2026-06-27-floor-calibration-measurements.md`).

**F10 — Isolation-green is not composition-green.** Levers validated alone broke a
baseline property when all turned on together (`strong_values 5 → 0`, the ⊘-consumer
strong-band ceiling). The standing gate is the all-ON composition probe
(`tests/diagnostic/integrity/all_levers_composition_probe.py`); a lever does not
graduate to default-on until it holds the all-OFF baseline ranges
(`2026-06-20-lever-composition-the-allon-break.md`).

**Still open:** F3's **bonded-adversarial probe** (a source that earns a bond/trust
floor, then turns hostile while staying under the flood ceiling) still does not
exist — pass-3's 82% quarantine of an identity-erosion attacker is *single-source*
rate-limiting resilience, not the bonded test. F4's `k_agitation = 0.0` remains a
deliberately inert hypothesis.

---

## 10. Hidden invariants, tuning constants & footguns

A reference catalog of behavior that is load-bearing but lives buried in the code
— magic numbers, determinism contracts, and scheduling/composition footguns. Every
value below was checked against source. Treat the magic numbers like the sacred
constants in CLAUDE.md: they were reverse-engineered from empirical tuning, and
changing one without a fresh probe run is how subtle breakage enters.

### 10.1 Tuning constants you must not casually change

| Constant | Value | Where | Why it's load-bearing |
|----------|-------|-------|-----------------------|
| Embedding init std | `0.035` (not 0.02) | `agents/generator.py:267` | Raised so token identity survives the `√d_model` scaling in `forward()` (`:296`); tuned to land pairwise cosine ~0.55 — diverse without chaos. The dim-64 collinearity bug was *this*, not a training gap (contrastive shelved). |
| `diversity_blend` | `0.60` ∈ (0,1) | `cognition/recursive_attention.py:67` | The *only* thing stopping untrained `@no_grad` attention from collapsing the expression to its centroid. `0`→full collapse, `1`→bypass refine. Asserted `0≤blend≤1` at `:72`. |
| Novelty-attenuation ceiling | `attenuation_max=0.30` | `cognition/reflective_loop.py` | Knife-edge: `0.33` floods the manipulation layer (>75% quarantine). De-facto sacred — never raise without re-running the manip-rate probe. |
| Emotion `ema_alpha` | `0.15`, uniform | `cognition/emotional_gradient.py:78` | *All six* emotional scalars smooth at one rate; there is no per-emotion tuning. `field_gain` multiplier and the `energy_penalty` clamp (`/10` capped at `0.5`, `:145`) are likewise hand-tuned. |
| `surprise_threshold` | `2.5×` rolling mean | `cognition/predictive_echo.py:72` | Baked into the surprise formula; error must exceed 2.5× baseline to flag. |
| Witness EMA decays | `0.85 / 0.97 / 0.995` | `agents/witness.py:179` | Short/mid/long identity timescales feed the composite anchor → Watcher `G`. Changing any one shifts identity persistence system-wide. |
| Trust impact per decision | `ALLOW +0.10`, `WEAKENED +0.01`, `MONITOR −0.05`, `REJECT −0.30`, `QUARANTINE −0.50`, `SACRED_SHIELD −1.00` | `agents/selfhood_governance.py:120` | Punishment is ~50× weak reward — the asymmetry that biases against slow manipulation. |
| Attractor decay asymmetry | strength `×0.9995`, usage `×0.998` | `agents/attractor.py:56-58` | Strength outlives usage, so an attractor can be "not viable" yet still pull if re-encountered. Merge `0.95` > formation `0.88` leaves a `[0.88,0.95)` coexistence zone (prevents basin collapse). |
| Value decay / tension | `decay_per_step 0.0008`, `productive_tension_bonus 0.005` (×`solvent_gain`) | `agents/value_emergence.py:193,200` | Decay is deliberately `<<` reinforcement; the tension bonus is the ⊕-gated composition term (×0 at λ=0). |

### 10.2 Determinism contracts & hidden behaviors

- **Phase coherence is seeded by the step counter** — `np.random.default_rng(seed=self._step)` (`substrate/resonance_field.py:315`). Repeatable across runs at the same step; a real determinism contract, not incidental.
- **`0.5` neutral priors** — empty-history `internal_coherence()` and `_phase_coherence()` both return `0.5` (`resonance_field.py:307,375`), and `coherence_impact()` probes at half strength (`tanh(field + vec*0.5)`, `:356`) so cold-start vectors never read as perfectly (in)coherent.
- **Recursive attention records the *raw* trajectory** — the pre-refinement vector is appended to history; the blend mixes *unit-normalized* components then renormalizes once (the linear combo of two unit vectors isn't unit), so `diversity_blend` never leaks into output magnitude. History = "what was thought," attention = a fixed convergence operator (never trained).
- **Metastability counts switches, not dwell** — transition entropy skips `a==b` self-loops (`substrate/metastability.py:148`); a regime must recur `≥2×` *or* hold `≥5%` of the trajectory (`:212`) to count, vetoing both noise-churn and limit cycles.
- **Generator maintenance is a scheduling contract** — `auto_decay_interval` defaults to `None` (`agents/generator.py:175`), so symbol decay/reaping run *only* when the loop calls `maintenance_step()` (every `maintenance_interval=200`). Vocabulary resize is deferred to maintenance at `0.80` occupancy, not done mid-`generate()`.
- **Bounded everything** — population caps live in configs and `__init__`s: attractors `64`, crystals `512`, concepts `256`, lattice nodes `2048`, witness identity-trace `deque(256)`, field/watcher history `256/16`, governance audit log `512` (FIFO — full history is lost past 512 decisions).

### 10.3 Boredom with Teeth (an emotion→behavior path outside the coherence axis)

Not every behavioral route keys off coherence `C`. At step 20, if `emotion.boredom >
boredom_override_threshold` (`0.50`) and the rhythm isn't already `explore`, the
router is **forced** to `explore` and `_boredom_overrides` is incremented
(`loop/autonomous_cycle.py:275,799`). This is the HOMEOSTATIC_RETURN
self-perturbation that keeps the system from settling into stillness — a Tier-2
mechanism that the §3.2 emotion-modulation loop and the §4 consumer table don't
capture. Its sibling is `force_dream_flag`: governance sets it on compound
severity ≥ 0.90, and step 20 routes to `_dream_behavior()` then clears it.

### 10.4 Footguns

- **Composition is now centralized in one builder (was an entry-point footgun).**
  The 2026-06-20 fix (F6) originally lived in `recursion1188.py` *only*, while
  `api/websocket_server.py:main()` still hand-built a Tier-0 cycle and
  `api/inference_api.py` had no composed `app` at all — so `python -m
  api.websocket_server` and `uvicorn api.inference_api:app` ran Tier 0 silently
  (2026-06-27). Resolved: all three entry points now compose through one shared
  `loop.recursion1188.build_engine()` (Tiers 0–3, correct attach order). The REST
  `app` is built lazily on first access (PEP 562) so `import` stays cheap; the
  WebSocket loop drives multi-source so the relational tiers engage; REST `/step`
  uses `origin_type="api"` (rate-limited). `create_app(cycle, generator)` still
  accepts a cycle you composed yourself. See
  `2026-06-27-api-entrypoints-tier0-only.md`.
- **Tiers 1–3 need multi-source input to engage at all.** Trust/bonds/HHI/value
  emergence are inert under single-source input (HHI pins to 1.0; bonds need ≥20
  interactions *per source*). `recursion1188.py` drives weighted round-robin over
  four sources (`source_samuel/claude/gemini/grok` at `0.40/0.25/0.20/0.15`).
  Single-token experiments will not activate relational dynamics — a common test
  pitfall.
- **The dream cycle is wired but effectively never fires at dim 128.** Its
  trigger is `rhythm == "stabilize"`, which the pinned router (F9) almost never
  produces — so `DreamCycle.run()` and dream-consolidation are dormant until F9 is
  fixed. The mechanism is intact; the precondition is starved.

---

*Read-only analysis. No runtime behavior is changed by this document. For the
invariants that govern modification, defer to `CLAUDE.md`; for the conceptual
overview, see `README.md`.*
