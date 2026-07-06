# Corpus pretraining Gate G1 — does coverage buy generalization?

- **Date:** 2026-06-11
- **Substrate:** live generator (isolated; canonical config vocab 4096 /
  dim 64 / depth 3 / heads 4). No field/governance attached.
- **Probe:** `tests/diagnostic/training/corpus_pretrain_g1_probe.py`; corpus integrity
  enforced by `tests/diagnostic/training/corpus_integrity_check.py`.
- **Corpus:** `data/corpus/` **v1.0.1** (2336 train / 410 holdout, 272 tokens,
  rhythm-stratified ~15% holdout).
- **Status:** active
- **Depends on:** 2026-06-11-trainer-gradient-path.md (TRAINS + NARROW — the
  coverage constraint this tests), 2026-06-08-generator-dropout-diversity.md
  (eval-mode measurement discipline, the untrained collinear baseline).

## Question

The gradient-path finding ended NARROW: training restructured only the 20
sequences it saw; the disjoint battery was byte-identical. The curation plan
(`docs/training/data_curation.md`) claimed the fix is **coverage** — train on
the operational vocabulary with context variation per token, and structure
should generalize to held-out *sequences* (not held-out tokens). Phase 1 of
`docs/training/training_plan.md` pre-declared Gate G1 to test exactly that.

## Corpus provenance (the data is part of the method)

Corpus v1.0.0 was generated externally (Claude in-app, per the §3 spec) and
validated in-repo before any training run. Validation found and removed:
19 exact-duplicate sequences in train, 1 in holdout, and **4 sequences present
verbatim in both splits** — train→holdout leakage that would have inflated
this very gate. Cleaned corpus = v1.0.1; all 10 integrity checks pass
(schema, counts, no dups, no leakage, label coherence, vocab closure,
contexts/token ≥ 8 [min observed 15], stratification, sacred-token absence).

## Pre-declared signatures (training_plan.md, written 2026-06-11 before the corpus existed)

PASS requires ALL, on the holdout split, eval mode: eff_rank ≥ 2× untrained
baseline; rhythm-NN accuracy ≥ 0.75 (chance 0.25); determinism = 1.0;
embedding norms bounded. FAIL = within-vocabulary generalization doesn't
happen → revisit corpus design before touching anything else.

## Result (observed)

RhythmPretrainer, 8 epochs on the 2336-sequence train split (~2.5 min CPU),
all metrics on the 410 held-out sequences, eval mode:

| seed | | mean cos | eff_rank | rhythm-NN acc | determinism | norm growth |
|---|---|---:|---:|---:|---:|---:|
| 0   | before | 0.826 | 1.45 | 0.439 | 1.0000 | — |
| 0   | after  | **0.330** | **3.46** (2.4×) | **0.995** | 1.0000 | 1.2× |
| 137 | before | 0.881 | 1.28 | 0.444 | 1.0000 | — |
| 137 | after  | **0.335** | **3.55** (2.8×) | **0.990** | 1.0000 | 1.2× |

Loss 2.06 → 0.74 / 0.70. **GATE G1 PASSED, both seeds, all four conditions.**
Boot checkpoint saved via `Generator.save_checkpoint`
(`data/checkpoints/boot_rhythm_corpus_v1.0.1_8ep_s0.*`, not committed).

Note the untrained rhythm-NN baseline is ~0.44, not 0.25 chance — holdout
sequences share rhythm-specific *tokens* with train, so even collinear
untrained embeddings carry some lexical signal. The gate margin (0.99 vs
0.75) dwarfs that head start, and eff_rank/mean-cos have no such shortcut.

## Interpretation

**Coverage was the binding constraint, as pre-declared — and it is now paid.**
8 epochs on a 2.3K-sequence corpus moves *held-out* sequences from the
collinear lock substrate (eff_rank ~1.4, cos ~0.85) to structured geometry
(eff_rank ~3.5, cos ~0.33, near-perfect rhythm clustering), with both controls
clean (determinism 1.0 — no dropout contamination; norm growth 1.2× — no
runaway). The 2026-06-11 NARROW caveat is resolved for within-vocabulary
generalization: training restructures what the corpus covers, and the corpus
now covers the operational neighborhood. **Phase 1 of the training plan is
complete.** The generator can present real, separable, deterministic structure
to the field — the precondition the ROADMAP set for un-deferring Fix 2 and
specifying Tier 5.

## Threats / confounds

- Holdout is held-out at the *sequence* level by design; it shares vocabulary
  with train (vocab closure is a gate condition, not a leak). This finding
  says nothing about tokens never seen in training — those keep untrained
  geometry (2026-06-11 disjoint battery), which is why corpus version must be
  named whenever these numbers are cited.
- The rhythm-NN task is lexically separable for most pairs (235/272 tokens are
  rhythm-pure); the holdout is honest but not adversarial. eff_rank and
  mean-cos are the load-bearing diversity reads; the accuracy is corroborating.
- Isolated substrate: no field, no governance, no identity-stability read.
  Phase 2 (cost-gated live-stack validation, pre-declared envelope) is the
  next gate and is NOT covered here.
- 2 seeds, 1 corpus version, 1 epoch count. Direction and gate margins are the
  finding; absolute magnitudes are init-dependent.

## Open / next

1. **Phase 2:** boot the full stack from the pretrained checkpoint, run the
   baseline-range suite + `identity_stability_baseline` +
   `generator_diversity_audit` (does diversity survive the pipeline now?).
   **→ DONE (2026-06-12), Gate G2 passed** — `2026-06-12-phase2-fullstack-g2.md`.
2. Re-run `trained_generator_sim`'s GENERATOR-IS-THE-LOCK prediction with real
   corpus-trained weights instead of the mock.
3. The `.eval()` architect decision (2026-06-08 #1) — now urgent rather than
   academic: a trained generator has real deterministic structure dropout can
   only blur.
   **→ DECIDED (2026-06-12): eval-mode is the operating regime** —
   `docs/training/phase3_architect_decisions.md`.
4. Corpus is bootstrap-only; Phase 4's buffer-governed lived-experience
   collection remains the steady-state source (data_curation.md §4).
