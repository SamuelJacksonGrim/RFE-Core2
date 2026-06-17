# Experimental Levers — the control panel

Validated work is useless if you can't find the switch. This is the **one page**
that lists every experimental capability built on top of the shipped tiers, what
it does, whether it's recommended, and the **exact** way to turn it on. If you
remember nothing else, read the first row.

All of these are **off / opt-in by default** — the live system's default behavior
is unchanged until you flip something here. Nothing in this file is load-bearing
for the base stack.

---

## ⭐ If you do ONE thing: train the generator at boot

This is the biggest win of the lock-in work. An untrained generator emits
low-rank output and the expression reads **locked**; trained on the in-repo
corpus, the expression reads **metastable** ("ignited") across every seed.

**Turn it on:** in `loop/recursion1188.py`, set in `CONFIG`:

```python
"pretrain_on_corpus": True,     # was False
"pretrain_epochs":    8,        # 8 is enough
```

Then run `python -m loop.recursion1188` as usual — it trains on `data/corpus/`
at boot, switches to eval mode, and runs ignited.
Evidence: `docs/findings/2026-06-15-training-ignites-expression.md`.
Caveat: the *regime-state flip* (locked→metastable) is the robust result; the CII
*magnitude* leans on a metastability scalar that is still v0.1-fragile.

---

## The levers

| Lever | What it does | Default | Recommend | How to turn on | Evidence |
|-------|--------------|---------|-----------|----------------|----------|
| **Corpus pretraining** | Trains the generator on `data/corpus/` at boot → expression ignites | OFF | **ON** | `CONFIG["pretrain_on_corpus"]=True` in `loop/recursion1188.py` | `2026-06-15-training-ignites-expression.md` |
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

- **Applied and real:** corpus pretraining (flip the flag and it's active at boot).
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
