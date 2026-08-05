# The first scheduled decay after a checkpoint resume crashes — `SymbolRegistry._profiles` dropped on rehydrate

- **Date:** 2026-07-21 · **Status:** resolved (surfaced in Garage **G0** resume test)
- **Fix:** `agents/symbolic_memory.py` (`SymbolRegistry.from_dict`), `agents/generator.py` (`load_ecology`)
- **Guard:** `tests/integration/checkpoint_registry_identity.py` (extended; in `run_all_tests.sh`)
- **Depends on:** `2026-06-12-checkpoint-registry-orphan` (same load path; guard extended here)

**Verdict:** a `session_persistence` run **resumed** from a checkpoint crashed ~step 350 at the first
`registry.decay_step()` — `AttributeError: 'SymbolRegistry' object has no attribute '_profiles'`. A **fresh**
persistence run completed 500 steps clean, so the defect is specific to the **resume** path.

**Root cause:** `from_dict` rehydrates via `__new__` and set only a subset of `__init__`'s attributes —
`_profiles`, `binding_leak`, `_last_decay_at` (all added to `__init__` in the 2026-07-18 Fix-0B/0-C work)
were never mirrored, and `load_ecology`'s in-place dict-swap inherited the incomplete key set. The old guard
round-tripped the checkpoint but never ran a post-load `decay_step()`, so CI missed it.

**Fix — "preserve, don't persist":** (1) `from_dict` re-establishes the three attrs at `__init__` defaults
(fix at source; no silent `getattr` mask). (2) `load_ecology` captures the boot-configured `_profiles`/
`binding_leak` before the swap and re-applies after — so a resumed **Fix-0B-ON** run keeps its counterweight
**without** baking config into the checkpoint (`CONFIG` stays authoritative; the rejected alt (A) would invert
the `component < YAML < CONFIG` precedence). Guard extended: **red pre-fix, 10/10 green** after; two-process
resume both exit 0. **Unblocks G2** (Fix-0B-ON across resumed runs).

*Consolidated 2026-08-05 — verdict, root cause, fix, and the preserve-not-persist decision kept. Full history in git.*
