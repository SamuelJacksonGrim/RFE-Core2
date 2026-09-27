"""Refuse to touch the live corpus or the live 128 checkpoint.

Hashes are the ones recorded on 2026-09-23 before this branch wrote anything.
A mismatch means something else moved a protected file; abort rather than
train on top of an unknown corpus.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LIVE = {
    "data/corpus/rhythm_train.jsonl":
        "f5d608597c195719f2b3634bbfcedbbe10f9aefac5b0bae4c4546741be221e61",
    "data/corpus/rhythm_holdout.jsonl":
        "61c93de1089c6b515675698fe63e8e29123c93001aae44b665f247254c148888",
    "data/checkpoints/generator_weights_5rhythm.pt":
        "71c646fb36d40e3b20cb03d1aa02f51c7a139ab4250aa701694fad8ef2482361",
    "data/checkpoints/generator_ecology_5rhythm.json":
        "d74c829c078e22b76423cdf1b5b02a2032e02b1b8ae142b85f51d19e7d27d600",
}

# Contrastive baselines from the dim-256 run. Read, never rewrite.
BASELINE_WEIGHTS = {
    128: "data/checkpoints/generator_weights_5rhythm_128paired.pt",
    256: "data/checkpoints/generator_weights_5rhythm_256.pt",
}
BASELINE_ECOLOGY = {
    128: "data/checkpoints/generator_ecology_5rhythm_128paired.json",
    256: "data/checkpoints/generator_ecology_5rhythm_256.json",
}
FROZEN_WEIGHTS = "data/checkpoints/generator_weights_5rhythm.pt"
FROZEN_ECOLOGY = "data/checkpoints/generator_ecology_5rhythm.json"

PROTECTED_NAMES = {
    "rhythm_train.jsonl",
    "rhythm_holdout.jsonl",
    "MANIFEST.md",
    "generator_weights_5rhythm.pt",
    "generator_ecology_5rhythm.json",
    "generator_weights_5rhythm_kimi.pt",
    "generator_ecology_5rhythm_kimi.json",
    "generator_weights_5rhythm_legible.pt",
    "generator_ecology_5rhythm_legible.json",
    "generator_weights_5rhythm_128paired.pt",
    "generator_ecology_5rhythm_128paired.json",
    "generator_weights_5rhythm_256.pt",
    "generator_ecology_5rhythm_256.json",
    "decoder_5rhythm.pt",
    "decoder_5rhythm_ecology.pt",
    "decoder_5rhythm_256.pt",
    "generator_weights_completion_128_gluepad.pt",
    "generator_ecology_completion_128_gluepad.json",
    "completion_head_128_gluepad.pt",
    "generator_weights_completion_128_rhythmce.pt",
    "generator_ecology_completion_128_rhythmce.json",
    "completion_head_128_rhythmce.pt",
    # S2 mouth. Phase C trains new files. These names stay refused.
    "generator_weights_completion_128_phaseb.pt",
    "generator_ecology_completion_128_phaseb.json",
    "completion_head_128_phaseb.pt",
    "generator_weights_completion_256_phaseb.pt",
    "generator_ecology_completion_256_phaseb.json",
    "completion_head_256_phaseb.pt",
    "banked_mouth_completion_128.pt",
    "banked_mouth_ecology_128.json",
    "banked_mouth_head_128.pt",
    "banked_mouth_completion_256.pt",
    "banked_mouth_ecology_256.json",
    "banked_mouth_head_256.pt",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_live_intact() -> dict:
    found = {}
    for rel, expect in LIVE.items():
        path = REPO / rel
        digest = sha256(path)
        if digest != expect:
            raise SystemExit(f"live file moved: {rel} sha256 {digest} != {expect}")
        found[rel] = digest
    return found


def refuse_protected(path: str) -> None:
    name = Path(path).name
    if name in PROTECTED_NAMES:
        raise SystemExit(f"refusing to write protected artifact: {path}")
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = REPO / resolved
    corpus = (REPO / "data" / "corpus").resolve()
    if corpus in resolved.resolve().parents or resolved.resolve() == corpus:
        raise SystemExit(f"refusing to write under the live corpus: {path}")
