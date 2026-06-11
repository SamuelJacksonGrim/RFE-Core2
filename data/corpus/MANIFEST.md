# Corpus MANIFEST

version: 1.0.1
date: 2026-06-11
generated_by: Claude (automated, RFE vocabulary); validated and cleaned in-repo

## Composition
- train: 2336 sequences (stabilize 573 / dream 585 / reflect 572 / explore 606)
- holdout: 410 sequences (stabilize 100 / dream 103 / reflect 101 / explore 106) — 14.9%
- rhythms: stabilize, dream, reflect, explore
- sources: source_samuel, source_claude, source_gemini, source_grok
- vocab: 272 plain-English tokens, RFE conceptual neighborhood
- contexts per unique token (train): min 15 (spec floor is 8, claimed 10)
- sequence lengths: 2–4 tokens
- sacred-constant tokens (`3.12`, `11.88`, `280.90`): absent, per
  `docs/training/data_curation.md` §3 exclusions. The English word "anchor"
  is present and is NOT the sacred ANCHOR symbol (whose token string is
  `3.12` — see `agents/governance_constants.py::PHILOSOPHICAL_CONSTANTS`).

## Split policy
Stratified by rhythm, ~15% holdout, sequences (not tokens) held out.
Token overlap between train/holdout is expected and correct; exact-sequence
overlap is not (see 1.0.1 changes). Holdout vocabulary is fully contained in
train vocabulary (0 unseen tokens), so holdout reads within-vocabulary
generalization — exactly what Gate G1 needs.

## Versioning
Any corpus change increments version. All findings reference corpus version.

### 1.0.1 (2026-06-11)
- Removed 19 exact-duplicate sequences within train, 1 within holdout
  (dedup key: token tuple; no rhythm-label conflicts existed).
- Removed 4 sequences from holdout that also appeared verbatim in train
  (`examine register`, `continuity alignment`, `sharpen rest`, `face shift`)
  — train→holdout leakage would inflate the Gate G1 generalization readout.
- Counts above are post-cleanup. Integrity is enforced by
  `python -m tests.diagnostic.corpus_integrity_check`.

### 1.0.0 (2026-06-11)
- Initial corpus: 2355 train / 415 holdout, generated per
  `docs/training/data_curation.md` §3.
