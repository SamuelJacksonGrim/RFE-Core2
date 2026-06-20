# Ground-truth pass 2: the generator common-mode is a real floor defect — and a false lock; the actual unlock chain (and first graduations)

- **Date:** 2026-06-20
- **Spec:** n/a (runtime ground-truth, measured at production config; forward fixes)
- **Status:** active — pass 2, building forward on the composed foundation
  (`2026-06-20-ground-truth-pass1-compose-the-runtime.md`). All numbers from
  RUNNING the production config (dim 128, depth 4), not from the prior ledger.
- **Mandate:** Samuel — verify against the running system, fix the floor forward,
  do not trust findings that may have measured a system the runtime never assembled.

## What was verified real
- **Foundation sound at production config.** Composed runtime (Tiers 0–3), 500 steps:
  allow_rate 0.986, 2–3 bonds, HHI 0.29 (LOW), 33 values with **13 reaching STRONG**.
  (The all-levers probe's `strong→0` was the ⊘ consumer, not the foundation.)
- **Baked bug-fixes real in code:** `AttractorCenter` is `@dataclass(eq=False)`
  (merge fix); `load_ecology` remaps weights in-place (registry-identity fix).
- **Generator common-mode is a real floor defect.** Untrained at dim 128: 8 distinct
  semantic regimes sit at pairwise cosine **+0.78**, with **81% of each regime's
  energy on a single shared axis**. de-collapse (verified live) gives *expression*
  metastability but does **not** remove this representational crowding.

## What was FALSE (corrected by running it)
The audit's headline causal claim — "the generator common-mode is the upstream lock"
— is **false**. Corpus pretraining roughly **halves** the common-mode (0.81→0.47) and
regime correlation (0.78→0.39), yet the composed field does **not** de-saturate:
coherence stays 0.97, rhythm 100% `explore`, field drift unchanged. Fixing the
generator's representation does not unlock the field. Two *other* findings had the
real story: the **reflective loop is the lock** (reconstruction-ablation) and the
**field coherence metric is saturated** (Cm reads ~0.9 even for orthogonal input).
The generator is upstream of representation, not of the lock.

## The real unlock chain (measured, 4-way)
| config | coherence | coh σ | field drift |
|---|---|---|---|
| foundation | 0.971 | 0.0032 | 0.93 |
| + pretrain | 0.970 | 0.0046 | 0.91 |
| + novelty attenuation | 0.938 | 0.0133 (4×) | 1.02 |
| + pretrain + attenuation | **0.924** | **0.0176 (5.5×)** | **1.18** |

- Pretrain alone: no effect on the lock (confirms the generator isn't the locker).
- **Novelty attenuation genuinely loosens the field** — coherence down, variability
  4×, drift up. The reflective loop is the lock; attenuation loosens it; it works.
- **They compose positively.** Pretrain *amplifies* attenuation (σ 4×→5.5×): better
  regime separation → the novelty trigger (`gnov = 1−|cos|`, ~0.78→~0.61 headroom)
  fires more → more loosening. The first constructive lever interaction found (vs the
  ⊘ consumer, which composed destructively).
- Honest caveat: rhythm stays `explore` — that is an *energy* band, not coherence;
  the field loosens without changing energy regime. Partial, real, not dramatic.

## Resistance held (the one documented risk, verified in-situ)
With pretrain + attenuation ON, composed dim-128 runtime: 400 clean multi-source
steps ran at 0.98 allow; then a single attacker hammering an identity-erosion pattern
(`identity dissolve erase`) was **quarantined 66/80 (82%)** and trust-floored to 0.1.
Novelty attenuation at the 0.30 ceiling does not compromise the immune system here.

## Forward fixes shipped (first graduations — validated → default ON)
In `loop/recursion1188.py` CONFIG:
- `pretrain_on_corpus: True` — fixes the generator floor defect (common-mode halved),
  amplifies the unlock, no health/resistance cost.
- `reflect_novelty_attenuation: True` — loosens the field lock at the verified-safe
  0.30 ceiling, resistance intact.

Booted end-to-end: the real entry point now trains, composes Tiers 0–3, and runs
with attenuation live — step-60 coherence 0.90 (vs 0.96+ bare substrate). The
loosening is real in the default loop, not just a probe.

## Open / next (forward)
- The **field coherence metric saturation** (Cm ~0.9 floor) is now the live floor
  issue: it makes the field read "coherent" regardless, blunting every coherence-gated
  consumer. This is the next floor-level thing to confront (and it is what makes the
  ⊘ cc-axis read ~0 — they are the same saturation).
- The operators (A/B/⊘ + consumer) still come last, against this now-looser field.
- Re-run the all-levers composition gate with the graduated baseline as the new floor.
