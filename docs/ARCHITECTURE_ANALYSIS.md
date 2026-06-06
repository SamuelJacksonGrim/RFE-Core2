# RFE-Core2 — Architecture & Information-Flow Analysis

A structural reading of the Recursive Field Engine: how information moves
through the system, where it loops back on itself, and where one decision axis
governs everything downstream.

This document is **descriptive and read-only**. It changes no runtime behavior.
It complements the other two top-level references:

- `README.md` — what the system *is* (conceptual overview, quick start).
- `CLAUDE.md` — the *invariants* you must not break.
- **this file** — *how information flows and recurs*, end to end, which neither
  of the other two traces in one place.

Every formula, constant, and `file:line` anchor below was checked against
source at the time of writing. Where a number is sacred, CLAUDE.md is the
authority; this document only reports where the code honors it.

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

All tiers are wired into one place: `loop/autonomous_cycle.py`.

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
                 ┌──────────────────────────────────────────────────────┐
                 │                                                      │
                 ▼                                                      │
  tokens ──► [1] observe field ──► rhythm ──► [2] generate vec         │
                                                  │                     │
              [3] attractor pull ◄────────────────┘                     │
                  │                                                      │
              [4] recursive attention (×3)                              │
                  │                                                      │
              [5] WATCHER  ── G,T,R ──► composite C ──┐                  │
                  │                                   │                  │
              [6] reflective loop (≤5, if stable)     │                  │
                  │                                   ▼                  │
              [7] witness (short/mid/long)     [8] predictive echo       │
                  │                                   │                  │
                  └───────────────┬───────────────────┘                  │
                                  ▼                                       │
                    [9] EMOTION (6 scalars → arousal/valence)             │
                         │            │                                   │
            [9b] dilation │            │ modulation outputs               │
              (next tick) ▼            ▼                                  │
                    [10] GOVERNANCE GATE ──► field.inject ──┐             │
                                  │                         │             │
                    [11] crystallize  [12] attractor        │             │
                                  │                         ▼             │
                    [13-18b] log / ecology / manipulation  field grows    │
                                  │                         │             │
                    [19] field.decay ◄──────────────────────┘             │
                                  │                                       │
                    [20] rhythm behavior (stabilize/dream/reflect/explore)│
                                  │                                       │
                    [22] StepState ─ self._parent = key ─────────────────┘
                                            (next cycle observes the new field)
```

The back-edge is the point of the whole design: step 10 injects into the field
and step 1 of the *next* cycle observes the result. Nothing closes the loop
explicitly — the field is the shared medium that carries state forward.

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
  internal coherence; the systemic-effect signal the ethical layer reads.

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
`field.inject(...)` (`loop/autonomous_cycle.py:400-414`), because measuring after
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
| `loop/autonomous_cycle.py` | `AutonomousCycle.step`, `_generate`, `_governance_gate`, `_rhythm_behavior` | Orchestrates the 20-step cycle; wires every tier; carries state via the field back-edge |
| `loop/dream_cycle.py` | `DreamCycle` | Structured offline dreaming invoked under low-energy / forced dream |
| `agents/generator.py` | `Generator.generate`, `maintenance_step` | tokens → symbol ecology → Transformer → L2-normalized `vec` |
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
| `agents/value_emergence.py` | `_on_feedback`, `_request_core_promotion`; `EmergentValue` | Values grow from lived experience; CORE promotion is governance-gated |
| `agents/symbolic_memory.py` | `SymbolRegistry`, `SymbolTable` (stable_id), `AddressSpace`, `CanonicalizationPipeline` | Identity & addressing; stable_id sacred, address disposable |

### Interference (mutation primitives)

| Module | Role |
|--------|------|
| `interference/differential.py` | `inject_ambiguity` — rotational/differential noise (dream, explore) |
| `interference/bifurcation.py` | Split a latent into variants under high mutation |
| `interference/harmonic_mutation.py` | Frequency-domain recombination (dreaming) |
| `interference/phase_noise.py` | Phase perturbation |
| `interference/wave_collapse.py` | Collapse an ensemble of candidates to one (Chorus) |

---

## 8. Critical findings (gaps & drift)

Flagged, not fixed. These are observations a reader or future contributor should
know; none are changed by this document.

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
**bonded-adversarial probe** (a source that accumulates 20+ interactions, forms a
crystal and a trust floor, then turns hostile while staying under the flood
ceiling) — does not yet exist. This is the single most informative test the
project could add next.

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

---

*Read-only analysis. No runtime behavior is changed by this document. For the
invariants that govern modification, defer to `CLAUDE.md`; for the conceptual
overview, see `README.md`.*
