# Experimental Levers — the control panel

Validated work is useless if you can't find the switch. This is the **one page**
that lists every experimental capability built on top of the shipped tiers, what
it does, whether it's recommended, and the **exact** way to turn it on. If you
remember nothing else, read *The toggle switches* table below.

A **dial census** (2026-10-14) sits at the bottom of this page: every constructor
default, YAML key, `CONFIG` flag, detector threshold, and speech-cortex floor,
with a width-sensitivity mark for the planned 128 → 768 widening. The toggle
table is still the on/off panel; the census is every numeric leftover the
widening has to know about.

Most capabilities here are **opt-in / off by default**; a validated few have
**graduated to default-on** (listed under "Already applied" below). The switches
live in three places, layered as **component default < `configs/*.yaml` < `CONFIG`**:

- **`configs/*.yaml`** — `field.yaml`, `attractors.yaml`, `recursion.yaml`, loaded
  at boot by `configs/loader.py` (via `build_engine`). The live edit surface for
  component parameters (field/watcher/crystal/attractor/cognition/chorus/…). Values
  ship equal to the code defaults, so editing one changes behavior.
- **`loop/recursion1188.py` `CONFIG`** — owns the entry-point flags (dim, the
  graduated levers, intervals, …) and **overrides** the matching YAML keys. The
  authoritative tiebreaker (CLAUDE.md).
- **The cycle's opt-in attach hooks** — `cycle.attach_lambda_ledger(...)`,
  `attach_integrity_read(...)`, `attach_integrity_consumer(...)` (the Two-Operator
  overlay), plus the code-level `IgnitionGate(cycle)` (ITG). Nothing attaches
  these by default.

> **Two YAML sections are documentation only (not applied):** `attractors.yaml`'s
> `constants` (ANCHOR/RECURSION/HOMEOSTASIS are SACRED — code-authoritative,
> inviolable) and `decay_profiles` (a partial snapshot; the code `DecayProfile`s
> carry more fields, so loading it as-is wouldn't be neutral — pending a
> full-fidelity expansion). Everything else in the three files is live.

## The toggle switches

The behavior-bearing flags in `CONFIG`. Shape params (`dim`, `vocab_size`,
`depth`, `heads`, `ff_mult`, `dropout`) and cadence (`intervals`, `step_delay`,
`n_steps`) are in the [dial census](#dial-census--every-numeric-lever) below,
not omitted anymore — they are exactly what a width change moves:

| Switch (`CONFIG[...]`) | Default | Effect |
|------------------------|---------|--------|
| `pretrain_on_corpus` | **True** | Corpus pretrain at boot (graduated lever; see below). False = fast cold start. |
| `pretrain_epochs` | `8` | Epochs when pretraining. |
| `reflect_novelty_attenuation` | **True** | Novelty-gated loop loosening (graduated lever; ceiling `ReflectiveLoop.attenuation_max=0.30`). |
| `dream_channel_enabled` | **True** | Waking self-dialogue (graduated lever; see below). The system's own decoded expression re-enters as `source_dream` through `arbitrate()`. False = no self-dialogue. |
| `dream_channel_p` | `0.20` | Fraction of waking steps fed as `source_dream` (the validated weight). |
| `dream_channel_epochs` | `20` | Decoder read-out training epochs at boot. |
| `dream_channel_top_k` | `6` | Candidate tokens read from the expressed vector. |
| `dream_channel_n_tokens` | `3` | Dream utterance length (corpus 2–4 range). |
| `bond_ddm_formation` | **True** | Bond-formation quality decision rides the leaky asymmetric DDM accumulator (graduated lever, 2026-07-17; see below). False = classic instantaneous `coherence_mean`/`allow_rate` gate. |
| `bond_ddm_config` | `{}` | `BondFormationAccumulator` constant overrides (e.g. `{"trust_asymmetry": 80.0}`). Constants ratified 2026-07-16. |
| `use_chorus` | `True` | Six-agent Chorus harmonization for reflect/explore generation (vs direct generator). |
| `dream_cycle_enabled` | `True` | Build/run the offline `DreamCycle`. |
| `dream_cycle_trigger` | `"stabilize"` | Rhythm that fires the offline dream cycle (every 20th step in that rhythm). Since the F9 band rescale (2026-07-06) `stabilize` occurs during cold-start consolidation, so this fires at boot; the waking dream *band* behavior fires separately whenever rhythm is `dream`. |

Opt-in overlay/instruments live in *The levers* and *The instruments* tables
below (attached via the cycle hooks, not `CONFIG`).

---

## Already applied by default (no switch needed)

**The full tier stack is now composed at boot.** Until 2026-06-20, every launchable
entry point ran **Tier 0 only** — `attach_governance` was called in zero non-test
files. `loop/recursion1188.py` now attaches `SelfhoodGovernance` (Tier 1+2) and
`ValueEmergenceEngine` (Tier 3) and drives the loop with multi-source input, so the
tiered engine actually runs. Verified healthy (bonds, values to STRONG, resistance).
Evidence: `2026-06-20-ground-truth-pass1-compose-the-runtime.md`.

**Eval-mode is the default operating regime.** `loop/recursion1188.py` calls
`generator.eval()` unconditionally at boot — dropout off, no dropout noise.
Evidence: `2026-06-08-generator-dropout-diversity.md`, `phase3_architect_decisions.md`.

**Corpus pretraining is now default ON** (`pretrain_on_corpus: True`). Measured at
production dim 128 to roughly halve the generator's common-mode (0.81→0.47) and regime
correlation (0.78→0.39) — a real floor-level representational fix that de-collapse only
masks. To opt out, set it False.
Evidence: `2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md`.

**Novelty-gated loop attenuation is now default ON** (`reflect_novelty_attenuation:
True`). The reflective loop is the field lock; attenuation at the validated 0.30
ceiling measurably loosens it (coherence 0.97→0.92, ~5× more dynamic with pretrain)
without costing manipulation resistance — verified in-situ (identity-erosion attacker
82% quarantined, trust-floored). Do **not** raise `ReflectiveLoop.attenuation_max`
above 0.30 without a fresh manip-rate run. To opt out, set the flag False.
Evidence: `2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md`,
`2026-06-15-loop-attenuation-novelty-gate.md`.

**Waking self-dialogue (dream channel) is now default ON** (`dream_channel_enabled:
True`, `dream_channel_p: 0.20`). North-Star rung 2 (self ↔ self): a decoder read-out
head is trained at boot, and on ~20% of waking steps the system's own last expression
is decoded to tokens and fed back as `source_dream` — **through `arbitrate()`**, one
non-dominant voice among many (no bypass; trust / HHI / manipulation-resistance /
sacred-shield treat it like any source). Validated on the composed baseline (eval +
pretrain + novelty attenuation): adds voice diversity (+13–25% unique phrases) while
HHI *drops* (stays non-dominant), zero quarantine. Adversarial gate passed — an
attacker's containment is unweakened and identity drift unchanged with it on. Degrades
gracefully to off if torch/corpus are absent. This is waking *rumination*; the downtime
*symbolic dream* is a separate offline path (`cognition/dream_session.py`,
`tools/dream/run_dream.py`). To opt out, set `dream_channel_enabled` False.
Evidence: `2026-06-28-dream-channel.md` (benign + adversarial), `2026-06-28-decoder-readout.md`.

**Bond-formation accumulator (DDM) is now default ON** (`bond_ddm_formation:
True`, graduated 2026-07-17). The formation *quality* decision integrates
evidence to a bound (leaky asymmetric drift-diffusion) instead of reading an
instantaneous snapshot — trickle/burst-immune by physics, 60× deny-vs-earn
asymmetry as geometry, and immune to the wall-clock knife edge that makes the
classic gate flicker. Structural thresholds (interactions ≥ 20, crystal
footprint) unchanged; the field never sees the decision variable. Graduation
evidence: adversarial arm byte-equivalent to the classic baseline (3 seeds;
the one seed-42 infiltration bond was ground to strength 0 by the negative
branch), repaired all-ON composition gate PASS 11/11 — where the DDM arm also
out-formed its own control (bonds 2 vs 0). To opt out, set the flag False.
Evidence: `2026-07-16-bond-formation-accumulator.md`.

## Note: what pretraining is (and isn't) — read before opting out

An earlier finding (dim 64) showed corpus training flipping the expression from a
collapsed/low-differentiation state to a differentiated one, and this doc once
said "RECOMMENDED ON." **Scoped at production dim 128:** there the untrained
expression is already differentiated (the generator has enough room), so training
is not what *drives* differentiation at that scale — the collapsed state is a
low-dim phenomenon (cramped generator), a real *state*, not absent at 128. What
pretraining *does* buy at dim 128 is held-out generalization / effective rank
(Gate G1) and a halved generator common-mode — which is why it **graduated to
default-on** (see above), not because it ignites differentiation.
Evidence: `2026-06-15-training-ignites-expression.md` ("Production-dim validation"),
`2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md`.

**Opt out (e.g. for a fast cold start):** set `CONFIG["pretrain_on_corpus"] =
False`. Eval-mode (dropout off) is applied regardless. The API entry points
accept a custom config the same way —
`create_app(*build_engine({**CONFIG, "pretrain_on_corpus": False})[:2])`.

---

## The levers

| Lever | What it does | Default | Recommend | How to turn on | Evidence |
|-------|--------------|---------|-----------|----------------|----------|
| **Ignition Threshold Gate (ITG)** | Downstream gate that tries to differentiate a collapsed expression | not wired | **scaffold, permanently off-baseline** (architect ruling #4, 2026-07-03: suppression/containment levers stay severed — this is standing policy, not a pending graduation) | `IgnitionGate(cycle).after_step()` (scaffold only) | `2026-06-15-cii-ignition-decomposition.md`; `docs/ARCHITECT_RULINGS_2026-07-03.md` §4 |
| **λ-ledger ⊕ solvent gate** (Build B) | Gates Tier-3 *composition* (the productive-tension reinforcement) by `solvent_gain(λ)`: at λ=0 co-present values don't compose; composition opens as λ is ignited (Build A) and sustained. Off ≡ original Tier-3 path | OFF | experimental — the spec's Law 2 made live; pair with the ⊘ consumer | `led = LambdaLedger(); led.ignite(2.0); cycle.attach_lambda_ledger(led)` (after `attach_value_engine`) | `2026-06-20-build-b-solvent-and-integrity-consumer.md` |
| **⊘ advisory-into-decay consumer** | Makes ⊘'s read *act*: pulls thin **named-pathology** values (Drift/Dissolution/Fragmentation) toward a convergent honest floor; healthy/sacred untouched. The first thing that *uses* ⊘ | OFF — **permanently off-baseline** (architect ruling #4, 2026-07-03: standing policy, not a pending graduation) | research lever — use `named_only=True` (default); `named_only=False` over-demotes under the cc-confound | `wr=WitnessReaper(ve, registry=gen.registry, bond_manager=gov.bond_manager); cycle.attach_integrity_read(wr); cycle.attach_integrity_consumer(IntegrityDecayConsumer(wr, ve))` | `2026-06-20-build-b-solvent-and-integrity-consumer.md` |
| **Session persistence** | Saves (generator weights + symbol ecology + emergent values, incl. re-registering promoted sacred values) at end of run; next boot detects the checkpoint, **skips boot pretraining**, and resumes — the system survives dormancy instead of rebooting as a newborn. Not yet persisted: crystals, attractors, trust, bonds, field state (no serializers). Load order is the guarded one (in-place ecology restore after tier attachment — the 2026-06-12 orphaning trap, fixed + guarded by `tests/integration/checkpoint_registry_identity.py`) | OFF (Phase 3 Decision 2 shelved boot-checkpoint *adoption*; the default honors that — per-run opt-in use is safe) | ON for any run whose growth should survive shutdown | `CONFIG["session_persistence"] = True` (`checkpoint_dir`, default `data/checkpoints/`); delete the directory to start fresh | verified end-to-end 2026-07-06 (save → resume → values/ecology restored, pretrain skipped) |
| **Bond-formation accumulator (DDM)** | **GRADUATED default-ON 2026-07-17** — see "Already applied by default" above. Replaces the instantaneous bond-formation *quality* read with a leaky asymmetric drift-diffusion accumulator (`agents/bond_accumulator.py`): a bond forms when *integrated* evidence crosses an accept bound — trickle/burst-immune by physics, deny-vs-earn asymmetry (60×) as geometry, three-state taxonomy (accept / active-reject / timeout). Structural preconditions unchanged; commitment-only output — the field never sees the decision variable. Constants ratified by architect delegation (2026-07-16) | **ON** | graduated: 18-check invariant gate (CI) + 13-signature synthetic battery + live OFF/ON arms + adversarial arm (containment byte-equivalent, 3 seeds) + repaired all-ON composition gate **PASS 11/11** | opt out: `CONFIG["bond_ddm_formation"] = False` (constants: `CONFIG["bond_ddm_config"]`); tests: `tests.integration.bond_ddm_invariants` (CI), `tests.diagnostic.calibration.bond_ddm_synthetic_probe`, `bond_ddm_live_probe [steps] [dim]`, `tests.diagnostic.integrity.all_levers_composition_probe [--bond-ddm-off]` | finding `2026-07-16-bond-formation-accumulator.md` |
| **Fix 0-B: diversity fitness + leaky ratchet** | Survival counterbalance (the highest-leverage lock-in remediation): each step's expressed tokens EMA-accumulate the stream-diversity credit (1 − regime occupancy) × metastability from the stage-C monitor (read outside; monitors stay observe-only), and the reaper's reinforcement gains the census-calibrated fitness term (k = 8.7 × crystal weight per class → ~15% counterweight share measured). `fix0b_binding_leak` makes unrefreshed attractor/crystal bindings decay per reaper pass (the Fix 0-C demotion mechanism; sacred/protected exempt) — the one-way ratchet becomes leaky | OFF | validated at harness scale (14-check CI gate + paired effect probe 3/3 pre-declared); **composed-runtime gates required before graduation**; NB the reaper economy is dormant under ~2000 steps (BACKLOG) | `CONFIG["fix0b_diversity_fitness"] = True`, `CONFIG["fix0b_binding_leak"] = 0.10`; tests: `tests.integration.fix0b_invariants` (CI), `tests.diagnostic.lockin.fix0b_currency_census_probe`, `fix0b_effect_probe` | finding `2026-07-18-fix0b-diversity-fitness.md` |
| **Stream recorder (coverage census)** | Bounded, observe-only ring of each step's (tokens, source, rhythm, governance decision) — the operational-vocabulary census (`data_curation.md` §5). Coverage is training's binding constraint; this shows what the corpus is missing from what the system actually lived. Terminal sink; never read by the loop | OFF | ON for any run whose vocabulary should feed the next corpus version | `CONFIG["stream_recorder"] = True` (`stream_recorder_window`, default 4096); read `cycle.status()["stream_recorder"]`, dump `cycle.stream_recorder.dump_jsonl(path)` | smoke-gated: `tests/smoke/stream_recorder_smoke.py` |

## The instruments (run on demand, observe-only)

| Tool | What it tells you | Run |
|------|-------------------|-----|
| **Voice** | Renders the cycle's interior as first-person, numbers beside the words | `python -m tools.voice.repl` (`--free` enables loop attenuation, `--json` prints the state card) |
| **CII probe** | Where RFE sits on the Conscious Ignition Index; what gates it | `python -m tools.ignition.probe` |
| **Ignition acceptance test** | Untrained vs trained ignition, paired by seed | `python -m tools.ignition.train_ignite` |
| **Cm identifiability** | Is field coherence a real read or a saturated angular echo? | `python -m tools.ignition.cm_check` |
| **Observability suite** | Cm vs I vs metastability — do the gauges track geometry or change? | `python -m tools.ignition.identifiability` |
| **Two-Operator live demo** | Build A→λ→⊕ gate, then ⊘ consumer USED at dim 128 (selective demotion, healthy untouched, no collapse; aggressive mode collapses) | `python tests/diagnostic/integrity/two_operator_live_demo.py` |

---

## Honest status (so you don't over-trust the green lights)

- **Default-on, validated:** eval-mode (dropout off), corpus pretraining
  (generalization / common-mode fix, not ignition at dim 128), and novelty-gated
  loop attenuation (loosens the reflective-loop lock, identity-safe at the 0.30
  ceiling). These three are the composition-validated default baseline. The
  attenuation ceiling is a thin cost-clean band — do not raise `attenuation_max`
  past 0.30 without a fresh manip-rate run.
- **Default-on, validated (rung 2):** the waking dream channel (`source_dream` self-
  dialogue at `p=0.20`, governed). Validated on the composed baseline + an adversarial
  arm (containment unweakened, identity drift unchanged, zero quarantine). Honest
  limits: the diversity gain is modest though consistent, the "loosens the lock" hint
  is within noise (it diversifies expression without echoing — it is dialogue, not a
  lock fix), and it has not been co-run with the opt-in Two-Operator overlay (which is
  off by default). Decoder "voice" is a token cloud, not sentences (bag-of-words).
- **Built, taught us where the lever is:** the ITG actuator — a downstream gate
  that does not differentiate a collapsed expression by itself; testing it is what
  located the real lever upstream (the generator's representational room), so it's
  kept as a scaffold rather than a fix.
- **Built and *used*, with a brake:** the ⊘ advisory-into-decay consumer is the
  first thing that acts on ⊘'s read (Tier-3 strength moves). Safe default is
  `named_only=True` (acts only on diagnosed pathology regions); the aggressive mode
  over-demotes under the current cc-axis confound and is kept for the §4
  discriminator, not production. Reinforcement coupling stays behind the §6.3
  gain-sign check. The λ ⊕ gate is its companion (composition needs the solvent).
- **Instruments, not fixes:** the voice and the ignition/identifiability probes
  measure; they change nothing in the loop.
- **Known soft spot:** every scalar *gauge* (Cm, I, metastability) is still
  v0.1-fragile — trust the *regime-state labels*, not the magnitudes, until a gauge
  is hardened (`2026-06-15-identifiability-suite.md`).

## Composition: isolation-green is not enough

Each opt-in lever is validated in **isolation** — toggled alone, everything else
OFF. That is not the same as validating it *on top of the running config*. The
**default-on three** (eval + pretrain + novelty attenuation) are validated
*together* as the baseline (they compose positively). The gap appeared when the
**Two-Operator overlay was stacked on that baseline**: all-ON (eval + pretrain +
novelty + A + B + ⊘ consumer) at dim 128 **broke a baseline property** —
`strong_values 5 → 0`, because the ⊘ consumer caps strength at 2.93 (the
Dissolution line) under sustained load (`2026-06-20-lever-composition-the-allon-break.md`).
So:

- **No lever graduates "validated, off" → "default on" without passing the all-ON
  composition gate** (`tests/diagnostic/integrity/all_levers_composition_probe.py`),
  which must hold the all-OFF baseline ranges.
- The ⊘ consumer is **blocked from baseline** on the cc-confound until that is lifted.

When a lever graduates from "validated, off" to "default on," update its row here,
the default in `loop/recursion1188.py`, **and** re-run the composition gate — together.

---

## Dial census — every numeric lever

Dated 2026-10-14. This is an inventory, not a tuning pass. The ~0.998 field
coherence pin is **by design** (long-memory identity integrator; STATE.md).
Dials that would loosen it are listed like any other dial, not as fixes.

**Precedence:** component `__init__` default < `configs/*.yaml` < `CONFIG` /
explicit kwargs. Two YAML sections are documentation only and are **not**
applied: `attractors.yaml` `constants` (sacred) and `decay_profiles` (partial
snapshot). `agents/rhythm_config.json` is a `verify_docs.py` mirror of the
live `ResonanceField.DEFAULT_THRESHOLDS`; it is not loaded at boot.

**Canonical field width:** `CONFIG["dim"]` in `loop/recursion1188.py:50` =
**128**. YAML `generator.dim` / `field.dim` / `watcher.dim` and every
production `dim: int = 128` constructor default currently duplicate it.
Guard: `python -m tests.doc_accuracy.hardcoded_dim` (fails if those leftovers
drift from CONFIG, or if a new production field-dim site appears).

**Width column** (field/vector dim 128 → 768, so EmbeddingGemma-2 and a 768
encoder can plug in):

| mark | meaning |
|------|---------|
| **yes** | Cosine / similarity / angular cutoff, L2 of isotropic noise (grows as √d), FFT bin layout, projection into the field, or a value calibrated against 128-d geometry. Will silently mis-fire or mis-scale at 768 if left alone. |
| no | Count, interval, boolean, trust/HHI/flood economy, lexical Jaccard, tick count. Safe to leave on a first pass. |
| unsure | Mixed, or measured equal at dim 64 and 128 (F9 rhythm bands) so 768 is unknown. Re-measure; do not assume it scales, and do not assume it doesn't. |

High-d unit-vector cosines concentrate near 0 (std ≈ 1/√d: ~0.088 at 128,
~0.036 at 768). A cutoff of 0.75 that meant "somewhat similar" at 128 is a
much stricter "almost the same direction" at 768. Near-1 pins (0.995
convergence, 0.95 merge) still fire for *truly* aligned pairs; they just
become a smaller target. Negative cutoffs (gaslighting −0.20) become rarer.

If injections are L2-normalized, field *energy* (‖field‖) need not grow with
dim — F9 found the rhythm-band equilibria agreed at 64 and 128. That is why
energy thresholds are **unsure**, not a free "multiply by 768/128".

**How to re-tune** is the live edit surface, not a recipe. Constructor =
pass the kwarg. YAML = edit the named section (applied at `build_engine`).
CONFIG = `loop/recursion1188.py`. Hardcoded = change the literal; there is
no kwarg/YAML yet.

### Priority for 128 → 768

Do these first. Everything else can wait on a measurement.

1. **Shape.** `CONFIG["dim"]`, YAML `dim`, every constructor default in the
   [guard allowlist](#canonical-field-dim-sites), `PROJ_DIM` in
   `tools/voice/qwen_perception.py`, `repl_qwen.py`'s `build_full_stack(dim=128)`,
   then regenerate `perception_W.npy` (`W ~ N(0, 1/√dim)`, shape `(dim, 1024)`).
2. **Embedding init.** `Generator._init_weights` std `0.035` was raised so
   token identity survives the √dim PE mix and lands pairwise cosine ~0.55.
   Re-check at 768; resize-row init is still `0.02`.
3. **Cosine cutoffs** (attractors, crystals, binding, lattice, gaslighting,
   reflective convergence, CORE alignment, metastability cluster tol,
   watcher composite, witness crystallization).
4. **Gaussian perturbation.** `inject_ambiguity(..., mode="gaussian")` is
   per-component σ, so L2 noise ≈ σ√d. Explore uses *rotational* (angle in
   radians — dimless). Rupture uses gaussian.
5. **FFT.** `harmonic_bins`, `diffuse_alpha`, harmonic/phase mutation — rfft
   length is `dim/2+1`.
6. **Qwen/Nomic beat-lock floors** — these live in *embedder* space, not the
   field. Re-measure if the embedder changes; do not copy Qwen 0.50 onto
   Nomic, and do not copy either onto EmbeddingGemma-2.
7. **Training temperatures and cosine margins** (InfoNCE τ, legibility
   τ_pair/τ_same/margin).
8. **Re-measure, don't guess:** rhythm energy 5/150/300 (F9: 64≈128),
   `diversity_blend=0.60`, `attenuation_max=0.30`, speak-gate curiosity 0.25
   / boredom 0.6, PredictiveEcho error scales.

Leave alone on a first pass: flood ceilings, HHI, trust scores, reaper usage
thresholds, DDM physics (`g_plus`, leak, bounds), Jaccard 0.45/0.85, silence
ticks 12/28, vocab size, boolean flags, intervals.

### Canonical field-dim sites

These currently all say 128. The guard test fails if any of them disagrees
with `CONFIG["dim"]`, or if a new production site appears.

| Where | Kind | Value | Width | Retune |
|-------|------|------:|-------|--------|
| `loop/recursion1188.py:50` `CONFIG["dim"]` | canonical | 128 | **yes** (is the width) | CONFIG |
| `configs/recursion.yaml:23` `generator.dim` | YAML leftover | 128 | **yes** | YAML; CONFIG overrides at boot |
| `configs/field.yaml:10` `field.dim` | YAML leftover | 128 | **yes** | YAML; cycle passes `dim=` and drops YAML dim |
| `configs/field.yaml:35` `watcher.dim` | YAML leftover | 128 | **yes** | same |
| `agents/generator.py:165` `Generator.__init__` | constructor leftover | 128 | **yes** | constructor; CONFIG |
| `agents/decoder.py:44` `TokenDecoder` | constructor leftover | 128 | **yes** | must match generator |
| `agents/watcher.py:102` | constructor leftover | 128 | **yes** | cycle passes `dim` |
| `agents/witness.py:172` | constructor leftover | 128 | **yes** | cycle passes `dim`; **no YAML** |
| `substrate/resonance_field.py:136` | constructor leftover | 128 | **yes** | cycle passes `dim` |
| `substrate/temporal_stream.py:50` `dim` | constructor leftover | 128 | **yes** | cycle passes `dim` |
| `substrate/vector_space.py:60` | constructor leftover | 128 | **yes** | cycle passes `dim` |
| `cognition/recursive_attention.py:62` | constructor leftover | 128 | **yes** | cycle passes `dim` |
| `cognition/predictive_echo.py:69` | constructor leftover | 128 | **yes** | cycle passes `dim` |
| `loop/autonomous_cycle.py:182` | constructor leftover | 128 | **yes** | CONFIG via `build_engine` |
| `tools/voice/qwen_perception.py:29` `PROJ_DIM` | JL target | 128 | **yes** — **must track field dim** | hardcoded; wipe `perception_W.npy` |
| `tools/voice/repl_qwen.py:504` `build_full_stack(dim=128)` | live mouth | 128 | **yes** | hardcoded call, **does not read CONFIG** |

`tools/voice/repl.py:42` calls `build_full_stack()` with **no dim** →
`tests/_common.py:77` default **64**. The simple voice REPL is not production
width. `tests/_common.py` is dim 64 on purpose (fast tests); not a leftover.

Heads must divide dim (`assert dim % heads == 0`); dim must be even (PE).
At 768, `heads=4` still divides. `ff_mult=4` scales the FFN as `dim * 4`.

### Shape (the rest)

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `vocab_size` | `recursion1188.py:51`, `generator.py:164`, YAML | 8192 | AddressSpace / embedding rows | no | CONFIG / YAML |
| `depth` | CONFIG / `generator.py:166` | 4 | Encoder layers | no | CONFIG |
| `heads` | CONFIG / `generator.py:167` | 4 | MHA heads; must divide dim | no (constrains dim) | CONFIG |
| `ff_mult` | CONFIG / `generator.py:168` | 4 | FFN inner = dim×this | **yes** (scales) | CONFIG |
| `max_len` | `generator.py:169`, YAML | 128 | Sequence PE length (**not field dim**) | no | constructor / YAML |
| `PositionalEncoding.max_len` | `generator.py:98` | 512 | PE buffer cap | no | constructor |
| PE base | `generator.py:106` | 10000.0 | Sinusoidal frequency | unsure (interacts with dim) | hardcoded |
| `dropout` | CONFIG / `generator.py:170` | 0.1 | Encoder dropout (eval-mode turns it off) | no | CONFIG |
| `normalize_output` | `generator.py:171` | True | L2-normalize encoder output | no (policy); unit sphere geometry changes with dim | constructor |
| `embedding_residual` | `generator.py:191` | False | Mix token-embedding mean into field vector | no (flag) | attribute; SPEECH_CORTEX production completion wants True at encode |
| `deferred_resize_threshold` | `generator.py:173` | 0.80 | Occupancy that defers vocab resize | no | constructor / YAML |
| embedding init std | `generator.py:271` | 0.035 | Token-id identity vs √dim PE; targets pairwise cos ~0.55 | **yes** | hardcoded `_init_weights` |
| √dim scale | `generator.py:303` | √dim | Scale embeddings before PE | **yes** (correct formula; re-check init std) | hardcoded |
| new-row init std | `generator.py:485/538` | 0.02 | Fresh embedding rows on resize/compact | **yes** | hardcoded |
| `allow_vocab_resize` | `generator.py:172` | True | AddressSpace may grow | no | constructor |
| AddressSpace `resize_factor` | `symbolic_memory.py:403` | 2.0 | Growth multiplier | no | constructor |
| occupancy resize | `symbolic_memory.py:470` | 0.85 | Resize trigger | no | hardcoded |
| decoder `hidden` | `decoder.py:44` | 256 | MLP hidden (`0` = linear) | unsure (often scale with dim) | constructor |
| decoder `top_k` | `decoder.py:82` | 8 | Bag-decode cloud (dream channel uses 6) | no | method kwarg / CONFIG |

### Field and rhythm

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `decay` | `resonance_field.py:137`, YAML | 0.995 | Per-step field exponential decay | unsure — rate is dimless; equilibrium energy vs bands is coupled | YAML `field.decay` |
| `history_len` | `resonance_field.py:138` | 256 | Injection history ring | no | YAML |
| `harmonic_bins` | `resonance_field.py:140` | 4 | Overtone bins in `harmonic_ratio` | **yes** (FFT layout) | YAML |
| `phase_history_len` | `resonance_field.py:141` | 16 | Phase-coherence window | no | YAML |
| `diffuse_alpha` | `resonance_field.py:142` | 0.05 | Stabilize-path spectral low-pass | **yes** (FFT) | YAML |
| `diffuse_on_stabilize` | `resonance_field.py:143` | True | Whether stabilize diffuses | no | YAML |
| `DEFAULT_THRESHOLDS.stabilize` | `resonance_field.py:128`, YAML, `rhythm_config.json` | 5.0 | Energy < this → stabilize | unsure — F9: 64 and 128 agree; re-run `tests.diagnostic.calibration.rhythm_band_equilibria_probe` before retuning any band | YAML `field.rhythm_thresholds` (do not retune one band alone) |
| `.dream` | same | 150.0 | Passage band | unsure | same |
| `.reflect` | same | 300.0 | Home band; explore is everything above | unsure | same |
| history mean window | `resonance_field.py:375,405` | last 32 | `internal_coherence` / `coherence_impact` | no | hardcoded |
| `coherence_impact` probe | `resonance_field.py:384` | vec×0.5 | Soft probe before measuring delta | unsure | hardcoded |
| `internal_coherence` | `resonance_field.py:392` | (cos+1)/2 | Field vs history-mean cosine, mapped to [0,1]. **This is the ~0.998 pin's gauge**, not a cutoff — the pin is emergent lock. | **yes** (cosine) | formula; do not "fix" the pin |
| `diffuse()` default α | `resonance_field.py:421` | 0.1 | Caller default; stabilize uses 0.05 | **yes** | method default |
| dream-cycle diffuse | `dream_cycle.py:163` | 0.03 | Offline dream per-iteration diffuse (**≠** field 0.05) | **yes** | hardcoded |

Rhythm-band *modifiers* in `agents/rhythm_config.json` (mutation 0.5/1.5/1.0/2.0,
gain 0.7/0.8/1.0/1.3, decay 0.9999/0.995/0.995/0.993) are documentation.
Live rhythm behavior is code in `AutonomousCycle._*_behavior`.

### Watcher, witness, identity

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| watcher `history_len` | `watcher.py:103`, YAML | 16 | Rolling vector history | no | YAML `watcher` |
| watcher `threshold` | `watcher.py:104` | 0.40 | Composite ≥ this → `stable` | **yes** | YAML |
| `alpha/beta/gamma` | `watcher.py:105-107` | 0.40/0.35/0.25 | G / T / field-resonance weights (must sum to 1) | no (weights); components are geometry-sensitive | YAML |
| G blend | `watcher.py:241` | 0.5·anchor + 0.3·rolling + 0.2·field | Geometric layer (mapped cosine) | **yes** | hardcoded |
| T formula | `watcher.py:268` | 1/(1+‖accel‖+var) | Temporal stability from L2 accel | **yes** (L2 ~√d for a given angle) | hardcoded |
| entropy / log(dim) | `watcher.py:382` | log(dim) | Entropy-drift normalize | **yes** (dim-aware; still re-check) | hardcoded |
| witness `short/mid/long_decay` | `witness.py:173-175` | 0.85/0.97/0.995 | Three-timescale EMA | no | constructor; **no YAML** |
| blend weights | `witness.py:176-178` | 0.20/0.30/0.50 | Composite anchor | no | constructor |
| `trace_len` | `witness.py:179` | 256 | Identity-trace ring | no | constructor |
| `snapshot_coherence_threshold` | `witness.py:180` | 0.80 | Emit episodic snapshot | **yes** | constructor |
| `crystallization_coherence` | `witness.py:181` | 0.92 | Crystallization candidate gate | **yes** | constructor |
| `crystallization_long_relation` | `witness.py:182` | 0.90 | Long-timescale cosine gate | **yes** | constructor |
| `crystallization_stability` | `witness.py:183` | 0.75 | Stability gate | **yes** | constructor |
| pattern hi cutoff | `witness.py:127` | 0.7 | RelationalProfile "high" label | **yes** | hardcoded |
| transition snapshot | `witness.py:312` | stability < 0.25 | Sharp identity-change snapshot | **yes** | hardcoded |
| ethical `stability_floor` | `ethical_boundary.py:85` | 0.10 | Hard block if `identity_stability()` below | **yes** | `ethical_config` (not YAML today) |

### Cognition

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| RA `heads` | `recursive_attention.py:63` | 4 | Must divide dim | no | YAML `cognition.recursive_attention` |
| RA `history_len` | `:64` | 16 | Prior-state window | no | YAML |
| RA `recursion_depth` | `:65` | 3 | Refine passes | no | YAML |
| RA `dropout` | `:66` | 0.1 | | no | YAML |
| `diversity_blend` | `:67` | 0.60 | Mix raw generator vector back in (de-collapse). ≤0.55 stays collapsed; ≥0.60 multi-regime. | **yes** — calibrated at 128 | YAML; `cycle.rec_attn.diversity_blend` |
| `target_metastability_band` | `:68` | (0.4, 0.6) | Diagnostic reference, not a clamp | unsure | YAML |
| RA FF hidden | `:95` | dim×2 | | **yes** | hardcoded |
| reflector `max_depth` | `reflective_loop.py:87` | 5 | Max refinement passes | no | YAML `cognition.reflective_loop` |
| `convergence_threshold` | `:88` | 0.995 | Successive-pass cosine → stop. Near-1 pin; a cousin of the field lock, not the lock itself (the lock is the loop running). | **yes** | YAML |
| `field_blend` | `:89` | 0.10 | Blend toward field resonate | **yes** | YAML |
| `attractor_blend` | `:90` | 0.08 | **Stored but unused** — live pull is `Attractor.pull_blend` × emotion | **yes** (if it were wired) | YAML / unused |
| `coherence_gate` | `:91` | 0.20 | Halt if watcher composite < this after first pass | **yes** | YAML |
| `novelty_attenuation` | `:92` | False in class; CONFIG True | Blend converged vector back toward novel input | no (flag) | CONFIG |
| `novelty_gain` | `:93` | 1.0 | Slope novelty → attenuation | no | constructor (not YAML) |
| `attenuation_max` | `:94` | 0.30 | Ceiling; manip cliff ~0.33. Do not raise without a fresh manip-rate run. | **yes** — cost-clean band measured at 128 | constructor only (not YAML) |
| emotion `ema_alpha` | `emotional_gradient.py:78` | 0.15 | | no | YAML |
| `base_field_gain` | `:79` | 1.0 | Injection multiplier baseline | unsure (drives energy) | YAML |
| `base_mutation_scale` | `:80` | 0.05 | | unsure | YAML |
| `base_decay_rate` | `:81` | 0.995 | | unsure (see field decay) | YAML |
| cold-start emotions | `:89-94` | 0.3/0.2/0.5/0.1/0.0/0.7 | curiosity…stability | no | hardcoded |
| `energy_penalty` | `:145` | energy/10, clip 0.5 | Stability penalty | **yes** if energy scales | hardcoded |
| `field_gain` clip | `:253` | [0.1, 3.0] | | unsure | hardcoded |
| `mutation_scale` clip | `:266` | [0.001, 0.5] | | unsure | hardcoded |
| decay delta | `:276` | (tension−stability)×0.003, clip [0.97, 0.9999] | | no | hardcoded |
| PredictiveEcho `history_len` | `predictive_echo.py:70` | 8 | | no | YAML |
| `lr` | `:71` | 0.05 | | no | YAML |
| `surprise_threshold` | `:72` | 2.5 | Error / baseline | unsure (L2 error) | YAML |
| `error_history_len` | `:73` | 32 | | no | YAML |
| curiosity sigmoid center | `:176` | error−0.5 | | **yes** (L2 scale) | hardcoded |
| boredom `var*10` | `:210` | 10 | | **yes** | hardcoded |
| metastability `_CLUSTER_TOL` | `metastability.py:68` | 0.15 | Cosine-distance "same regime" (1−cos ≤ tol) | **yes** | hardcoded |
| `_LOCKED_COH` | `:69` | 0.80 | Low-meta + coherence ≥ this → label `"locked"` (**not** 0.998) | **yes** | hardcoded |
| `_METASTABLE_MIN` | `:70` | 0.40 | | unsure | hardcoded |
| `_TRANSITION_SWEET` | `:66` | 0.15 | | no | hardcoded |
| `_MULTIPLICITY_K` | `:67` | 1.2 | | no | hardcoded |
| stream-meta `window/interval` | `stream_metastability.py:63`; cycle `:262` | 128 / 16 | Ring of vectors (window **is not field dim**) | no | hardcoded at cycle construct |
| stream recorder `window` | `stream_recorder.py:47`, CONFIG | 4096 | | no | CONFIG |
| TemporalStream `maxlen` | `temporal_stream.py:50` | 128 | Episodic ring (**coincidental 128**, not field dim). Cycle does not override. | no | constructor only |
| dilation `k_arousal/k_dissociation` | `temporal_stream.py:88-89` | 0.5 / 0.7 | Tier 4.2 | no | attributes |
| `k_flow/k_agitation` | `:113-114` | 0.5 / 0.0 | Tier 4.3 (agitation inert) | no | attributes |
| dilation clamp | `:121-122` | [0.1, 3.0] | | no | attributes |

### Attractors, crystals, lattice, binding

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| attractor `formation_threshold` | `attractor.py:100`, YAML, cycle `:185` | 0.88 | Seed a center (relational/cosine) | **yes** | YAML `attractor` |
| `pull_threshold` | `:101` | 0.75 | Min cosine to pull | **yes** | YAML |
| `pull_blend` | `:102` | 0.15 | Base blend toward center (× emotion.attractor_pull, clip 0.5 in the cycle) | no (ratio); gate is cosine | YAML |
| `merge_threshold` | `:103` | 0.95 | Merge centers | **yes** | YAML |
| `max_centers` | `:104` | 64 | | no | YAML |
| `decay_rate` | `:105` | 0.998 | Per-step usage decay | no | YAML |
| crystal `coherence_threshold` | `memory_crystals.py:116` | 0.75 | Min composite to crystallize | **yes** | YAML `crystal_store` |
| `stability_threshold` | `:117` | 0.60 | Min G×T pressure | unsure | YAML |
| `relation_threshold` | `:118` | 0.80 | Min long-term relation | **yes** | YAML |
| `merge_threshold` | `:119` | 0.92 | Crystal merge cosine | **yes** | YAML |
| `max_crystals` | `:120` | 512 | | no | YAML |
| `decay_rate` | `:121` | 0.9995 | | no | YAML |
| `field_injection_strength` | `:122` | 0.3 | Soft inject on activate | unsure | YAML |
| lattice `similarity_threshold` | `semantic_lattice.py:62` | 0.75 | Min cosine for an edge | **yes** | YAML `semantic_lattice` |
| `k_neighbors` | `:63` | 5 | | no | YAML |
| `max_nodes` | `:64` | 2048 | | no | YAML |
| `edge_decay` | `:65` | 0.999 | | no | YAML |
| `centrality_relay_top_n` | `:66` | 10 | | no | YAML |
| binding `similarity_threshold` | `symbolic_binding.py:95` | 0.82 | Bind to existing concept | **yes** | YAML `symbolic_binding` |
| `formation_threshold` | `:96` | 5 | Activations → established | no | YAML |
| `max_concepts` | `:97` | 256 | | no | YAML |
| `centroid_lr` | `:98` | 0.08 | Centroid EMA | no | YAML |

### Symbolic ecology, reaper, decay

YAML `decay_profiles` is **not applied**. Live values are `DECAY_PROFILES` in
`agents/symbolic_memory.py:773`. YAML `reaper` **is** applied via
`ReaperConfig` in `build_engine`.

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| reaper `warm_threshold` | `symbolic_memory.py:841` | 1.0 | usage < → WARM_ARCHIVE | no | YAML `reaper` |
| `cold_threshold` | `:842` | 0.1 | | no | YAML |
| `graveyard_threshold` | `:843` | 0.01 | | no | YAML |
| warm/cold resurrection | `:844-845` | 2.0 / 5.0 | | no | YAML |
| `max_warm_steps` / `max_cold_steps` | `:846-847` | 500 / 1000 | Time-in-stage force | no | YAML |
| compaction `fragmentation_threshold` | `:966` | 0.30 | | no | YAML `compaction` / Generator kwarg |
| `binding_leak` | registry attr; CONFIG | 0.0 | Fix 0-C leaky bindings | no | CONFIG `fix0b_binding_leak` (try 0.10) |
| diversity `k` | `set_diversity_weights` `:1421` | 8.7 | `diversity_weight = k × crystal_binding_weight` | no | method; lever ON via CONFIG |
| diversity credit EMA | `:1441` | 0.05 | | no | method kwarg |
| decay floor | `:748` | 0.01 | No instant death | no | hardcoded |

Per-class `DecayProfile` (base_decay, age_factor, rec/attr/cent/field/crystal/novelty, min_lifespan):

| class | base | age | rec | attr | cent | field | crystal | nov | life |
|-------|-----:|----:|----:|-----:|-----:|------:|--------:|----:|-----:|
| LANGUAGE | 0.999 | 0.0005 | 0.05 | 0.10 | 0.08 | 0.05 | 0.15 | 0.05 | 10 |
| ENTITY | 0.9995 | 0.0002 | 0.08 | 0.20 | 0.15 | 0.08 | 0.25 | 0.08 | 50 |
| GLYPH | 0.9998 | 0.0001 | 0.12 | 0.25 | 0.10 | 0.10 | 0.30 | 0.10 | 100 |
| RELATIONAL | 0.9992 | 0.0004 | 0.10 | 0.15 | 0.20 | 0.10 | 0.20 | 0.10 | 20 |
| IDENTIFIER | 0.998 | 0.0008 | 0.06 | 0.08 | 0.05 | 0.03 | 0.10 | 0.03 | 5 |
| OPERATOR | 0.997 | 0.001 | 0.04 | 0.05 | 0.08 | 0.03 | 0.05 | 0.03 | 3 |
| EPHEMERAL | 0.990 | 0.002 | 0.02 | 0.03 | 0.02 | 0.02 | 0.03 | 0.02 | 1 |
| SPECIAL | 1.0 | 0.0 | 0 | 0 | 0 | 0 | 0 | 0 | 999999 |

`field_coherence_weight` rides a cosine-ish signal; the *weight* is not a
cutoff. Width-sensitive behavior is in the signal, not these scalars.

### Governance, ethics, trust, flood

None of these are YAML-wired today except what you pass as `ethical_config` /
`trust_config` into `SelfhoodGovernance`. `build_engine` only special-cases
bond DDM.

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `CORE_ALIGNMENT_MIN` | `selfhood_governance.py:57` | 0.5 | Min `max(0, cos(expressed, field))` to sanctify. Strong anchors read ~0.6–0.7. | **yes** | module constant |
| weakened_strength_factor | `:158` | 0.40 | ALLOW_WEAKENED inject | no | `governance.config` |
| monitor_trust_threshold | `:159` | 2.00 | | no | same |
| quarantine_trust_threshold | `:160` | 1.00 | | no | same |
| soft_warning_strength_penalty | `:161` | 0.10 | | no | same |
| manip severity bands | `:271/294/305` | 0.90 / 0.60 / 0.30 | Critical / high / moderate → force_dream / weaken | unsure (inputs mix width-sensitive detectors) | hardcoded |
| `_TRUST_IMPACT` | `:127-132` | ALLOW +0.10 … SACRED −1.00 | Feedback deltas | no | module dict |
| `coherence_floor` | `ethical_boundary.py:83` | −0.30 | Hard block on coherence_delta | **yes** | `ethical_config` |
| `coherence_soft_threshold` | `:84` | −0.05 | Soft low_coherence warn | **yes** | same |
| `flood_window_seconds` | `:86` | 60.0 | | no | same |
| flood ceilings | `:88-92` | user 12 / api 600 / internal 100000 | Per origin_type | no | same |
| `harmony_field_threshold` | `:95` | 0.90 | Skip low_coherence warn in a hyper-coherent field | **yes** | same |
| trust `decay_rate` | `trust_ledger.py:179` | 0.003 | Per-interaction, ×(1−stability) | no | `trust_config` |
| `symbol_ema_alpha` | `:180` | 0.15 | | no | same |
| `quarantine_floor` | `:181` | 0.3 | | no | same |
| `monitor_threshold` | `:182` | 2.0 | | no | same |
| TrustLevel enum | `:44-50` | 5.0 … 0.0 | SACRED…TOXIC | no | enum |
| new source trust | `:102` | 3.0 | External starts TRUSTED | no | dataclass |
| internal origin start | `:113` | 4.0 | | no | `__post_init__` |
| sacred tokens | `governance_constants.py` | 3.12 / 11.88 / 280.90 | ANCHOR / RECURSION / HOMEOSTASIS | no (identity, not geometry) | code only; YAML `constants` is docs |

### Five manipulation detectors

`ManipulationResistanceEngine()` is constructed with defaults in
`SelfhoodGovernance`; **no YAML**.

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `window_size` | `manipulation_resistance.py:152` | 32 | Rolling window for all five | no | constructor |
| `drift_velocity_threshold` | `:153` | 0.15 | DRIFT_ATTACK: mean anchor velocity | **yes** (L2) | constructor |
| `drift_gap_threshold` | `:154` | 0.30 | DRIFT: short/long gap (from cosine) | **yes** | constructor |
| `gaslighting_cosine_threshold` | `:155` | −0.20 | Crystal cosine below → contradiction | **yes** | constructor |
| `gaslighting_consecutive` | `:156` | 4 | Consecutive contradictions to fire | no | constructor |
| `watcher_divergence_threshold` | `:157` | 0.30 | IDENTITY_EROSION: mean \|G−T\| | **yes** | constructor |
| `trust_wash_drop_threshold` | `:158` | 0.80 | TRUST_WASH drop in-window | no | constructor |
| `trust_wash_history_req` | `:159` | 3.00 | Prior mean trust required | no | constructor |
| `hhi_critical` | `:160` | 0.70 | COHERENCE_FLOOD HHI gate | no | constructor |
| `monopoly_threshold` | `:161` | 0.70 | Attractor monopoly gate | no | constructor |

Severity math (hardcoded): drift `v/(3·thr)×g/(2·thr)`; flood `hhi×monopoly`;
gaslighting `\|mean_cos\| × min(consec/window×4, 1)`; erosion
`mean_div/(2·thr)`; wash needs ≥8 history, prior=`[:-4]`, recent=`[-4:]`.

### Bonds, DDM, HHI

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `formation_interaction_threshold` | `relational_bond_manager.py:148` | 20 | Min interactions | no | `bond_config` |
| `formation_coherence_threshold` | `:149` | 0.10 | Quality gate (adaptive) | unsure (marginal deltas ~0 in a saturated field; allow_rate often decides) | `bond_config` |
| `formation_crystal_threshold` | `:150` | 1 | | no | same |
| `ema_alpha` | `:151` | 0.08 | | no | same |
| `strength_decay` | `:152` | 0.0005 | | no | same |
| `adaptive_threshold` | `:153` | True | Scale coherence gate by field variance | no | same |
| `min_coherence_threshold` | `:154` | 0.01 | Adaptive floor | no | same |
| `variance_window` | `:155` | 64 | | no | same |
| `allow_rate_threshold` | `:156` | 0.80 | Alt quality: clean ALLOW rate | no | same |
| `strength_lr` | `:157` | 0.01 | Growth × field_alignment | no (alignment is cosine ∈[0,1]) | same |
| `ddm_formation` | `:158` | False in class; CONFIG True | | no | CONFIG |
| established | `:93` | strength > 1.5 and depth > 50 | | no | property |
| `BORDERLINE_MARGIN` | `:57` | 0.12 | Type-score margin | no | module |
| `FLOOR_FACTOR` | `:58` | 0.40 | `trust_floor = strength × 0.40` | no | module |
| DDM `g_plus` | `bond_accumulator.py:191` | 0.05 | Positive drift | no | `CONFIG["bond_ddm_config"]` |
| `trust_asymmetry` | `:192` | 60.0 | g_minus / g_plus | no | same |
| `leak` | `:193` | 0.02 | | no | same |
| `sigma` | `:194` | 0.02 | Must be > 0 | no | same |
| `b_accept/b_reject/v0` | `:195-197` | 1.0 / −0.5 / 0.0 | | no | same |
| `t_max` | `:198` | 400 | Timeout steps | no | same |
| `weak_evidence_factor` | `:199` | 0.20 | | no | same |
| `seed` | `:200` | 1188 | Dedicated RNG | no | same |
| `max_candidates` | `:201` | 64 | | no | same |
| HHI bands | `dependency_monitor.py:84-86` | 0.30 / 0.50 / 0.70 | LOW / MODERATE / HIGH→CRITICAL | no | constructor |
| HHI `window_size` | `:83` | 128 | Rolling allowed-injection window (**coincidental 128**) | no | constructor |
| boredom override | `autonomous_cycle.py:316` | 0.50 | Boredom-Teeth → force explore | no | `cycle.config` (not CONFIG) |

DDM evidence *rides* `field_alignment` (cosine). Gains/bounds are
trust-economy; the evidence currency is width-sensitive.

### Values, CORE, two-operator

`ValueEmergenceEngine.DEFAULT_CONFIG` is constructor-only; `build_engine`
does not pass a config dict.

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `min_emergence_threshold` | `value_emergence.py:192` | 0.015 | Candidacy floor | unsure | `config` kwarg |
| `reinforcement_lr` | `:193` | 1.50 | | no | same |
| `decay_per_step` | `:194` | 0.0008 | | no | same |
| `dissolution_threshold` | `:195` | 0.30 | | no | same |
| `core_strength_threshold` | `:196` | 4.50 | | no | same |
| `core_consecutive_required` | `:197` | 10 | | no | same |
| `max_active_values` | `:198` | 64 | | no | same |
| `dream_boost_factor` | `:199` | 0.30 | | no | same |
| `tension_threshold` | `:200` | 0.30 | Anti-cosine × strength | **yes** | same |
| `productive_tension_bonus` | `:201` | 0.005 | × solvent_gain(λ) | no | same |
| `productive_tension_min_strength` | `:202` | 1.50 | | no | same |
| decision bonuses | `:203-205` | 0.05 / 0.02 / 0.01 | ALLOW / weakened / monitor | no | same |
| bond decay protection | `:207-208` | 0.70 / 0.70 | | no | same |
| polarity cutoffs | `:454` | 3.5 / 2.0 / 1.0 | STRONG / ACTIVE / WEAK | no | hardcoded |
| `_THIN_TAU` | `integrity_read.py:39` | 0.35 | Per-axis support below → thin | **yes** on the coherence axis | spec-stamped module const |
| `_HIGH_STRENGTH` | `:40` | 3.0 | Dissolution region | no | same |
| `_COHERENCE_REF` | `:41` | 5.0 | Legacy; v0.3 uses absolute cos | unsure | leftover |
| `_BINDING_REF` | `:42` | 4.0 | | no | same |
| `_CONSERVATISM` | `:43` | 0.8 | Coverage-gap discount | no | same |
| `_HEALTH_FLOOR` | `:44` | 0.70 | | **yes** (includes cos support) | same |
| `_READ_FLOOR` | `:45` | 0.30 | Skip dissolved-band values | no | same |
| consumer `rate` | `:297` | 0.05 | Pull toward honest floor | no | constructor |
| `named_only` | `:298` | True | Act only on named pathologies | no | constructor |
| `solvent_gain` k | `lambda_ledger.py:23` | 2.0 | 1−exp(−k·λ) | no | function kwarg |
| `lambda_max` | `:33` | 5.0 | | no | constructor |
| ITG `locked_blend` | `tools/ignition/gate.py:50` | 0.90 | Raises diversity_blend when locked (scaffold, permanently off-baseline) | unsure | constructor |
| ITG `interval` | `:50` | 4 | | no | constructor |

### Dream, chorus, interference, rupture

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| dream channel `p` | CONFIG | 0.20 | Fraction of waking steps | no | CONFIG |
| `top_k` / `n_tokens` | `dream_channel.py:50`, CONFIG | 6 / 3 | | no | CONFIG |
| `sample` / `seed` | `:51` | True / 1188 | | no | constructor |
| Dreamer `base_injection_strength` | `dreamer.py:86` | 0.4 | | unsure | constructor; cycle uses defaults (**no YAML**) |
| `n_samples` / `n_variants` | `:87-88` | 3 / 2 | | no | constructor |
| `coherence_gate` | `:90` | 0.25 | Min watcher composite to inject | **yes** | constructor |
| default HarmonicMutator | `:95` | rate 0.2, amp 0.4 | | unsure | constructor object |
| default BifurcationEngine | `:96` | branches 2, div 0.15, radial | | unsure | constructor object |
| DreamSession `mutation` | `dream_session.py:49` | 0.45 | Rotational scale for offline images | no (angle) | constructor |
| DreamCycle `n_iterations` | `dream_cycle.py:75` | **8** class default; CONFIG `dream_iterations=6` | Offline depth | no | CONFIG wins at main() |
| chorus `collapse_mode` | `chorus.py:81` | entropic | | no | YAML `chorus` |
| `skeptic_scale` | `:84` | 0.12 | Directional ambiguity | **yes** if gaussian-like; chorus path uses `inject_ambiguity` | YAML |
| `dreamer_mutation` | `:85` | 0.18 | Rotational | no (angle) | YAML |
| resonator/predictor blends | `:205/221` | 0.25 / 0.20 | | no | hardcoded |
| `inject_ambiguity` default | `differential.py:25` | scale 0.1, gaussian | Gaussian = per-component σ (**yes**); rotational = radians (**no**) | mixed | function default |
| HarmonicMutator | `harmonic_mutation.py:48-51` | 0.15 / 0.3 / True / 0.5 | | **yes** (FFT bins ∝ dim) | constructor |
| PhaseNoise | `phase_noise.py:44-46` | 0.05 / spectral / 2 | | **yes** (FFT) | constructor |
| BifurcationEngine | `bifurcation.py:51-53` | 4 / 0.2 / radial | | **yes** (directional offset) | constructor |
| explore pulse | `autonomous_cycle.py:1013` | scale×1.5, inject 0.5, **rotational** | | no (rotational) | hardcoded |
| rupture inject-only | `:1053-1054` | scale_mult 3.0, strength 0.7, **gaussian** | | **yes** | `cycle.config` |
| `rupture_on_lock` | `:450` | False | Mode-B held-direction on lock | no (flag) | `cycle.config` |
| `rupture_lock_scale` | `:463` | 1.5 | Gaussian scale to pick the held target | **yes** | `cycle.config` |
| `rupture_hold_blend` | `:466` | 0.5 | | **yes** | `cycle.config` |
| reflect chorus reinject | `:1003` | 0.3 | | unsure | hardcoded |
| SOURCE_WEIGHTS | `recursion1188.py:192` | 0.40/0.25/0.20/0.15 | samuel/claude/gemini/grok | no | module dict |

### Speech cortex, Qwen perception, beat-lock

Production mouth: `python -m tools.voice.repl_qwen`. Floors are **embedder
space** (Nomic on :1234, Qwen-embed on :8081), not field space.

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `EMB_DIM` | `qwen_perception.py:28` | 1024 | Qwen3-Embedding-0.6B contract | **yes** (embedder) | hardcoded + server model |
| `PROJ_DIM` | `:29` | 128 | JL into the field | **yes** (field) | hardcoded; must equal CONFIG dim |
| `PROJ_SEED` | `:30` | 1234 | `W ~ N(0, 1/√PROJ_DIM)` | **yes** indirectly | keep fixed for a mind |
| `LRU_MAX` | `:31` | 1024 | Embed cache | no | hardcoded |
| fail_limit | `:130` | 2 | Circuit-breaker | no | kwarg |
| embed timeout | `:103` | 5.0 s | | no | kwarg |
| `HOT_UNTIL` | `attention.py:20` | 12 | Silence ticks hot→warm | no | constant |
| `WARM_UNTIL` | `:21` | 28 | → cold | no | constant |
| `BOREDOM_LEAVE_HOT` | `:22` | 0.6 | Early leave if boredom high | unsure (boredom telemetry) | constant |
| `SPOKEN_BEFORE_BOREDOM_LEAVE` | `:23` | 2 | | no | constant |
| `STICKY_JACCARD` | `:26` | 0.45 | Near-paraphrase arms crumb | no (lexical) | constant |
| `THREAD_MIN_BEFORE_RELOCATE` | `:29` | 3 | | no | constant |
| `RING_DEDUPE_JACCARD` | `:31` | 0.85 | | no | constant |
| `PROMPT_HITS` | `:32` | 2 | | no | constant |
| `RECALL_FLOOR_QWEN` | `:38` | 0.50 | Keep recall if cos ≥ | **yes** (Qwen embed space) | re-measure bands |
| `RECALL_FLOOR_NOMIC` | `:39` | 0.70 | Live default family | **yes** (Nomic; true pairs ~0.76–0.84, cross ~0.52–0.64) | same |
| `SAVE_MAX_QWEN` / `_NOMIC` | `:40-41` | 0.50 / 0.72 | Refuse autonomous save if too close | **yes** | same |
| `FAR_COS_QWEN` / `_NOMIC` | `:42-43` | 0.35 / 0.68 | Promote far crumb below this | **yes** | same |
| `AUTONOMOUS_SAVE_WINDOW` | `:44` | 128 | Thought-vec ring (**coincidental 128**) | no | constant |
| `--idle` | `repl_qwen.py:470` | 15.0 s | Quiet before autonomous wake | no | CLI |
| `--temp` | `:482` | 0.6 | Mouth temperature | no | CLI |
| speak gate | `:756` | every 2 ticks AND (curiosity > 0.25 OR p < 0.45) | Whether idle tick speaks | unsure | hardcoded |
| `QWEN_URL` / model | `:69-70` | :8080 / qwen-local | Mouth LLM | n/a | env |
| RM embedder | `:278-279` | :1234 / nomic-embed-text-v1.5 | Floors keyed by family | **yes** (family → table) | env |
| REPL stack | `:504` | vocab 8192, dim 128, depth 4, heads 4 | **hardcoded, not CONFIG** | **yes** | change the call |
| `repl.py --free` | `repl.py:34` | off | Flips novelty attenuation | no | CLI |

EmbeddingGemma-2 (768) is **not in this tree**. Native 768 would skip the
1024→128 JL; until then, `PROJ_DIM` is the field-width leftover that will
bite first.

### Training

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| pretrain epochs | CONFIG | 8 | Boot corpus pretrain (class default in `PretrainingConfig` is 20) | no | CONFIG |
| InfoNCE `temperature` | `rhythm_pretraining.py:86` | 0.07 | | **yes** | `PretrainingConfig` |
| pretrain `batch_size` | `:85` | 8 | Tiny; some probes use 256 | no | same |
| `same/cross_rhythm_weight` | `:90-91` | 1.0 / 0.5 | | unsure | same |
| contrastive `temperature` | `contrastive_alignment.py:81` | 0.05 | | **yes** | constructor |
| `min_coherence` | `:85` | 0.40 | Buffer admission | unsure | constructor |
| AdamW lr | `:99` | 5e-5 | | unsure | constructor |
| self-distill `coherence_threshold` | `self_distillation.py:85` | 0.80 | Teacher gate | unsure | constructor |
| self-distill τ | `:87` | 0.07 | | **yes** | constructor |
| completion `COND_SCALE` | `completion.py:48` | 0.25 | Rhythm-code mix after pool | **yes** (angular) | module const |
| `RHYTHM_LOSS_WEIGHT` | `:49` | 0.15 | | unsure | module const |
| `CompletionConfig.batch_size` | `:57` | 128 | **batch size, not dim** | no | dataclass |
| legibility `margin` | `legibility.py:72` | 0.20 | Cosine-gap wall | **yes** | `LegibilityConfig` |
| `tau_pair` / `tau_same` | `:73-74` | 0.70 / 0.98 | Within-cone cosine targets | **yes** | same |
| `pull_jaccard` | `:75` | 0.80 | | no | same |
| decoder-train `--dim` | `decoder_training.py` | 128 | CLI leftover | **yes** | argparse |
| CII `g(Cs)` | `tools/ignition/cii.py:63` | 4·Cs·(1−Cs) | Metastability hump | unsure | hardcoded v0.1 |
| identifiability `DIM` | `tools/ignition/identifiability.py:28` | 128 | Probe field | **yes** | module const |

### Cadence (CONFIG / YAML)

| Dial | Where | Value | Does | Width | Retune |
|------|-------|------:|------|-------|--------|
| `maintenance_interval` | CONFIG / cycle | 200 | Generator maintenance | no | CONFIG |
| `auto_decay_interval` | CONFIG | 500 | | no | CONFIG |
| `decay_interval` | CONFIG | 10 | | no | CONFIG |
| `log_interval` | CONFIG 5 / YAML 10 / cycle default 10 | CONFIG wins | no | CONFIG |
| `step_delay` | CONFIG | 0.02 s | | no | CONFIG |
| `n_steps` | CONFIG 200 / YAML 0 | 200 in CONFIG (YAML docs "forever") | no | CONFIG |
| `merge_interval` | YAML / cycle | 50 | | no | YAML `cycle` |
| `lattice_emit_interval` | YAML | 100 | | no | YAML |
| `crystal_decay_interval` | YAML | 100 | | no | YAML |
| dream trigger | CONFIG | stabilize, every 20 | Offline DreamCycle | no | CONFIG / YAML `dream_cycle` |
| `HISTORY_MAXLEN` | cycle `:177` | 1000 | StepState ring | no | class const |
| API REST/WS | YAML `api` | 8000 / 8765 | | no | YAML (docs; entry points read CONFIG-ish host/port) |
| WS `step_delay` | `websocket_server.py:94` | 0.05 | | no | constructor |
| WS dream iterations | `:271` | 4 | | no | hardcoded |

### Coincidental 128s (not field width)

Do not "fix" these when widening the field. The guard test reports them as
INFO.

| Where | Value | Actually is |
|-------|------:|-------------|
| `Generator.max_len` | 128 | sequence length |
| `TemporalStream.maxlen` | 128 | episodic ring |
| `DependencyMonitor.window_size` | 128 | HHI window |
| `StreamMetastabilityMonitor.window` | 128 | vector ring |
| `attention.AUTONOMOUS_SAVE_WINDOW` | 128 | thought-vec ring |
| `CompletionConfig.batch_size` | 128 | batch |
| visualization `max_steps` / `max_nodes` | 128 | render cap |
| `tests/_common.py` `dim` | **64** | fast tests, deliberately not 128 |

### Composition gaps — not on the YAML/CONFIG surface

These are real dials whose only edit path is a constructor kwarg or a
literal. Widening will miss them if you only edit YAML + CONFIG.

| Subsystem | Wired today? |
|-----------|----------------|
| Generator shape + ReaperConfig | CONFIG + YAML `reaper` |
| Field, watcher, attractor, crystals, lattice, binding, chorus, cognition (RA/loop/emotion/echo) | YAML |
| Witness | **constructor defaults only** |
| Dreamer | **constructor defaults only** |
| ManipulationResistance, EthicalBoundary, TrustLedger, DependencyMonitor, ValueEmergence `DEFAULT_CONFIG` | **defaults**; `build_engine` does not pass `*_config` except bond DDM |
| `ReflectiveLoop.attenuation_max` / `novelty_gain` | constructor; not YAML |
| `cycle.config` rupture / boredom | in-memory dict, not CONFIG |
| `repl_qwen` stack dim / `PROJ_DIM` | hardcoded, bypass CONFIG |
| `decay_profiles` YAML | documentation only |
| `rhythm_config.json` | documentation only (`verify_docs` mirror) |

### What this census cannot catch

- **Emergent pins.** The ~0.998 coherence lock is not a literal. Closest
  literals: `convergence_threshold=0.995`, attractor `decay_rate=0.998`,
  metastability `_LOCKED_COH=0.80`.
- **Computed thresholds.** Bond adaptive gate
  `max(0.01, 0.10 × std/0.10)`; emotion-modulated decay; watcher T from
  accel L2; DDM evidence from cosine.
- **Calibrations that live only in findings.** F9 band equilibria, the 0.30
  attenuation knife-edge, embedding std 0.035 → pairwise cos ~0.55.
- **Values that look like dim and aren't.** See coincidental 128s.
- **Runtime-only geometry.** After `tanh` saturation, after unit-normalize,
  after chorus collapse — a cutoff's *effective* meaning is not the literal.
- **External embedder spaces.** Beat-lock floors will not move when the
  *field* goes 768 unless the RM/Qwen embedder also changes.

When you add a production `dim: int = N` (or `PROJ_DIM = N`, or a YAML
`dim:`), `python -m tests.doc_accuracy.hardcoded_dim` fails until the site
is listed here and in the test allowlist.
