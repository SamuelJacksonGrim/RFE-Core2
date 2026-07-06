# Corpus MANIFEST

version: 1.2.0
date: 2026-07-06
generated_by: Claude (automated, RFE vocabulary); validated and cleaned in-repo;
operational-vocabulary extension built by data/corpus/build_extension_v1_1_0.py

## Composition
- train: 2870 sequences
- holdout: 501 sequences — 14.9%
- rhythms: stabilize, dream, reflect, explore
- vocab: 335 plain-English tokens — RFE conceptual neighborhood + the full
  operational vocabulary (Resonance Family streams, DEFAULT_RHYTHM_SEEDS,
  bootstrap WORDS, recursion1188 DEFAULT_TOKENS)
- contexts per unique token (train): min 9 (spec floor is 8)
- sequence lengths: 2–4 tokens
- sacred-constant tokens (`3.12`, `11.88`, `280.90`): absent, per
  `docs/training/data_curation.md` §3 exclusions. The English word "anchor"
  is present and is NOT the sacred ANCHOR symbol (whose token string is
  `3.12` — see `agents/governance_constants.py::PHILOSOPHICAL_CONSTANTS`).

## Source labels — removed in 1.2.0 (historical note)

Corpus versions ≤ 1.1.0 carried a per-sequence `source` field
(`source_samuel/claude/gemini/grok`). It was a **synthetic placeholder, not
provenance** — v1.0.x labels were assigned near-uniformly by the external
generator (768/749/695/658 across train, not the nominal 0.40/0.25/0.20/0.15
weights), the v1.1.0 extension assigned them by weighted RNG, the
source×rhythm cross-tab was flat, and nothing ever trained on the field
(`to_rhythm_seeds()` drops it; the only consumer was the integrity check's
enum validation). The Phase-4 source-diversity mechanism it nominally
reserved a slot for operates on **live-collected** samples, which carry real
`source_id`s from the loop (see `cognition/stream_recorder.py`) — the curated
corpus never needed the field. 1.2.0 removes it; the schema is now
`{"tokens": [...], "rhythm": "..."}`. Training-visible content (tokens +
rhythm labels) is byte-identical to 1.1.0, so G1/G2 findings against 1.1.0
remain valid for the training path.

## Split policy
Stratified by rhythm, ~15% holdout, sequences (not tokens) held out.
Token overlap between train/holdout is expected and correct; exact-sequence
overlap is not (see 1.0.1 changes). Holdout vocabulary is fully contained in
train vocabulary (0 unseen tokens), so holdout reads within-vocabulary
generalization — exactly what Gate G1 needs.

## Versioning
Any corpus change increments version. All findings reference corpus version.

### 1.2.0 (2026-07-06)
- **Source field removed** (schema: `{tokens, rhythm}`). The labels were
  synthetic (RNG/uniform), trained on by nothing, and misleading as
  provenance — see §Source labels above. Tokens, rhythm labels, sequence
  order, and the train/holdout split are unchanged from 1.1.0
  (training-visible data byte-identical). `build_extension_v1_1_0.py` is a
  historical artifact of the 1.1.0 build — do not re-run it against a
  ≥ 1.2.0 corpus (it emits the old schema).

### 1.1.0 (2026-06-12)
- **Operational-vocabulary extension** (+534 train / +91 holdout): the v1.0.x
  corpus covered the conceptual neighborhood but missed 63 of the 113 tokens
  the live system actually runs on (Resonance Family streams, rhythm seeds,
  bootstrap words, recursion1188 DEFAULT_TOKENS) — violating the
  data_curation.md §2.1 coverage requirement and leaving Phase 2 untestable.
  Built deterministically (seed 1188) by `build_extension_v1_1_0.py`: the
  operational sequences anchored under their natural rhythms + every missing
  token padded to ≥12 contexts from same-rhythm partner pools. Rhythm
  assignments are the hand-curated table in the build script — architect may
  amend and re-run.

### 1.0.1 (2026-06-11)
- Removed 19 exact-duplicate sequences within train, 1 within holdout
  (dedup key: token tuple; no rhythm-label conflicts existed).
- Removed 4 sequences from holdout that also appeared verbatim in train
  (`examine register`, `continuity alignment`, `sharpen rest`, `face shift`)
  — train→holdout leakage would inflate the Gate G1 generalization readout.
- Integrity is enforced by `python -m tests.diagnostic.training.corpus_integrity_check`.

### 1.0.0 (2026-06-11)
- Initial corpus: 2355 train / 415 holdout, generated per
  `docs/training/data_curation.md` §3.
