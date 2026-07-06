"""
training/corpus.py

Loader for the curated rhythm corpus (`data/corpus/`).

The corpus is the Phase 1 deliverable of `docs/training/training_plan.md`:
rhythm-labeled JSONL sequences over the operational vocabulary, with a
held-out split for the Gate G1 generalization readout. Schema per
`docs/training/data_curation.md` §3:

    {"tokens": ["...", ...], "rhythm": "stabilize|dream|reflect|explore"}

(Corpus versions <= 1.1.0 also carried a synthetic per-sequence "source"
label; it was provenance-shaped noise trained on by nothing and was removed
in v1.2.0 — see the MANIFEST's source-labels note.)

`to_rhythm_seeds()` adapts a loaded split to the `{rhythm: [token_list, ...]}`
shape `RhythmPretrainer` consumes, so the pretrainer runs on the corpus file
instead of its in-code `DEFAULT_RHYTHM_SEEDS`.

Findings produced from a corpus must name its MANIFEST version
(`corpus_version()`), per `data/corpus/MANIFEST.md` §Versioning.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"

TRAIN_PATH = CORPUS_DIR / "rhythm_train.jsonl"
HOLDOUT_PATH = CORPUS_DIR / "rhythm_holdout.jsonl"
MANIFEST_PATH = CORPUS_DIR / "MANIFEST.md"

RHYTHMS = ("stabilize", "dream", "reflect", "explore")


def load_corpus(path: Path) -> List[dict]:
    """Load one JSONL split as a list of {tokens, rhythm} records."""
    records: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def to_rhythm_seeds(records: List[dict]) -> Dict[str, List[List[str]]]:
    """Group records into the {rhythm: [token_list, ...]} shape RhythmPretrainer takes."""
    seeds: Dict[str, List[List[str]]] = {r: [] for r in RHYTHMS}
    for rec in records:
        seeds[rec["rhythm"]].append(list(rec["tokens"]))
    return seeds


def corpus_version() -> str:
    """Read the corpus version from the MANIFEST (for naming in findings)."""
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\S+)", text, re.MULTILINE)
    return m.group(1) if m else "unknown"
