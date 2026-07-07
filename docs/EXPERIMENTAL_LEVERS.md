# Experimental Levers — the control panel

Validated work is useless if you can't find the switch. This is the **one page**
that lists every experimental capability built on top of the shipped tiers, what
it does, whether it's recommended, and the **exact** way to turn it on. If you
remember nothing else, read *The toggle switches* table below.

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

The behavior-bearing flags in `CONFIG` (operational shape params — `dim`,
`vocab_size`, `depth`, `heads`, `ff_mult`, `dropout`, intervals, `step_delay`,
`n_steps` — are omitted; they tune size/cadence, not behavior):

| Switch (`CONFIG[...]`) | Default | Effect |
|------------------------|---------|--------|
| `pretrain_on_corpus` | **True** | Corpus pretrain at boot (graduated lever; see below). False = fast cold start. |
| `pretrain_epochs` | `8` | Epochs when pretraining. |
| `reflect_novelty_attenuation` | **True** | Novelty-gated loop loosening (graduated lever; ceiling `ReflectiveLoop.attenuation_max=0.30`). |
| `dream_channel_enabled` | **True** | Waking self-dialogue (graduated lever; see below). The system's own decoded expression re-enters as `source_dream` through `arbitrate()`. False = no self-dialogue. |
| `dream_channel_p` | `0.20` | Fraction of waking steps fed as `source_dream` (the validated weight). |
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
