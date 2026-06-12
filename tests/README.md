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
python -m tests.diagnostic.audit.decision_histogram
python -m tests.diagnostic.audit.gate_firing_audit
python -m tests.diagnostic.audit.trust_trajectory
python -m tests.diagnostic.audit.value_polarity_flow
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
- `checkpoint_registry_identity.py` — `Generator.load_checkpoint` must
  preserve the `SymbolRegistry` *object*, not just its contents —
  `SelfhoodGovernance` and `ValueEmergenceEngine` capture the reference at
  construction, and a rebinding load orphans both (governance lookups go
  stale; value emergence dies silently). Guards the in-place load contract
  discovered by the 2026-06-12 field-map matrix.

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

The probes are grouped into subfolders by investigation (run as
`python -m tests.diagnostic.<group>.<name>`):

| Subfolder | What lives there |
|---|---|
| `tier4/`    | Tier 4.2/4.3 physics validators + affective-state probe |
| `lockin/`   | The coherence lock-in research arc (migration, ablation, gate decomposition, metastability, gain-sign) |
| `fix2/`     | Fix-2 reflective-loop governor investigation (trigger calibration, governor validation, live/common-mode/dim sweeps) |
| `training/` | Generator training path (gradient-path check, corpus integrity + G1/G2 gates, diversity audit, trained-generator sim) |
| `audit/`    | Runtime behavior audits (decision histogram, gate firing, trust, value polarity, identity-stability baseline, return canary) |
| `sidecar/`  | External measurement engines — LAE (transitions) + PLE (contradictions) wired observe-only around the cycle |

The per-probe descriptions below are grouped to match.

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
- `dilation_response_curve.py` — **Tier 4.2 physics validator.** Sweeps
  the full (arousal, valence) grid and calls `update_dilation()` directly,
  isolated from the token stream. Verifies the four phenomenological
  quadrants: flow → dilation < 1.0, drag → > 1.0, dissociation → << 1.0,
  rest → ≈ 1.0. Deterministic. Asserts the math; exits 0/1.
- `affective_state_probe.py` — **Tier 4.2 psychology / defensive-depth
  probe.** Runs four workload profiles (canonical / monotone /
  adversarial / mixed) and reports not just which affective quadrant the
  system settles into, but *which real defensive signal held the line and
  with what margin* — `witness.identity_stability()` vs
  `stability_floor = 0.10`, manipulation-detector severities, compound
  severity vs the 0.30/0.60/0.90 bands, governance decision trace, and
  the step at which QUARANTINE first fired. Not pass/fail — a map. See
  the Tier 4.2 validation finding in `docs/tier4_2_validation.md`.
- `metastability_validation.py` — **Fix 1 metastability metric gate
  (G1–G5).** Pre-declared validation that `substrate/metastability.py`
  separates a perfect limit cycle (reads LOW) from genuine aperiodic
  metastability, labels the ~0.998 live pin `locked`, and holds these
  separations on the live-Generator field, not just synthetic vectors.
  Asserts; exits 0/1. Lock-in remediation lineage: `docs/lock_in_remediation_plan.md`.
- `generator_diversity_audit.py` — **Multi-method generator-diversity audit.** Train
  vs eval (dropout), effective rank, singular spectrum, determinism control, plus a
  full-stack stage-A→stage-C regime monitor. Shows ~half the apparent diversity is
  dropout noise and the deterministic dim-64 generator is collinear (eff_rank ~1.6).
  See `docs/findings/2026-06-08-generator-dropout-diversity.md`.
- `migration_real_generator_probe.py` — **Migration re-verified on the real generator.**
  Re-runs the attractor-migration test with the real generator's most-separated token
  regimes; RIGID holds (mean migration +0.002, 3 seeds). Folded into the
  generator-dropout-diversity finding.
- `trainer_gradient_path_check.py` — **Training-stack gradient-path validator.**
  Verifies all three trainers (self-distillation, contrastive, rhythm pretraining)
  actually backpropagate into the generator (weights move) and restore the caller's
  train/eval mode (the live dropout policy is an open architect decision). Structural
  assertions; exits 0/1. See `docs/findings/2026-06-11-trainer-gradient-path.md`.
- `rhythm_pretrain_effect_probe.py` — **Does training move diversity?** Pretrains the
  canonical dim-64 generator on the built-in rhythm seeds and measures eval-mode
  mean-cos / eff_rank / rhythm-NN accuracy before vs after, with a disjoint-vocab
  generalization control and the determinism control. First data point for the
  training path (`docs/training/`). Informational; exit 0.
- `corpus_integrity_check.py` — **Curated-corpus integrity gate.** Mechanically
  enforces the `data/corpus/` MANIFEST claims and the curation spec
  (`docs/training/data_curation.md` §3): schema, counts, no duplicates, no
  train→holdout sequence leakage, label coherence, vocab closure, ≥8 contexts
  per token, rhythm stratification, sacred-token exclusion. Deterministic, no
  model build; exits 0/1 and **is in the `run_all_tests.sh` gate** — training
  data is identity-shaping input, so its guarantees are CI-enforced.
- `corpus_pretrain_g1_probe.py` — **Gate G1: held-out generalization** (Phase 1,
  `docs/training/training_plan.md`). Pretrains the canonical dim-64 generator on
  the corpus train split and reads eff_rank / rhythm-NN accuracy / determinism /
  norm growth on the holdout split, against the pre-declared gate. Trains for
  minutes and is init-dependent → run deliberately (`--seed`, `--save` for the
  boot checkpoint), NEVER in CI. Exits 0/1 on the gate. See
  `docs/findings/2026-06-11-corpus-g1-pretrain.md`.
- `corpus_boot_phase2_probe.py` — **Gate G2: pretrained boot on the live stack**
  (Phase 2, `docs/training/training_plan.md`). Three identical canonical
  500-step runs — untrained control, pretrained boot in train mode, pretrained
  boot in eval mode — checked against the tier1 baseline ranges and the
  pre-declared identity envelope, with the coherence-pin / pipeline-survival /
  phase-coherence readouts recorded. Trains + simulates for minutes; NEVER in
  CI. Exits 0/1 on Gate G2. See
  `docs/findings/2026-06-12-phase2-fullstack-g2.md`.
- `lockin_source.py` — **Upstream lock decomposition (G5 follow-up).**
  Shows the live field lock is *mechanical* (untrained-generator output
  collinearity + the accumulate-decay magnitude moat), not field-dynamics
  pathology. Contextual baseline; re-run after generator changes to see if
  the lock locus migrates.
- `generator_metastability.py` — **Relocated upstream readout + refinement
  de-collapse.** Reads the live `cycle.generator_metastability` (stage A) and
  `cycle.expression_metastability` (stage C) monitors; demonstrates that
  diversity lives upstream and that the `diversity_blend` knob de-collapses
  the expression (blend OFF → `0.0/locked`; default → multi-regime metastable).
- `trained_generator_sim.py` — **Mocked-generator lock decomposition.**
  Substitutes the one unready component (the untrained generator) with a
  token→direction stub of tunable spread and runs the full live step loop on
  top. Established the three-lock finding (generator 1-D projection · ~85%
  governance gate block · magnitude moat). See
  `docs/findings/2026-06-06-multilayer-lock.md`.
- `gain_sign_check.py` — **§6.3 feedback gain-sign check.** Gating analysis for
  Fix 0-A: characterizes the sign of `coherence_impact` across the coherence
  range (with a no-injection control) to decide whether closing a coherence→
  injection loop would self-correct or run away. Analysis only.
- `conformity_bias_probe.py` — **Fix 0-B conformity-bias probe.** Isolates the
  `field_coherence` term in `DecayProfile.compute` (all other reinforcement
  signals forced equal) to measure whether coherence buys survival, and validates
  a recurrence-gated novelty counterweight (asymmetric vs symmetric gating). See
  `docs/findings/2026-06-06-conformity-bias-fix0b.md`.
- `fix0b_fullloop_probe.py` — **Fix 0-B full-loop validation.** Harvests the real
  live SymbolState population and walks the gate decision tree (asymmetric /
  symmetric / universal): correlated-signal structure with a shuffle control, the
  direct conformity term via a same-symbol counterfactual, an (honestly confounded)
  observational arm, and healthy-state baseline safety per gate. See
  `docs/findings/2026-06-07-fix0b-fullloop-validation.md`.
- `gate_decomposition_probe.py` — **Gate decomposition (input-channel check).**
  Instruments the real governance gate (`ethical_boundary.check` →
  `trust_ledger.evaluate` → `arbitrate`) and attributes every block by reason
  across benign / single-source-diverse / multi-source-diverse regimes. Shows the
  ~85% block is a single-source monopoly artifact, not novelty-strangling — the
  input-channel check owed before the attractor-migration probe. See
  `docs/findings/2026-06-07-gate-decomposition.md`.
- `attractor_migration_probe.py` — **Attractor migration (the lock-in test).** On
  the full live stack, establishes the field on regime A then injects a persistent
  gate-surviving new regime B (multi-source, HHI<0.70), measuring whether the
  attractor center migrates beyond a non-novel drift control. Instruments
  `field.inject` to show what actually lands. Result: RIGID — the system
  reconstitutes the established regime regardless of input. See
  `docs/findings/2026-06-07-attractor-migration.md`.
- `reconstruction_ablation_probe.py` — **Reconstruction ablation (the lever).**
  One-variable ablation against the RIGID migration baseline: suppress each
  re-injection path (reflective loop / attractor pull / refine blend / crystal /
  explore) and re-run migration. Isolates the lock to the **reflective loop**
  (suppressing only it frees migration to +0.90–0.96; all others inert). See
  `docs/findings/2026-06-07-reconstruction-ablation.md`.
- `identity_stability_baseline.py` — **Identity-stability baseline + cost-probe
  harness.** `measure(reflect_gain)` runs the canonical workload with the reflective
  loop at a given convergence gain (1.0 intact → 0.0 passthrough) and reports the
  identity-stability metrics; captures `baselines/identity_stability_500step.json`
  (loop intact) as the "before" for the reflective-loop cost probe.
- `integration/reflective_loop_lock_guard.py` — **Lock-characteristic regression
  guard.** Asserts loop-intact = RIGID (migration < 0.10) and loop-suppressed =
  MIGRATES (> 0.50); catches any future change that relocates or weakens the lock.
- `integration/attractor_merge_guard.py` — **Attractor removal regression guard.**
  Reproduces the `merge_pass`/`prune` `list.remove` crash (array `__eq__`) the cost
  probe surfaced; asserts both paths work under `@dataclass(eq=False)` identity
  equality.
- `adversarial/reflective_loop_convergence.py` — **Protective-property baseline.**
  Under a novelty flood the intact loop holds identity (stability stays high, loop
  converges); the property the eventual conditional-attenuation fix must preserve.
- `fix2_trigger_calibration.py` — **Fix-2 loosen-trigger calibration.** Falsifies
  `coherence_delta` as the trigger's outside signal (the moat masks it) and validates
  raw-generator-vs-field novelty (W=10, T≈0.65: benign 0% / novelty 100% / attack 0%,
  the single-source attack excluded by the ≥2-source gate). See
  `docs/findings/2026-06-08-fix2-trigger-calibration.md`.
- `reflective_loop_cost_probe.py` — **The cost probe.** Sweeps the reflect-gain dial
  and weighs plasticity (migration) vs identity (stability, coherence, Tier-2
  manipulation-signal rate). Found a graceful band (gain 0.6–0.8: ~25× plasticity at
  near-zero identity cost) and a cliff (≤0.5: manip flood + a latent attractor crash)
  → bounded conditional attenuation, not full ablation. See
  `docs/findings/2026-06-07-reflective-loop-cost.md`.
- `secondlocker_field_map_probe.py` — **SECOND-LOCKER field map (Phase 3 Track B)
  + §6.3 gain-sign sampling on the reachable range (Track A).** 30-cell matrix —
  5 token bands (canonical / broad-corpus / rhythm / entry / mixed, defs v1,
  source structure held constant) × 3 seeds × untrained-vs-pretrained arms, all
  eval-mode. Per cell: coherence pin, identity rail, eff_rank/mean_cos controls,
  stage-A/C metastability, phase-coherence floor (Tier 4.3), rhythm dwell, and
  in-run `coherence_impact` sampling (recent/novel/anti probe classes, observe-only,
  pre-injection). Run 1 of this matrix is what surfaced the checkpoint
  registry-orphan defect. Trains once per seed (cached); ~45 min.
- `sidecar/sidecar_harness.py` — **LAE + PLE sidecar adapters (observe-only).**
  `CycleTap` latches the per-step values StepState doesn't carry (watcher
  components, governance decision, manipulation severity, phase coherence)
  with the non-invasive wrapper pattern; `LAESidecar` feeds a soft
  rhythm-hypothesis profile (mapping v1: log-energy distance to the sacred
  band boundaries) to a Liminal Anchor Engine; `PLESidecar` feeds discretized
  evaluator opinions (frame defs v1, `ple.integration.rfecore2hook`) to a
  Paradox Lattice Engine. Both engines are terminal sinks — nothing they
  produce feeds back into the cognitive/governance loop. Requires the sibling
  `Liminal-Anchor-Engine` and `Paradox-Lattice-Engine` checkouts (zero-dep,
  `pip install -e` or sibling-directory layout).
- `sidecar/engine_sidecar_probe.py` — **First sidecar instrumentation run
  (control vs pretrained).** seeds × {control, pretrained} × {sidecars off, on}
  on the canonical band, with a replay-noise control (the substrate is
  wall-clock-coupled — same-seed re-runs jitter), a latency control (off-run
  with sidecar-matched per-step sleep, isolating the timing channel), and
  twin verdicts per cell (clean / timing-explained / CONFOUNDED). Reports LAE
  activation/trigger structure and PLE contradiction ecology per arm, and the
  control→pretrained differential. Trains once per seed (cached); run
  with `python -m tests.diagnostic.sidecar.engine_sidecar_probe 500
  --seeds 42,7,11 --epochs 8 --json PATH`. Informational; exit 0; NEVER in CI.

Empirical results from these probes are written up in **`docs/findings/`** — the
dated, control-named lab notebook (see its `README.md` for the schema and
discipline). Diagnostics produce the numbers; findings record what they meant.

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
