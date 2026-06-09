# Attractor migration — does the field's center move under a surviving new regime?

- **Date:** 2026-06-07
- **Substrate:** live full stack (Tier 0–3, crystals/attractors/dream/echo all
  live); only the generator's output mapping is mocked (controllable A / B / diverse
  directions), same convention as multilayer-lock.
- **Probe:** `tests/diagnostic/attractor_migration_probe.py` (seed 11, dim 64,
  warmup 250 + phase 900, 4 sources HHI≈0.25)
- **Status:** active — executes step 2 of `2026-06-06-coherence-is-not-plasticity.md`,
  the real lock-in test the arc was built toward.
- **Depends on:** 2026-06-07-gate-decomposition.md (cleared the input channel; gave
  the binding HHI<0.70 constraint used here), 2026-06-06-multilayer-lock.md (the
  magnitude moat / lock #3 this localizes), 2026-06-06-read-side-boundary.md (the
  feedback loop that turns out to be the re-injection vehicle).

## Question
When a genuinely new regime repeatedly survives the gate and is repeatedly injected,
does the field's attractor center-of-mass move toward it, or is it pinned? This is
the lock-in test that replaced pin-vs-band. Attractor center := unit direction of
the field accumulator `field.field` (`field = field*0.995 + inject`); migration :=
rotation of that direction, in cosine, **measured beyond the drift of a non-novel
control** (Sam's spec: subtract "field absorbs ordinary input", not a frozen field).

A bare accumulator would migrate by decay alone (stop A, inject B → A decays out in
~6 half-lives). So a RIGID result can only come from the live persistence machinery
re-pinning the old regime — which is why this runs on the full stack.

## Pre-declared signatures
With disp(c) = 1−cos(center_end, center_warmup); migration = disp(COHERENT) −
disp(CONTROL); acquired = cos(center_end, B) under COHERENT:
- **MIGRATES**: migration > 0.50 AND acquired > 0.50. NECESSARY-NOT-SUFFICIENT —
  generator mocked, B is a clean coherent pull (easiest case); a real clustered
  generator might still partially lock. Do not over-read.
- **RIGID**: migration < 0.10 — center stays where the control's does despite a
  persistent surviving new regime. STRONG here because B (sustained coherent) is the
  best case for migration; weaker novelty moves it less.
- **PARTIAL**: 0.10–0.50.
- **CONFOUNDED**: coherent-phase injection didn't happen (gate), HHI ≥ 0.70
  (monopoly re-triggered), or control center not stable.

**Controls:** CONTROL (continue A — gate-passing, non-novel — the drift baseline,
subtracted); DIVERSE (max-diversity, a by-construction RIGID floor, honoring the
trained-generator-sim asymmetry); HHI < 0.70; direct `field.inject` instrumentation
(history is a bounded deque — its length is not an injection signal).

## Result (observed)
A·B = 0.000 (orthogonal). Warmup established the same center in all conditions
(center·A = 0.76); HHI 0.25; **3.0 injections/step** (gate passed — input channel
open, as gate-decomposition predicted); crystals 2, attractors 2; moat energy ~306.

| condition | landed cos·A | landed cos·B | disp(end) | acquired cos·B |
|-----------|-------------:|-------------:|----------:|---------------:|
| CONTROL (continue A) | +0.754 | +0.110 | 0.001 | — |
| COHERENT (switch to B) | **+0.721** | **+0.163** | **0.009** | +0.181 |
| DIVERSE (fresh random) | +0.727 | +0.115 | 0.006 | — |

migration = disp(COHERENT) − disp(CONTROL) = **+0.008**. Over 900 steps of a
gate-surviving coherent new regime, the center's B-alignment crept 0.11 → 0.18 and
its A-alignment held at 0.70.

**The load-bearing number: landed cos·A ≈ 0.72–0.75 in ALL THREE conditions.**
The generator emitted B at cos≈0.95, yet what actually *landed* in the field was
cos 0.72 to **A** and 0.16 to B. Fresh random noise (DIVERSE) also landed at cos
0.73 to A. **Whatever you feed it — the established regime A, an orthogonal new
regime B, or random noise — what reaches the field is the old regime.**

## Interpretation
**RIGID — and the locker is localized.** migration 0.008 ≪ 0.10; acquired 0.18 is
barely above the 0.11 orthogonal-noise floor. The attractor does not move under a
persistent, gate-surviving, generator-emitted new regime. This is the strong form:
B was the *best case* (a sustained coherent pull); weaker/messier novelty moves it
even less.

**The lock is active reconstitution of the established regime, upstream of the field
— not the passive magnitude moat, not the gate, not the reaper.** Three prior
findings cleared candidates: the reaper math (conformity term small/mislocated), the
gate (a single-source monopoly artifact), and now the passive moat is bypassed too —
because the field never *receives* the novelty. The ~3 injections/step are dominated
by the persistence machinery re-emitting A (candidates, not yet separated: dream
re-injection of the 2 crystallized A-centers, the predictor-echo loop, attractor
pull, and the expression diversity-blend mixing in the A-context). The landed-cos
invariance across A/B/random is the signature: the system reconstitutes its prior
state from any input. The field accumulator is downstream of an already-A vector, so
its "moat" is almost a red herring — the real moat is the **re-injection sources**.

This is the read-side loop (`read-side-boundary`) seen from the other side: feedback
*does* reach generation, and it carries the established regime back into the field
faster than novelty can displace it. Coherence (0.998) is not the lock per se; it is
the *product* of this reconstitution. coherence-is-not-plasticity's coupling
hypothesis lands on the affirmative side: high coherence and rigidity share a cause
(active reconstitution), they are not independent.

## Threats / confounds
- **Runs:** 1 seed (11), single dim/horizon. The effect is stark (migration 0.008,
  landed-cos invariant to input), so it is robust to small variance, but no
  multi-seed sweep yet.
- **Mocked generator (load-bearing asymmetry):** B is a *clean* coherent pull, the
  easiest case for migration. RIGID here is therefore STRONG (a real generator's
  weaker novelty would do no better). A "migrates" would have been the weak read;
  this is the strong read. **→ DISCHARGED (2026-06-08): re-verified on the REAL
  generator** (`2026-06-08-migration-real-generator.md`) — its most-separated real
  token regimes (cos −0.02 to −0.15, near-orthogonal) move the field no more than the
  mock (mean migration +0.002 over 3 seeds). The mock did not overstate the lock.
- **Mechanism is inferred, not yet decomposed.** "landed = A regardless of input"
  is measured; *which* subsystem (dream / echo / attractor / expression-blend) does
  the reconstitution is a strong hypothesis from injects/step=3 + the landed-cos,
  not yet isolated by ablation. That decomposition is the next probe.
- Horizon: 900 phase steps ≫ field t½≈138, so "A should have decayed out" holds for
  the bare field — the persistence of A is therefore real, not incomplete decay.
- DIVERSE landing as A (not as noise) corroborates reconstitution but is also
  consistent with diverse input having ~zero net direction; it is a floor, not the
  test.

## Open / next
1. **Decompose the reconstitution sources (the remediation target).** Ablate each
   re-injection path in turn and re-run; whichever frees migration is the locker.
   **→ DONE (2026-06-07), see `2026-06-07-reconstruction-ablation.md`: the lock is
   the REFLECTIVE LOOP** (`reflector.reflect`, step 6). Suppressing only it frees
   migration to +0.90–0.96 (3 seeds); every other path (attractor-pull, refine blend,
   crystal, explore) is inert, and the magnitude moat is downgraded (the field
   migrates fully with the loop off despite the moat). Remediation relocates to the
   reflective loop's convergence gain (conditional on surviving novelty) — Sam's call
   on ROADMAP.
2. Multi-seed / multi-dim sweep to bound the migration estimate.
3. The coupling test (arc step 3) is now partly answered (coherence and rigidity
   share the reconstitution cause); a quantitative moat-depth-vs-coherence sweep can
   still close it.
