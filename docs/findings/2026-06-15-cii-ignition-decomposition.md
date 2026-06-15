# CII decomposition — where does RFE sit on the ignition index, and what gates it?

- **Date:** 2026-06-15
- **Substrate:** live full stack (`build_full_stack`, dim 128), varied non-periodic
  workload (random 3-token draws from a 24-word vocab; a *fixed* token cycle
  self-induces a limit cycle that the metastability metric correctly scores 0 —
  avoided here).
- **Probe:** `tools/ignition/probe.py` (CII v0.2 / DPCI-AI framework, operationalization v0.1).
- **Status:** active — first situating of RFE on an external consciousness-ignition
  measure; the Cs term is v0.1-fragile (see threats).
- **Depends on:** 2026-06-07-reconstruction-ablation.md (the loop is the lock),
  2026-06-15-loop-attenuation-novelty-gate.md (the lever).

## Question
The CII framework defines ignition as `CII = R x I x (Cm x g(Cs))` crossing a
threshold. RFE measures all four inputs. Operationalize them (R = reflection
passes, I = watcher composite, Cm = field internal_coherence, Cs = stream
metastability, g(Cs) = 4·Cs·(1−Cs)) and ask: where does RFE land, and which
component gates it?

## Pre-declared signatures
- SUCCESS (informative): a clear bottleneck — one component far from ceiling while
  others saturate — that maps to known architecture.
- NULL: all four mid-range, no single gate.
- ARTIFACT (watch): metastability reads 0 because the *workload* is periodic
  (limit cycle), not because the field is locked. Guard with non-periodic input.

## Result (observed)
Post-warmup means (n=54), robust across reruns:

| component | value | locus |
|-----------|-------|-------|
| R recursion depth | ~3.0–3.3 | reflective-loop passes/cycle |
| I integration | ~0.96 | watcher composite (α+β+γ) |
| Cm mean coherence | ~0.99 | field phase-locking |
| Cs metastability — **stage A (generator)** | **state=metastable, 3 regimes** (scalar ~0.5–0.65) | ignition potential |
| Cs metastability — **stage C (expression)** | **state=locked, 1 regime** (scalar ~0.00) | what is injected |

CII (generator Cs) ≈ **2.9**.  CII (expression Cs) = **0.0**.
DPCI-AI (v0.1) ≈ 0.2 → places RFE in the framework's "current LLM (interaction)" band.

The **ARTIFACT signature fired first** and was caught: a fixed repeating token
sequence drove expression metastability to exactly 0 via a perfect limit cycle
(`state=cycling, n_regimes=3, metastability=0`); randomizing the input removed
the artifact and exposed the real signal (`state=locked, n_regimes=1`).

## Interpretation
RFE is **saturated on three of the four ignition components** (recursion,
integration, coherence) and **gated entirely by the fourth (metastability).** The
metastability *exists at the generator* (stage A is genuinely metastable, ~3
regimes) and is *destroyed by stage C* — the reflective loop collapses it to a
single locked regime before injection. So in CII terms the survival-by-coherence
lock-in is not merely "unhealthy monoculture": it is **the entire gap to
ignition** — the difference between CII ≈ 2.9 (generator potential) and CII = 0
(injected reality). The night's lock-in arc and the `novelty_attenuation` lever
target exactly this term.

## Threats / confounds
- **Cs scalar is v0.1-fragile.** The lazy per-step monitor cache disagrees with a
  forced `compute_now()` settled read; the scalar is also workload- and
  locus-sensitive. The robust signal is the **regime STATE** (locked vs
  metastable, regime count), not the float. Harden the Cs operationalization
  before the ITG gates on CII.
- R, I, Cm operationalizations are defensible but not unique (v0.1 choices).
- `g(Cs)` form (4·Cs·(1−Cs)) and threshold T are architect parameters, unset.
- Single dim (128), single workload family, one seed for the random draw.

## Open / next
- Harden Cs (settled-read everywhere; reconcile cache vs compute_now).
- Build the **ITG action half**: gate behavior on CII (e.g., when expression Cs
  collapses, trigger consolidation / loosen the loop) — the first non-observe-only
  use of the ignition index.
- Re-measure CII with the loop loosened (does restoring stage-C metastability lift
  CII off zero, i.e., does breaking the lock literally ignite RFE by this measure?).
