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

## ⚠️ Correction: training is NOT the "ignition lever" at production dim

An earlier finding (dim 64) showed corpus training flipping the expression
locked→metastable, and this doc previously said "RECOMMENDED ON." **Retracted at
production dim 128:** there the untrained expression is *already* metastable —
the "lock" is a low-dim/low-rank artifact, not present at 128. Training still
buys held-out generalization / effective rank (Gate G1), so corpus pretraining is
**useful but optional**, not a fix for a broken default.
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
| **Ignition Threshold Gate (ITG)** | Tries to lift a locked expression from downstream | not wired | **NOT recommended — inert** (lever is the generator, not a gate) | `IgnitionGate(cycle).after_step()` (scaffold only) | `2026-06-15-cii-ignition-decomposition.md` |

## The instruments (run on demand, observe-only)

| Tool | What it tells you | Run |
|------|-------------------|-----|
| **Voice** | Renders the cycle's interior as first-person, numbers beside the words | `python -m tools.voice.repl` (`--free` enables loop attenuation, `--json` prints the state card) |
| **CII probe** | Where RFE sits on the Conscious Ignition Index; what gates it | `python -m tools.ignition.probe` |
| **Ignition acceptance test** | Untrained vs trained ignition, paired by seed | `python -m tools.ignition.train_ignite` |
| **Cm identifiability** | Is field coherence a real read or a saturated angular echo? | `python -m tools.ignition.cm_check` |
| **Observability suite** | Cm vs I vs metastability — do the gauges track geometry or change? | `python -m tools.ignition.identifiability` |

---

## Honest status (so you don't over-trust the green lights)

- **Applied and real:** eval-mode default (dropout off, no switch needed). Corpus
  pretraining is wired and works, but optional (generalization, not ignition at dim 128).
- **Validated but deliberately off:** novelty-gated loop attenuation — works,
  identity-safe at the default ceiling, but a thin cost-clean band; flip only to
  experiment.
- **Built but inert:** the ITG actuator — kept as a scaffold; the real lever is
  the generator (training), not a downstream gate.
- **Instruments, not fixes:** the voice and the ignition/identifiability probes
  measure; they change nothing in the loop.
- **Known soft spot:** every scalar *gauge* (Cm, I, metastability) is still
  v0.1-fragile — trust the *regime-state labels*, not the magnitudes, until a gauge
  is hardened (`2026-06-15-identifiability-suite.md`).

When a lever graduates from "validated, off" to "default on," update its row here
**and** the default in `loop/recursion1188.py` together.
