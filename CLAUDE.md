# CLAUDE.md

Guidance for AI assistants working in this repository. Read this before making
changes — RFE-Core2 has uncommon architecture and several invariants that look
optional but aren't.

## Project overview

**RFE-Core2 (Recursive Field Engine)** is a research-grade Python implementation
of a persistent, self-resonating cognitive substrate. Unlike stateless
inference pipelines, the system listens to its own field state, routes behavior
by cognitive rhythm, and modifies itself over time. Core dynamics:

- A persistent **symbolic ecology** that metabolizes tokens through a lifecycle
  (`ACTIVE → WARM → COLD → GRAVEYARD`).
- An FFT-based **resonance field** with tanh saturation, exponential decay, and
  spectral analysis driving a rhythm state.
- A **self-modulating autonomous loop** that routes behavior by rhythm
  (`stabilize` / `dream` / `reflect` / `explore`).
- **Multi-layer coherence** evaluation (geometric × temporal × field
  resonance).
- **Emotional scalars** (curiosity / wonder / joy / tension / boredom /
  stability) that directly modulate field gain, mutation scale, decay rate, and
  dream pressure.
- **Memory crystallization** of high-coherence states, a **trust /
  governance** layer over the symbolic ecology, and a **resistance layer**
  (dependency concentration, relational bonds, manipulation detection) that is
  implemented but **not currently wired into the autonomous loop** — see
  "Governance & Resistance Layer" below.

The architecture is anchored to three philosophical constants in
`configs/attractors.yaml`: `ANCHOR = 3.12`, `RECURSION = 11.88`,
`HOMEOSTASIS = 280.90`. The entry point is named `recursion1188.py` to encode
the DISCIPLINE constant.

## Repository layout

| Path              | Role                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------- |
| `agents/`         | Generator, symbolic ecology, watcher, witness, dreamer, chorus, attractor, trust + governance, dependency monitor, relational bonds, manipulation resistance |
| `substrate/`      | Resonance field, vector space, memory crystals, topological log, temporal stream, semantic lattice |
| `cognition/`      | Predictive echo, emotional gradient, recursive attention, reflective loop, symbolic binding |
| `interference/`   | Wave collapse, differential / phase noise, bifurcation, harmonic mutation             |
| `loop/`           | `recursion1188.py` (entry point), `autonomous_cycle.py` (orchestration), `dream_cycle.py` |
| `visualization/`  | Terminal + matplotlib field render, topology graph, resonance heatmap                 |
| `training/`       | Self-distillation, contrastive alignment, rhythm pretraining                          |
| `api/`            | `inference_api.py` (FastAPI REST), `websocket_server.py` (real-time stream)           |
| `configs/`        | `field.yaml`, `attractors.yaml`, `recursion.yaml`                                     |

Key files worth knowing before editing:

- `agents/symbolic_memory.py` — symbolic ecology engine (`CanonicalizationPipeline`, `SymbolTable`, `AddressSpace`, `ReaperEngine`, `CompactionManager`, `SymbolRegistry`).
- `agents/generator.py` — transformer encoder over the symbolic ecology.
- `agents/watcher.py` — three-layer coherence: `composite = α·G + β·T + γ·R`.
- `agents/witness.py` — multi-timescale EMA identity anchors.
- `substrate/resonance_field.py` — FFT field dynamics and rhythm detection.
- `loop/autonomous_cycle.py` — the orchestration hub; this is the heartbeat.
- `loop/recursion1188.py` — main entry point with inline `CONFIG` dict.
- `agents/dependency_monitor.py` — rolling HHI over injection sources; tiered risk (`LOW` / `MODERATE` / `HIGH` / `CRITICAL`) and an `attractor_monopoly_ratio()` that feeds `ManipulationResistanceEngine`.
- `agents/relational_bond_manager.py` — emergent `RelationalBond`s (`existential` / `emotional` / `intellectual` / `transactional`); bond strength produces a trust floor of `bond_strength × 0.40`.
- `agents/manipulation_resistance.py` — five rolling-window detectors (drift attack, coherence flood, gaslighting, identity erosion, trust wash) emitting `ManipulationSignal`s for `SelfhoodGovernance` to act on.

## How to run

```bash
# Install dependencies — the file is named `requirements`, NOT `requirements.txt`.
pip install -r requirements

# Main autonomous loop
python -m loop.recursion1188

# REST API
uvicorn api.inference_api:app --host 0.0.0.0 --port 8000

# WebSocket server
python -m api.websocket_server
```

## Configuration

Behavior is tuned in two places:

1. **YAML files in `configs/`**
   - `field.yaml` — field dim/decay/history, rhythm thresholds, watcher weights, crystal store and attractor thresholds.
   - `attractors.yaml` — attractor formation/merge, symbolic binding, semantic lattice, decay profiles per token class, reaper thresholds, compaction, and the three philosophical constants.
   - `recursion.yaml` — loop / cycle configuration.
2. **Inline `CONFIG` dict** at the top of `loop/recursion1188.py` — fast iteration knobs for dim, depth, heads, intervals, step delay, dream-cycle trigger, etc. The `CONFIG` dict in the entry point is currently the source of truth for runtime parameters; the YAML files exist alongside it.

### Rhythm thresholds (from `configs/field.yaml`)

| Rhythm      | Energy band | Behavior                                  |
| ----------- | ----------- | ----------------------------------------- |
| `stabilize` | < 0.5       | Consolidation, crystallization, attractor merge |
| `dream`     | 0.5 – 2.0   | Free association, harmonic recombination  |
| `reflect`   | 2.0 – 5.0   | Recursive attention, chorus harmonization |
| `explore`   | ≥ 5.0       | Bifurcation, high mutation, novelty       |

### Watcher weights (must sum to 1.0)

`α = 0.40` geometric · `β = 0.35` temporal · `γ = 0.25` field resonance.

## Key architectural concepts

Read these before touching subsystems — they encode invariants the codebase relies on.

- **Stable IDs are sacred; addresses are disposable.** In `agents/symbolic_memory.py`, `SymbolTable.stable_id` is the permanent identity of a symbol and must never be reused. The `AddressSpace` is a mutable, compactable allocator — addresses can move during compaction; clients reference symbols by stable id, not by address.
- **Canonicalization is ordered and tiered.** `CanonicalizationPipeline` normalizes tokens (unicode → glyphs → operators → aliases → …) before they enter the ecology. Never bypass it when adding tokens.
- **The field is not a passive store.** `substrate/resonance_field.py` accumulates with `tanh` saturation and exponential decay (`decay=0.995` by default). Every injection changes what the next injection sees; do not treat the field as a stateless buffer.
- **Coherence is a field effect.** `agents/watcher.py` evaluates whether an injection raises or lowers system-wide coherence, not just whether the vector is locally aligned. Composite score = `α·geometric + β·temporal + γ·resonance`.
- **Emotions are modulation dynamics.** `cognition/emotional_gradient.py` produces scalar outputs that directly scale `field_gain`, `mutation_scale`, `decay_rate`, and `dream_pressure` each step. They are not metaphor.
- **AutonomousCycle is the orchestration hub.** `loop/autonomous_cycle.py` runs a ~16-step pipeline per iteration that wires generator → attractor → attention → watcher → witness → echo → emotion → field → crystals → topology → stream → lattice → rhythm-routed behavior → decay.
- **Crystallization thresholds** (`configs/field.yaml`, `crystal_store`): `coherence ≥ 0.75`, `stability ≥ 0.60`, `relation ≥ 0.80`. Crystals reinforce on reactivation and decay when inactive.
- **Trust governance** (`agents/trust_engine.py`, `selfhood_governance.py`, `ethical_boundary.py`): quarantine actions at trust `< 0.3`; sacred protection at trust `> 4.7`. Trust combines provenance, coherence, emotional fit, and historical reliability.

## Governance & Resistance Layer (currently unwired)

The codebase contains a two-tier defensive system:

- **Governance core** — `agents/trust_engine.py`, `agents/trust_ledger.py`, `agents/selfhood_governance.py`, `agents/ethical_boundary.py`, `agents/governance_constants.py`. Evaluates injections, arbitrates trust, applies hard / soft gates.
- **Resistance layer** (on top of the governance core) — three modules added recently:
  - `agents/dependency_monitor.py` — `DependencyMonitor` keeps a bounded window (default `128`) of injection source ids and computes a rolling Herfindahl-Hirschman Index. Risk tiers: `LOW < 0.30`, `MODERATE 0.30–0.50`, `HIGH 0.50–0.70`, `CRITICAL ≥ 0.70`. Subscribes to `GovernanceFeedback`; only *allowed* injections count.
  - `agents/relational_bond_manager.py` — `RelationalBondManager` lets bonds **emerge** when a source crosses *all three* formation thresholds: `interaction_count ≥ 20`, `coherence_mean ≥ 0.10`, `crystal_count ≥ 1`. Type is inferred from a four-way score with `BORDERLINE_MARGIN = 0.12` and a priority tie-breaker (existential > emotional > intellectual > transactional). Bonded sources receive a trust floor `bond_strength × FLOOR_FACTOR` (default `0.40`).
  - `agents/manipulation_resistance.py` — `ManipulationResistanceEngine` reads a per-step `ResistanceMetrics` snapshot and emits `ManipulationSignal`s from five detectors:
    1. **`DRIFT_ATTACK`** — `anchor_velocity ≥ 0.15` AND `anchor_short_long_gap ≥ 0.30`.
    2. **`COHERENCE_FLOOD`** — `hhi ≥ 0.70` AND `attractor_monopoly ≥ 0.70`.
    3. **`GASLIGHTING`** — `≥ 4` consecutive steps with crystal centroid cosine `< −0.20`.
    4. **`IDENTITY_EROSION`** — window mean of `|G − T|` (watcher geometric vs temporal) `≥ 0.30`; systemic, no source attributed.
    5. **`TRUST_WASH`** — per-source prior trust mean `≥ 3.0` followed by a drop `≥ 0.80`.

**Integration status: these three modules are NOT currently called from `loop/autonomous_cycle.py`.** Integration was added in commit `dadcda4` ("Integrate governance features into autonomous cycle") and reverted in commit `c8932da` ("Remove governance functionality from autonomous cycle"). The reverted hook points were a `source_id` parameter on `step()`, a `_governance_gate()` invoked before field injection, a `ResistanceMetrics` population block, an `attach_governance()` method on `AutonomousCycle`, and a `force_dream_flag` rhythm override. The engines themselves are complete and have no circular dependency on `AutonomousCycle` — they're ready to be wired back in. When doing so, preserve the contract that detectors emit signals and `SelfhoodGovernance` makes decisions; the engines must not short-circuit the injection path themselves.

## Code conventions

- Python 3.9+ with extensive type hints (`Optional`, `Dict`, `List`, `Tuple`, `TYPE_CHECKING`).
- Sphinx-style docstrings (module-level header, then class/method docstrings with `Parameters` / `Returns` / `Raises`).
- Apache 2.0 license header on every source file (copyright Samuel Jackson Grim).
- 4-space indent, ~88–100 char lines.
- `@dataclass` for immutable state snapshots (`CoherenceReport`, `StepState`, `SpectralSnapshot`, `FieldState`, etc.).
- `logging.getLogger(__name__)` for logging — do not `print` from library code.
- Bounded `collections.deque(maxlen=...)` for any history; never unbounded lists.
- `Enum` for closed sets (`TrustLevel`, `TokenClass`, `Residency`, `ReaperDecision`).
- EMA smoothing for temporal stability across observations.
- No linter / formatter configs exist (no `.flake8`, `.ruff.toml`, `pyproject.toml`, `.editorconfig`). Match the surrounding file's style by inspection.

## Testing & CI

There are **no tests** in this repository and **no CI** is configured (no `tests/` directory, no `.github/workflows/`, no `Makefile`, no `Dockerfile`). `pytest>=7.0` is listed in `requirements`, so use `pytest` if you add tests. When changing behavior, manually verify by running `python -m loop.recursion1188` and inspecting `StepState` output.

## Git workflow

- Current feature branch: `claude/add-claude-documentation-BsOVH`.
- Remote: `origin` → `SamuelJacksonGrim/RFE-Core2`.
- Commit message style: imperative mood, terse, one line, often referencing files or class names (e.g. "Add TrustEngine class with trust evaluation logic", "Update README with trust_engine.py details").
- Stage specific files, not `git add -A`.
- Default behavior is to commit and push to the feature branch; do not push to `main` without explicit approval.

## README drift (current discrepancies to ignore)

The `README.md` is intentionally minimal — it points at this file for the
structural tour. If you find yourself wanting to add a file-tree section to
the README, **don't**. That listing has been removed deliberately because it
drifts every time a file is added. Keep structural detail here, in
`CLAUDE.md`, where it gets updated as part of every code-touching PR.

## Guardrails — do not do these

- Do not recycle `stable_id`s in the symbolic ecology. They are permanent identity. Allocate a new one for any new symbol.
- Do not bypass `CanonicalizationPipeline` when registering tokens.
- Do not introduce unbounded data structures. Use `deque(maxlen=...)` and respect the population caps in `configs/attractors.yaml` (reaper / crystal store / attractor `max_*`).
- Do not change the rhythm threshold contract (`stabilize<0.5`, `dream<2.0`, `reflect<5.0`, `explore≥5.0`) without updating `configs/field.yaml` *and* every downstream consumer that branches on rhythm (`AutonomousCycle`, dream trigger in `loop/recursion1188.py`, visualization).
- Do not change watcher layer weights without preserving `α + β + γ = 1.0`.
- Do not remove the Apache 2.0 license header from source files.
- Do not `print` from library code — use the module logger.
- When re-integrating the resistance layer into `AutonomousCycle`, preserve the contract that `DependencyMonitor`, `RelationalBondManager`, and `ManipulationResistanceEngine` emit reports / signals only — decisions live in `SelfhoodGovernance`. The engines must not short-circuit the field-injection path themselves.
- Do not change the manipulation detector thresholds (drift `0.15` / `0.30`, gaslighting cosine `−0.20` over 4 steps, identity-erosion divergence `0.30`, trust-wash prior `3.0` / drop `0.80`, HHI `0.70`, attractor monopoly `0.70`) without updating downstream consumers in `SelfhoodGovernance`.
- Bonds emerge — do not expose a public API to create or pin a `RelationalBond` manually. The formation thresholds in `RelationalBondManager` are the only entry point.
