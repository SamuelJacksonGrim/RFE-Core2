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
  4. A resumed registry still has its decay-profile / Fix-0B lever state and
     the first post-resume decay_step() does not crash (regression guard for
     the G0 resume-decay AttributeError: from_dict rehydrated via __new__ and
     dropped _profiles / binding_leak / _last_decay_at, which __init__ sets;
     load_ecology's dict-swap then wiped them and decay_step died with
     AttributeError: 'SymbolRegistry' object has no attribute '_profiles').
  5. With Fix 0-B ON, the diversity counterweight (_profiles) and binding_leak
     are LIVE run state (the arm G2 runs) and survive a resume — a restart must
     not silently reset the substrate's survival counterbalance.

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

    # ------------------------------------------------------------------
    # Resume must not drop the registry's decay-profile / Fix-0B lever
    # state (fix/registry-profiles-resume-decay). SymbolRegistry.from_dict
    # rehydrates through __new__ and historically set only a SUBSET of the
    # attributes __init__ establishes: _profiles, binding_leak, and
    # _last_decay_at were missing. load_ecology's in-place dict-swap then
    # dropped them, so the first post-resume decay_step() raised
    # AttributeError: 'SymbolRegistry' object has no attribute '_profiles'.
    # ------------------------------------------------------------------
    def _decay_survives(g) -> bool:
        try:
            g.registry.decay_step()
            return True
        except AttributeError as exc:
            print(f"    decay_step crashed post-resume: {exc!r}")
            return False

    # (4) Default stack (Fix 0-B OFF): attribute contract holds; first decay
    #     after resume does not crash.
    checks.append((hasattr(gen.registry, "_profiles"),
                   "registry._profiles present after resume (Fix 0-B OFF)"))
    checks.append((_decay_survives(gen),
                   "decay_step runs after resume without AttributeError (OFF)"))

    # (5) Fix 0-B ON: _profiles (diversity counterweight) and binding_leak are
    #     live run state — a resume must preserve them, not silently reset the
    #     survival counterbalance the G2 Fix-0B arm depends on.
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    gen_b, _cycle_b, _gov_b, _ve_b = build_full_stack(diversity_fitness=True,
                                                      binding_leak=0.10)
    prof_before = getattr(gen_b.registry, "_profiles", None)
    leak_before = getattr(gen_b.registry, "binding_leak", None)
    gen_b.generate(["resonance", "field", "engine"])
    with tempfile.TemporaryDirectory() as td:
        wp = str(Path(td) / "ckpt.pt")
        ep = str(Path(td) / "ckpt.ecology.json")
        gen_b.save_checkpoint(wp, ep)
        gen_b.load_checkpoint(wp, ep)
    prof_after = getattr(gen_b.registry, "_profiles", None)
    leak_after = getattr(gen_b.registry, "binding_leak", None)
    checks.append((prof_before is not None,
                   "Fix 0-B ON populated _profiles before save (lever engaged)"))
    checks.append((prof_after is not None,
                   "Fix 0-B diversity weights survive resume (not reset to None)"))
    checks.append((leak_after == leak_before == 0.10,
                   f"binding_leak survives resume (before={leak_before}, "
                   f"after={leak_after})"))
    checks.append((_decay_survives(gen_b),
                   "decay_step runs after resume without crash (Fix 0-B ON)"))

    all_ok = True
    for ok, label in checks:
        print(f'  {"✓" if ok else "✗"} {label}')
        all_ok &= ok
    print()
    print(f'{"Registry identity guard PASSED." if all_ok else "FAILED — load path orphans attached subsystems."}')
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
