# Full-system run — report (2026-06-28)

Deep instrumented snapshot of the composed engine on the PR #58 branch, captured
**before merge** to (a) validate the about-to-merge config wiring end-to-end and
(b) produce a tuning baseline. Paired design, 3 seeds/arm, 1000 steps, multi-source
input. Raw data: `run_*.jsonl` (per-step), `status_*.json` (every 25 steps),
`governance_*.json`, `summary.json`, `aggregate.json`, `plots/`.

## Control & method

- **Control arm `levers_off`** — graduated levers OFF (`pretrain_on_corpus=False`,
  `reflect_novelty_attenuation=False`); dim 128, eval-mode on. The pre-graduation
  baseline.
- **Test arm `levers_on`** — default `CONFIG` (both levers on).
- Everything else identical: same seeds (7, 11, 42), same weighted multi-source
  round-robin (`source_samuel/claude/gemini/grok`), `origin_type="internal"`,
  built via `build_engine()` (so the new YAML config path is exercised).
- Substrate: **live** (Generator-warmed), CPU, torch 2.12. Both arms run the full
  Tier 0–3 stack.

## Pre-declared signatures

Framed from prior findings (not blind — this is a characterization run):
- **Levers working** would look like: `levers_on` loosens field coherence off the
  ~0.97 ceiling AND keeps stage-C (expression) metastability multi-regime; `levers_off`
  sits pinned and/or collapses stage C.
- **F9 (rhythm pin)** would look like: rhythm ≈ all `explore`, dreams ≈ 0, in **both**
  arms (structural, not lever-related).
- **F8 (CORE dead)** would look like: 0 CORE promotions in every run.
- **Surprise / confound** would look like: arms indistinguishable, or `levers_on`
  collapsing, or a crash on the new config path.

## Result (observed) — means ± stdev across 3 seeds

| Metric | `levers_off` (control) | `levers_on` (default) |
|--------|------------------------|------------------------|
| Coherence C | **0.971 ± 0.001** | **0.921 ± 0.002** |
| Field energy ‖f‖ | 263.4 ± 0.5 | 288.0 ± 4.5 |
| Metastability — stage A (generator) | 0.427 ± 0.163 | 0.569 ± 0.021 |
| Metastability — stage C (expression) | **0.060 ± 0.066** | **0.579 ± 0.020** |
| Dilation factor | 0.961 ± 0.002 | 0.929 ± 0.007 |
| Explore fraction | 0.9957 ± 0.0005 | 0.9957 ± 0.0005 |
| Dream fraction | 0.001 ± 0.0 | 0.001 ± 0.0 |
| Crystals (final) | 2 | 2–4 |
| Attractors (final) | 0–1 | 2–3 |
| Values total / strong / **CORE** | 33 / 22–26 / **0** | 33 / 20–22 / **0** |
| Bonds (candidate / **established**) | 1–2 / **0** | 2–3 / **0** |
| HHI | ~0.29 | ~0.29 |
| Governance decisions (last 512) | 512 allow | 512 allow |
| Boot / step wall | ~0.04s / ~55s | ~90–112s / ~65–71s |

Plots: `plots/metastability_AvsC.png`, `coherence_trajectory.png`,
`field_energy_trajectory.png`, `rhythm_distribution.png`, `dilation_trajectory.png`,
`arousal_trajectory.png`, `valence_trajectory.png`.

## Interpretation

1. **The default-on levers are strongly validated, multi-seed.** They take stage-C
   (expression) metastability from **0.06 (collapsed, one seed literally 0.0) to 0.58
   (multi-regime)** and loosen field coherence 0.97 → 0.92, with richer durable
   structure forming (attractors 0–1 → 2–3, crystals up to 4). Tight stdev (≤0.02 on
   the expression metric) ⇒ robust, not seed-luck. This is the clearest evidence yet
   that graduating them to default-on was correct.

2. **The collapse is between stages A and C, and pretraining is what prevents it.**
   In the control, the generator stream carries some diversity (stage A ≈ 0.43) but
   the expression collapses (stage C ≈ 0.06) — the untrained-attention mean-pool
   collapse the `diversity_blend` is meant to guard. `diversity_blend` is 0.60 in
   *both* arms, so the blend alone does **not** save stage C at production scale;
   corpus pretraining (halved generator common-mode) is what keeps A≈C (0.57 ≈ 0.58).
   The blend and the floor-level representational fix are complementary, not
   redundant.

3. **F9 (rhythm pin) is confirmed structural and lever-independent.** Both arms sit
   at `explore` 99.6% with field energy ~263–288 against a band ceiling of 5 — ~55×
   over. Dreams fire once (the cold-start step) out of 1000. The dream cycle is
   effectively dead at dim 128 regardless of the levers. This is the highest-value
   tuning target and needs the co-tuned band/`diffuse_on_stabilize` fix, not a
   constant tweak.

4. **F8 (CORE dead) is confirmed: 0 CORE promotions across all 6 runs.** 33 values
   emerge and 20–26 reach the strong band, but none promote — the
   `coherence_contribution ≥ 5.0` gate is structurally unreachable (the reverted
   alignment-gate fix, pending the sacred-vs-CORE governance call).

5. **New observation — bonds form but never *establish*.** 1–3 transactional bond
   candidates appear per run with high interaction counts (140–421) and crystals,
   but **0 establish** in any run: the per-source `coherence_mean` runs slightly
   **negative** (~−0.01 to −0.03), below the `coherence_mean ≥ 0.10` establishment
   threshold. So the relational tier registers partners but the establishment gate is
   never satisfied in this regime. Candidate tuning target (companion to the F7
   coherence-axis story — per-source coherence is being read on an axis that sits
   near zero here).

6. **Governance is clean and healthy** under benign multi-source load: HHI ~0.29
   (LOW), all-allow decisions, trust ~4.1, no quarantines. (No adversary was present
   in this run — resistance is *not* exercised here; see Threats.)

7. **Affective time is live and sane.** Dilation sits at 0.93–0.96 (mild
   compression — moderate arousal, positive valence ⇒ slight flow-direction
   time-tightening), `levers_on` a touch lower (more dynamic field). Terminal sink,
   as designed.

## Threats / confounds

- **Runs:** 3 seeds × 2 arms × 1000 steps, once. Tight cross-seed stdev on the
  headline metrics; the high-variance one is control stage-A metastability
  (0.43 ± 0.16) — the collapsed arm is unstable upstream too.
- **Benign load only.** No adversarial/bonded-hostile input — this run says nothing
  about resistance (the F3 bonded-adversarial probe is still the open test). All-allow
  is expected for clean internal traffic, not evidence of weak defense.
- **Decision histogram is the last ≤512 of 1000** (audit log cap), so warm-up
  `allow_weakened` decisions aged out — it reads steady-state, not the full run.
- **CPU, dim 128, corpus v1.1.0.** Stage-C absolute metastability is generator-init
  dependent; trust the **levers_on − levers_off gap**, not the absolute magnitudes
  (per the identifiability finding, gauges are v0.1-fragile — labels over magnitudes).
- **Metastability monitors recompute every 16 steps** (lazy); early-run zeros are
  warm-up, not signal.

## Open / next (tuning queue, by leverage)

1. **F9 — rhythm/energy rescale (highest).** Co-tune the bands with
   `diffuse_on_stabilize` (now a real knob: `ResonanceField.diffuse_alpha` /
   `diffuse_on_stabilize`) so typical energy lands in `reflect`/`dream`, not pinned
   `explore`. Re-run this harness as the before/after gate.
2. **F8 — CORE promotion** via the absolute field-alignment axis, behind the
   sacred-vs-CORE `SACRED_SHIELD` distinction.
3. **Bond establishment gate** — investigate why per-source `coherence_mean` is
   ~negative; either the gate (0.10) or the axis it reads needs rescoping.
4. Re-run with an **adversarial arm** to exercise resistance (turns all-allow into a
   real test) — closes the gap this benign run leaves.

## Reproduce

```
python -m tests.diagnostic.full_system_run \
    --steps 1000 --seeds 42,7,11 --arms levers_on,levers_off \
    --status-every 25 --out docs/findings/logs/2026-06-28-full-system-run
python -m tests.diagnostic.full_system_analyze \
    --out docs/findings/logs/2026-06-28-full-system-run
```
