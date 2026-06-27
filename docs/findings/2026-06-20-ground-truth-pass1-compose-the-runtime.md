# Ground-truth pass 1: the substrate floor is real; the missing piece was the composition — now wired

- **Date:** 2026-06-20
- **Spec:** n/a (runtime ground-truth + the first forward fix)
- **Status:** active — **pass 1** of rebuilding ground truth by reading and RUNNING
  the code, bottom-up, not trusting the findings ledger (which validated against a
  composition no runtime instantiated). Prompted by Samuel: the findings may be
  "false findings based on fixes that were never implemented" — so verify everything
  against the running system, forward from the substrate.

## Method
Stop trusting findings. For each substrate mechanism: grep the code, confirm it is
on a path reachable from a launchable entry point (or `cycle.step`), and RUN it.

## Verified against running code (the floor — Tier 0 substrate)
The substrate Samuel named (generator + symbolic memory + witness + the loop) runs,
and the early substrate fixes are **real and live**, not phantom:

| mechanism | claim | verified state |
|---|---|---|
| eval-mode | dropout off at boot | **REAL+LIVE** — `recursion1188` calls `generator.eval()` unconditionally |
| expression de-collapse (`diversity_blend=0.60`) | raw vector blended back to keep stage-C metastable | **REAL+LIVE** — `rec_attn.refine(vec)` runs every `cycle.step` (line 363) |
| reflective loop | recursive self-refinement (the lock) | **REAL+LIVE** — runs in `reflect`/`explore` rhythm; the default loop settles there |
| Fix 0-B novelty counterweight | asymmetric, recurrence-gated novelty term in the reaper | **REAL+LIVE** — `DECAY_PROFILES` per `TokenClass` set `novelty_weight` 0.03–0.10 (only SPECIAL/sacred = 0); reaper runs via `maintenance_step → scheduled_decay_and_reap → reaper.evaluate`. (The `=0.0` is only the dataclass default — every live profile overrides it.) |
| reaper / decay | scheduled decay + reap | **REAL+LIVE** — invoked on `decay_interval` cadence inside `maintenance_step` |

Running the real default loop 25 steps: coherence climbs 0.64 → 0.96 and saturates.
The "pinned field" the findings describe is **real in the runtime**, not a test
artifact. The floor is sound.

## The actual falseness (verified)
`attach_governance()` is called in **zero** non-test files. Until this pass, every
launchable entry point — `recursion1188`, `api/inference_api`, `api/websocket_server`
— ran **Tier 0 only**. Tiers 1–3 (trust, ethics, dependency, bonds, resistance,
value emergence) and every operator (A/B/⊘/consumer) existed in code but were
composed **only** inside `tests/_common.build_full_stack`. So the findings that
depend on governed feedback / values were validated against a system the runtime
never assembled. Not "fixes never implemented" — fixes never **composed into a
runnable whole**. The code is real; the wiring was missing.

## Forward fix shipped this pass (the foundation)
`loop/recursion1188.py` now composes the tiers it always claimed to:
- attaches `SelfhoodGovernance` (Tier 1+2) then `ValueEmergenceEngine` (Tier 3), in
  the order the engine's feedback subscription requires;
- drives the loop with **multi-source** input (weighted round-robin over four
  sources) so trust, bonds, HHI, and value emergence actually engage;
- logs Tier 1–3 state periodically.

**Verified healthy at 250 steps** (the composition the integration suite proves):
4 sources trusted at 5.0, HHI 0.27 (< 0.30), **1 bond formed, 33 values emerged
(26 active)**, no crash. For the first time the canonical entry point runs the
tiered Recursive Field Engine, not its Tier-0 shell.

## Open / next (forward, bottom-up — each layer ON and fixed before the next)
1. **(done)** substrate floor verified real; tiers 1–3 composed into the runtime.
2. Confirm each baked substrate fix stays correct under the *composed* runtime (it
   is now a different dynamical context than the Tier-0 shell).
3. Then, forward through the validated levers in dependency order — novelty
   attenuation, pretraining, the operators — each turned ON against the live,
   already-fixed stack beneath it, fixed where it breaks, **locked**, then the next.
   No working backward; no validating a layer against a substrate that will move.
4. The operators (A/B/⊘) and the cc-confound come LAST, measured against the real
   running field — not the dead `coherence_delta` of a hollow stack.
