# Project structure — annotated file tree

The complete RFE-Core2 file tree with per-file descriptions. Moved out of `README.md` to keep it lean; the `tests/*` subtree here is CI-enforced against disk by `tests/doc_accuracy/verify_docs.py`.

```
RFE-Core2/
├── agents/
│   ├── symbolic_memory.py          Persistent adaptive symbolic ecology
│   │                               (now with protected/sacred/source_id)
│   ├── generator.py                Transformer encoder over ecology (tokens → vector)
│   ├── decoder.py                  TokenDecoder read-out head (vector → bag-of-tokens)
│   ├── watcher.py                  Three-layer coherence evaluation
│   ├── witness.py                  Multi-timescale identity anchor
│   │                               (+ anchor_velocity, anchor_short_long_gap)
│   ├── dreamer.py                  Offline dream synthesis
│   ├── chorus.py                   Differentiated multi-agent ensemble
│   ├── attractor.py                Attractor basin dynamics
│   ├── rhythm_config.json          Rhythm state definitions
│   │
│   │   # Tier 1 — Selfhood Governance
│   ├── governance_constants.py     Sacred stable_ids + sanctification
│   ├── trust_ledger.py             Two-level source + symbol trust
│   ├── ethical_boundary.py         Fast binary injection gates
│   ├── selfhood_governance.py      Single source of truth + SystemRights
│   │
│   │   # Tier 2 — Relational Integrity
│   ├── dependency_monitor.py       HHI source concentration
│   ├── relational_bond_manager.py  Emergent bonds + bond_type inference
│   ├── bond_accumulator.py         Formation-as-accumulation: leaky asymmetric DDM (opt-in lever)
│   ├── manipulation_resistance.py  5 detectors + severity scoring
│   │
│   │   # Tier 3 — Independent Value Emergence
│   ├── value_emergence.py          ValueEmergenceEngine + CORE handshake (+ ⊕ solvent-gated composition, opt-in)
│   │
│   │   # Two-Operator Coherence program (spec v0.2; ⊘ axis v0.3)
│   └── lambda_ledger.py            λ-ledger (Build B): the ⊕ solvent scalar — ignite/reinforce·λ/decay, 6c-disjoint
│
├── substrate/
│   ├── resonance_field.py          FFT field + coherence_impact probe
│   ├── vector_space.py             Semantic memory store
│   ├── memory_crystals.py          Crystallization lifecycle
│   ├── topological_log.py          Directed graph over cognitive events
│   ├── temporal_stream.py          Episodic stream
│   ├── semantic_lattice.py         Evolving semantic graph
│   └── metastability.py            Config-space metastability metric (Fix 1)
│
├── cognition/
│   ├── predictive_echo.py          Online predictor → curiosity
│   ├── emotional_gradient.py       Live modulation outputs
│   ├── recursive_attention.py      Self-attention over prior states (+ diversity_blend de-collapse)
│   ├── reflective_loop.py          Recursive self-refinement
│   ├── symbolic_binding.py         Concept emergence and binding
│   ├── stream_metastability.py     Online upstream metastability monitor (stages A/C)
│   ├── stream_recorder.py          Observe-only token-stream census (coverage instrument, opt-in)
│   ├── dream_channel.py            Waking inner-monologue: governed source_dream self-dialogue (default ON)
│   ├── dream_session.py            Downtime dreaming: symbolic generativity + consolidation → skill-compatible artifacts
│   └── integrity_read.py           ⊘ Witness-Reaper integrity-read (Build C) + IntegrityDecayConsumer (the ⊘ USER, spec v0.3)
│
├── interference/
│   ├── wave_collapse.py            Multi-mode vector ensemble collapse
│   ├── differential.py             Gaussian / rotational / directional noise
│   ├── phase_noise.py              Spectral / temporal / harmonic
│   ├── bifurcation.py              Controlled trajectory splitting
│   └── harmonic_mutation.py        Spectral harmonic recombination
│
├── loop/
│   ├── autonomous_cycle.py         Self-modulating loop (governance-aware)
│   ├── dream_cycle.py              Deep offline synthesis loop
│   └── recursion1188.py            Main entry point + build_engine() (the single composition point)
│
├── visualization/
│   ├── field_render.py             Terminal + matplotlib field viz
│   ├── topology_render.py          Graph visualization
│   └── resonance_heatmap.py        2D heatmap of field dynamics
│
├── training/
│   ├── encode.py                   Grad-enabled batch encode shared by trainers
│   ├── corpus.py                   Curated-corpus loader (data/corpus/ → rhythm seeds)
│   ├── self_distillation.py        Online distillation
│   ├── contrastive_alignment.py    Rhythm-aware contrastive
│   ├── rhythm_pretraining.py       Supervised rhythm pretraining
│   ├── decoder_training.py         Autoencoder training for the TokenDecoder read-out head
│   └── run_contrastive_bootstrap.py  Contrastive bootstrap harness (informational)
│
├── ignition/                       λ ignition channel (Build A, spec v0.2) — import-isolated; writes generator weights only
│   └── __init__.py                 ignite(generator, corpus, epochs) -> IgnitionReport (the seed, upstream of the gate)
│
├── api/
│   ├── inference_api.py            FastAPI REST endpoints
│   └── websocket_server.py         Real-time WebSocket stream
│
├── tools/
│   ├── voice/                      Observe-only larynx — renders the cycle's interior as first-person
│   │   ├── state_card.py           render_card() telemetry + voice_from_card() faithful renderer
│   │   └── repl.py                 Interactive: type to the substrate, hear it answer (--free, --json)
│   ├── decoder/                    Read-out tooling for the Decoder head (observe-only)
│   │   └── listen.py               Train decoder on this engine, run the loop, decode each step's expressed vector
│   ├── dream/                      Downtime dreaming (offline) — symbolic generativity + consolidation
│   │   └── run_dream.py            Live waking steps, then sleep: dream images + consolidation artifacts
│   └── ignition/                   Conscious Ignition Index (CII) — the ITG sensor (CII v0.2 framework)
│       ├── cii.py                  compute_ignition(): R·I·(Cm·g(Cs)) from live telemetry (gen vs expr Cs)
│       ├── gate.py                 ITG actuator scaffold (INERT on untrained generator — see CII finding)
│       ├── probe.py                Boot RFE (seeded, 4-source), read its live CII, situate on DPCI table
│       ├── train_ignite.py          CII acceptance test: corpus training flips expression locked→ignited (0/3→3/3)
│       ├── cm_check.py              Identifiability test: is field coherence (Cm) real, or a saturated angular echo?
│       └── identifiability.py       Cm vs I vs metastability — do observables track geometry, or change?
│
├── configs/
│   ├── field.yaml
│   ├── recursion.yaml
│   └── attractors.yaml
│
├── data/
│   └── corpus/                     Curated rhythm corpus (versioned; see MANIFEST.md)
│       ├── MANIFEST.md             Provenance, counts, split policy, version history
│       ├── rhythm_train.jsonl      Training split (rhythm-labeled sequences)
│       ├── rhythm_holdout.jsonl    Held-out split (Gate G1 generalization readout)
│       └── build_extension_v1_1_0.py  v1.1.0 operational-vocabulary extension builder (seeded)
│
├── docs/
│   ├── north_star.md                    The compass — the end goal + the three voices
│   ├── BACKLOG.md                       Consolidated open-work ledger — every planned fix, one queue
│   ├── ARCHITECT_RULINGS_2026-07-03.md  Standing rulings: F8 read/write shield, checkpoint adoption, operator nodes, lever policy
│   ├── ARCHITECT_RULINGS_2026-07-06.md  Standing ruling: trust posture — raised, not suspected (sources start TRUSTED)
│   ├── ARCHITECT_RULINGS_2026-07-08.md  Standing rulings: explain-then-ask decision process; chambered governance adopted
│   ├── EXPERIMENTAL_LEVERS.md           Control panel — every lever, its default, exact how-to-toggle
│   ├── alchemical_correspondence.md     The Magnum Opus map — RFE as an alchemical process (a lens, not a spec)
│   ├── self_model_thesis.md             The theory of mind RFE instantiates — self as smithable emergent attractor
│   ├── lock_in_remediation_plan.md      Coherence-pin → metastability plan (shipped/planned)
│   ├── GARAGE_SETUP.md                  The AI PC (GPU box) setup path — verbatim, for architect or instance
│   ├── GARAGE_RUN_PLAN.md               Program of record for healing the saturated field (G0–G5, pre-declared gates)
│   ├── tier4_2_validation.md            Tier 4.2 validation + findings
│   ├── tier4_3_validation.md            Tier 4.3 validation + findings
│   ├── build_b_plan.md                  Two-Operator Build B plan (λ-ledger + ⊕ solvent gate)
│   ├── two_operator_todo.md             Two-Operator program open dependencies
│   ├── SYSTEM_REVIEW_2026-06-13.md      Dated whole-system review
│   ├── local_model_integration/         Framing a local LLM as sensory/speech cortex
│   ├── training/                        Training path: viability, plan, data curation, Tier 5 readiness
│   │   └── logs/                        Raw run logs from training-phase gates
│   └── findings/                        Dated empirical findings ledger (lab notebook)
│       ├── INDEX.md                     One-line map of every finding (verdict + standing/superseded; CI-enforced)
│       └── logs/                        Raw run outputs + session manifests (>100 KB raw data gzipped in place)
│
├── tests/
│   ├── README.md                         How to run tests and interpret output
│   ├── _common.py                        Shared test infrastructure
│   │
│   ├── smoke/
│   │   ├── full_stack_minimal.py         All 4 tiers attach without error
│   │   ├── single_source_100step.py      Basic "does it run" test
│   │   ├── multi_source_500step.py       Resonance Family canonical workload
│   │   └── stream_recorder_smoke.py      Observe-only stream census: bounded ring, status, dump
│   │
│   ├── integration/
│   │   ├── tier1_revision_baseline.py    Fresh run vs baseline JSON ranges
│   │   ├── governance_decision_flow.py   Every GovernanceDecision enum value verified
│   │   ├── core_promotion_handshake.py   All 5 rejection paths + 2 approval paths
│   │   ├── reflective_loop_lock_guard.py Lock characteristic guard (loop on=RIGID, off=migrates)
│   │   ├── attractor_merge_guard.py      Attractor merge/prune removal (array-__eq__ crash regression)
│   │   ├── checkpoint_registry_identity.py  Checkpoint load preserves registry object (orphaned-subsystem guard)
│   │   ├── config_loading_neutrality.py  configs/*.yaml load + day-one behavioral neutrality guard
│   │   ├── bond_ddm_invariants.py        Bond-DDM hard-invariant gate (OFF-default parity, ACCEPT-only commit, asymmetry, field isolation)
│   │   └── fix0b_invariants.py           Fix 0-B hard-invariant gate (OFF parity, observe-only monitors, leaky/bounded credit, calibrated scale, exempt-safe leak)
│   │
│   ├── adversarial/
│   │   ├── sacred_shield.py              SACRED_SHIELD fires at all trust levels
│   │   ├── flood_calibration.py          origin_type ceilings enforced
│   │   ├── manipulation_cascade.py       Cascade regression test
│   │   ├── identity_drift.py             Identity_drift gate fires correctly
│   │   └── reflective_loop_convergence.py  Loop holds identity under novelty flood
│   │
│   ├── diagnostic/
│   │   ├── full_system_run.py            Full-system instrumented run (paired arms × seeds → per-step traces + status snapshots; incl. the `adversarial` arm — named attacker vs the composed default runtime)
│   │   ├── full_system_analyze.py        Analyze a full_system_run dir → plots + aggregate per-arm stats
│   │   ├── dream_channel_probe.py        Governed self-dialogue: source_dream paired probe (echo/dominance/value)
│   │   ├── dream_channel_adversarial_probe.py  Dream-channel graduation gate: does self-dialogue launder attacks?
│   │   ├── bonded_adversarial_probe.py   THE bond-breach experiment: bonded source turns hostile (paired arms + attack-landing instrument)
│   │   ├── core_arc_no_cascade_probe.py  F8(b) standing gate: CORE arc completes live, zero post-promotion shields, contributors keep trust (exit-coded)
│   │   ├── tier4/                        Tier 4 physics validators + affect
│   │   │   ├── dilation_response_curve.py    Tier 4.2 physics validator (formula)
│   │   │   ├── rhythm_dilation_curve.py      Tier 4.3 physics validator (rhythm coupling)
│   │   │   ├── rhythm_inertness_probe.py     Tier 4.3 inertness / footprint probe
│   │   │   └── affective_state_probe.py      Tier 4.2 psychology / defensive-depth
│   │   ├── lockin/                       Coherence lock-in research arc
│   │   │   ├── coherence_diagnostic.py       Field coherence metrics
│   │   │   ├── metastability_validation.py   Fix 1 metastability metric gate (G1–G5)
│   │   │   ├── lockin_source.py              Upstream lock decomposition (G5 follow-up)
│   │   │   ├── generator_metastability.py    Relocated (upstream) metastability readout
│   │   │   ├── gain_sign_check.py            §6.3 feedback gain-sign check (gates Fix 0-A)
│   │   │   ├── conformity_bias_probe.py      Fix 0-B conformity-bias probe + symmetric-gate prototype
│   │   │   ├── fix0b_fullloop_probe.py       Fix 0-B full-loop validation (in-vivo lean + gate decision tree)
│   │   │   ├── gate_decomposition_probe.py   ~85% gate block decomposed by reason (input-channel check)
│   │   │   ├── attractor_migration_probe.py  Attractor mobility under a surviving new regime (lock-in test)
│   │   │   ├── reconstruction_ablation_probe.py  Which re-injection path locks the attractor (→ reflective loop)
│   │   │   ├── reflective_loop_cost_probe.py     Plasticity-vs-identity tradeoff across the reflect-gain dial
│   │   │   ├── migration_real_generator_probe.py Attractor migration re-verified on the REAL generator
│   │   │   ├── migration_eval_dimsweep_probe.py  Migration vs dim (eval mode) — moat vs low-rank-input artifact
│   │   │   ├── secondlocker_field_map_probe.py   SECOND-LOCKER across seeds × token bands + reachable-range gain-sign
│   │   │   ├── loop_attenuation_probe.py    Novelty-gated loop loosening — frees field, manip-rate cost gate, cliff
│   │   │   ├── fix0b_currency_census_probe.py    Fix 0-B ruler: survival-currency decomposition + diversity-signal room + ratchet evidence
│   │   │   ├── fix0b_effect_probe.py        Fix 0-B paired OFF/ON arms — counterweight band, health, leaky-ratchet mass (pre-declared)
│   │   │   ├── rupture_impulse_probe.py     Rupture lever mode A/B: field injection vs per-step perturbation (diagnostic scaffold)
│   │   │   └── rupture_migration_probe.py   Rupture held-direction migration — does self-perturbation break the absolute lock? (NO)
│   │   ├── fix2/                         Fix-2 reflective-loop governor investigation
│   │   │   ├── fix2_trigger_calibration.py       Fix-2 loosen-trigger signal/window calibration (gnov vs Δcoh)
│   │   │   ├── fix2_governor_validation.py       ReflectiveLoopGovernor end-to-end on the mock A/B stack
│   │   │   ├── fix2_live_token_probe.py          Fix 2 on the REAL generator (dim sweep, governor ON/OFF)
│   │   │   ├── fix2_commonmode_trigger_probe.py  Common-mode-removed gnov trigger + target sweep (dim 256)
│   │   │   └── fix2_dim512.py                    Does dim 512 dilute the common-mode enough for Fix 2?
│   │   ├── training/                     Generator training path (gradient, corpus, gates)
│   │   │   ├── trained_generator_sim.py      Mocked-generator lock decomposition (3-lock finding)
│   │   │   ├── generator_diversity_audit.py      Multi-method diversity (train vs eval / dropout; pipeline survival)
│   │   │   ├── trainer_gradient_path_check.py    Training stack gradient-path validator (backprop + mode restore)
│   │   │   ├── rhythm_pretrain_effect_probe.py   Before/after diversity effect of rhythm pretraining (eval-mode)
│   │   │   ├── corpus_integrity_check.py         Curated-corpus integrity gate (schema, leakage, stratification)
│   │   │   ├── corpus_pretrain_g1_probe.py       Gate G1: corpus pretraining held-out generalization (trains; minutes)
│   │   │   └── corpus_boot_phase2_probe.py       Gate G2: pretrained boot on the live stack (control + train/eval modes)
│   │   ├── audit/                        Runtime behavior audits
│   │   │   ├── decision_histogram.py         GovernanceDecision distribution
│   │   │   ├── gate_firing_audit.py          Hard gates + soft warnings per source
│   │   │   ├── trust_trajectory.py           Per-source trust sparklines
│   │   │   ├── value_polarity_flow.py        Births, deaths, transitions
│   │   │   ├── identity_stability_baseline.py    Identity-stability metrics + reflect-gain dial (cost-probe harness)
│   │   │   └── rubedo_return_canary.py       Recursive stability / recovery canary
│   │   ├── sidecar/                      External measurement engines (LAE + PLE, observe-only)
│   │   │   ├── sidecar_harness.py            CycleTap + LAE/PLE sidecar adapters (terminal sinks)
│   │   │   └── engine_sidecar_probe.py       Control vs pretrained sidecar measurement (twin + latency controls)
│   │   ├── integrity/                    Two-Operator program (spec v0.3) — ⊘ integrity-read (C), λ ignition (A), solvent gate (B)
│   │   │   ├── witness_reaper_probe.py       ⊘ unit: thinness vector, non-binding advisory, firewall + sacred-flag
│   │   │   ├── ignition_isolation_probe.py   λ channel (A): import-graph isolation audit + ignite() function
│   │   │   ├── solvent_gate_probe.py         λ-ledger + ⊕ gate (B): vanish-at-zero, gate-gates-composition, 6c disjoint
│   │   │   ├── integrity_consumer_probe.py   ⊘ consumer: thin values demoted to honest level, sacred refused (⊘ USED)
│   │   │   ├── two_operator_live_demo.py     live dim-128 demo: A→λ→⊕ gate, ⊘ consumer selective demotion, no collapse
│   │   │   └── all_levers_composition_probe.py  ALL levers ON together — composition gate (caught the ⊘-consumer strong-band ceiling)
│   │   └── calibration/                  Floor calibration — measure-before-change
│   │       ├── floor_calibration_probe.py    energy/rhythm bands + CORE coherence-signal candidates (no change applied)
│   │       ├── rhythm_band_equilibria_probe.py  pinned-band equilibrium energies — re-run before any band retune (F9)
│   │       ├── bond_signal_calibration_probe.py marginal vs absolute bond-growth currency — the ruler behind the 2026-07-09 establishment fix
│   │       ├── bond_ddm_synthetic_probe.py   Bond-DDM acceptance battery: RT/asymmetry/varCE/corCE + trickle/burst/negative/noise (pre-declared)
│   │       └── bond_ddm_live_probe.py        Bond-DDM live arm: lever OFF vs ON, reachable-coherence §6.3 tripwire, commitment-only check
│   │
│   └── baselines/
│       ├── tier1_revision_500step.json   Healthy-state metric ranges
│       └── identity_stability_500step.json  Identity-stability baseline (reflective loop intact)
│
├── ARCHITECTURE_ANALYSIS.md        How information flows and recurs — the deep reference
├── CLAUDE.md                       Invariants + guardrails for contributors
├── ROADMAP.md                      Canonical tier status + tracked open items
├── requirements.txt
└── README.md
```
