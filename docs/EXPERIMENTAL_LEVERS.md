# Experimental Levers — the control panel

Validated work is useless if you can't find the switch. This is the **one page**
that lists every experimental capability built on top of the shipped tiers, what
it does, whether it's recommended, and the **exact** way to turn it on. If you
remember nothing else, read the first row.

All of these are **off / opt-in by default** — the live system's default behavior
is unchanged until you flip something here. Nothing in this file is load-bearing
for the base stack.

---

## Already applied by default (no switch needed)

**Eval-mode is now the default operating regime.** Per the Phase 3 architect
decision (2026-12), `loop/recursion1188.py` calls `generator.eval()`
unconditionally at boot — dropout off — so a default run is no longer riding
dropout noise. This was *decided* months ago but had been reachable only via the
pretraining flag; it is now wired into the default path.
Evidence: `2026-06-08-generator-dropout-diversity.md`, `phase3_architect_decisions.md`.

## Note: training is a *generalization* lever, not the differentiation driver at production dim

An earlier finding (dim 64) showed corpus training flipping the expression from a
collapsed/low-differentiation state to a differentiated one, and this doc once
said "RECOMMENDED ON." **Scoped at production dim 128:** there the untrained
expression is already differentiated (the generator has enough room), so training
is not what *drives* differentiation at that scale — the collapsed state is a
low-dim phenomenon (cramped generator), a real *state*, not absent at 128.
Training still buys held-out generalization / effective rank (Gate G1), so corpus
pretraining is **useful, optional** rather than required.
Evidence: `2026-06-15-training-ignites-expression.md` ("Production-dim validation").

**Turn it on (optional):** in `loop/recursion1188.py` `CONFIG`,
`"pretrain_on_corpus": True`. It trains on `data/corpus/` at boot. (Eval-mode is
already applied regardless.)

---

## The levers

| Lever | What it does | Default | Recommend | How to turn on | Evidence |
|-------|--------------|---------|-----------|----------------|----------|
| **Corpus pretraining** | Trains the generator on `data/corpus/` at boot (generalization / eff_rank) | OFF | optional — NOT required for ignition at dim 128 | `CONFIG["pretrain_on_corpus"]=True` in `loop/recursion1188.py` | `2026-06-15-training-ignites-expression.md` |
| **Novelty-gated loop attenuation** | Loosens the reflective loop's reconvergence when genuinely-new input survives → lets the field migrate | OFF | leave OFF (cost-clean band is a knife edge) | `CONFIG["reflect_novelty_attenuation"]=True`; ceiling is `ReflectiveLoop.attenuation_max` (0.30, do not raise without a fresh manip-rate run) | `2026-06-15-loop-attenuation-novelty-gate.md` |
| **Ignition Threshold Gate (ITG)** | Downstream gate that tries to differentiate a collapsed expression | not wired | **scaffold** — testing it located the lever upstream (the generator), so a downstream gate isn't the fix | `IgnitionGate(cycle).after_step()` (scaffold only) | `2026-06-15-cii-ignition-decomposition.md` |
| **λ-ledger ⊕ solvent gate** (Build B) | Gates Tier-3 *composition* (the productive-tension reinforcement) by `solvent_gain(λ)`: at λ=0 co-present values don't compose; composition opens as λ is ignited (Build A) and sustained. Off ≡ original Tier-3 path | OFF | experimental — the spec's Law 2 made live; pair with the ⊘ consumer | `led = LambdaLedger(); led.ignite(2.0); cycle.attach_lambda_ledger(led)` (after `attach_value_engine`) | `2026-06-20-build-b-solvent-and-integrity-consumer.md` |
| **⊘ advisory-into-decay consumer** | Makes ⊘'s read *act*: pulls thin **named-pathology** values (Drift/Dissolution/Fragmentation) toward a convergent honest floor; healthy/sacred untouched. The first thing that *uses* ⊘ | OFF | experimental — use `named_only=True` (default); `named_only=False` over-demotes under the cc-confound | `wr=WitnessReaper(ve, registry=gen.registry, bond_manager=gov.bond_manager); cycle.attach_integrity_read(wr); cycle.attach_integrity_consumer(IntegrityDecayConsumer(wr, ve))` | `2026-06-20-build-b-solvent-and-integrity-consumer.md` |

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

- **Applied and real:** eval-mode default (dropout off, no switch needed). Corpus
  pretraining is wired and works, but optional (generalization, not ignition at dim 128).
- **Validated but deliberately off:** novelty-gated loop attenuation — works,
  identity-safe at the default ceiling, but a thin cost-clean band; flip only to
  experiment.
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

Each lever above is validated in **isolation** — toggled alone, everything else OFF.
That is not the same as validating the **all-ON** configuration, and the gap is real:
turning every behaviour-bearing lever on together (eval + pretrain + novelty
attenuation + A + B + ⊘ consumer) at dim 128 **broke a baseline property** —
`strong_values 5 → 0`, because the ⊘ consumer caps strength at 2.93 (the Dissolution
line) under a sustained workload (`2026-06-20-lever-composition-the-allon-break.md`).
So:

- **No lever graduates "validated, off" → "default on" without passing the all-ON
  composition gate** (`tests/diagnostic/integrity/all_levers_composition_probe.py`),
  which must hold the all-OFF baseline ranges.
- The ⊘ consumer is **blocked from baseline** on the cc-confound until that is lifted.

When a lever graduates from "validated, off" to "default on," update its row here,
the default in `loop/recursion1188.py`, **and** re-run the composition gate — together.
