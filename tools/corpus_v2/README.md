# tools/corpus_v2 — groundwork for the base-encoder corpus

Code for building corpus v2: a general **base** encoder that learns language and reasoning (design:
[`docs/training/corpus_v2_pipeline.md`](../../docs/training/corpus_v2_pipeline.md)). No training data lives here —
the corpus is private by design; only the method and the tests are public.

| File | What it does |
|---|---|
| `base_vocab_policy.py` | Glue v2 (the 19 spatial glue words of `tools/longseq/lexicon.py` + logic, negation, condition, contrast, comparison, time, questions, modality, pronouns = 146), reasoning content seeds, tone markers, abbreviation expansion, contraction expansion, hyphen splitting. |
| `intensity.py` | Per-row intensity tag (ALL-CAPS runs, emphasis, `!!!`, stretched words, emoticons) — information lowercasing erases. Perception of the input only; never sets the system's emotional state (emotion emerges — see the e8-eea principle). |
| `pii_scrub.py` | Standalone scrubber for personal info and credentials (dry run by default; writes cleaned copies elsewhere, never edits originals). Useful to anyone cleaning chat exports. |
| `check_probes.py` | Verifies the reasoning probe set (`data/probes/`) only uses in-vocabulary words. |

Run from the repo root, e.g. `python -m tools.corpus_v2.intensity` (self-test) or
`python tools/corpus_v2/pii_scrub.py my_exports/` (dry run).
