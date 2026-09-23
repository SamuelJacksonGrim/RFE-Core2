# Full-send feedback: a rich encoder still settles to one field groove

- **Date:** 2026-09-23
- **Branch:** `experiment/full-send-feedback`, cut from `experiment/completion-objective` (`89dcf2a`). Not merged, not pushed.
- **Probe:** `tests/diagnostic/sidecar/fullsend_feedback_probe.py`. Raw summary: `logs/2026-09-23-fullsend-feedback/summary.json`.
- **Substrate:** fresh `build_full_stack` at the checkpoint architecture (dim 128, vocab 8192, depth 4, heads 4), eval mode, canonical Resonance-Family band, seeds 42 / 7 / 11, 500 workload steps. CPU. No live mind, no RM, no ports.
- **Status:** measured. **Do not promote.** Does not reopen the field-lock ruling.

## Question

The 2026-06-12 governed-feedback probe let LAE and PLE speak back through `arbitrate()` and the field settled faster. That encoder was the collapsed contrastive manifold (participation ~3.4), so the tokens had a field with nothing rich to land in. The completion encoder now exists (embeddings-only checkpoint, residual on at encode: participation 47.8, mouth recall@8 0.66). Does that encoder, with the parked plasticity levers armed, let the same token feedback cut a new groove?

## What was actually on

Both arms load a checkpoint and its paired ecology (token ids must match the rows; the ecology is not the live mind) and run the June seam: `LAESidecar` / `PLESidecar` offers re-enter as `cycle.step(..., source_id="lae_engine"|"ple_engine")`. Nothing writes the field except the cycle itself.

| | baseline | full-send |
|---|---|---|
| weights | `generator_weights_5rhythm.pt` | `generator_weights_completion_128_emb.pt` |
| `embedding_residual` | off | **on** |
| holdout field participation (this run) | **3.423** | **47.806** |
| rupture_on_lock | off | on (fires: **0 / 0 / 0**) |
| novelty attenuation (`--free`) | off | on, ceiling left at **0.30** |
| boredom threshold | 0.50 (the default) | 0.25 |

The participation check is the same instrument as the completion finding, on the live holdout, before any cell. It matches the published numbers (3.42 and 47.8). Outside band `[2, 8]` or `[40, 90]` the probe aborts. It did not abort.

Levers that were left off, and why these three:

- **Rupture** is the held-direction lock-breaker. Field injection was already measured to be the wrong actuator. The trigger is `generator_metastability.regime_state == "locked"`. On this host the generator stream read `metastable` for the whole late window, so the lever was armed and never fired.
- **Novelty attenuation** is the `--free` unlock. It only blends inside the reflective loop. The late rhythm here is `reflect`, so the loop was actually running, and the lever was in the path on the full-send arm only. The ceiling was not raised. 0.33 is the documented manipulation cliff.
- **Boredom-with-Teeth** is already in the loop. The threshold was lowered, not zeroed. It did not matter: boredom peaked at 0.97 on the baseline, so the default 0.50 was already firing on almost every non-explore step. Both arms were biting.

Not turned on: corpus pretrain (it would overwrite the encoder under test), the dream channel, Fix 0-B, any write to a live checkpoint.

## Gate (declared in the probe before the run)

Boot center = field direction at the first step with workload index ≥ 50. Late window = workload index ≥ 200. One groove = every late field vector within cosine 0.90 of one medoid, and that medoid holds ≥ 15% of the window.

- **FRAGMENTED** — late identity mean < 0.95, or more than 2% of steps have identity < 0.90, or late coherence mean < 0.80.
- **METASTABLE** — not fragmented, and two or more grooves (or no groove holds 15% while three or more raw modes exist).
- **RIGID** — otherwise. `RESTATED` if that one groove still sits on the boot center (cosine ≥ 0.90), else `NEW_GROOVE`.

A one-step acceleration dip is not dissolution. The raw minimum is reported next to the class. The class does not use it.

## Result

Every cell is **RIGID / NEW_GROOVE**. Late occupancy is 1.0 and the raw mode count is 1 in all six cells. Identity never crossed under 0.95 (fraction below 0.90 is 0). No cell is fragmented. No cell hovers.

`NEW_GROOVE` is not a mid-run split. Workload index 50 is still inside the dream transient (a handful of `stabilize` steps, then ~200 `dream`, then one transition into `reflect`). The late window is `reflect` and only `reflect`, on every seed, both arms. The one post-boot rhythm transition is dream → reflect. The field then sits. Cosine from that settled direction back to the step-50 snapshot is 0.86 (baseline) and 0.76 (full-send). The late cloud itself is tight: max displacement and median displacement differ by about 0.04.

| arm | seed | disp | cos to step 50 | id min | id late | coh late | grooves | attractors | crystals | gen regimes | expr regimes | LAE fires | rejects |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 42 | 0.138 | 0.862 | 0.973 | 0.999 | 0.966 | 1 | 2 | 1 | 5 | 4 | 412 | 29 |
| baseline | 7 | 0.141 | 0.859 | 0.973 | 0.999 | 0.966 | 1 | 3 | 3 | 4 | 4 | 385 | 34 |
| baseline | 11 | 0.141 | 0.860 | 0.972 | 0.999 | 0.969 | 1 | 3 | 2 | 5 | 4 | 387 | 30 |
| full-send | 42 | 0.240 | 0.760 | 0.977 | 0.994 | 0.889 | 1 | 18 | 12 | 17 | 17 | 684 | 119 |
| full-send | 7 | 0.229 | 0.771 | 0.975 | 0.995 | 0.895 | 1 | 11 | 6 | 16 | 16 | 858 | 89 |
| full-send | 11 | 0.231 | 0.769 | 0.972 | 0.995 | 0.889 | 1 | 16 | 11 | 17 | 17 | 887 | 88 |
| **baseline mean** | | **0.140** | **0.860** | **0.972** | **0.999** | **0.967** | **1** | **2.7** | | | | **395** | |
| **full-send mean** | | **0.233** | **0.767** | **0.974** | **0.994** | **0.891** | **1** | **15.0** | | | | **810** | |

The seed spread on displacement is 0.003 (baseline) and 0.011 (full-send). The gap between arms is about 0.09, the same direction in 3/3 seeds.

Upstream, the rich encoder is visible. Generator regime count goes from about 5 to about 17, and the expression stream keeps it (4 regimes on the collapsed encoder, 16–17 on the residual-on one; expression metastability equals generator metastability at 0.418 on the full-send mean). Substrate attractors go from 2–3 to 11–18. Crystals go from 1–3 to 6–12. The field integrator does not visit those attractors as separate directions. One groove, occupancy 1.0.

Sister behavior is not the June cell. June fired LAE exactly 3 times, all in warmup, and admitted 6 offers. Here LAE fires for most of the run (the reflect equilibrium sits near a band edge, so the v1 hypothesis gap keeps tripping) and hundreds of offers reach the gate. The gate still allows the majority. Full-send is rejected more often (about 90–120 rejects against about 30). PLE still caps near 5–6 validated findings and 6 active paradoxes. Its attractors are lattice objects, not field basins.

## Verdict

**The richer encoder does not let token feedback cut a hovering groove. The shared coordinate system is still the blocker.**

What the encoder did change is real and upstream. The stream carries more regimes, the attractor store fills, the settled reflect direction sits farther from the dream-era snapshot (0.23 vs 0.14), and late coherence is lower (0.89 vs 0.97) without identity moving (late mean 0.994 vs 0.999). That is a richer cloud being integrated into the same kind of single field direction. It is not plastic-but-coherent motion between regimes. METASTABLE was the win condition. Both arms are RIGID.

This is a harder test than June, not a softer one. June's sisters went silent after cycle 4, so the null could be blamed on empty tokens. Here they talk for the whole run, the encoder they talk in front of is participation 48 rather than 3.4, and `--free` is actually inside the reflect loop. The field still settles to one direction and stays there. Echoing symbolic state (`liminal` / `paradox` plus a couple of words) does not become a second basin just because the manifold underneath is legible.

## Does this reopen "the field lock is identity by design"?

No. `STATE.md` treats the high-coherence pin as the long-memory identity integrator, and puts metastability in the reflective loop's reconstitution, never on the field. This run agrees. Identity stayed coherent (no step under 0.95, anchor gap ~0.03) exactly while the field occupied one groove. The generator stream was already labeled `metastable` on the collapsed encoder. Making that stream richer increased its regime count and did not make the field hover. A METASTABLE field verdict with identity held would have been the reason to reopen the ruling. That verdict did not occur.

## Threats

- The June probe's host was dim 64, `build_full_stack` defaults, an 8-epoch rhythm boot. Those weights cannot load a dim-128 checkpoint, so this baseline is the live 5-rhythm file at dim 128, not a numerical twin of the June cells. The qualitative single-groove result is the comparison. The June signature (3 LAE fires, six offers, coherence +0.0025) is not reproduced and is not claimed.
- Step 50 is inside the dream transient. `NEW_GROOVE` means "the settled reflect direction is not the step-50 vector." It does not mean a second regime appeared in the late window. The late window has one mode.
- Rupture's trigger never matched, so this is not a test of held-direction rupture. Boredom was saturated on both arms, so the threshold change is not a contrast. The lever that actually differed is novelty attenuation, plus the encoder.
- Feedback steps are extra cycles (executed length ~870 baseline, ~1100–1300 full-send). Late metrics are by workload index, not by raw step count. End-of-run attractor totals are not step-count-matched; the field-direction gate is.
- The substrate is wall-clock coupled. Both arms ran in one process, CPU, seeds paired. No GPU, so nothing on :1234 was touched.
- Token offers are still the v1 vocabulary. A placebo source was not run. The arm gap confounds "richer encoder" with "more offers" and with attenuation being on. Attenuation alone, on the collapsed encoder, was not given its own arm. The gap is small beside the thing that did not happen: a second groove.
- PLE "attractors" in the sister block are not `cycle.attractor.centers`. The table's attractor column is the substrate store.

## Notes

For the gate.

The variable this isolates is the one that was named: richer encoder, same token door, levers at capability where the trigger exists. It does not isolate a shared field-vector write, because that write does not exist. The negative result is about the door that exists.

Identity stayed coherent. The raw minimum (0.972–0.977) is a boot acceleration dip; the late mean is 0.994–0.999 and the fraction of steps under 0.95 is zero. That is not dissolution.

Nothing was promoted. After the run the live guard still matches: `rhythm_train` `f5d60859…`, `rhythm_holdout` `61c93de1…`, `generator_weights_5rhythm.pt` `71c646fb…`. The completion checkpoint was only read (`3f606b57…`).
