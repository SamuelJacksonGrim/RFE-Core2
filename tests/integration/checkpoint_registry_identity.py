"""
tests/integration/checkpoint_registry_identity.py

Regression guard: Generator.load_checkpoint must preserve the SymbolRegistry
OBJECT — not just its contents.

SelfhoodGovernance and ValueEmergenceEngine capture `generator.registry` at
construction (tests/_common.build_full_stack wiring, mirroring the README
composition). A load path that REBINDS the registry orphans both onto a stale
object: governance symbol lookups go silently stale, and value emergence dies
entirely — every `get_by_stable_id` misses, so no value is ever born. This is
exactly how the 2026-06-12 SECOND-LOCKER field-map matrix produced
active_values=0 in all 15 pretrained cells (finding:
docs/findings/2026-06-12-checkpoint-registry-orphan.md).

Checks (no training required — an untrained round-trip exercises the path):
  1. save_checkpoint -> load_checkpoint keeps `gov.registry is gen.registry`
     and `ve.registry is gen.registry` True.
  2. Values still form after the round-trip (60 canonical steps,
     active_values(min_strength=0) > 0) — the behavioral symptom that
     caught the original defect.
  3. Vocab survives the round-trip (loaded registry resolves a token
     registered before save).

Exit 0 = pass, 1 = fail. Fast (~seconds); part of run_all_tests.sh.
"""

from __future__ import annotations

import logging
import random
import sys
import tempfile
from pathlib import Path

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from tests._common import (RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
                           build_full_stack)

SEED = 42
N_STEPS = 60


def main() -> int:
    print("=" * 72)
    print("  INTEGRATION: checkpoint round-trip preserves registry identity")
    print("=" * 72)
    print()

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack()

    # Register a token before save so we can check vocab survival.
    gen.generate(["resonance", "field", "engine"])
    pre_vocab = gen.registry.address_space.vocab_size

    with tempfile.TemporaryDirectory() as td:
        wp = str(Path(td) / "ckpt.pt")
        ep = str(Path(td) / "ckpt.ecology.json")
        gen.save_checkpoint(wp, ep)
        gen.load_checkpoint(wp, ep)

    checks = []
    checks.append((gov.registry is gen.registry,
                   "governance registry reference survives load"))
    checks.append((ve.registry is gen.registry,
                   "value-engine registry reference survives load"))
    checks.append((gen.registry.address_space.vocab_size == pre_vocab,
                   f"vocab survives round-trip ({pre_vocab} tokens)"))

    # Behavioral symptom: values must still form post-load.
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    sids = list(RESONANCE_FAMILY_SOURCES)
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    for _ in range(N_STEPS):
        src = random.choices(sids, weights=weights)[0]
        cycle.step(random.choice(RESONANCE_FAMILY_SOURCES[src]),
                   source_id=src, origin_type="internal")
    n_values = len(ve.active_values(min_strength=0.0))
    checks.append((n_values > 0,
                   f"value emergence alive after load ({n_values} values "
                   f"in {N_STEPS} steps)"))

    all_ok = True
    for ok, label in checks:
        print(f'  {"✓" if ok else "✗"} {label}')
        all_ok &= ok
    print()
    print(f'{"Registry identity guard PASSED." if all_ok else "FAILED — load path orphans attached subsystems."}')
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
