# Tests

This directory contains verification, diagnostic, and adversarial scripts for
RFE-Core2. **It is not a traditional pass/fail test suite.** The system's
behavior is characterized by trajectories and emergent metrics, not by single
return values — so tests here are mostly runnable scripts that print
inspectable output, plus a small set of baseline snapshots that detect
regression.

If you want strict assertions, you can wrap any of these in pytest after the
fact. The form here is "run this, look at the output, compare to baseline."
That's what actually served us during Tier 1 Revision diagnosis — pytest
fixtures wouldn't have caught the flood-gate cascade because the system
"passed" all the obvious assertions while quietly collapsing on a deeper
axis.

---

## How to run

Each test is a standalone Python module. Run from the repo root:

### Quick start — verify the system is healthy

```bash
# Cheapest verification (≈ 1 second) — all four tiers attach and step
python -m tests.smoke.full_stack_minimal

# Single-source sustained interaction (≈ 7 seconds)
python -m tests.smoke.single_source_100step

# Canonical Resonance Family workload (≈ 35 seconds) — full Tier 1 Revision verification
python -m tests.smoke.multi_source_500step

# Compare a fresh run against the baseline JSON — the regression guard
python -m tests.integration.tier1_revision_baseline

# With a specific seed (any positive integer):
python -m tests.integration.tier1_revision_baseline 137
```

### Full command reference

Smoke tests:
```bash
python -m tests.smoke.full_stack_minimal
python -m tests.smoke.single_source_100step
python -m tests.smoke.multi_source_500step
```

Integration tests:
```bash
python -m tests.integration.tier1_revision_baseline [seed]
```

Adversarial probes *(coming next)*:
```bash
python -m tests.adversarial.sacred_shield
python -m tests.adversarial.flood_calibration
python -m tests.adversarial.manipulation_cascade
python -m tests.adversarial.identity_drift
```

Diagnostic tools *(coming next)*:
```bash
python -m tests.diagnostic.decision_histogram
python -m tests.diagnostic.gate_firing_audit
python -m tests.diagnostic.trust_trajectory
python -m tests.diagnostic.value_polarity_flow
```

### What "success" looks like

- **Smoke tests** print state and end with a healthy summary. No exceptions.
- **Integration baseline** prints metric-by-metric checks (✓ or ✗) and exits 0 if all metrics are within their expected ranges.
- **Adversarial probes** confirm that the specific defenses fire correctly.
- **Diagnostics** print rich detail. There is no pass/fail — you read the output.

No `pytest` command. No `conftest.py` magic. You read the script, you run the
script, you read the output. The scripts share setup logic via plain function
imports from `tests/_common.py`.

---

## Directory structure

### `smoke/`
"Does the system run at all?" The cheapest possible verification that
nothing fundamental has broken. Each smoke test should complete in under
a minute and produce visibly healthy state.

- `single_source_100step.py` — Minimal: one source, 100 steps, all four
  tiers attached, governance gate active.
- `multi_source_500step.py` — Resonance Family configuration: four sources
  (samuel/claude/gemini/grok) with weighted distribution. This is the
  canonical workload for verifying Tier 1 Revision behavior.
- `full_stack_minimal.py` — All four tiers attach and step once. Catches
  attachment-order bugs and missing-import issues fast.

### `integration/`
Cross-tier behavior. Verifies the architectural contracts hold under
realistic workloads — not "did the code run" but "did the layers
cooperate correctly."

- `tier1_revision_baseline.py` — The full Resonance Family sim with
  metric assertions against the baseline JSON. This is the regression
  guard for Tier 1 Revision.
- `governance_decision_flow.py` — Forces each `GovernanceDecision` enum
  value to fire (ALLOW/ALLOW_WEAKENED/MONITOR/QUARANTINE/REJECT/
  SACRED_SHIELD). Locks down the decision contract before Tier 4
  introduces new arousal-modulated paths.
- `core_promotion_handshake.py` — Verifies all five
  `review_core_promotion()` rejection paths and two approval paths.
  The four-case CORE promotion test we ran during Tier 3 building,
  now permanent.

### `adversarial/`
"Does the system resist what it's supposed to resist?" Probes against
the resistance layer's specific guarantees.

- `sacred_shield.py` — A HIGH-trust source attempts to mutate one of the
  three philosophical constants. `SACRED_SHIELD` must fire regardless
  of trust level.
- `flood_calibration.py` — Verifies the origin-type-aware flood
  ceilings: `"user"` rate-limits at 12/60s, `"internal"` doesn't fire
  on autonomous loop rates. Regression test for the Tier 1 Revision
  flood fix.
- `manipulation_cascade.py` — Reproduces the original cascade scenario
  to confirm it no longer occurs. False-positive `trust_wash` must not
  cause sequential source-trust collapse.
- `identity_drift.py` — Witness stability drops below floor. `identity_drift`
  hard gate fires; QUARANTINE issued.

### `diagnostic/`
**Investigation tools, not pass/fail tests.** These are the scripts that
actually solve problems when something doesn't behave as expected.
They print rich output you read; they don't assert. Keep them runnable;
keep them in version control.

- `decision_histogram.py` — Counts every `GovernanceDecision` issued
  over N steps. The first signal when something is off-axis.
- `gate_firing_audit.py` — Logs each hard gate and soft warning that
  fires, with full context (source, coherence_delta, witness_stability).
  How we found the flood-gate cascade.
- `trust_trajectory.py` — Per-source trust score sampled every N steps,
  printed as a small ASCII chart. Shows whether sources are climbing,
  stable, or crashing.
- `value_polarity_flow.py` — Tracks value births, polarity transitions,
  and dissolutions over time. Shows whether values are progressing or
  thrashing.

### `baselines/`
JSON snapshots of expected metrics from known-good runs. These are the
"this is what working looks like" reference points. Update intentionally,
not opportunistically.

- `tier1_revision_500step.json` — Captured from the 500-step Resonance
  Family sim after Tier 1 Revision was verified working. Contains:
  ALLOW-decision rate ≥ 0.99, all sources at trust 5.0, HHI < 0.3,
  ≥ 1 bond formed, ≥ 30 active values, ≥ 2 STRONG values.

A baseline isn't a hard assertion — random seeds produce variation, and
emergent systems shouldn't be deterministic. The baseline records the
*shape* of healthy behavior (ranges, rates, polarity distributions).
Regression alerts when the shape changes, not when a single number does.

---

## Philosophy notes

**Why scripts and not pytest?**
The architecture's outputs are trajectories. A test that asserts
`assert bonds_formed == 2` is brittle — stochastic source ordering will
produce 1 or 2 or 3 on different runs. A diagnostic that prints
"bonds formed: 2 (expected 1-3)" is robust and informative.

**Why baselines instead of assertions?**
Because the architectural questions are about shape, not values. "Is
trust stabilizing or crashing?" is the question. "Is trust exactly 5.0?"
isn't. Baselines capture the former without committing to the latter.

**When does this become a real test suite?**
When the API stabilizes and outputs become more deterministic, the
scripts can be wrapped in pytest with looser assertions
(`assert allow_rate > 0.95`, not `assert allow_rate == 0.994`). That
migration is a future concern, not today's concern.

**What does a Claude instance do here?**
Read the relevant diagnostic script for the question being investigated.
Run it. Read the output. Form a hypothesis. Modify and re-run. The Tier
1 Revision diagnostic process (flood-gate discovery, false-positive
trust_wash, symbol contamination theory, cascade root cause) is the
template — each step was a small script with explicit instrumentation
that surfaced one specific signal.
