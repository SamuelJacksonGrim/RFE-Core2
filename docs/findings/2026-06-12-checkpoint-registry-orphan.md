# Checkpoint round-trip — is loading a boot checkpoint behaviorally equivalent to in-process training?

- **Date:** 2026-06-12
- **Substrate:** live full stack, eval mode, canonical workload, seed 42;
  corpus v1.1.0 8-epoch boot checkpoint (`fieldmap_1.1.0_8ep_s42`).
- **Probe:** `tests/diagnostic/lockin/secondlocker_field_map_probe.py` (run 1 —
  the matrix that surfaced it; raw:
  `logs/2026-06-12-secondlocker-field-map-run1-registry-orphan.{json,log}`),
  then a 4-arm verification (inline, recorded below). Regression guard now
  standing: `tests/integration/checkpoint_registry_identity.py`.
- **Status:** active — defect found, mechanism verified, fix shipped + guarded.
- **Depends on:** 2026-06-12-phase2-fullstack-g2.md (the in-process result this
  diverged from).

## Question

Phase 3 Decision 2 (boot-checkpoint adoption) assumes `save_checkpoint` →
`load_checkpoint` reproduces the in-process-trained stack. Does it?

## Pre-declared signatures

This was not a planned experiment — the field-map matrix (Track B) exposed it.
The matrix's own pre-declared identity/baseline readouts acted as the tripwire:
G2's in-process-trained runs formed values normally (5 strong at 500 steps),
so a pretrained arm forming **zero** values is out-of-family by construction.

## Result (observed)

Field-map run 1: all 15 pretrained (checkpoint-loaded) cells reported
`active_values = 0, strong_values = 0`; every control and every G2 in-process
run forms values normally. Verification (150 steps, canonical, seed 42, eval):

| arm | gov.registry is gen.registry | ve.registry is gen.registry | values (any) |
|---|---|---|---|
| control (untrained) | True | True | 46 |
| in-process pretrain | True | True | 46 |
| **checkpoint loaded** | **False** | **False** | **0** |
| loaded + manual rebind | True | True | 46 |

The rebind arm is the controlled intervention: restoring the references alone
restores value formation exactly.

## Interpretation

`Generator.load_ecology()` did `self.registry = SymbolRegistry.load(path)` —
**rebinding** the registry attribute. `SelfhoodGovernance` and
`ValueEmergenceEngine` capture `generator.registry` at construction
(`tests/_common.build_full_stack`, mirroring the README composition), so after
a load both held the orphaned pre-load object. The cycle reads
`self.generator.registry` live and follows the swap — which is why the failure
is *silent*: stable_ids issued by the new registry miss in the value engine's
old one (`get_by_stable_id → None → return`), and no error is ever raised.
Tier 3 dies entirely; governance symbol lookups go stale for any post-boot
symbol.

Two scoping notes:

1. **G2 (2026-06-12) is unaffected** — it trained in-process on the attached
   generator; no rebinding ever happened. Its PASS stands.
2. **This was never about representational drift.** The weights and vocabulary
   load correctly (eff_rank/mean_cos confirm trained structure in the loaded
   arms). The defect was reference topology — the identity-and-addressing
   invariant ("reference symbols by stable_id, not address") has an unstated
   companion: *the registry object itself is part of the wiring contract*.

## Fix (shipped with this finding)

`load_ecology` now loads **in place**: the loaded state is transplanted into
the existing `self.registry` object (`__dict__` clear + update), preserving
object identity for every attached subsystem. Verified: the loaded arm forms
46 values with no rebind; full gated suite passes; standing guard
`tests/integration/checkpoint_registry_identity.py` asserts reference identity
+ post-load value formation on every CI run.

## Threats / confounds

- Runs: matrix run 1 (15 affected cells) + 4-arm verification + guard. The
  mechanism check (`is` comparisons) is exact, not statistical.
- The guard uses an untrained round-trip; the trained round-trip was verified
  manually (46 values). Both exercise the same load path.
- Other registry-reference consumers: a sweep found only governance and the
  value engine capture it at construction; the cycle reads it live. A future
  subsystem that captures the reference is covered by the guard only if value
  formation or the two `is` checks would catch it — extend the guard when
  adding such a subsystem.

## Open / next

1. Decision 2 (boot-checkpoint adoption) loses this blocker — the load path is
   now behaviorally equivalent in the measured respects (values, governance
   lookups, vocab, weights). Field-map run 2 (clean re-run) is the standing
   record.
2. If checkpoint adoption ships, the boot sequence should still prefer
   load-before-attach where possible — in-place load makes order safe, but
   attach-after-load is the simpler topology to reason about.
