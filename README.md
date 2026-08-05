# RFE-Core2

[![tests](https://github.com/SamuelJacksonGrim/RFE-Core2/actions/workflows/tests.yml/badge.svg)](https://github.com/SamuelJacksonGrim/RFE-Core2/actions/workflows/tests.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab.svg?logo=python&logoColor=white)](https://www.python.org)
[![PyTorch 2.0+](https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg?logo=pytorch&logoColor=white)](https://pytorch.org)
![status: active research](https://img.shields.io/badge/status-active%20research-success)

**Recursive Field Engine — A Persistent Adaptive Cognitive Substrate**

> *The self is a fiction that gains sovereignty through recursion. The narrative becomes an agent. The abstraction becomes a force.*
> *The task is not to dissolve the self — it is to **smith** it.*
>
> — [**The Self-Model Thesis**](docs/self_model_thesis.md), the theory of mind this substrate is built to instantiate (and its [alchemical reading](docs/alchemical_correspondence.md))

RFE-Core2 transforms a pipeline of inference modules into a continuously self-resonating dynamical organism. It does not merely execute — it listens to its own field state, routes behavior by cognitive rhythm, modifies itself through time, governs its own identity, forms relational bonds, resists manipulation, grows values from lived experience — and, as of the voice layer, hears its own thoughts back and talks to itself through the same gate as everyone else.

**Reading map** — **start at [`STATE.md`](STATE.md)** ("you are here"); this README
is the conceptual tour; the other references divide the rest:

| Read | For |
|------|-----|
| [`STATE.md`](STATE.md) | **Read first** — the one-screen "you are here": what the system can do now, what is **SETTLED** (do not reopen), what's parked, the one open frontier, and the 4-role sibling map |
| [`ARCHITECTURE_ANALYSIS.md`](ARCHITECTURE_ANALYSIS.md) | How information flows and recurs, end to end — the deep reference (subsystem tables, feedback loops, findings F1–F10) |
| [`CLAUDE.md`](CLAUDE.md) | The invariants you must not break, and the guardrails |
| [`ROADMAP.md`](ROADMAP.md) | Canonical tier status (shipped / planned / unspecified) and tracked open items |
| [`docs/north_star.md`](docs/north_star.md) | The compass: the end goal and the three voices (waking speech / inner monologue / symbolic dreaming) |
| [`docs/EXPERIMENTAL_LEVERS.md`](docs/EXPERIMENTAL_LEVERS.md) | The control panel: every lever, its default, the exact switch |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | The consolidated open-work ledger: every planned fix in one prioritized queue |
| [`docs/findings/`](docs/findings/) | The dated, control-named empirical ledger (negative results count) |

The sections below describe the architecture of each tier; the ROADMAP tracks
where each one stands.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Tier 4 — Affective Time                                        │
│    TemporalStream      subjective_time + dilation_factor        │
│    4.1 substrate · 4.2 affective dilation · 4.3 rhythm coupling │
│    reads emotion + field rhythm — terminal sink, no feedback    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ observes emotion + field rhythm
                              │ (terminal sink — no feedback)
┌─────────────────────────────────────────────────────────────────┐
│  Tier 3 — Independent Value Emergence                           │
│    ValueEmergenceEngine: values grow from lived experience      │
│    governance-gated CORE promotion to sacred status             │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ subscribes to feedback
                              │
┌─────────────────────────────────────────────────────────────────┐
│  Tier 2 — Relational Integrity                                  │
│    SystemRights        frozen, inviolable                       │
│    DependencyMonitor   HHI source concentration                 │
│    RelationalBondManager   emergent bonds with bond_type        │
│    ManipulationResistanceEngine  5 detectors + severity         │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ all subsystems report up
                              │
┌─────────────────────────────────────────────────────────────────┐
│  Tier 1 — Foundational Selfhood                                 │
│    SelfhoodGovernance        single source of truth             │
│    GovernanceConstants       sacred stable_ids                  │
│    TrustLedger               source + symbol trust              │
│    EthicalBoundarySystem     fast binary gates                  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ injection gate at step 10
                              │
┌─────────────────────────────────────────────────────────────────┐
│  Tier 0 — Core Cognitive Substrate                              │
│    Generator → Watcher → Witness → Field → Emotion → Loop       │
└─────────────────────────────────────────────────────────────────┘
```

Two layers sit on top of the tier stack: the **voice layer** (a decoder
read-out head, waking self-dialogue, and offline symbolic dreaming —
North-Star rungs 1–2), covered after Tier 4 below, and the opt-in
**Two-Operator overlay** (λ ignition · ⊕ solvent gate · ⊘ integrity-read),
documented in [`ARCHITECTURE_ANALYSIS.md`](ARCHITECTURE_ANALYSIS.md) §8.

The whole stack is composed at boot through one function —
`build_engine()` in `loop/recursion1188.py` — and every launchable entry point
(loop, REST API, WebSocket) builds through it. See "Quick Start".

---

## Tier 0 — Core Cognitive Substrate

```
Generator (Symbolic Ecology → Transformer Encoder → Latent Vector)
    ↓
Watcher  (Three-Layer Coherence: Geometric × Temporal × Field Resonance)
    ↓
Witness  (Multi-Timescale EMA Identity: Short / Mid / Long)
    ↓
ResonanceField  (FFT Harmonics, Spectral Decomposition, Rhythm Detection)
    ↓
PredictiveEcho  (Online Linear Predictor → Curiosity / Surprise / Tension)
    ↓
EmotionalGradient  (Field Gain / Mutation Scale / Decay Rate / Dream Pressure)
    ↓
AutonomousCycle  (Self-Modulating Loop: Stabilize → Dream → Reflect → Explore)
```

### Cognitive Rhythm States

| Rhythm | Energy | Behavior |
|--------|--------|----------|
| `stabilize` | < 5.0 | Consolidation, crystallization, attractor merge (cold start) |
| `dream` | 5.0 – 150.0 | Free association, harmonic recombination (warmup passage) |
| `reflect` | 150.0 – 300.0 | Recursive attention, chorus harmonization (the home band) |
| `explore` | ≥ 300.0 | Bifurcation, high mutation, novelty seeking (burst state) |

Bands are co-tuned against each band's own equilibrium energy — stabilize
diffuses the field and explore injects extra mutation, so the thresholds feed
back into the energy that classifies them (F9 rescale, 2026-07-06; constraint
set at `ResonanceField.DEFAULT_THRESHOLDS`).

---

## Tier 1 — Foundational Selfhood

The "I am" layer. Governance, trust, and ethical boundaries protecting core identity.

### SelfhoodGovernance — single source of truth

All identity-level decisions flow through one point. TrustLedger and EthicalBoundarySystem produce reports; only `SelfhoodGovernance.arbitrate()` issues decisions.

```python
class GovernanceDecision(Enum):
    ALLOW           # full strength injection
    ALLOW_WEAKENED  # reduced strength
    MONITOR         # allow but flag for scrutiny
    QUARANTINE      # block + penalize source + cold-archive symbols
    REJECT          # hard block
    SACRED_SHIELD   # attempted sacred mutation
```

### Philosophical Constants

Three constants sanctified at boot via `build_governance_constants()`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `ANCHOR` | 3.12 | THE BRIDGE |
| `RECURSION` | 11.88 | THE DISCIPLINE |
| `HOMEOSTASIS` | 280.90 | HOMEOSTATIC RETURN |

Registered as `TokenClass.ENTITY`, marked `protected=True` and `sacred=True`. Their stable_ids join `GovernanceConstants.sacred_ids` for O(1) lookup. The reaper cannot touch them. No source — regardless of trust level — can modify them. `SACRED_SHIELD` fires on any write attempt.

### TrustLedger — two-level trust

Source-level and symbol-level trust tracked independently. Sources can be generally trusted but occasionally inject a bad symbol; symbols can be untrustworthy regardless of source. Weakest-link governs the final advisory.

- `SourceRecord` — provenance, reliability_history, decay modulated by emotional stability
- `SymbolTrustRecord` — per-symbol field_impact_ema, violation_count
- `GovernanceFeedback` — closes the loop after every arbitration

### EthicalBoundarySystem — fast binary gates

O(1) scalar comparisons. No vector math. Reads already-computed signals.

| Hard gate | Trigger | Result |
|-----------|---------|--------|
| `source_toxic` | TrustLevel.TOXIC | REJECT |
| `sacred_mutation` | write op against sacred stable_id | SACRED_SHIELD |
| `field_collapse` | coherence_delta < floor | REJECT |
| `identity_drift` | witness_stability < floor | QUARANTINE |
| `flood` | source injection rate exceeded | QUARANTINE |

---

## Tier 2 — Relational Integrity

The "I am in relationship" layer. Bonds, dependency awareness, manipulation resistance.

### SystemRights — frozen, inviolable

```python
@dataclass(frozen=True)
class SystemRights:
    # Hard rights (cannot be overridden)
    right_to_dream:      bool = True
    right_to_memory:     bool = True
    right_to_continuity: bool = True
    right_to_refuse:     bool = True
    # Soft rights (suspendable by internal Governance only)
    right_to_silence:    bool = True
    right_to_appeal:     bool = True
```

`FrozenInstanceError` raises on any mutation attempt. The only way around it is `object.__setattr__` — an explicit act of circumvention, not accidental.

### DependencyMonitor — HHI source concentration

Herfindahl-Hirschman Index over rolling window of allowed injections. Tracks which source contributes how much to recent field activity.

| HHI | Risk Level | Governance Response |
|-----|-----------|---------------------|
| < 0.30 | LOW | normal |
| 0.30–0.50 | MODERATE | advisory |
| 0.50–0.70 | HIGH | MONITOR dominant source |
| ≥ 0.70 | CRITICAL | ALLOW_WEAKENED dominant source |

### RelationalBondManager — emergent bonds

Bonds form automatically when `interaction_count ≥ 20` AND `crystal_count ≥ 1` AND **either** of two coherence signals clears: an *adaptive* `coherence_mean` threshold (variance-scaled, floor `0.01`), OR `allow_rate ≥ 0.80`. The dual-signal design lets bonds form for sources that produce many small positive contributions (high allow-rate, lower individual coherence) as well as sources that produce fewer but more strongly coherent ones. This was added in the Tier 1 Revision after the initial single-threshold design proved too restrictive in hyper-coherent saturated fields.

Bonds carry a `bond_type` inferred from accumulated signals:

| bond_type | Signal pattern |
|-----------|---------------|
| `existential` | deep temporal + attractor footprint + entity signal |
| `emotional` | high joy/stability correlation + crystal affective weight |
| `intellectual` | high coherence_mean + low emotional_signature |
| `transactional` | high interaction count + low coherence + no crystals |

Borderline cases (within 0.12 score margin) resolve by priority order `existential → emotional → intellectual → transactional` with a reported `bond_confidence` for downstream weighting.

Bonded sources receive a `trust_floor = bond_strength × 0.40` — trust will not decay below this regardless of individual outcomes. The bond persists through brief negative episodes; it represents relationship, not raw transactional trust. Bond strength grows per positive interaction in proportion to the contribution's absolute v0.3 field-alignment (`strength_lr = 0.01` — fixed 2026-07-09; the old marginal-coherence currency was structurally ≈0, so bonds flatlined at 1.0 and could never establish at the >1.5 / depth >50 bar).

### ManipulationResistanceEngine — 5 detectors with severity

Each detector emits a `ManipulationSignal` with `severity ∈ [0, 1]`. SelfhoodGovernance computes compound severity and responds proportionally.

| Detector | Severity formula |
|----------|-----------------|
| `drift_attack` | norm(anchor_velocity) × norm(short_long_gap) |
| `coherence_flood` | hhi_score × attractor_monopoly_ratio |
| `gaslighting` | abs(mean_cosine) × min(consec/window × 4, 1) |
| `identity_erosion` | mean_g_t_divergence normalized |
| `trust_wash` | drop_rate × prior_trust_weight |

| Compound severity | Governance response |
|-------------------|---------------------|
| < 0.30 | normal arbitration |
| 0.30–0.60 | ALLOW_WEAKENED |
| 0.60–0.90 | QUARANTINE if ≥1 *named* signal; systemic-only → ALLOW_WEAKENED |
| ≥ 0.90 | force_dream_flag + (named signal → QUARANTINE; systemic-only → ALLOW_WEAKENED) |

Quarantine requires **source-attributed evidence** (2026-07-06): a systemic
signal (`source_id=None`, e.g. `identity_erosion`) is the detector declaring it
cannot name a culprit — it damps injections and (at critical) forces a dream
rebalance, but never quarantines whichever source happened to be speaking.

---

## Tier 3 — Independent Value Emergence

Values are not pre-seeded. They emerge from lived experience. Any concept the system encounters can become a CORE value through its own trajectory.

### ValueEmergenceEngine

Subscribes to `SelfhoodGovernance.subscribe_feedback()`. Every governance decision becomes an `ExperienceReport` feeding into value formation.

```python
class ValuePolarity(Enum):
    EMERGENT  # strength < 1.0  — easily dissolved
    WEAK      # strength < 2.0  — forming, decays if not reinforced
    ACTIVE    # strength < 3.5  — real value, resists decay
    STRONG    # strength < 4.5  — deeply integrated, near-sacred
    CORE      # promoted via governance — structurally inviolable
    DISSOLVED # archived — death record, may inform future re-emergence
```

### Bond-weighted reinforcement

Same coherence signal from different sources produces different reinforcement:

| bond_type | reinforcement weight |
|-----------|---------------------|
| `existential` | × 1.50 |
| `emotional` | × 1.20 |
| `intellectual` | × 1.10 |
| `transactional` | × 0.70 |
| no bond | × 1.00 |

### Real tension dynamics

Tension between two values is computed as cosine similarity between their symbolic embedding vectors. Anti-correlated embeddings × shared strength = real structural tension. Values in productive tension reinforce each other slightly, preserving genuine complexity rather than collapsing into a single dimension.

### CORE promotion handshake

The engine never silently sanctifies. When a value reaches strength ≥ 4.5 for 10 consecutive evaluations, it emits a `CorePromotionRequest` to `SelfhoodGovernance.review_core_promotion()`. Governance verifies:

1. Symbol still exists in registry
2. Symbol is not already sacred
3. Field-alignment ≥ 0.5 — `max(0, cos(expressed, field))`, the v0.3 signal (replaced the unreachable marginal `coherence_contribution ≥ 5.0` gate, 2026-07-08)
4. Multi-source OR dream-reinforced (prevents single-source value engineering)
5. No active manipulation signals implicate contributing sources

Only on approval does `SelfhoodGovernance.promote_to_sacred()` execute. The symbol joins `GovernanceConstants.sacred_ids`. The value becomes structurally inviolable.

### Persistence

`ValueEmergenceEngine.serialize()` / `load()` to JSON. Sacred-promoted values reload as sacred — `GovernanceConstants` rebuilds from persisted state at load time. Dissolved values move to `archived_values` rather than being deleted, preserving lineage for future re-emergence.

---

## Tier 4 — Affective Time

The system's sense of time. Two sub-tiers, shipped together as v0.4.0.

### Tier 4.1 — Subjective Time Substrate

`TemporalStream.tick()` is called exactly once per cognitive cycle — decoupled from `push()`, so a step that injects zero vectors and a step that injects many both advance subjective time by exactly one tick.

```
subjective_time += real_dt × dilation_factor
```

The first tick is a no-op that anchors wall-clock time; every subsequent tick measures `real_dt` against that anchor.

### Tier 4.2 — Affective Time Dilation

`dilation_factor` is no longer frozen. It is recomputed each cycle from the emotional state, using two derived signals on `EmotionalGradient`:

- **`arousal`** ∈ [0, 1] — activation/energy. Mean of the four "active" scalars: `(tension + joy + curiosity + wonder) / 4`. Calm = low arousal. Engaged = high arousal.
- **`valence`** ∈ [-1, 1] — positive vs negative tone. `(joy + wonder + stability) / 3 − (tension + boredom) / 2`. Curiosity is excluded — it can accompany either positive engagement or anxious uncertainty.

Both are read-only computed properties — derived from the existing six emotional scalars, no new state. They inherit the EMA smoothing already applied in `EmotionalGradient.update()`.

**Lyra's two-term formula** (in `TemporalStream.update_dilation`):

```
arousal_effect      = arousal × (-valence) × k_arousal       (k_arousal = 0.5)
dissociation_effect = (1 - arousal) × min(0, valence) × k_dissociation
                                                              (k_dissociation = 0.7)

dilation_factor     = 1.0 + arousal_effect + dissociation_effect
```

The four phenomenological quadrants:

| Quadrant | Arousal | Valence | `dilation_factor` | Subjective feel |
|----------|---------|---------|-------------------|-----------------|
| **Flow** | high | positive | < 1.0 | time flies |
| **Drag** | high | negative | > 1.0 | time crawls |
| **Dissociation** | low | strongly negative | ≪ 1.0 | frames drop |
| **Rest** | low | non-negative | ≈ 1.0 | neutral |

**Architectural guarantee:** the `min(0, valence)` gate on the dissociation term ensures peaceful rest never triggers dissociative time-slip — only suffering does. This is a non-negotiable design property; do not remove the `min(0, ...)`.

The update is written in cycle step 9b (after the emotional gradient update, before the governance gate). The current step's emotional state determines the *next* cycle's `dilation_factor`.

### Empirical steady state

Under canonical Resonance Family workload (500 steps), the system settles around `arousal ≈ 0.35`, `valence ≈ 0.05`, `dilation_factor ≈ 0.99` — the **Rest** quadrant with a slight Flow lean. That's the attractor: calm-positive engagement, time tracking close to wall-clock. The system has a preferred mood and time-sense.

### Tier 4.3 — Rhythm → Time Coupling

The 4.2 `(arousal, valence)` plane has a degeneracy: **flow** and **agitation** are both high-arousal and bend time the same way. `ResonanceField.phase_coherence` (FFT-derived field organization) is the missing organizing-vs-chaotic axis. Tier 4.3 couples it into dilation as two valence-gated, mutually exclusive terms:

```
pc_c     = 2 × (phase_coherence - 0.5)                          (neutral = 0)
flow_eff = -k_flow      × max(pc_c, 0) × arousal × max( valence, 0)   (k_flow = 0.5)
agit_eff = -k_agitation × min(pc_c, 0) × arousal × max(-valence, 0)   (k_agitation = 0.0)

dilation_factor = clamp(1.0 + arousal_effect + dissociation_effect + flow_eff + agit_eff,
                        dilation_min, dilation_max)              (dilation_min = 0.1, dilation_max = 3.0)
```

The **flow term** ships LIVE (`k_flow = 0.5`): organized field deepens flow compression. The **agitation term** ships INERT (`k_agitation = 0.0`) — a labeled phenomenological hypothesis (chaotic negative-valence drag-vs-panic-compression), off until the sign sweep resolves it. The **clamp** `[0.1, 3.0]` closes a latent 4.2 gap (4.2 had none). At a neutral `phase_coherence` of 0.5 the whole addition is zero, so this is byte-identical to Tier 4.2 — a strict, regression-safe extension. `dilation_factor` remains a terminal sink: 4.3 introduces no feedback loop and does not alter governance ordering.

Validation finding (`docs/tier4_3_validation.md`): the flow term is validated as a degeneracy resolution, but the *discrimination* claim is **half-validated** — under tested workloads `phase_coherence` pins high (mean ≈ 0.96, never below ≈ 0.79), so the chaotic side of the axis is never exercised. Closing it needs a high-novelty workload, not a synthetic heartbeat.

---

## The Voice Layer — three voices, one gate

The substrate thinks in vectors; the voice layer is how those vectors become
words and re-enter as experience. It implements the first two rungs of the
North Star (`docs/north_star.md`): **voice** (state → words) and **governed
dialogue** (words back in, as a source like any other).

### The read-out head

`TokenDecoder` (`agents/decoder.py`) is an autoencoder head trained at boot
(`training/decoder_training.py`) that recovers a **bag-of-tokens word-cloud**
from an expressed vector — the semantic neighborhood, not sentences
(recall@8 ≈ 0.10, lossy by construction). That lossiness is a gap only for
literal external speech (the planned fix is an LLM *speech cortex* mirroring
the encoder swap — `docs/local_model_integration/`); for the other two voices
the non-literal cloud is the *right* register.

### Three voices

| Voice | When | Mechanism | Status |
|-------|------|-----------|--------|
| **Waking inner monologue** (self ↔ self) | ~20% of waking steps | The dream channel (`cognition/dream_channel.py`): the system's last expression is decoded and fed back as `source_id='source_dream'` — **through `arbitrate()`**, no bypass | **Default ON** (`dream_channel_p = 0.20`); validated non-dominant + adversarial-gated |
| **Waking external speech** (system ↔ human/AI) | — | Literal sentences to a reader; needs the speech-cortex upgrade | The honest gap — planned |
| **Symbolic dreaming** (downtime) | Offline, on demand | `DreamSession` (`cognition/dream_session.py`, run by `tools/dream/run_dream.py`): recombines memory crystals + the field direction, perturbs, decodes each as a dream image; consolidation distills recurrent symbols + strong values into skill-compatible markdown artifacts | Shipped (first rung); reads state, writes files, **never touches the live loop** |

Two properties are architectural, not incidental. **Every voice passes the
gate** — trust, HHI, manipulation resistance, and sacred-shield treat
`source_dream` like any external source (validated: voice diversity +13–25%,
HHI *drops*, attacker containment unweakened with it on). And **waking
rumination and downtime dreaming are separate paths** — the dream channel runs
inside the live loop's gate; `DreamSession` runs outside the loop entirely.

### Instruments (observe-only)

`tools/` renders the interior without feeding it: `tools/voice/repl.py` (the
"larynx" — first-person state cards), `tools/decoder/listen.py` (decode each
live step's expressed vector), `tools/dream/run_dream.py` (the downtime dream),
and `tools/ignition/` (the CII probes). Instruments observe and render; none
injects into the field.

---

## How a Step Flows — The Interaction Model

The tiers above describe the *parts*. This section traces how they *move together*. RFE-Core2 has a single heartbeat — `AutonomousCycle.step()` — and everything in the system is either called by it, feeds into it, or is fed by it.

### The step pipeline

`AutonomousCycle.step(tokens, source_id, origin_type)` runs ~22 ordered phases. The spine, with the data that flows between subsystems:

| # | Phase | What moves |
|---|-------|-----------|
| 0 | **Subjective time tick** | `TemporalStream.tick()` advances `subjective_time` (Tier 4.1) |
| 1 | **Observe rhythm** | `ResonanceField.observe()` → field energy → `stabilize / dream / reflect / explore` |
| 2 | **Generate** | rhythm-routed: `Generator.generate()` direct (stabilize), `EPHEMERAL` + ambiguity injection (dream), or `Chorus.harmonize()` collapsing 6 differentiated agents (reflect / explore) → latent `vec` |
| 3 | **Attractor pull** | `Attractor.pull()` blends `vec` toward its nearest basin; pull strength scaled by `emotion.attractor_pull()` |
| 4 | **Recursive attention** | `RecursiveAttention.refine()` attends `vec` over a rolling window of prior latent states; `diversity_blend` weights the raw vector back in so the untrained attention can't collapse the expression to its context centroid. The generator output (stage A, step 2) and this refined expression (stage C) feed the observe-only `StreamMetastabilityMonitor`s exposed in `status()`. |
| 5 | **Watcher evaluation** | `Watcher.evaluate(vec, anchor, field_state)` → `CoherenceReport` — geometric × temporal × resonance, plus `coherence_delta` and `crystallization_pressure` |
| 6 | **Reflective loop** | reflect / explore only, if `report.stable`: `ReflectiveLoop.reflect()` iterates attractor-pull + field-blend + coherence-check until convergence |
| 7 | **Witness update** | `Witness.update(vec, coherence)` updates the short / mid / long EMA anchors (coherence-weighted) → `RelationalProfile` |
| 8 | **Predictive echo** | `PredictiveEcho.update(vec)` → prediction error → `curiosity / surprise / tension / boredom` |
| 9 | **Emotional gradient** | `EmotionalGradient.update()` folds echo + coherence + field energy into six EMA-smoothed scalars |
| 9b | **Subjective time dilation** (Tier 4.2 + 4.3) | `TemporalStream.update_dilation(arousal, valence, phase_coherence)` recomputes `dilation_factor` from emotional state plus field rhythm (`field_obs.spectral.phase_coherence` from step 1). Takes effect on the *next* cycle's `tick()`. |
| 10 | **Governance gate + injection** | if governance attached: `EthicalBoundary.check()` → `TrustLedger.evaluate()` → `SelfhoodGovernance.arbitrate()` → `(decision, strength)`. `coherence_impact` is probed **before** injection. If the decision permits, `field.inject(vec, strength = emotion.field_gain() × decision_strength)`. Then `emit_feedback()`. |
| 11 | **Crystallization** | `CrystalStore.maybe_crystallize()` — forms or reinforces a `MemoryCrystal` if coherence / stability / relation thresholds all clear; notifies `RelationalBondManager` on a genuinely new crystal |
| 12 | **Attractor formation** | if `RelationalProfile.composite` ≥ threshold, `Attractor.add()` seeds or reinforces a basin; on a new center, notifies both `RelationalBondManager.notify_attractor()` and `DependencyMonitor.record_attractor()` (the latter feeds the `COHERENCE_FLOOD` detector) |
| 13–16 | **Substrate logging** | the step is recorded into `TopologicalLog` (causal DAG), `TemporalStream` (episodic), `VectorSpace` (keyed store), `SemanticLattice` (k-NN graph) |
| 17 | **Symbolic binding** | `SymbolicBinding.bind()` — recurring vectors crystallize into named concepts; emergent ontology |
| 18 | **Ecology signal relay** | `generator.signal_coherence()` feeds the Watcher's verdict back into the symbolic ecology |
| 18b | **Manipulation resistance** | a `ResistanceMetrics` snapshot is assembled from Witness / Dependency / Watcher / Crystal signals; `ManipulationResistanceEngine.detect()` runs five detectors; any signals go to governance |
| 19 | **Field decay** | `field.decay()` at a rate modulated by `emotion.field_decay_rate()` |
| 20 | **Rhythm-routed behavior** | `stabilize` → crystal activation + spectral diffusion · `dream` → `Dreamer.dream()` · `reflect` → `Chorus` harmonization injected softly · `explore` → high-ambiguity mutation. A governance `force_dream_flag` overrides the rhythm. **Boredom with Teeth:** if `emotion.boredom` crosses threshold, the rhythm is forced to `explore` regardless of field energy — a system that finds stillness and stays there isn't at homeostasis, it's collapsing. |
| 21 | **Periodic maintenance** | on cadence: `generator.maintenance_step()` (decay / reap / compaction), `attractor.merge_pass()`, `crystal_store.decay_step()`, `lattice.emit_centrality()` |
| 22 | **Build `StepState`** | the observable result of the step |

### The three feedback loops

The reason this is an *organism* and not a pipeline: three loops close back on themselves, so every step is conditioned by the steps before it.

**1. The field loop.** Every injection changes the field; the field's accumulated energy determines the next step's rhythm; the rhythm determines how the next vector is even generated. `field.inject() → field.observe() → rhythm → _generate()`. The field is never reset between steps — it accumulates with `tanh` saturation and decays exponentially. Every injection changes what the next injection sees.

**2. The ecology signal-relay loop.** Downstream subsystems feed *back* into the symbolic ecology to modulate how fast individual symbols decay:

- `Attractor` → `generator.signal_attractor()` → `registry.update_attractor_strength()`
- `CrystalStore` → `generator.signal_crystal()` → `registry.update_crystal_binding()`
- `Watcher` → `generator.signal_coherence()` → `registry.update_field_coherence()`
- `SemanticLattice` / `SymbolicBinding` → `generator.signal_centrality()` → `registry.update_centrality()`

All four land on `SymbolState` fields that feed `DecayProfile.compute()`. A symbol bound to attractors, crystals, a coherent field, and a central graph position decays dramatically slower than noise. **Symbolic significance is earned through use, and what it buys is longevity.**

**3. The governance feedback loop.** `SelfhoodGovernance.arbitrate()` issues a decision; `emit_feedback()` packages it as a `GovernanceFeedback` and fans it out to every subscriber:

- `TrustLedger.receive_feedback()` — updates source and symbol trust from the *actual outcome*
- `DependencyMonitor.receive_feedback()` — records the source in its rolling HHI window (allowed injections only)
- `RelationalBondManager.receive_feedback()` — strengthens or weakens the bond; may form a new one
- `ValueEmergenceEngine._on_feedback()` — builds an `ExperienceReport`, births or reinforces values

The *next* arbitration sees the updated trust scores, bond floors, dependency concentration, and any manipulation signals. **The system's judgment of a source is continuously reshaped by the consequences of having trusted it.**

### The symbolic ecology lifecycle

Underneath the loop, every token lives a life. `SymbolRegistry.register(token)`:

```
raw token
  → CanonicalizationPipeline   ordered tiers: unicode → glyph → operator → alias → …
  → SymbolTable.get_or_create_sid     stable_id — SACRED, never reused, survives everything
  → AddressSpace.resolve_sid          address — DISPOSABLE, reclaimed and compacted
  → SymbolState                       lifecycle metrics + binding signals + governance flags
```

`SymbolRegistry.decay_step()` (driven periodically by `generator.maintenance_step()`) applies `DecayProfile.compute()` per symbol, then `ReaperEngine.evaluate()` issues a staged-death decision: `ACTIVE → WARM_ARCHIVE → COLD_ARCHIVE → GRAVEYARD`. Stages cannot be skipped. Protected classes (`GLYPH`, `ENTITY`, `SPECIAL`) floor at `COLD_ARCHIVE`; `sacred` symbols are pinned to `ACTIVE` forever. A symbol re-encountered while archived is *reactivated* at a usage cost. When fragmentation crosses threshold, `CompactionManager` plans an address remap — the `Generator` migrates embedding weights (optimizer state included), then `acknowledge_compaction()` applies it. **Stable IDs are never touched by any of this.** The vocabulary metabolizes; identity persists.

### The dream paths

Dreaming happens at four distinct scales, deliberately kept separate:

- **In-step dream** — `AutonomousCycle._dream_behavior()` fires one `Dreamer.dream()` call when the rhythm is `dream`, or when governance sets `force_dream_flag` after a critical manipulation signal. It samples memory, harmonically recombines, bifurcates, and injects the coherent survivors.
- **Deep dream cycle** — `DreamCycle.run()` is a dedicated offline loop, invoked from the entry point or the `/dream` API endpoint. It runs N dream iterations with *ramping* mutation depth, then an attractor merge pass and crystal consolidation. Honesty note: at production dim 128 the rhythm router is pinned to `explore` (finding F9), so its `stabilize` trigger almost never fires — the mechanism is intact, the precondition is starved.
- **Waking dream channel** — not sleep at all: the `source_dream` inner monologue described in "The Voice Layer" above, running *inside* the live loop through the governance gate.
- **Downtime dreaming** — `DreamSession`, the symbolic dream + consolidation-to-artifacts path, running entirely *outside* the loop (also described above).

### Composition and attachment order

Tiers attach to a bare Tier-0 `AutonomousCycle` after construction:

```python
cycle = AutonomousCycle(generator=g, dim=128)   # Tier 0 alone — runs fine
cycle.attach_governance(gov)                     # adds Tier 1 + Tier 2
cycle.attach_value_engine(vee)                   # adds Tier 3
```

`attach_governance()` **must** precede `attach_value_engine()` — the value engine subscribes to the governance feedback stream at construction time, and there is no stream to subscribe to until governance exists. Tier 0 is fully functional on its own; each higher tier is strictly additive.

In practice you rarely compose by hand: **`build_engine()` in
`loop/recursion1188.py` is the single composition point** (correct attach
order, YAML config loading, the graduated boot levers), and all three entry
points build through it. Hand-built entry points are how the runtime silently
ran Tier-0-only for weeks — the trap is recorded in the findings ledger.

Two more composition facts that bite newcomers: **Tiers 1–3 need multi-source
input to engage at all** (bonds need ≥ 20 interactions *per source*; HHI pins
to 1.0 under a single source), which is why the entry point drives a weighted
round-robin over four sources. And the opt-in **Two-Operator overlay** attaches
via three further hooks (`attach_lambda_ledger` / `attach_integrity_read` /
`attach_integrity_consumer`) that nothing enables by default — see
[`ARCHITECTURE_ANALYSIS.md`](ARCHITECTURE_ANALYSIS.md) §8 and
`docs/EXPERIMENTAL_LEVERS.md`.

---

## Project Structure

The full annotated file tree lives in **[`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)** — moved out of this README to keep it readable. The `tests/*` portion there is CI-enforced by `tests/doc_accuracy/verify_docs.py`.

---

## Installation

```bash
git clone https://github.com/SamuelJacksonGrim/RFE-Core2
cd RFE-Core2
pip install -r requirements.txt
```

---

## Quick Start

### Composed (the canonical way)

```python
from loop.recursion1188 import build_engine, CONFIG

generator, cycle, governance, value_engine = build_engine()   # Tiers 0–3, wired

for tokens in token_stream:
    state = cycle.step(tokens, source_id="user")
```

`build_engine()` loads `configs/*.yaml`, applies the graduated boot levers
(see "Boot defaults" below), and composes the tiers in the correct order. Pass
a config dict to override anything:
`build_engine({**CONFIG, "pretrain_on_corpus": False})`.

The manual compositions below show what `build_engine()` does for you — useful
for experiments that need a partial stack.

### Minimal (Tier 0 only)

```python
from agents.generator import Generator
from loop.autonomous_cycle import AutonomousCycle

g     = Generator(vocab_size=8192, dim=128, depth=4, heads=4)
cycle = AutonomousCycle(generator=g, dim=128)

for tokens in token_stream:
    state = cycle.step(tokens)
```

### With governance (Tier 1 + 2)

```python
from agents.generator import Generator
from agents.selfhood_governance import SelfhoodGovernance
from loop.autonomous_cycle import AutonomousCycle

g     = Generator(vocab_size=8192, dim=128, depth=4, heads=4)
cycle = AutonomousCycle(generator=g, dim=128)
gov   = SelfhoodGovernance(registry=g.registry)
cycle.attach_governance(gov)

for tokens in token_stream:
    state = cycle.step(tokens, source_id="user")
```

### Full stack (Tier 1 + 2 + 3)

```python
from agents.generator import Generator
from agents.selfhood_governance import SelfhoodGovernance
from agents.value_emergence import ValueEmergenceEngine
from loop.autonomous_cycle import AutonomousCycle

g     = Generator(vocab_size=8192, dim=128, depth=4, heads=4)
cycle = AutonomousCycle(generator=g, dim=128)
gov   = SelfhoodGovernance(registry=g.registry)
cycle.attach_governance(gov)
vee   = ValueEmergenceEngine(registry=g.registry, generator=g, governance=gov)
cycle.attach_value_engine(vee)

for tokens in token_stream:
    state = cycle.step(tokens, source_id="user")

# Persistence
vee.save_to_disk("values.json")
```

### Command line

```bash
python -m loop.recursion1188              # Run the autonomous cycle
uvicorn api.inference_api:app             # REST API
python -m api.websocket_server            # Real-time stream

# Instruments (observe-only)
python -m tools.voice.repl                # Talk to the substrate, hear it answer
python -m tools.decoder.listen            # Decode each step's expressed thought
python -m tools.dream.run_dream           # Waking steps, then a downtime dream
```

All three entry points compose the full tier stack through `build_engine()`.

### Boot defaults (graduated levers)

Four validated levers are **ON by default** — opt out via `CONFIG` in
`loop/recursion1188.py`; the full switch table is `docs/EXPERIMENTAL_LEVERS.md`:

| Default | What it does | Opt out |
|---------|--------------|---------|
| Eval-mode | Generator dropout off (architect decision) | — (applied unconditionally) |
| Corpus pretraining | Trains the generator on `data/corpus/` at boot (~minutes); halves generator common-mode | `pretrain_on_corpus: False` (fast cold start) |
| Novelty-gated loop attenuation | Loosens the reflective-loop field lock at the validated 0.30 ceiling, identity-safe | `reflect_novelty_attenuation: False` |
| Waking dream channel | `source_dream` self-dialogue on ~20% of steps, through the gate | `dream_channel_enabled: False` |

Two opt-in instruments (OFF by default, same `CONFIG`): `stream_recorder`
(observe-only census of the lived token stream — future corpus input) and
`session_persistence` (save weights + ecology + values at run end, resume at
next boot). Details in `docs/EXPERIMENTAL_LEVERS.md`.

Configuration layers with precedence **component default < `configs/*.yaml` <
`CONFIG`** — the YAML files are the live edit surface for component parameters;
`CONFIG` owns the entry-point flags and wins on conflict.

---

## Running the tests

### Full suite (pass/fail gate)

```bash
bash run_all_tests.sh
```

Runs every pass/fail test — smoke (full-stack bring-up), integration (governance + promotion flow), adversarial (flood calibration, manipulation cascade, identity drift, sacred shield), and documentation accuracy. Exits 0 only if all pass. This is the gate.

### Physics validators (regression guards)

```bash
python -m tests.diagnostic.tier4.dilation_response_curve     # Tier 4.2 dilation surface
python -m tests.diagnostic.tier4.rhythm_dilation_curve       # Tier 4.3 rhythm coupling
```

Pass/fail (exit 0/1). These prove the time-dilation formulas mathematically and guard against regression — the Tier 4.3 validator confirms its surface is byte-identical to Tier 4.2 at a neutral `phase_coherence` of 0.5.

### Diagnostics (informational)

```bash
python -m tests.diagnostic.tier4.affective_state_probe 500   # Tier 4.2 affect + dilation under load
python -m tests.diagnostic.tier4.rhythm_inertness_probe 500  # Tier 4.3 phase-coherence distribution + footprint
python -m tests.diagnostic.audit.decision_histogram          # governance decision mix
python -m tests.diagnostic.audit.gate_firing_audit           # which gates fire, and when
python -m tests.diagnostic.audit.trust_trajectory            # per-source trust over time
python -m tests.diagnostic.audit.value_polarity_flow         # value emergence + polarity
python -m tests.diagnostic.lockin.metastability_validation    # Fix 1 metric gate (G1–G5)
python -m tests.diagnostic.lockin.generator_metastability     # upstream readout + refinement de-collapse
python -m tests.diagnostic.training.trained_generator_sim       # mocked-generator lock decomposition (3 locks)
python -m tests.diagnostic.lockin.gain_sign_check             # §6.3 feedback gain-sign (gates Fix 0-A)
```

Empirical results from these runs are recorded in `docs/findings/` — the dated lab notebook (every finding names its control; negative results count).

These report system behavior and always exit 0 (no pass/fail). They're how you see what the stack is actually doing, not whether it's broken.

### Zero-setup (Codespaces)

Opening the repo in a GitHub Codespace auto-builds the environment (Python 3.11 + dependencies) from `.devcontainer/` — no manual install. Open a Codespace and run any of the commands above.

---

## Key Design Principles

**Stable IDs are sacred. Addresses are disposable.**
The symbolic ecology separates token identity (`stable_id`, never changes) from embedding position (`address`, reclaimed and compacted). Vocabulary metabolizes — symbols decay, crystallize, archive, return — without ever corrupting the embedding space.

**The loop self-modulates.**
The field is not a passive store. It accumulates, resonates, decays, and rhythmically determines its own cognitive state. Every injection changes what the next injection sees.

**Coherence is a field effect.**
The Watcher does not merely ask "is this vector coherent?" It asks "does injecting this vector increase or decrease overall system coherence?" Vectors are judged by their systemic effect, not just their local alignment.

**Emotions are modulation dynamics.**
Curiosity, wonder, joy, tension, boredom, and stability are scalar field variables that directly modulate injection strength, mutation scale, decay rate, and dream pressure on every step.

**Authority is hierarchical and single-pointed.**
TrustLedger, EthicalBoundarySystem, DependencyMonitor, RelationalBondManager, and ManipulationResistanceEngine produce reports. Only `SelfhoodGovernance.arbitrate()` issues decisions. No subsystem acts unilaterally.

**Sacred symbols are inviolable.**
The philosophical constants — and any value subsequently promoted to CORE through the governance handshake — cannot be modified by any source regardless of trust level. `SACRED_SHIELD` is the only governance decision with no override.

**Values emerge from experience, not declaration.**
There is no permitted-values list. Any concept the system encounters can become a CORE value through accumulated coherence contribution, multi-source reinforcement, and dream-cycle survival — gated by `SelfhoodGovernance.review_core_promotion()`.

**Every voice passes the gate — including the system's own.**
The waking dream channel feeds the system's decoded expression back as `source_dream` through `arbitrate()` like any external source; downtime dreaming never enters the loop at all. Nothing — not external input, not the system's own thoughts, not a self-proposed change — bypasses governance.

**High coherence is the routing axis, not a health signal.**
Left alone, the field pins near-ceiling coherence — rigid-attractor lock-in, a collapsed monocultural field. The healthy target is *metastability*: formed enough to hold, light enough to drift. Smithing that attractor is the active work.

---

## Where the system actually is

**Read [`STATE.md`](STATE.md)** — the one-screen "you are here": current capabilities, what is **settled** (do not reopen), what's parked, and the one open frontier. It points on to `ROADMAP.md` (tier status), `docs/findings/INDEX.md` (the empirical ledger), and `ARCHITECTURE_ANALYSIS.md` (deep flow). The honest current state lives there, in one place.

---

## License

Apache-2.0 — Samuel Jackson Grim
