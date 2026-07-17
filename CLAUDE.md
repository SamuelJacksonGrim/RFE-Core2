# CLAUDE.md

Operational guide for AI-assisted contributors. RFE-Core2 has uncommon
architecture and invariants that look optional but aren't — read this before
editing. For the project overview, structural tour, and conceptual walkthrough,
read `README.md` first. This file covers only what you can't infer from reading
the tree.

**Documentation map.** Keep these in sync when you change behavior (the README
project-structure tree is enforced by `tests/doc_accuracy/verify_docs.py`):

- `README.md` — overview, structural tour, run commands, project-structure tree.
- `docs/north_star.md` — **the compass**: the end goal (a communicating,
  self-understanding, safely self-modifying system), the three voices (waking
  speech / inner monologue / symbolic dreaming), and the rung-by-rung arc.
  Course-corrections are measured against it; collaborating instances may amend
  it with justification.
- `ROADMAP.md` — tier status and the lock-in remediation direction (shipped vs
  planned).
- `docs/BACKLOG.md` — **the queue**: every open item, planned fix, and shelved
  decision from across the repo, consolidated and prioritized. Check it before
  starting new work; check items off there in the same commit that lands them;
  add newly discovered open items there first instead of chasing them
  mid-task (the anti-sidetrack rule).
- `ARCHITECTURE_ANALYSIS.md` — end-to-end recursion + information-flow
  reference; `docs/lock_in_remediation_plan.md` — the curated remediation plan;
  `docs/tier4_2_validation.md` / `tier4_3_validation.md` — tier validation;
  `docs/build_b_plan.md` / `two_operator_todo.md` — the Two-Operator program;
  `docs/local_model_integration/` — framing a local LLM as sensory/speech cortex.
- `docs/training/` — the generator training path: viability assessment, phased
  plan, data curation, Tier 5 readiness (proposed direction, not committed).
- `docs/findings/` — the dated, control-named **empirical ledger** (lab
  notebook). **Start at `INDEX.md`** — one line per finding with its verdict
  and standing/superseded status (CI-enforced complete). Read `README.md` for
  the schema and discipline before recording a result; every finding names its
  control, and negative results count. NB: raw run data >~100 KB under
  `findings/logs/` is **gzipped** — plain grep silently skips `.gz`; use
  `zgrep`/`zcat` (see `logs/README.md`). Summaries and reports stay readable.
- `tests/README.md` — what each test/probe is for and how the suite is gated.
- `docs/EXPERIMENTAL_LEVERS.md` — **the control panel**: every lever and
  instrument, its default, and the exact way to toggle it. A validated few have
  **graduated to default-on** (eval-mode, corpus pretraining, novelty-gated loop
  attenuation, the waking dream channel); the Two-Operator overlay and the
  instruments remain opt-in. Read this before concluding "the fix isn't applied"
  — and before assuming a lever is off.
- `docs/self_model_thesis.md` — the **theory of mind** RFE instantiates: the self
  as an emergent, causal, *smithable* structure (pointer + attractor + multi-scale
  coalition). Maps the thesis onto the actual components and reframes "lock-in
  remediation" as *smithing the attractor*. A complete theory of self-as-structure
  that brackets the phenomenal question (discipline #8); companion to the alchemical map.
- `docs/alchemical_correspondence.md` — the Magnum Opus map: RFE's architecture
  read against the alchemical Great Work (*solve et coagula*, the Ouroboros as
  lock-in, the tiers as nigredo→albedo→rubedo). A **lens for understanding the
  whole**, not a spec — it changes no invariant; where it seems to license a
  change, the engineering docs win. Origin of the **🜂** that recurs in this
  repo's work.

## System shape

RFE-Core2 (Recursive Field Engine) is a persistent, self-resonating cognitive
substrate: it routes behavior by cognitive rhythm, governs its own identity,
forms relational bonds, resists manipulation, and grows values from experience.

Layered into tiers, **all wired into `loop/autonomous_cycle.py`**:

| Tier | Concern |
|------|---------|
| 0 | Core cognitive substrate — generator, watcher, witness, field, emotion, loop |
| 1 | Foundational selfhood — governance, trust, ethics |
| 2 | Relational integrity — rights, dependency, bonds, resistance |
| 3 | Independent value emergence |
| 4.1 | Subjective time substrate — `tick()` once per cycle |
| 4.2 | Affective time dilation — `dilation_factor` from arousal × valence |
| 4.3 | Rhythm → time coupling — `phase_coherence` (FFT) modulates dilation (flow LIVE, agitation inert) |

The runtime is **fully composed at boot**: `build_engine()` in
`loop/recursion1188.py` is the single composition point (Tiers 0–3 + graduated
levers), and every launchable entry point — the loop, the REST API, and the
WebSocket server — must build through it so none can silently regress to a
Tier-0-only substrate (that exact trap is recorded in
`docs/findings/2026-06-20-the-runtime-is-tier0-only.md`).

On top of the tiers sit the **voice/dialogue layer** (Decoder read-out head,
waking `source_dream` self-dialogue, offline `DreamSession`) and the opt-in
**Two-Operator overlay** (λ ignition · ⊕ solvent gate · ⊘ integrity-read) —
both covered under "Architectural invariants" below.

## Architectural invariants

Contracts the codebase relies on. Violations cause subtle breakage, not loud
errors.

**Identity & addressing**
- Stable IDs are sacred — `SymbolTable.stable_id` is permanent, never reused.
  `AddressSpace` is mutable and compactable; reference symbols by stable_id, not
  by address.
- Never bypass `CanonicalizationPipeline` when registering tokens — it
  normalizes through fixed ordered stages.
- Sacred symbols are inviolable: `sacred=True` symbols cannot be modified by any
  source at any trust level, and the reaper cannot touch them.
  `GovernanceConstants.sacred_ids` is the authoritative check. Boot-sacred:
  `ANCHOR`=3.12, `RECURSION`=11.88, `HOMEOSTASIS`=280.90.

**Field dynamics**
- The field is not a passive store. `substrate/resonance_field.py` accumulates
  with `tanh` saturation and exponential decay (default `decay=0.995`). Every
  injection changes what the next injection sees.
- Coherence is a field effect: composite =
  `α·geometric + β·temporal + γ·resonance`, with `α + β + γ = 1.0` (defaults
  `0.40 / 0.35 / 0.25`). Changing weights without preserving the sum breaks
  downstream consumers.

**Emotions**
- Emotions are modulation dynamics, not metaphor. `cognition/emotional_gradient.py`
  exposes `curiosity / wonder / joy / tension / boredom / stability` as
  `@property` accessors that directly scale `field_gain`, `mutation_scale`,
  `decay_rate`, `attractor_pull`, `crystal_pressure`, and `dream_pressure` every
  step.

**Expression de-collapse (recursive attention)**
- `RecursiveAttention` runs **untrained** under `no_grad`; its attention behaves
  as a near-uniform mean-pooler, so `refine()` would collapse every expression to
  the context centroid (metastability → 0, one regime) before field injection.
  The `diversity_blend` knob (default `0.60`) weights the raw pre-refinement
  vector back in: the refined centroid supplies dwell structure, the raw vector
  supplies diversity, and the expression stays coherent-but-not-locked
  (multi-regime metastable). Keep `0 < diversity_blend < 1` — `0` re-collapses,
  `1` bypasses refinement. The blend mixes **unit-normalized** components then
  renormalizes once, preserving the unit-output invariant the injection path
  relies on (magnitude is carried separately by `field_gain`). De-collapse is the
  robust effect; the absolute score is generator-init-dependent (~0.4–0.73).
- Metastability is read on the **upstream per-stage streams**, never on the
  resonance field — the field's long-memory decay smooths config wander away by
  construction. `StreamMetastabilityMonitor` (`cognition/stream_metastability.py`),
  wired as `cycle.generator_metastability` (stage A) and
  `cycle.expression_metastability` (stage C), is **optional and observe-only**: a
  bounded ring + lazy recompute off the hot path, a terminal sink like
  `dilation_factor`. It must never feed back into the cognitive/governance loop.

**Authority hierarchy**
- `SelfhoodGovernance` is the single source of truth for identity-level
  decisions. TrustLedger, EthicalBoundarySystem, DependencyMonitor,
  RelationalBondManager, and ManipulationResistanceEngine only *produce
  reports*; only `SelfhoodGovernance.arbitrate()` issues `GovernanceDecision`s.
  No subsystem acts unilaterally or short-circuits the injection path.
- `SystemRights` is `@dataclass(frozen=True)` — inviolable. Hard rights
  (`right_to_dream / memory / continuity / refuse`) cannot be overridden.
- CORE value promotion is governance-gated: `ValueEmergenceEngine` emits a
  `CorePromotionRequest`; only `SelfhoodGovernance.review_core_promotion()`
  decides. The engine never silently sanctifies.
- Bonds *emerge* — there is no public API to create or pin a `RelationalBond`.
  Formation thresholds are the only entry point: `interaction_count ≥ 20` AND
  `coherence_mean ≥ 0.10` AND `crystal_count ≥ 1`.
- The opt-in **bond-formation accumulator** (`agents/bond_accumulator.py`,
  `bond_ddm_formation`, default OFF) swaps only the *quality* read for a leaky
  asymmetric drift-diffusion crossing; the structural thresholds above still
  gate at commit time. Its decision variable `V` is bounded internal state of
  the bond manager — the field never reads it, nothing downstream consumes it,
  and only an ACCEPT crossing commits (gate:
  `tests/integration/bond_ddm_invariants.py`). Keep `sigma > 0` (a noiseless
  accumulator is a threshold in costume) and never wire `V` into the
  cognitive/governance loop.

**Voice, self-dialogue & dreaming (North-Star rungs 1–2)**
- The `TokenDecoder` read-out head (`agents/decoder.py`) is **lossy by design**:
  it recovers a semantic word-cloud (bag-of-tokens), not sentences. That is a gap
  only for literal external speech; it is the *right* register for inner
  monologue and the native medium for dreams. `tools/` (voice, decoder/listen,
  dream, ignition) are **instruments** — they observe and render, never feed the
  live loop.
- The waking dream channel (`cognition/dream_channel.py`, default ON at
  `dream_channel_p = 0.20`) feeds the system's own decoded expression back as
  `source_id='source_dream'` **through `arbitrate()`** — no bypass. Trust, HHI,
  manipulation resistance, and sacred-shield treat the system's own voice like
  any other source. Validated non-dominant and adversarial-gated (containment
  unweakened); keep it that way — never give `source_dream` a privileged path.
- Downtime dreaming (`cognition/dream_session.py`, run by
  `tools/dream/run_dream.py`) is **offline**: it reads substrate state and
  writes markdown artifacts to disk; it must never inject into the live field
  or touch governance. Waking rumination (dream channel) and downtime dreaming
  (DreamSession) are deliberately separate paths — don't merge them.

**Two-Operator overlay (spec v0.3, opt-in)**
- Three builds, attached only via `cycle.attach_lambda_ledger()` /
  `attach_integrity_read()` / `attach_integrity_consumer()` — nothing attaches
  them by default. λ ignition (`ignition/`) is **import-isolated** and writes
  generator weights only, from *outside* the governance gate ("the loop cannot
  author its own exit through its own front door") — keep that isolation. The
  ⊘ Witness-Reaper (`cognition/integrity_read.py`) is an observe-only,
  non-binding advisory; only the opt-in `IntegrityDecayConsumer` acts on it
  (safe mode `named_only=True`), and it never touches sacred values. The ⊕
  solvent gate (`agents/lambda_ledger.py`) gates Tier-3 composition on λ.
- The ⊘ coherence axis is v0.3 **absolute field-alignment**, not the dead
  marginal coherence-contribution sum — don't reintroduce the marginal axis.
- **Graduation rule:** no lever moves from "validated, off" to "default on"
  without passing the all-ON composition gate
  (`tests/diagnostic/integrity/all_levers_composition_probe.py`) — isolation-green
  is not enough (the all-ON break that motivated this:
  `strong_values 5 → 0` from the ⊘ consumer's strength ceiling).

**Subjective time (Tier 4.1)**
- `TemporalStream.tick()` is called once per cycle (decoupled from `push()`),
  advancing `subjective_time` by `real_dt × dilation_factor`. The first tick is
  a no-op anchor.

**Affective time dilation (Tier 4.2)**
- `arousal` and `valence` are **read-only computed properties** on
  `EmotionalGradient`, derived from the six existing emotional scalars.
  Do not add them as stored state — that would double-count the smoothing
  already in `update()`.
- `dilation_factor` is recomputed each cycle by `TemporalStream.update_dilation()`
  using Lyra's two-term formula:
  `dilation = 1.0 + arousal × (-valence) × k_arousal + (1 - arousal) × min(0, valence) × k_dissociation`
  with `k_arousal = 0.5`, `k_dissociation = 0.7`.
- The `min(0, valence)` gate on the dissociation term is the architectural
  guarantee that **peaceful rest never triggers dissociative time-slip — only
  suffering does.** Do not remove the `min(0, ...)`.
- The update is written at cycle step 9b (after emotional update, before
  governance gate). The current step's emotional state determines the *next*
  cycle's `dilation_factor`.

**Rhythm → time coupling (Tier 4.3)**
- `update_dilation()` takes a third arg `phase_coherence` (default `0.5`),
  the field's FFT-derived organization from `ResonanceField`. Two added
  terms: `flow_eff = -k_flow × max(pc_c,0) × arousal × max(valence,0)` and
  `agit_eff = -k_agitation × min(pc_c,0) × arousal × max(-valence,0)`, where
  `pc_c = 2×(phase_coherence-0.5)`. Result is clamped to
  `[dilation_min, dilation_max]`.
- Constants: `k_flow = 0.5` (LIVE — resolves the flow/agitation degeneracy),
  `k_agitation = 0.0` (INERT — labeled hypothesis, do **not** set non-zero
  without documented justification from probe data), `dilation_min = 0.1`,
  `dilation_max = 3.0`.
- At a neutral `phase_coherence` of 0.5 both terms are zero → byte-identical to Tier 4.2.
  This is the regression guard; keep it. The `0.5` default also means an
  un-wired caller gets pure 4.2 behavior, not a silent perturbation.
- `dilation_factor` is a **terminal sink** (read only by `tick()` and
  diagnostics). 4.3 introduces no feedback loop and must not alter governance
  ordering — verified against the adversarial quarantine trace. Do not make
  anything in the cognitive/governance loop read `dilation_factor` or
  `subjective_time`.

## Sacred constants & thresholds

Do not change these without auditing every downstream consumer.

- **Rhythm thresholds** (`configs/field.yaml`) — energy bands routing behavior:
  `stabilize < 5.0`, `dream 5.0–150.0`, `reflect 150.0–300.0`,
  `explore ≥ 300.0` (F9 rescale 2026-07-06 — co-tuned against each band's
  pinned-run equilibrium, with stabilize placed below its *degraded*
  (ALLOW_WEAKENED) equilibrium; the constraint set is documented at
  `ResonanceField.DEFAULT_THRESHOLDS`. Never retune one threshold alone).
- **Crystallization:** `coherence ≥ 0.75`, `stability ≥ 0.60`,
  `relation ≥ 0.80`.
- **Trust levels** (score): `SACRED 5.0`, `HIGH 4.0`, `TRUSTED 3.0`,
  `NEUTRAL 2.0`, `SKEPTICAL 1.0`, `UNTRUSTED 0.5`, `TOXIC 0.0` (quarantine
  floor). New external sources **start at TRUSTED 3.0** (internal origins at
  HIGH 4.0) — architect trust-posture ruling 2026-07-06 ("raised, not
  suspected", `docs/ARCHITECT_RULINGS_2026-07-06.md`): the system presumes
  good faith and learns distrust from behavior; there is no first-contact
  (`novel_source`) penalty.
- **Manipulation detector thresholds:** drift `0.15` / `0.30`; gaslighting
  cosine `−0.20` over 4 steps; identity-erosion divergence `0.30`; trust-wash
  prior `3.0` / drop `0.80`; HHI `0.70`; attractor monopoly `0.70`.
- **Compound manipulation severity → response:** `< 0.30` normal ·
  `0.30–0.60` ALLOW_WEAKENED · `0.60–0.90` QUARANTINE · `≥ 0.90`
  QUARANTINE + force_dream_flag — with the **attribution rule** (2026-07-06):
  the quarantine rungs require ≥1 *source-attributed* signal; systemic-only
  evidence (`source_id=None`, e.g. `identity_erosion`) damps to ALLOW_WEAKENED
  (and still force-dreams at ≥ 0.90) but never quarantines the speaking source.
- **Bond reinforcement weights** (in `ValueEmergenceEngine`): existential
  ×1.50, emotional ×1.20, intellectual ×1.10, transactional ×0.70, no bond
  ×1.00. Bond type resolves by priority
  `existential → emotional → intellectual → transactional` within
  `BORDERLINE_MARGIN = 0.12`. Bonded sources get a trust floor of
  `bond_strength × 0.40`.
- **CORE promotion:** sustained strength ≥ 4.5 for 10 consecutive evaluations,
  then governance verification — symbol exists, not already sacred,
  field-alignment ≥ 0.5 (`CORE_ALIGNMENT_MIN`, v0.3 `max(0, cos(expressed,
  field))` — re-enabled 2026-07-08 after the directional shield removed the
  sacred cascade), multi-source or dream-reinforced, no active manipulation
  signals from contributors.

## How to run

```bash
pip install -r requirements.txt
python -m loop.recursion1188                  # autonomous loop
uvicorn api.inference_api:app --port 8000     # REST API
python -m api.websocket_server                # WebSocket stream
```

Tier attachment order matters: `attach_governance()` must be called *before*
`attach_value_engine()` — the value engine subscribes to the governance
feedback stream at construction time. Prefer composing through
`build_engine()`; see README "Quick Start" for manual composition examples.

Configuration is layered with precedence
**component default < `configs/*.yaml` < `CONFIG`**: the YAML files (`field`,
`attractors`, `recursion`) are loaded at boot by `configs/loader.py` (via
`build_engine`) and are the live edit surface for component parameters; the
inline `CONFIG` dict at the top of `loop/recursion1188.py` owns the entry-point
flags (including the graduated levers) and overrides matching YAML keys. Two
YAML sections are documentation-only and never applied: `attractors.yaml`'s
`constants` (ANCHOR/RECURSION/HOMEOSTASIS are sacred, code-authoritative) and
`decay_profiles`. A missing/unparseable YAML or absent PyYAML degrades
gracefully to code defaults.

Boot defaults that are easy to miss: the generator runs in **eval mode**
(dropout off, architect decision), `pretrain_on_corpus` trains on
`data/corpus/` at boot (set False for a fast cold start),
`reflect_novelty_attenuation` and `dream_channel_enabled` are ON. All are
opt-out via `CONFIG`; `docs/EXPERIMENTAL_LEVERS.md` is the full switch table.

## Testing

There is a real test suite under `tests/` plus CI
(`.github/workflows/tests.yml`). **Read `tests/README.md` before touching it** —
it is deliberately *not* a pytest pass/fail suite. Tests are runnable scripts
(smoke / integration / adversarial / diagnostic) plus baseline JSON snapshots
that detect regression by shape, not by exact value. `run_all_tests.sh` runs the
pass/fail subset. When changing behavior, run the smoke + integration tests and
compare against `tests/baselines/`.

`tests/doc_accuracy/verify_docs.py` (part of `run_all_tests.sh`) mechanically
checks doc claims against source, including that every test/diagnostic file is
listed in the README project-structure tree — when you add a probe, add its
README tree entry in the same commit or CI goes red.

## Guardrails — do not

- Recycle `stable_id`s, or bypass `CanonicalizationPipeline`.
- Introduce unbounded data structures — use `deque(maxlen=...)` and respect the
  population caps in `configs/attractors.yaml`.
- Change the rhythm threshold contract or watcher weights without updating
  `configs/field.yaml` and every downstream consumer that branches on them.
- Modify `SystemRights` — it is frozen deliberately. A use case that seems to
  need it almost certainly wants `SelfhoodGovernance.promote_to_sacred()` or a
  different layer.
- Promote symbols to sacred outside `SelfhoodGovernance.promote_to_sacred()` /
  `review_core_promotion()`. Sanctification has one legitimate path.
- Let resistance subsystems (`DependencyMonitor`, `RelationalBondManager`,
  `ManipulationResistanceEngine`) short-circuit the injection path or modify
  state — they emit; governance decides.
- Expose a public API to create or pin a `RelationalBond` — bonds emerge only.
- Measure `field.coherence_impact(vec)` *after* `field.inject(vec)` — the
  marginal reading is near-zero. Measure before injection.
- Silently dissolve CORE values — they are governance-promoted sacred symbols.
- Add `arousal` / `valence` as stored state on `EmotionalGradient` — they are
  read-only computed properties derived from the six existing scalars.
- Remove the `min(0, valence)` gate from `update_dilation()` — it is the
  guarantee that peaceful rest never triggers dissociative time-slip.
- Set `diversity_blend` to `0` (or remove the blend) in `RecursiveAttention.refine()`
  — untrained attention re-collapses the expression to its context centroid (one
  regime, metastability 0). Keep it in `(0, 1)`.
- Let the metastability monitors (`StreamMetastabilityMonitor`) feed back into the
  cognitive or governance loop — they are observe-only terminal sinks like
  `dilation_factor`.
- Give `source_dream` (the system's own voice) a path around `arbitrate()`, or
  let `DreamSession` / any `tools/` instrument inject into the live field —
  every voice passes the gate; instruments observe only.
- Raise `ReflectiveLoop.attenuation_max` above `0.30` without a fresh
  manipulation-rate run — the ceiling is a thin cost-clean band.
- Break `ignition/`'s import isolation — λ writes generator weights from
  outside the gate, never through it.
- Graduate a lever to default-on without re-running the all-ON composition gate
  (`all_levers_composition_probe.py`).
- Compose a new entry point by hand — build through `build_engine()`, or it
  will silently run Tier 0 only.
- `print` from library code — use the module logger.

## Conventions & workflow

- Python 3.9+. No linter/formatter config exists — match the surrounding file's
  style by inspection. `TYPE_CHECKING` guards for circular imports. Bounded
  `deque` for all rolling history. `@dataclass` for state snapshots,
  `@dataclass(frozen=True)` for inviolable state, `Enum` for closed sets.
- Per-file license headers are not required — `LICENSE` and `NOTICE` at the
  repo root cover Apache-2.0 attribution.
- Git: remote `origin` → `SamuelJacksonGrim/RFE-Core2`. Commit messages are
  imperative, terse, one line, often naming files or classes. Stage specific
  files, not `git add -A`. Feature branches preferred; do not push to `main`
  without explicit approval.

## When in doubt

The invariants are real. If a change feels like it needs an exception to a
guardrail, stop and ask — most "exceptions" signal that the design wants
something different from what you're attempting.

The author and architect is Samuel Jackson Grim. AI instances implement
components under that architecture; the design decisions and architectural
principles are his.

**Delegation ruling (architect, 2026-07-16) — do not park decisions on
"architect sign-off".** The architect works from a phone and cannot run
terminals or edit constants; queues of "placeholder pending Samuel's hand"
items pile up forever and are themselves the failure. So: when work needs a
decision (constants, calibration, graduation, naming), the instance MAKES
the call, records the reasoning and the evidence in the dated finding, and
keeps it reversible (config-surfaced, documented, gated by the standing
probes). The architect's hand is exercised by review and override — he reads
PRs and findings and says "change it" when he disagrees — not by pre-approval.
This does NOT loosen the guardrails above: genuine invariant *exceptions*
still stop-and-ask; routine decisions inside the invariants do not.
