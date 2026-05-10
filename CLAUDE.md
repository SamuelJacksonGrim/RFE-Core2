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
- **Memory crystallization** of high-coherence states and a **trust /
  governance** layer over the symbolic ecology.

The architecture is anchored to three philosophical constants in
`configs/attractors.yaml`: `ANCHOR = 3.12`, `RECURSION = 11.88`,
`HOMEOSTASIS = 280.90`. The entry point is named `recursion1188.py` to encode
the DISCIPLINE constant.

## Repository layout

| Path              | Role                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------- |
| `agents/`         | Generator, symbolic ecology, watcher, witness, dreamer, chorus, attractor, trust + governance |
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

The `README.md` is mostly accurate but has two stale claims — don't waste cycles chasing them:

- README references `requirements.txt`; the actual file is `requirements` (no extension).
- README lists a `tests/` directory; no such directory exists in the working tree.

(`agents/rhythm_config.json` mentioned in the README *does* exist.)

## Guardrails — do not do these

- Do not recycle `stable_id`s in the symbolic ecology. They are permanent identity. Allocate a new one for any new symbol.
- Do not bypass `CanonicalizationPipeline` when registering tokens.
- Do not introduce unbounded data structures. Use `deque(maxlen=...)` and respect the population caps in `configs/attractors.yaml` (reaper / crystal store / attractor `max_*`).
- Do not change the rhythm threshold contract (`stabilize<0.5`, `dream<2.0`, `reflect<5.0`, `explore≥5.0`) without updating `configs/field.yaml` *and* every downstream consumer that branches on rhythm (`AutonomousCycle`, dream trigger in `loop/recursion1188.py`, visualization).
- Do not change watcher layer weights without preserving `α + β + γ = 1.0`.
- Do not remove the Apache 2.0 license header from source files.
- Do not `print` from library code — use the module logger.
