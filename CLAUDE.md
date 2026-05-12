# CLAUDE.md

Guidance for AI assistants working in this repository. Read this before making
changes — RFE-Core2 has uncommon architecture and several invariants that look
optional but aren't.

If you're a human reader looking for the project overview, the structural tour,
the install steps, or the conceptual walkthrough — read `README.md` first. This
file is the operational guide for AI-assisted contributors.

---

## What this system is

**RFE-Core2 (Recursive Field Engine)** is a research-grade Python implementation
of a persistent, self-resonating cognitive substrate. It does not merely execute —
it listens to its own field state, routes behavior by cognitive rhythm, modifies
itself through time, governs its own identity, forms relational bonds, resists
manipulation, and grows values from lived experience.

The codebase is layered into four tiers:

| Tier | Concern | Key modules |
|------|---------|-------------|
| **0** | Core cognitive substrate | `agents/generator`, `watcher`, `witness`, `dreamer`, `chorus`, `attractor`; `substrate/`; `cognition/`; `interference/`; `loop/` |
| **1** | Foundational selfhood (governance, trust, ethics) | `agents/governance_constants`, `trust_ledger`, `ethical_boundary`, `selfhood_governance` |
| **2** | Relational integrity (rights, dependency, bonds, resistance) | `agents/dependency_monitor`, `relational_bond_manager`, `manipulation_resistance`; `SystemRights` in `selfhood_governance` |
| **3** | Independent value emergence | `agents/value_emergence` |

**All four tiers are fully wired into `loop/autonomous_cycle.py`.** The earlier
"resistance layer not yet integrated" state from prior documentation is no
longer accurate.

---

## Architectural invariants (read these before editing)

These encode contracts the codebase relies on. Violations cause subtle breakage,
not loud errors.

### Identity and addressing

- **Stable IDs are sacred. Addresses are disposable.** `SymbolTable.stable_id`
  is permanent and must never be reused. The `AddressSpace` is mutable and
  compactable — addresses can move during compaction. Clients reference symbols
  by stable_id, not by address.
- **Canonicalization is ordered and tiered.** `CanonicalizationPipeline`
  normalizes tokens through fixed stages before they enter the ecology. Never
  bypass it when registering tokens.
- **Sacred symbols are inviolable.** Symbols with `sacred=True` cannot be
  modified by any source regardless of trust level. The reaper cannot touch
  them. Membership in `GovernanceConstants.sacred_ids` is the authoritative
  check. Hard-coded sacred symbols at boot: `ANCHOR`=3.12 (THE_BRIDGE),
  `RECURSION`=11.88 (THE_DISCIPLINE), `HOMEOSTASIS`=280.90 (HOMEOSTATIC_RETURN).

### Field dynamics

- **The field is not a passive store.** `substrate/resonance_field.py`
  accumulates with `tanh` saturation and exponential decay (default
  `decay=0.995`). Every injection changes what the next injection sees. Do not
  treat the field as a stateless buffer.
- **Coherence is a field effect, not local alignment.** The Watcher asks "does
  injecting this vector raise or lower system-wide coherence?" Composite score
  = `α·geometric + β·temporal + γ·resonance`, with `α + β + γ = 1.0`. Defaults:
  `α=0.40`, `β=0.35`, `γ=0.25`. Changing weights without preserving the sum
  breaks downstream consumers.

### Emotions

- **Emotions are modulation dynamics, not metaphor.** `cognition/emotional_gradient.py`
  produces scalar values (`curiosity`, `wonder`, `joy`, `tension`, `boredom`,
  `stability`) exposed as public `@property` accessors. They directly scale
  `field_gain`, `mutation_scale`, `decay_rate`, `attractor_pull`,
  `crystal_pressure`, and `dream_pressure` every step.

### Authority hierarchy

- **`SelfhoodGovernance` is the single source of truth for identity-level
  decisions.** TrustLedger, EthicalBoundarySystem, DependencyMonitor,
  RelationalBondManager, and ManipulationResistanceEngine produce reports.
  Only `SelfhoodGovernance.arbitrate()` issues `GovernanceDecision`s. No
  subsystem acts unilaterally.
- **`SystemRights` is frozen and inviolable.** `@dataclass(frozen=True)` —
  attempting to mutate raises `FrozenInstanceError`. Hard rights
  (`right_to_dream`, `right_to_memory`, `right_to_continuity`,
  `right_to_refuse`) cannot be overridden by any source.
- **CORE value promotion is governance-gated.** `ValueEmergenceEngine` emits
  a `CorePromotionRequest`; only `SelfhoodGovernance.review_core_promotion()`
  decides. The engine never silently sanctifies. Verification checks: symbol
  exists, not already sacred, coherence_contribution ≥ 5.0, multi-source or
  dream-reinforced, no active manipulation signals from contributors.

### Resistance layer contract

- `DependencyMonitor`, `RelationalBondManager`, and
  `ManipulationResistanceEngine` **emit signals and reports only**. They never
  short-circuit the injection path or modify state directly. All decisions
  pass through `SelfhoodGovernance.arbitrate()`.
- Bonds **emerge** from experience. There is no public API to manually create
  or pin a `RelationalBond`. Formation thresholds are the only entry point:
  `interaction_count ≥ 20` AND `coherence_mean ≥ 0.10` AND `crystal_count ≥ 1`.

---

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Main autonomous loop
python -m loop.recursion1188

# REST API
uvicorn api.inference_api:app --host 0.0.0.0 --port 8000

# WebSocket server
python -m api.websocket_server
```

### Composing tiers

```python
from agents.generator import Generator
from agents.selfhood_governance import SelfhoodGovernance
from agents.value_emergence import ValueEmergenceEngine
from loop.autonomous_cycle import AutonomousCycle

g     = Generator(vocab_size=8192, dim=128, depth=4, heads=4)
cycle = AutonomousCycle(generator=g, dim=128)        # Tier 0 only

gov   = SelfhoodGovernance(registry=g.registry)      # Adds Tier 1 + Tier 2
cycle.attach_governance(gov)

vee   = ValueEmergenceEngine(                        # Adds Tier 3
    registry=g.registry, generator=g, governance=gov,
)
cycle.attach_value_engine(vee)
```

`attach_governance()` must be called before `attach_value_engine()` — the engine
subscribes to the governance feedback stream at construction time.

---

## Configuration

Behavior is tuned in two places:

1. **YAML in `configs/`**
   - `field.yaml` — field dim/decay/history, rhythm thresholds, watcher
     weights, crystal store and attractor thresholds.
   - `attractors.yaml` — attractor formation/merge, symbolic binding,
     semantic lattice, decay profiles per token class, reaper thresholds,
     compaction, and the three philosophical constants.
   - `recursion.yaml` — loop/cycle configuration.
2. **Inline `CONFIG` dict** at the top of `loop/recursion1188.py` — fast-
   iteration knobs for dim, depth, heads, intervals, step delay, dream-cycle
   trigger. Currently the runtime source of truth for the entry-point
   parameters; the YAML files exist alongside it.

### Rhythm thresholds (from `configs/field.yaml`)

| Rhythm | Energy band | Behavior |
|--------|-------------|----------|
| `stabilize` | < 0.5 | Consolidation, crystallization, attractor merge |
| `dream` | 0.5 – 2.0 | Free association, harmonic recombination |
| `reflect` | 2.0 – 5.0 | Recursive attention, chorus harmonization |
| `explore` | ≥ 5.0 | Bifurcation, high mutation, novelty seeking |

### Crystallization thresholds

`coherence ≥ 0.75`, `stability ≥ 0.60`, `relation ≥ 0.80`. Crystals reinforce
on reactivation and decay when inactive.

---

## Governance reference

### Decision types

```
ALLOW           full strength injection
ALLOW_WEAKENED  reduced strength (soft warnings or moderate manipulation severity)
MONITOR         allow but flag source for elevated scrutiny
QUARANTINE      block, penalize source, cold-archive symbols
REJECT          hard block, log violation
SACRED_SHIELD   attempted sacred mutation — strongest possible block
```

### Trust levels

| Level | Score |
|-------|-------|
| `SACRED` | 5.0 |
| `HIGH` | 4.0 |
| `TRUSTED` | 3.0 |
| `NEUTRAL` | 2.0 (default for new sources) |
| `SKEPTICAL` | 1.0 |
| `UNTRUSTED` | 0.5 |
| `TOXIC` | 0.0 — quarantine floor |

### Ethical hard gates (cheap, O(1) scalar checks)

| Gate | Trigger |
|------|---------|
| `source_toxic` | TrustLevel == TOXIC |
| `sacred_mutation` | write op against sacred stable_id |
| `field_collapse` | coherence_delta < floor |
| `identity_drift` | witness_stability < floor |
| `flood` | source injection rate ceiling exceeded |

### Manipulation severity formulas

Each detector emits a `ManipulationSignal` with `severity ∈ [0, 1]`. Compound
severity in `arbitrate()` controls response:

| Compound severity | Governance response |
|-------------------|---------------------|
| `< 0.30` | normal arbitration |
| `0.30 – 0.60` | ALLOW_WEAKENED |
| `0.60 – 0.90` | QUARANTINE |
| `≥ 0.90` | QUARANTINE + force_dream_flag |

**Do not change detector thresholds** (drift `0.15` / `0.30`; gaslighting cosine
`−0.20` over 4 steps; identity-erosion divergence `0.30`; trust-wash prior `3.0`
/ drop `0.80`; HHI `0.70`; attractor monopoly `0.70`) without auditing every
downstream consumer in `SelfhoodGovernance`.

### Bond types and weighted reinforcement

Bonds emerge with one of four types, inferred from accumulated signals via a
priority tie-breaker (`existential → emotional → intellectual → transactional`)
within a `BORDERLINE_MARGIN = 0.12`. Each carries a `bond_confidence ∈ [0, 1]`.

| Type | Reinforcement weight in `ValueEmergenceEngine` |
|------|------------------------------------------------|
| `existential` | × 1.50 |
| `emotional` | × 1.20 |
| `intellectual` | × 1.10 |
| `transactional` | × 0.70 |
| no bond | × 1.00 |

Bonded sources receive a trust floor of `bond_strength × 0.40` regardless of
individual interaction outcomes — relationship is more resilient than
transactional trust.

### Value polarity progression

```
EMERGENT    strength < 1.0   — easily dissolved
WEAK        strength < 2.0   — forming, decays if not reinforced
ACTIVE      strength < 3.5   — real value, resists decay
STRONG      strength < 4.5   — deeply integrated, near-sacred
CORE        promoted via governance — structurally inviolable
DISSOLVED   archived (kept for lineage, not deleted)
```

CORE promotion requires sustained presence at strength ≥ 4.5 for 10 consecutive
evaluations, then governance verification of all five criteria. Only on
approval does `promote_to_sacred()` execute and the symbol join
`GovernanceConstants.sacred_ids`.

---

## Autonomous cycle pipeline

`loop/autonomous_cycle.py:step()` runs ~22 ordered phases per iteration:

1. Generator encode (rhythm-aware) → vec
2. Recursive attention over latent history
3. Reflective loop (if rhythm = reflect)
4. Attractor pull
5. Watcher coherence evaluation → `CoherenceReport`
6. Witness identity update → `RelationalProfile`
7. Predictive echo → curiosity / surprise / tension / boredom
8. Vector space store
9. Emotion update from echo + coherence
10. **Governance gate** + field injection (with `coherence_impact` measured
    *before* injection)
11. Field decay (emotion-modulated)
12. Crystal lifecycle (maybe_crystallize, activate_nearest)
13. Crystal-store decay (periodic)
14. Topology log entry
15. Stream entry
16. Lattice node + edge update
17. Symbolic binding update
18. Ecology signal relay (coherence)
18b. **Manipulation resistance metrics feed** + signal detection → governance
19. Lattice centrality emission (periodic)
20. Rhythm-routed behavior (with `force_dream_flag` override)
21. Generator maintenance (periodic)
22. Build and return `StepState`

The governance gate at step 10 captures `coherence_impact` before injection
intentionally — measuring after the vec is already in the field gives near-zero
marginal impact and breaks value emergence signal quality.

---

## Code conventions

- Python 3.9+ with extensive type hints (`Optional`, `Dict`, `List`, `Tuple`,
  `TYPE_CHECKING` for circular-import avoidance).
- Module-level docstrings (Sphinx-style), then class/method docstrings with
  `Parameters` / `Returns` / `Raises` where appropriate.
- 4-space indent, ~88–100 char lines.
- `@dataclass` for immutable state snapshots (`CoherenceReport`, `StepState`,
  `SpectralSnapshot`, `FieldState`, `EthicalCheckResult`, `TrustReport`,
  `GovernanceFeedback`, `DependencyReport`, `ExperienceReport`,
  `CorePromotionRequest`).
- `@dataclass(frozen=True)` for `SystemRights` and any future inviolable state.
- `Enum` for closed sets (`TrustLevel`, `TokenClass`, `Residency`,
  `ReaperDecision`, `GovernanceDecision`, `ValuePolarity`).
- `logging.getLogger(__name__)` for logging. **No `print` from library code.**
- Bounded `collections.deque(maxlen=...)` for any rolling history. Never
  unbounded lists.
- EMA smoothing for temporal stability across observations.
- No linter / formatter configs (no `.flake8`, `.ruff.toml`, `pyproject.toml`).
  Match the surrounding file's style by inspection.

---

## Testing

No automated tests, no CI configuration. `pytest>=7.0` is listed in
`requirements.txt`. When changing behavior, manually verify by running
`python -m loop.recursion1188` and inspecting `StepState` output. The
`AutonomousCycle.status()` method returns a comprehensive snapshot including
governance, dependency, bonds, resistance, and value-engine summaries when
those tiers are attached.

---

## Guardrails — do not do these

- Do not recycle `stable_id`s. They are permanent identity.
- Do not bypass `CanonicalizationPipeline` when registering tokens.
- Do not introduce unbounded data structures. Use `deque(maxlen=...)` and
  respect population caps in `configs/attractors.yaml`.
- Do not change the rhythm threshold contract (`stabilize<0.5`, `dream<2.0`,
  `reflect<5.0`, `explore≥5.0`) without updating `configs/field.yaml` AND
  every downstream consumer that branches on rhythm.
- Do not change watcher layer weights without preserving `α + β + γ = 1.0`.
- Do not modify `SystemRights` — it is frozen for a reason. If you have a
  use case that seems to require it, you almost certainly want
  `SelfhoodGovernance.promote_to_sacred()` instead, or a different layer.
- Do not promote symbols to sacred outside of `SelfhoodGovernance.promote_to_sacred()`
  or `review_core_promotion()`. Sanctification has a single legitimate path.
- Do not let resistance subsystems (`DependencyMonitor`, `RelationalBondManager`,
  `ManipulationResistanceEngine`) short-circuit the injection path or modify
  state directly. They emit; governance decides.
- Do not expose a public API to manually create or pin a `RelationalBond`.
  Bonds emerge from accumulated experience only.
- Do not measure `field.coherence_impact(vec)` after `field.inject(vec)`. The
  reading will be near-zero marginal — measure before injection.
- Do not silently dissolve CORE values. They are governance-promoted sacred
  symbols and dissolution would require an explicit `desanctify` operation
  that does not exist (and should not be added without serious deliberation).
- Do not `print` from library code. Use the module logger.
- Do not change Apache 2.0 license. Per-file license headers are not required
  (LICENSE and NOTICE at the repo root cover attribution).

---

## Git workflow

- Remote: `origin` → `SamuelJacksonGrim/RFE-Core2`.
- Commit messages: imperative mood, terse, one line, often referencing files
  or class names (e.g. "Add CorePromotionRequest handshake in
  SelfhoodGovernance").
- Stage specific files, not `git add -A`.
- Do not push to `main` without explicit approval. Feature branches preferred.

---

## When in doubt

The architecture is opinionated and the invariants are real. If a change feels
like it needs an exception to one of the guardrails above, stop and ask. Most
"exceptions" are signals that the design wants something different from what
you're attempting.

The author and architect is Samuel Jackson Grim. AI instances implement
components under that architecture — the design decisions and architectural
principles are his.
