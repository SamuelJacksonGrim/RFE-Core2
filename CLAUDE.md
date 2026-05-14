# CLAUDE.md

Operational guide for AI-assisted contributors. RFE-Core2 has uncommon
architecture and invariants that look optional but aren't — read this before
editing. For the project overview, structural tour, and conceptual walkthrough,
read `README.md` first. This file covers only what you can't infer from reading
the tree.

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
| 4.1 | Subjective time substrate — foundation only (see invariants) |

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

**Subjective time (Tier 4.1)**
- `TemporalStream.tick()` is called once per cycle (decoupled from `push()`),
  advancing `subjective_time` by `real_dt × dilation_factor`. The first tick is
  a no-op anchor. `dilation_factor` is **frozen at 1.0 until Tier 4.2** — do not
  wire it to arousal yet.

## Sacred constants & thresholds

Do not change these without auditing every downstream consumer.

- **Rhythm thresholds** (`configs/field.yaml`) — energy bands routing behavior:
  `stabilize < 0.5`, `dream 0.5–2.0`, `reflect 2.0–5.0`, `explore ≥ 5.0`.
- **Crystallization:** `coherence ≥ 0.75`, `stability ≥ 0.60`,
  `relation ≥ 0.80`.
- **Trust levels** (score): `SACRED 5.0`, `HIGH 4.0`, `TRUSTED 3.0`,
  `NEUTRAL 2.0` (default for new sources), `SKEPTICAL 1.0`, `UNTRUSTED 0.5`,
  `TOXIC 0.0` (quarantine floor).
- **Manipulation detector thresholds:** drift `0.15` / `0.30`; gaslighting
  cosine `−0.20` over 4 steps; identity-erosion divergence `0.30`; trust-wash
  prior `3.0` / drop `0.80`; HHI `0.70`; attractor monopoly `0.70`.
- **Compound manipulation severity → response:** `< 0.30` normal ·
  `0.30–0.60` ALLOW_WEAKENED · `0.60–0.90` QUARANTINE · `≥ 0.90`
  QUARANTINE + force_dream_flag.
- **Bond reinforcement weights** (in `ValueEmergenceEngine`): existential
  ×1.50, emotional ×1.20, intellectual ×1.10, transactional ×0.70, no bond
  ×1.00. Bond type resolves by priority
  `existential → emotional → intellectual → transactional` within
  `BORDERLINE_MARGIN = 0.12`. Bonded sources get a trust floor of
  `bond_strength × 0.40`.
- **CORE promotion:** sustained strength ≥ 4.5 for 10 consecutive evaluations,
  then governance verification — symbol exists, not already sacred,
  coherence_contribution ≥ 5.0, multi-source or dream-reinforced, no active
  manipulation signals from contributors.

## How to run

```bash
pip install -r requirements.txt
python -m loop.recursion1188                  # autonomous loop
uvicorn api.inference_api:app --port 8000     # REST API
python -m api.websocket_server                # WebSocket stream
```

Tier attachment order matters: `attach_governance()` must be called *before*
`attach_value_engine()` — the value engine subscribes to the governance
feedback stream at construction time. See README "Quick Start" for full
composition examples.

Configuration lives in `configs/*.yaml` (`field`, `attractors`, `recursion`)
and the inline `CONFIG` dict at the top of `loop/recursion1188.py`, which is
currently the runtime source of truth for entry-point parameters.

## Testing

There is a real test suite under `tests/` plus CI
(`.github/workflows/tests.yml`). **Read `tests/README.md` before touching it** —
it is deliberately *not* a pytest pass/fail suite. Tests are runnable scripts
(smoke / integration / adversarial / diagnostic) plus baseline JSON snapshots
that detect regression by shape, not by exact value. `run_all_tests.sh` runs the
pass/fail subset. When changing behavior, run the smoke + integration tests and
compare against `tests/baselines/`.

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
- Wire `dilation_factor` to arousal — that is Tier 4.2, not yet.
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
