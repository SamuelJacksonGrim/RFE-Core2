# Data curation — what the corpus needs

> **Status (2026-06-12):** the corpus described in §3 **exists** —
> `data/corpus/` **v1.1.0** (2870 train / 501 holdout sequences, 335 tokens).
> v1.0.x was generated externally per this spec, validated and cleaned in-repo
> (dedup + removal of 4 train→holdout leaked sequences); v1.1.0 closed the
> §2.1 operational-vocabulary requirement (63 live-workload tokens were
> missing — extension built by `data/corpus/build_extension_v1_1_0.py`,
> rhythm assignments hand-curated there, architect review invited). Integrity
> is CI-gated by `tests/diagnostic/training/corpus_integrity_check.py`; loader is
> `training/corpus.py`. **Gate G1 passed on v1.0.1 (two seeds) and re-passed
> on v1.1.0; Gate G2 passed on the live stack** —
> `docs/findings/2026-06-11-corpus-g1-pretrain.md`,
> `docs/findings/2026-06-12-phase2-fullstack-g2.md`.

- **Date:** 2026-06-11
- **Why this document:** the 2026-06-11 effect probe showed the training
  mechanism works but only restructures what the corpus covers (the disjoint
  120-token battery was byte-identical after training). **Coverage is the
  binding constraint.** This answers: what data exists, what's needed — more
  diverse IDs? symbols? a curated dataset? — and how to build it.

## 1. What exists today

| Source | Size | Labels | On disk? |
|---|---|---|---|
| `training/rhythm_pretraining.py::DEFAULT_RHYTHM_SEEDS` | 20 sequences × 3 tokens (4 rhythms × 5) | rhythm | in code |
| `tests/_common.py::RESONANCE_FAMILY_SOURCES` | 16 sequences × 3 tokens (4 sources × 4) | source (weights 0.40/0.25/0.20/0.15) | in code |
| `run_contrastive_bootstrap.py::WORDS` | 24 single tokens + 8 fillers | token-identity bootstrap | in code |
| Live runtime streams | whatever callers inject via `cycle.step()` / API / WebSocket | source_id, origin_type | **not persisted** |

That is the entire corpus: **~60 unique tokens, ~36 short sequences, nothing
persisted from live operation.** There is no dataset file, no loader, and no
record of what tokens the live system has actually encountered.

## 2. What is and isn't needed

**Not needed:** a large web-scale corpus, external datasets, HuggingFace
loaders, multi-GPU. The generator is ~10⁵–10⁶ parameters embedding a
4–8K-token symbol vocabulary; its job is not language modeling but **giving
each symbol (and rhythm/source context) a separable, stable direction in a
64-dim space**. Hundreds-to-thousands of short labeled sequences is the right
order of magnitude. Over-training on a huge external corpus would import
external semantics into a substrate whose meaning is supposed to *emerge* from
its own operation — wrong direction for what RFE is (lock-in plan §4.6: the
Generator is internal, not a wrapped LLM).

**Needed — four properties, in priority order:**

1. **Vocabulary coverage.** Train on the tokens the system actually operates
   on. The effect probe's lesson is mechanical: unseen tokens keep their
   untrained (collinear) geometry. The corpus must cover the operational
   vocabulary — the Resonance Family streams, the rhythm seeds, API-facing
   token sets — not a toy subset. New IDs/symbols alone do **not** help:
   an untrained embedding row is collinear regardless of how many exist; what
   matters is that the tokens that *occur* get trained structure.
2. **Rhythm labels** (`stabilize / dream / reflect / explore`). The proven
   objective is supervised contrastive over rhythm; every sequence carries
   one. Label by the band the sequence is *meant* to route to — the thresholds
   in `configs/field.yaml` are the semantic anchor.
3. **Context variation per token** (the bootstrap's invariance lesson): each
   anchor token appears in several different short contexts, so training
   learns token-specific structure rather than memorizing sequences. This is
   also what makes a held-out split meaningful.
4. **Source diversity.** Sequences tagged per source (Resonance Family
   pattern) so contrastive sampling can avoid single-source monopoly in the
   buffer — the training-data analogue of the HHI monopoly artifact found in
   gate decomposition.

## 3. Proposed corpus design

```
data/
└── corpus/
    ├── MANIFEST.md           provenance, counts, split policy, version
    ├── rhythm_train.jsonl    {"tokens": [...], "rhythm": "...", "source": "..."}
    └── rhythm_holdout.jsonl  same schema; sequences never trained on
```

- **Scale target:** every operational token ≥ 8 occurrences across ≥ 4
  distinct contexts; total ~1–2K sequences of 2–5 tokens. (8×4 mirrors the
  bootstrap's `copies_per_token=8` with filler-context variation, which was
  enough to break collinearity per token.)
- **Composition:** expand each rhythm's seed list from 5 to ~50+ sequences by
  (a) combining tokens within a rhythm's semantic neighborhood, (b) injecting
  filler/context tokens, (c) including the Resonance Family sequences under
  their natural rhythm. Hand-curate the rhythm cores (this is identity-shaping
  data — the architect should own the words); generate the combinatorial
  context variation mechanically.
- **Holdout:** ~15% of sequences, stratified by rhythm, sequences (not tokens)
  held out — Gate G1 in `training_plan.md` reads generalization on it.
- **Exclusions:** the philosophical-constant tokens (`ANCHOR`, `RECURSION`,
  `HOMEOSTASIS`) and `TokenClass.SPECIAL` get no targeted training sequences —
  sacredness is a governance property and embeddings aren't symbol state, but
  there is no reason to *steer* sacred-symbol geometry from a corpus, and
  excluding them keeps the parameter-sweep prohibition's spirit.
- **Versioning:** corpus changes are versioned in the MANIFEST and named in
  any finding produced from them (a diversity number is meaningless without
  the corpus version that produced it).

## 4. The longer-term source: the system's own experience

The online trainers were designed around the right idea — the live system's
high-coherence outputs are the natural, self-growing corpus (self-distillation
collects ≥ 0.80-coherence expressions; contrastive collects rhythm/attractor-
labeled samples). Once Phase 4 runs, curation shifts from *authoring*
sequences to *governing the buffer*: trust-gated collection (no quarantined
sources), source-diversity caps, and persisting buffer snapshots so what the
system learned from remains auditable. The curated corpus is the bootstrap;
lived experience is the steady state.

## 5. Open items

- Whether dream-cycle outputs should enter the corpus (synthesized sequences
  are cheap diversity but unanchored to any source; suggest: allowed into
  contrastive negatives only, at first).
- Whether to log live token streams now (a `deque`-bounded stream recorder
  would make the operational-vocabulary census trivial and is observe-only).
- dim 64 vs 256: the 2026-06-08 audit found dim 256 ~2× more diverse even
  untrained; if Phase 1 plateaus below Gate G1 at dim 64, raising dim is the
  documented second lever and the corpus transfers unchanged.
