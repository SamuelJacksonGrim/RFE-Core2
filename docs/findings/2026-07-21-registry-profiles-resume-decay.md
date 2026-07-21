# The first scheduled decay after a checkpoint resume crashes — `SymbolRegistry._profiles` is dropped on rehydrate

- **Date:** 2026-07-21
- **Substrate:** garage box (WSL2 + RTX 5070 Ti), dim 128, eval-mode, `session_persistence` ON; surfaced during `GARAGE_RUN_PLAN.md` **G0** box verification (resume test)
- **Control / guard:** `tests/integration/checkpoint_registry_identity.py` (extended here; part of `run_all_tests.sh`)
- **Fix:** `agents/symbolic_memory.py` (`SymbolRegistry.from_dict`), `agents/generator.py` (`load_ecology`)
- **Status:** resolved
- **Depends on:** `2026-06-12-checkpoint-registry-orphan.md` (same load path; that finding's guard is the file extended here)

## Signature

A run booted with `session_persistence` ON, resumed from a prior session's
checkpoint, and then died mid-run at the first scheduled decay pass:

```
AttributeError: 'SymbolRegistry' object has no attribute '_profiles'
  agents/symbolic_memory.py:1339  decay_step()
    profiles = self._profiles if self._profiles is not None else DECAY_PROFILES
```

Boot resume itself worked — the logs showed `Session checkpoint found … will
resume` and `weights + ecology + emergent values restored from previous run`,
and boot pretraining was correctly skipped. The crash came ~step 350, when
generator auto-maintenance first called `registry.decay_step()`. A **fresh**
`session_persistence` run (no checkpoint to load) completed 500 steps and saved
cleanly — the defect is specific to the **resume** path.

## Root cause

`SymbolRegistry.from_dict` rehydrates through `cls.__new__(cls)` (to preserve
stable-id identity), then sets attributes by hand — but only a **subset** of
what `__init__` establishes. Three attributes that `__init__` sets and
`decay_step()` reads unconditionally were missing from the rehydrated instance:

- `_profiles` (Fix 0-B per-registry decay-profile overrides; `None` at default),
- `binding_leak` (Fix 0-C demotion leak; `0.0` at default),
- `_last_decay_at` (decay-pass cursor; `0` at default).

These were added to `__init__` on 2026-07-18 (the Fix 0-B/0-C work) but never
mirrored into `from_dict`. `Generator.load_ecology` restores IN PLACE by
`self.registry.__dict__.clear()` + `update(loaded.__dict__)` — so the cleared
registry inherited exactly the (incomplete) key set of the rehydrated copy, and
`_profiles` was simply absent. The existing registry-orphan guard round-tripped
the checkpoint but never exercised a post-load `decay_step()`, so the gap was
invisible to CI.

## Decision — preserve, don't persist

There is a second, quieter failure beneath the crash. The cycle constructor
applies the Fix 0-B/0-C levers to the registry at boot
(`set_diversity_weights()` → `_profiles`; `binding_leak = …`) **before**
`load_checkpoint` runs, and `load_ecology`'s dict-swap then wiped those
boot-applied values. So even once the crash is prevented, a naïve "default to
`None` on rehydrate" would make a resumed **Fix-0B-ON** run silently lose its
diversity counterweight and its binding leak after the first restart — and the
Fix-0B-ON arm is exactly what **G2** runs. This is the substantive call, not
just "stop the crash."

`_profiles` / `binding_leak` are **config-derived boot state**, applied every
boot from `CONFIG` by the cycle constructor; `to_dict` deliberately does not
persist them. Two ways to keep Fix-0B-ON alive across resume:

- **(A) Persist into the checkpoint.** Rejected: a checkpoint taken Fix-0B-ON,
  later resumed under a Fix-0B-*off* `CONFIG`, would have the checkpoint
  override the config flag — inverting the `component < YAML < CONFIG`
  precedence contract. Config baked into a checkpoint is the anti-pattern.
- **(B) Preserve the boot-applied values across the in-place restore.** Chosen.
  `CONFIG` stays authoritative (the cycle constructor already applied the lever
  at boot); the restore simply must not clobber it.

## Fix

1. **`SymbolRegistry.from_dict`** now re-establishes the three attributes at
   their `__init__` defaults (`_profiles=None`, `binding_leak=0.0`,
   `_last_decay_at=0`). A rehydrated registry — standalone, or via `load()` —
   always honors `__init__`'s contract, so the first `decay_step()` never
   raises. This is the fix at the source.
2. **`Generator.load_ecology`** captures the live `_profiles` / `binding_leak`
   from the boot-configured registry before the dict-swap and re-applies them
   after, so a resumed Fix-0B-ON run keeps its counterweight. No config is
   written to the checkpoint; the lever flag stays owned by `CONFIG`.

No belt-and-suspenders `getattr` guard was added in `decay_step()`: the source
fix makes the attribute always present, and a silent `getattr` default would
only mask a future `from_dict` omission that this test should instead catch loud.

## Guard (the test that now fails-without / passes-with)

`tests/integration/checkpoint_registry_identity.py` extended with, after the
checkpoint round-trip: (4) `_profiles` present and `decay_step()` runs without
`AttributeError` (Fix 0-B OFF); (5) with Fix 0-B ON + `binding_leak=0.10`,
`_profiles` stays non-`None` and `binding_leak` stays `0.10` across the resume,
and `decay_step()` runs. Confirmed **red** on the pre-fix code (the two OFF
checks and all three ON-survival checks failed with the exact AttributeError),
**green** after the fix (10/10 checks).

## Resolution

- Real two-process resume (fresh → restart, 500 steps each) re-run after the
  fix: **both processes exit 0** (run 2 previously crashed ~step 350). → DONE
- Full `run_all_tests.sh` green after the fix (+ the extended guard). → DONE
- Unblocks **G2**, which requires `session_persistence` ON across long/resumed
  runs, including the Fix-0B-ON arm.
