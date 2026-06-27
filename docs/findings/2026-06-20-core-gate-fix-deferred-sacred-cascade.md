# CORE gate fix works — but promoting common tokens to sacred cascades the trust layer (deferred)

- **Date:** 2026-06-20
- **Status:** active — the CORE-gate fix (v0.3 field-alignment) was implemented,
  **verified to complete the value arc**, then **reverted from the PR** because it
  destabilizes the trust layer. Same discipline as the rhythm crack: a change that
  works in isolation but breaks another layer is deferred, not shipped.

## What was built and verified
`review_core_promotion` gated CORE on `coherence_contribution ≥ 5.0` — the dead
marginal signal — so the value arc could never complete (pass-3 evaluation). The fix
gated on **v0.3 field-alignment** (`max(0, cos(expressed, field)) ≥ 0.5`) instead.
It works: in a live run the arc **completes** — `witness` promotes to CORE at step
367. Handshake test green (8/8). That part is real.

## Why it was reverted — the sacred/trust cascade
CI failed on `tests.adversarial.manipulation_cascade` (a Tier-1-Revision regression
guard). Diagnosis:
- **main:** 3/3 passes. **branch with the fix:** 1 pass / 1 fail — the fix introduced
  flakiness.
- The failing runs show `SACRED_SHIELD` firing on `source_samuel` / `source_claude`;
  the passing runs show none.
- **Isolation:** raising `CORE_ALIGNMENT_MIN` to 2.0 (promotion impossible, but the
  same `generate()` code path still runs) → **3/3 pass, 0 shields**. So the cause is
  the **promotion itself**, not RNG perturbation from the alignment computation.

Mechanism: CORE promotion makes the value's **symbol sacred** in the registry
(`promote_to_sacred` → `GovernanceConstants.sacred_ids`). The promoted symbols are
**common tokens** the sources send every cycle (`witness`, etc.). A source that then
includes that token in normal input trips `SACRED_SHIELD` (mutation-of-sacred) and
takes a **trust penalty**; the penalties accumulate and collapse the source to the
TOXIC floor (0.1) → the exact cascade the guard protects against. It is
nondeterministic only because *whether* a value crosses the CORE threshold within
500 steps is nondeterministic (substrate torch/uuid nondeterminism).

## The real issue (architect call)
The architecture conflates two things the fix made collide:
- **Sacred** = boot constants (ANCHOR/RECURSION/HOMEOSTASIS) that sources never send
  → `SACRED_SHIELD` + trust penalty is correct (real attack).
- **CORE** = a value *promoted from a source's own legitimate contributions* → the
  contributing sources send that token constantly. Penalizing their trust for
  *referencing* a concept they helped sanctify is wrong.

`SACRED_SHIELD` should still **block modification** of a CORE symbol, but the **trust
penalty** must distinguish "attempting to mutate a sacred symbol's identity" (attack)
from "including a now-sacred token in normal input" (legitimate reference). That is a
governance-layer design decision — not a constant tweak — so it is owed its own work.

## Status
Reverted in this PR; the dead-gate limitation (CORE unreachable) is restored as the
**stable** state. The ⊘ coherence-axis v0.3 fix (independent, in `integrity_read`)
**stays** — it shares the alignment idea but does not promote anything to sacred.

## Next (the CORE fix, done right)
1. Decide how `SACRED_SHIELD`'s trust penalty treats normal reference of a CORE token
   (e.g., no penalty for a source in the symbol's `contributing_sources`; or CORE
   symbols get dissolution-immunity without mutation-attack trust penalties).
2. Re-apply the v0.3 alignment gate on top of that.
3. Re-run `manipulation_cascade` ×N for stability before merge.
