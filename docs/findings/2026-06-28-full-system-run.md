# Full-system run — what is the composed engine actually doing, pre-merge?

- **Date:** 2026-06-28
- **Substrate:** live (Generator-warmed, dim 128, corpus v1.1.0, CPU); full Tier 0–3 stack via `build_engine()`
- **Probe:** `tests/diagnostic/full_system_run.py` + `full_system_analyze.py`; raw data + plots + detailed report in `docs/findings/logs/2026-06-28-full-system-run/` (see `report.md`)
- **Status:** active
- **Depends on:** ground-truth-pass3-stack-evaluation, floor-calibration-measurements, ground-truth-pass2-floor-fix-and-unlock-chain, api-entrypoints-tier0-only

## Question

Before merging PR #58 (architecture refresh + API Tier-0 fix + live YAML config),
what is the whole composed system actually doing? Capture it deeply and paired
(default levers vs levers-off) so the differences are attributable and the data is a
reusable tuning baseline.

## Pre-declared signatures

- Levers working: `levers_on` loosens coherence off ~0.97 AND keeps stage-C
  metastability multi-regime; `levers_off` pinned and/or collapsed at stage C.
- F9: rhythm ≈ all `explore`, dreams ≈ 0, in **both** arms (structural).
- F8: 0 CORE promotions in every run.
- Confound: arms indistinguishable, or `levers_on` collapsing, or a crash on the new
  config path.

## Result (observed)

3 seeds × 2 arms × 1000 steps, multi-source, means ± stdev:

| Metric | levers_off | levers_on |
|--------|-----------|-----------|
| Coherence | 0.971 ± 0.001 | 0.921 ± 0.002 |
| Metastability stage C (expression) | **0.060 ± 0.066** | **0.579 ± 0.020** |
| Metastability stage A (generator) | 0.427 ± 0.163 | 0.569 ± 0.021 |
| Field energy | 263 | 288 |
| Explore frac / Dream frac | 0.996 / 0.001 | 0.996 / 0.001 |
| Values total / strong / CORE | 33 / 22–26 / **0** | 33 / 20–22 / **0** |
| Bonds candidate / **established** | 1–2 / **0** | 2–3 / **0** |
| HHI / decisions | 0.29 / all-allow | 0.29 / all-allow |

No crash on the new YAML config path; both arms ran the full tier stack.

## Interpretation

- **Levers validated, multi-seed:** they lift stage-C metastability 0.06 → 0.58 and
  loosen coherence 0.97 → 0.92, with more attractors/crystals — graduating them to
  default-on was correct. The collapse is **between stages A and C**, and corpus
  pretraining (not `diversity_blend`, which is on in both arms) is what keeps A≈C at
  production scale; the two fixes are complementary.
- **F9 confirmed structural** (rhythm pinned `explore`, energy ~55× over band ceiling,
  dream cycle dead) and **lever-independent** — the top tuning target.
- **F8 confirmed:** 0 CORE across all 6 runs.
- **New:** bonds form but never *establish* — per-source `coherence_mean` runs slightly
  negative (~−0.01), below the 0.10 establishment gate, despite 140–421 interactions.
- Governance clean under benign load (no adversary present — resistance untested here).

## Threats / confounds

- Runs: once (3 seeds × 2 arms). Benign load only — says nothing about resistance
  (all-allow is expected for clean internal traffic; F3 bonded-adversarial probe still
  open). Decision histogram is the last ≤512 of 1000 (audit cap). Gauge magnitudes are
  v0.1-fragile — trust the levers_on−off **gap**, not absolutes. CPU, dim 128.

## Open / next

Tuning queue (by leverage): (1) F9 rhythm/energy rescale co-tuned with
`diffuse_on_stabilize` — re-run this harness as the before/after gate; (2) F8 CORE
promotion behind the sacred-vs-CORE distinction; (3) bond-establishment gate vs the
near-zero per-source coherence axis; (4) re-run with an adversarial arm to exercise
resistance. Full detail + plots: `docs/findings/logs/2026-06-28-full-system-run/`.
