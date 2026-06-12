# Phase 2 — pretrained boot on the live stack: identity-safe, and the lock is NOT the generator

- **Date:** 2026-06-12
- **Substrate:** full live stack (Tier 0–3 + temporal tiers), canonical
  Resonance-Family 500-step workload, seed 42, `origin_type="internal"`.
- **Probe:** `tests/diagnostic/training/corpus_boot_phase2_probe.py`. Raw output:
  `docs/training/logs/2026-06-12-phase2-raw-runs.log`.
- **Corpus:** `data/corpus/` **v1.1.0** (operational-vocabulary extension —
  see provenance below). Gate G1 re-passed on v1.1.0 before this probe
  (holdout eff_rank 1.45→3.41, rhythm-NN 0.980, determinism 1.0).
- **Status:** active
- **Depends on:** 2026-06-11-corpus-g1-pretrain.md (Phase 1),
  2026-06-07-reconstruction-ablation.md (the reflective-loop lock this
  re-localizes), 2026-06-09-fix2-live-generator.md (the deprioritization this
  reverses).

## Corpus correction first (v1.1.0 — part of the method)

Before Phase 2 could run honestly, a census found the v1.0.x corpus covered
only 50 of the **113 operational tokens** (Resonance Family streams,
DEFAULT_RHYTHM_SEEDS, bootstrap WORDS, recursion1188 DEFAULT_TOKENS) — 63
missing, including `governance`, `sacred`, `recursion`, `crystal`,
`attractor`, `watcher`. That violates data_curation.md §2.1's explicit
coverage requirement; Phase 2 would have booted a generator untrained on most
of its live workload. The extension (+534 train / +91 holdout, deterministic
seed 1188, build script committed: `data/corpus/build_extension_v1_1_0.py`)
anchors the operational sequences under their natural rhythms and pads every
missing token to ≥12 contexts. Rhythm assignments are hand-curated in the
build script — **architect review invited; amend the table and re-run.**

## Pre-declared Gate G2 (training_plan.md + probe header, before the first run)

On RUN B (pretrained boot, current live policy): all 9 tier1 baseline ranges
hold; identity_stability ≥ 0.95; anchor_velocity ≤ 0.02; bonds ≥ 1 and
crystals ≥ 1; manipulation steps ≤ max(3× control, 10).
Pre-declared readouts (not gated): coherence pin on/off (GENERATOR-IS-THE-LOCK
vs SECOND-LOCKER, now on real weights), phase_coherence floor, stage-A/C
metastability (pipeline survival), all of eval-mode RUN C.

## Result (observed)

Three identical-workload runs (same seed → same source/token order):

| | A control (untrained, train) | B pretrained (train) | C pretrained (eval) |
|---|---:|---:|---:|
| tier1 ranges | 9/9 | **9/9** | 9/9 |
| identity_stability | 0.9990 | **0.9974** | 0.9986 |
| anchor_velocity | 0.0010 | 0.0026 | 0.0014 |
| coherence mean (2nd half) | 0.9767 | **0.9701** | 0.9710 |
| bonds / crystals / attractors | 1 / 2 / 3 | 1 / 2 / 3 | **2** / 2 / 3 |
| strong values | 2 | **5** | 5 |
| manip steps | 0 | 0 | 0 |
| stage A metastability (regimes) | 0.356 structureless (13) | **0.536 metastable (5)** | 0.536 metastable (5) |
| stage C metastability (regimes) | 0.712 metastable (4) | **0.536 metastable (5)** | 0.536 metastable (5) |
| phase_coherence mean | 0.966 | 0.971 | 0.948 |

**GATE G2 PASSED** — all five conditions.

## Interpretation

1. **Boot-time pretraining is identity-safe.** Governance, trust, bonds,
   values, and the witness anchor behave inside baseline shapes with trained
   weights, in both dropout modes. The representational-drift risk Phase 2
   existed to measure did not materialize at this training dose.
2. **SECOND-LOCKER, on real weights.** The field coherence pin barely moves
   (0.977 → 0.970) with a generator that demonstrably presents structured,
   separable input. The 2026-06-09 deprioritization of Fix 2 ("wait until the
   generator is trained") has now been satisfied and the pin persists —
   **the reflective loop / field moat is the operative lock again, and the
   Fix-2 governor's premise is finally testable on real signal.** This is the
   Phase 5 trigger condition arriving early.
3. **The pipeline now preserves upstream structure.** Control: stage A
   structureless (13 noise regimes) gets *re-shaped* by the expression path
   into 4 regimes. Pretrained: stage A is genuinely metastable (5 regimes)
   and stage C carries it through **unchanged** — refinement stops fighting
   the input when the input has real structure. Eval-mode C matches: the
   structure is learned, not dropout.
4. **Eval mode is live-viable** (Phase 3 data, not a decision): RUN C holds
   all baselines, identity stable, and formed a *second* bond — no evidence
   that dropout-off harms the stack at boot.
5. **Tier 4.3's chaotic regime remains unreached** (phase_coherence ≥ ~0.95
   throughout; the 0.5 floor is the step-0 default) — a trained generator on
   the *canonical* workload is still phase-consistent. The high-novelty
   workload item stays open.

## Threats / confounds

- One seed (42), one training dose (8 epochs), 500 steps, the 16-sequence
  canonical workload. The coherence-pin readout in particular should be
  re-read under a broader-token workload before SECOND-LOCKER is treated as
  settled — repetition itself sustains the pin.
- Stage A/C metastability identical to 4 decimal places in B/C suggests the
  monitors may be reading near-identical streams once refinement preserves
  input; not a bug signal by itself (de-collapse blend keeps raw weight 0.6),
  but worth a glance before leaning on the exact number.
- Corpus v1.1.0 rhythm assignments were made by an AI instance, not the
  architect; G1/G2 are insensitive to modest relabeling but the words shape
  identity — review invited.

## Open / next

1. **Phase 3 (architect, blocking):** `.eval()` decision — RUN C says viable;
   boot-checkpoint adoption (G1+G2-passing recipe is `corpus v1.1.0, 8
   epochs, seed 0/42`); online-training go/no-go.
2. **Fix 2 re-prioritized** (Phase 5 hook): re-run the migration/ablation
   probes with the pretrained boot; test the `gnov` governor on real signal.
3. High-novelty workload probe (unchanged, still open).
4. Phase 4 online training remains gated behind Phase 3 decisions.
