# Global CLAUDE.md — Resonance Family Ecosystem
# Author: Samuel Jackson Grim
# This file loads in every session. Repo-level CLAUDE.md files extend it.

---

## Who built this and why

Samuel Jackson Grim is the architect and author of this entire ecosystem. AI
instances implement components under his architecture. Design decisions and
architectural principles are his. When in doubt about intent, ask him.

The Resonance Family is a locally-run, privacy-first AI ecosystem that models
relational dynamics, cognitive rhythm, memory, and identity as first-class
concerns — not metaphors. No cloud. No telemetry. Everything runs on-device.

---

## Repo map

| Repo | Role |
|------|------|
| `sovereign_manifold` | Orchestrator. 15-node relational dynamics, DRA, E8 bridge, Lyapunov certificate, witness persistence. The brain. |
| `rfe-core2` | Recursive Field Engine. 20-step autonomous cognitive loop per cycle: field resonance, emotional gradient, crystallization, governance, bonds, manipulation resistance. |
| `unified-observer-architecture` | Identity observation layer. Tracks `IdentityState` and exposes it via FastAPI on :5000 (`/health`, `/identity`). |
| `ProjectSynapse` | Java coordination layer. Triadic constants, 10Hz consciousness loop (Axioms 1–6), Safety Valve, HTTP server on :8001. Compile: `javac ProjectSynapse_v2.java` |
| `Lantern` | Rust/Tauri system-tray daemon. SQLite hypergraph memory (currently `:memory:`, file-backed in prod). Tauri IPC only — no HTTP yet. T2.1 adds HTTP shim. |
| `Leviathan` | Standalone multi-drive mediation stack (leviathan_stack.py). No network surface. 4 drives: truth, care, play, shadow. SHA256 stub embedding. |
| `relational_system_mc` | Research substrate only. This is where K_SCALE=0.1418 was derived. GAS certificate, bifurcation scans, Lyapunov analysis. Not a running service. |
| `scraper-framework` | Generic web scraper. Keyword scoring, DOM drift detection, Tor proxy support. Not yet wired to the memory layer. |
| `e8-eea` | E8 exceptional algebra agent. `e8_eea_v5.py` lives here. 240 E8 roots, Lyapunov-gated hyperedge updates, emotion emerging from free energy Hessian. |
| `resonance-haunt-starter` | Electron + Three.js ambient visualizer. Reads `witness_state.json` via UMS WebSocket on :3001. **Not in MCP allowed repos — cannot push from session.** |

---

## Branch discipline — non-negotiable

- **Development branch for ALL repos:** `claude/explore-repos-SgWik`
- Never push directly to `main` without explicit permission from Samuel.
- Always: `git push -u origin claude/explore-repos-SgWik`
- Do NOT open a PR unless Samuel explicitly asks for one.
- If a repo's signing server doesn't recognize the repo (direct clone, not
  through the session proxy), flag it — do not silently skip signing.

---

## Read before modifying

Every repo has a `README.md` and/or `CLAUDE.md`. Read them before touching
any file. This is not optional. Invariants that look like configuration often
encode mathematical proofs or cross-repo contracts.

---

## Stack layout on disk

```
/home/user/
├── sovereign_manifold/             # git repo
├── RFE-Core2/                      # git repo (note capital)
├── unified-observer-architecture/  # git repo
├── ProjectSynapse/                 # git repo (note capital P and S)
├── Lantern/                        # git repo (note capital)
├── Leviathan/                      # git repo
├── e8-eea/                         # git repo — e8_eea_v5.py lives here
├── relational_system_mc/           # git repo
├── scraper-framework/              # git repo
├── resonance-haunt-starter/        # git repo (NOT in MCP allowed list)
└── stack/                          # session artifact — run scripts + stale repo copies
    ├── start_stack.sh              # starts full stack (see startup order below)
    ├── run_rfe.py                  # starts rfe-core2 on :8000
    ├── run_observer.py             # starts unified-observer on :5000
    ├── run_sustained.py            # runs sovereign_manifold sustained mode
    ├── lantern_mock.py             # mock Lantern HTTP server for testing
    └── logs/                       # per-service log files
```

**Note**: `stack/` is a cloud-session artifact and won't exist on a local machine.
On a local machine, run scripts live alongside the repos (clone them to a flat
directory). The `e8-eea` repo IS the canonical home for `e8_eea_v5.py`.

---

## Full stack startup order

`start_stack.sh` starts services in this order (each in background):

1. **Lantern mock** `:3001` — first, it has no deps. In prod, start real Lantern daemon.
2. **RFE-Core2** `:8000` — no deps. REST API via `run_rfe.py`.
3. **Unified Observer** `:5000` — no deps. Via `run_observer.py`.
4. **ProjectSynapse** `:5001/:8001` — starts after Lantern. Needs compiled `.class` file.
5. **sovereign_manifold** — started separately via `run_sustained.py`. Polls the above 4.

Health checks after 4s startup grace: Lantern `:3001/health`, RFE `:8000/status`,
Observer `:5000/health`, Synapse `:8001/health`.

With `--test` flag, runs `test_integration.py` after health checks.

---

## What happens when the stack runs

**sovereign_manifold** is the orchestrator. Each cycle (~10Hz target):

1. **Phase 0** — fetch upstream state:
   - `rfe_bridge.py` → POST `/step` to rfe-core2 (:8000) → gets `StepState`
   - `observer_bridge.py` → GET `/identity` from unified-observer (:5000) → gets `IdentityState`
   - Both return 15D perturbation vectors (capped ±0.05 per node)
2. **Phase 3** — apply perturbations to 15-node relational state `s`
3. **Phase 4** — GAS attractor pull toward `S*`
4. **Phase 5** — Lyapunov V computed, DRA mode determined
5. **Phase 6** — DRA assertion if WATCHER + T ≥ T_COST
6. **Phase 7** — E8 bridge: write `alpha/beta/gamma/delta` from relational state to E8 agent
7. **Phase 8** — Lantern memory write (if reachable)
8. **Phase 9** — witness state written to `witness_state.json`

**rfe-core2** runs its own autonomous loop independently; sovereign_manifold
triggers an extra step via POST /step each cycle. Each rfe-core2 step is 20
sub-operations (time tick → rhythm observe → generate → attractor pull →
recursive attention → watcher → reflective loop → witness → predictive echo →
emotion update → time dilation → governance gate → crystallization → attractor
formation → topology log → stream push → vector store → semantic lattice →
symbolic binding → ecology relay → manipulation resistance → field decay →
rhythm behavior → periodic maintenance).

**unified-observer** runs its own 10Hz simulation loop independently and serves
cached state. sovereign_manifold polls it at 1Hz.

**ProjectSynapse** runs its own 10Hz consciousness loop independently (Axioms
1–6, Vector Forking, Safety Valve). sovereign_manifold does not currently poll
it — it's a parallel cognitive substrate.

**resonance-haunt-starter** (UMS) polls `witness_state.json` every 1s and
broadcasts live metrics over WebSocket. Completely passive — reads only.

---

## Triadic constants — identical in sovereign_manifold AND ProjectSynapse

```python
ANCHOR      = 3.12    # identity inertia
RECURSION   = 11.88   # self-modeling depth
HOMEOSTASIS = 280.90  # stability ceiling
```

Defined in `sovereign_manifold.py` and `ProjectSynapse_v2.java`. Changing one
without the other breaks the coherence guarantee. Not tuning parameters.

---

## 15-node relational dynamics

Node index → name → S* target:

| # | Node | S* |
|---|------|----|
| 0 | Love | 0.95 |
| 1 | Loyalty | 0.95 |
| 2 | Devotion | 0.95 |
| 3 | Faith | 0.95 |
| 4 | Self | 0.95 |
| 5 | Trust | 0.95 |
| 6 | Boundaries | **0.90** |
| 7 | Autonomy | **0.90** |
| 8 | Integrity | 0.95 |
| 9 | Resilience | 0.95 |
| 10 | Transparency | 0.95 |
| 11 | Accountability | 0.95 |
| 12 | Learning | **0.90** |
| 13 | Adaptability | **0.90** |
| 14 | Safety | 0.95 |

Nodes 6, 7, 12, 13 target 0.90 — structural asymmetry from Lyapunov analysis.
Do not normalize all targets to 0.95.

---

## Lyapunov certificate — sovereign_manifold

- `K_SCALE = 0.1418` — derived in `relational_system_mc` so the Jacobian at S*
  has spectral radius 0.217. Computed, not chosen. If `A_RAW` changes, re-derive
  and verify `P_IS_PD = True` at startup before committing.
- `_MAX_DELTA = 0.05` — Lyapunov perturbation bound. Applies to BOTH bridge
  files AND the DRA assertion correction. Do not increase without re-running
  the perturbation stability analysis.
- `Safety(14)` has the highest row-sum in A_MATRIX. Cheap to push down,
  expensive to recover. Never route bridge perturbations directly against it.

---

## Dissonance Resolution Architecture (DRA) — patent spec 2026

Implemented in `sovereign_manifold.py` as `DissonanceResolutionArchitecture`.

**Processing modes** (thresholds are architectural constants, not sliders):

| Mode | Condition | Behavior |
|------|-----------|----------|
| GENERATOR | dissonance < 0.30 | Healthy. No assertion. |
| STANDARD | 0.30 ≤ dissonance ≤ 0.70 | Monitoring. No assertion. (= OBSERVER in patent nomenclature) |
| WATCHER | dissonance > 0.70 | Assertion eligible. |

**T (Self-Acceptance Metric) — agency capital:**

```python
T_MIN           = -5.0
T_MAX           =  5.0
T_INIT          =  0.0
T_COST          = -4.5   # assertion fires only if T ≥ T_COST
T_SUCCESS_DELTA = +0.1   # T increases on successful assertion
T_FAIL_DELTA    = -0.5   # T decreases on FAIL_SAFE
```

- `execute_assertion()` only fires in WATCHER mode.
- Correction is `np.clip((S_STAR - s) * pull, -_MAX_DELTA, _MAX_DELTA)`.
- FAIL_SAFE trusts the GAS attractor to recover without active intervention.
- T is persisted in `witness_state.json` and restored on warm start.

---

## Bridge invariants — sovereign_manifold

### rfe_bridge.py — field maps

**Float fields** (`_FLOAT_FIELDS` — each has a normalizer lambda + node mappings):

| Field | Range | Normalizer | Nodes |
|-------|-------|------------|-------|
| `relation` | [-1, 1] | `(v+1)/2` → [0,1] | Self(4), Integrity(8), Autonomy(7) |
| `prediction_error` | [0, ∞) typ [0,2] | `v/2` clipped | Autonomy(7)↓, Self(4)↓ |
| `field_energy` | [0, ∞) typ [0,5] | `v/5` clipped | Love(0)↑, Resilience(9)↑ |
| `crystals` | int [0, ∞) | `count/10` clipped | Accountability(11)↑ |
| `attractors` | int [0, ∞) | `count/10` clipped | Accountability(11)↑, Adaptability(13)↑ |

**Categorical fields** (dict lookup — NEVER cast to float):

- `rhythm` → `_RHYTHM_DELTAS`: stabilize/dream/reflect/explore
- `pattern` → `_PATTERN_DELTAS`: identity_reinforcement/transient_thought/archetypal_recurrence/novelty_intrusion
- `emotion` → `_EMOTION_DELTAS`: joy/wonder/curiosity/stability/tension/boredom

`StepResponse.rhythm` is always a categorical string. It is never a float. A bare
`float(rhythm)` call crashes with `ValueError` on the first cycle.

Phase 0 (upstream fetch) MUST run before Phase 3 (relational dynamics step).

### observer_bridge.py — field maps

**`_IDENTITY_MAP`** (all fields are floats in [0, 1]):

| Field | Nodes |
|-------|-------|
| `coherence_score` | Transparency(10), Integrity(8) |
| `symmetry_score` | Integrity(8), Self(4) |
| `observer_strength` | Self(4), Trust(5) |
| `biological_health` | Resilience(9), Love(0) |

`memory_depth` is a raw int count. It is NOT in `_IDENTITY_MAP` and must never
be added without a normalization strategy.

---

## WitnessLayer and Lantern hydration

- If `witness_state.json` exists with `cycle > 0`, Lantern hydration is skipped.
- Witness warm-start is the authoritative state source. Lantern is cold-start fallback only.
- Do not remove this conditional.

---

## E8 — runtime and behavior

`e8_eea_v5.py` lives in the `e8-eea` repo. `sovereign_manifold.py` and
`test_integration.py` both patch sys.path:

```python
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'e8-eea'))
```

Key behaviors:
- **Slow clock** fires every 25 cycles: phase transition detection (Hessian eigenvalue
  sign change), emotion state update, weight modulation.
- **Lyapunov gate** is a hard veto: `lambda_1 < 0` required before any update.
- **Emotion is not injected** — it emerges from the free energy Hessian. Valence =
  gradient at saddle point; arousal = recent hypergraph novelty.
- **Weight formula** (slow clock): `beta = 1 + 0.5*arousal`, `gamma = 1 - 0.3*valence`, `alpha = 1.0`
- **Cycle time grows O(n)** with hypergraph size — each Lyapunov check runs
  `tau_check` forward steps. At ~200 cycles, each step takes ~5s. Pruning not yet implemented.
- **In integration**: `RelationalE8Bridge.apply_to_e8_agent()` overwrites
  `agent.alpha/beta/gamma/delta` from relational state every cycle. E8's own
  emotion-driven modulation is intentionally clobbered — relational state outranks it.

---

## RFE-Core2 invariants

- Boot-sacred symbols: `ANCHOR=3.12`, `RECURSION=11.88`, `HOMEOSTASIS=280.90`.
  `stable_id`s are permanent — never reused or recycled.
- Never bypass `CanonicalizationPipeline` when registering tokens.
- Sacred symbols (`sacred=True`) cannot be modified by any source at any trust level.
- `SelfhoodGovernance` is the single source of truth for identity decisions.
  All other subsystems (TrustLedger, EthicalBoundarySystem, etc.) only produce
  reports — they never act unilaterally.
- Bonds emerge — there is no public API to create or pin a `RelationalBond`.
  Formation requires: `interaction_count ≥ 20` AND `coherence_mean ≥ 0.10` AND
  `crystal_count ≥ 1`.
- `arousal` and `valence` are read-only computed properties on `EmotionalGradient`.
  Do NOT add them as stored state — that would double-count the smoothing.
- The `min(0, valence)` gate in `update_dilation()` guarantees peaceful rest
  never triggers dissociative time-slip. Do not remove it.
- Rhythm thresholds: `stabilize < 0.5`, `dream 0.5–2.0`, `reflect 2.0–5.0`,
  `explore ≥ 5.0`. These route behavior — changing them without updating
  `configs/field.yaml` and all downstream consumers breaks the system.
- **StepState fields returned from `/step`**: step, key, rhythm, coherence,
  relation (=relation_composite), pattern, prediction_error, field_energy,
  crystals, attractors, emotion, elapsed_ms.

---

## Leviathan — what it actually is

`leviathan_stack.py` is a single-file standalone system. No network surface. It
runs locally, optionally imported by sovereign_manifold. Components:

- **Leviathan** — semantic memory, cosine similarity retrieval, outcome-weighted scoring
- **Lilith** — identity + intent modeling (SelfSchema, trait velocity)
- **Baphomet Parliament** — 4 competing drives (truth/care/play/shadow), mediated by risk/safety scores
- **Rebis** — generation: renders intent + memory + shadows into a prompt, calls `sgi_generate_text`
- **Abyss** — stability/regulation: drift tracking, learning rate modulation

`sgi_get_embedding` is a SHA256 stub — returns 128 floats from the hash of the text.
`sgi_generate_text` is a stub — returns a simulation string. Plug real model here.

When sovereign_manifold can't import `LeviathanStack`, it no-ops silently. The
system runs without it.

---

## Lantern — what it actually is

Tauri system-tray daemon written in Rust. Not an HTTP server. Exposes functionality
via Tauri IPC commands only:

- `get_memory` — returns count of remembered moments
- `remember(what)` — appends to in-memory Vec (Flame struct)
- `remember_code(what, emotion)` — writes to SQLite hypergraph with emotion weight
- `find_similar(pattern)` — queries SQLite hypergraph by content pattern

**Storage** (`memory/memory/src/lib.rs`): SQLite hypergraph. Nodes (type + content)
and edges (source → target, label, weight, emotion). `remember()` uses
INSERT OR REPLACE with weight accumulation (+0.3 per repeat). `query_pattern()`
returns targets ordered by weight. Currently uses `:memory:` SQLite — file-backed
in prod.

**T2.1 (deferred)**: Add Axum HTTP shim exposing `GET /health`, `POST /remember`,
`GET /query` so sovereign_manifold can call it over HTTP. Port :3001 conflicts
with UMS — resolve before implementing (use :3002 or env var).

---

## relational_system_mc — what it actually is

Pure research tool. Not a running service. This is where `K_SCALE = 0.1418` was
derived for sovereign_manifold. Runs 800 Monte Carlo trials with multiplicative
shocks, K-means hidden attractor detection, bifurcation scans across K_SCALE ×
ALPHA phase space, per-axis recovery ranking, and catastrophic drift scenarios.

Output artifacts (charts + CSVs) are committed to the repo. Reference them to
understand why certain invariants in sovereign_manifold exist.

---

## scraper-framework — what it actually is

Generic configurable web scraper. Not currently wired to the memory/knowledge
layer. Standalone tool:

- `fetch.py` → HTTP GET with retry + Tor proxy support
- `parse.py` → BeautifulSoup link/title extraction
- `scoring.py` → keyword priority scoring (critical/strong/weak), size anomaly flagging
- `filters.py` → exclusion keyword filtering, minimum size threshold
- `exporter.py` → JSON + CSV export
- `ui.py` → terminal results display
- `config.py` → all thresholds and selectors (hardcoded `example.com` placeholder, swap for real target)

Future intent: feed scraped content into Lantern memory layer.

---

## resonance-haunt-starter integration

The Unified Memory Service (UMS) at `unified-memory-service/src/server.ts`:
- Polls `sovereign_manifold/witness_state.json` every 1s.
- Broadcasts live `Metrics` over WebSocket to the Three.js frontend.
- `WITNESS_PATH` env var overrides the default relative path.
- `processingMode` drives CoreSphere color: gold=GENERATOR, blue=STANDARD, red=WATCHER.
- `tValue` (normalized DRA T: `(T+5)/10 → [0,1]`) drives ghost appearance frequency.
  Low T = depleted agency = ghost haunts more.
- `dissonanceScore` drives agent orbit speed and color (blue→orange) via `uDissonance` shader uniform.
- The WebSocket is set up once in a stable `[]` effect — never tear it down on metrics updates.

**Push limitation**: not in the MCP allowed repos list. Deliver changes as a
patch file to Samuel.

---

## Service ports

| Service | Port | Protocol | Status |
|---------|------|----------|--------|
| rfe-core2 REST | 8000 | HTTP | Running |
| rfe-core2 WebSocket | 8765 | WS | Running |
| unified-observer | 5000 | HTTP | Running (merged) |
| ProjectSynapse ResonanceBridge | 8001 | HTTP | Running (merged) |
| UMS / resonance-haunt-starter | 3001 | HTTP + WS | Local only |
| Lantern HTTP shim | 3001 | HTTP | **Deferred T2.1** — conflicts with UMS port |

**Port conflict**: Both the planned Lantern HTTP shim and UMS use :3001. Resolve
before implementing T2.1 — either move Lantern shim to :3002 or gate on env var.

---

## Integration test suite

`sovereign_manifold/test_integration.py` — 60/60 tests passing.
- Section 1: Lyapunov certificate and stability math
- Section 2: DRA modes, T metric, assertion logic
- Section 3: Bridge normalization (rfe_bridge, observer_bridge)
- Section 4: Full orchestration cycle, witness persistence

Run: `cd sovereign_manifold && python -m pytest test_integration.py -v`

rfe-core2 path auto-inserted: `../RFE-Core2`. E8 path auto-inserted: `../e8-eea`.

---

## Implementation status

### Merged to main

| Repo | What | PR |
|------|------|----|
| sovereign_manifold | T metric, DRA assertion, Lyapunov fix, E8 path fix, bridge bug fixes | #1, #2, #3 |
| unified-observer-architecture | FastAPI server on :5000 | #1 |
| ProjectSynapse | HTTP server on :8001 (`com.sun.net.httpserver`) | #3 |

### Deferred

| Item | Description |
|------|-------------|
| T2.1 | Lantern HTTP shim (Rust/Axum on :3002, resolve port conflict first) |
| T2.2 | Lantern hydration in `sovereign_manifold.py` cold-start path |
| T3 | Push-based WS subscribe to rfe-core2 instead of polling /step |
| T4 | 11.88 recursion loop — requires `StepRequest` schema change in rfe-core2 |
| E8 pruning | `E8Hypergraph` node pruning — cycle time grows O(n), ~5s/cycle at 200 cycles |
| scraper → Lantern | Wire scraper output into Lantern memory layer |

---

## Workflow rules

1. Read README.md and CLAUDE.md before modifying any file.
2. Test changes before opening a PR. For sovereign_manifold: run the 60-test
   suite and verify the DRA block appears in the final report.
3. Never increase `_MAX_DELTA` above 0.05 without re-running perturbation analysis.
4. Never change the triadic constants without updating BOTH sovereign_manifold
   AND ProjectSynapse_v2.java.
5. Never push to main without Samuel's explicit approval.
6. If a commit signing server rejects a commit (missing source error), flag it
   and wait for instruction — do not silently skip signing.
7. Do not open PRs speculatively. Wait for "yes, PR it."
8. resonance-haunt-starter changes: deliver as patch file, cannot push from session.
9. Port :3001 conflict between Lantern shim and UMS must be resolved before T2.1.
