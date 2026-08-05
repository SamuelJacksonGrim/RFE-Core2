# Checkpoint round-trip — is loading a boot checkpoint behaviorally equivalent to in-process training?

- **Date:** 2026-06-12 · **Status:** resolved (defect found → fixed → guarded)
- **Probe:** `secondlocker_field_map_probe.py` (run 1 surfaced it) + 4-arm verification
- **Guard:** `tests/integration/checkpoint_registry_identity.py` (standing, in CI)
- **Depends on:** `2026-06-12-phase2-fullstack-g2`

**Verdict:** NO — loading a checkpoint was *not* equivalent; `load_ecology` **rebound** the registry
attribute, silently orphaning governance + the value engine (Tier 3 formed **zero** values).

**Control (the tell):** control and in-process pretrain each form **46** values with `gov.registry is
gen.registry == True`; the **checkpoint-loaded** arm → **0 values**, both `is` checks **False**; a
manual-rebind arm restores exactly **46** — isolating reference topology as the cause, not weight drift
(eff_rank/mean_cos confirmed trained structure loaded fine). Silent because new-registry stable_ids miss
in the value engine's orphaned old one (`get_by_stable_id → None`), no error raised.

**Fix (shipped with this finding):** `load_ecology` now loads **in place** (`__dict__` clear + update),
preserving object identity for every attached subsystem. Loaded arm forms 46 values with no rebind; standing
guard asserts reference identity + post-load value formation every CI run. Unblocked boot-checkpoint adoption.

*Consolidated 2026-08-05 — verdict, control, and fix preserved; lab-notebook prose trimmed. Full history in git.*
