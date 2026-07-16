# Bond formation as accumulation-to-bound — the quality gate becomes a leaky asymmetric DDM (opt-in)

- **Date:** 2026-07-16
- **Substrate:** (a) synthetic evidence streams (no substrate — unit arm);
  (b) untrained `tests/_common.build_full_stack()` full Tier 0–3 stack,
  Resonance Family workload, paired lever-OFF/lever-ON arms at dim 64 and
  production dim 128, standard determinism discipline (seed 42)
- **Probe:** `tests/integration/bond_ddm_invariants.py` (new, CI-gated),
  `tests/diagnostic/calibration/bond_ddm_synthetic_probe.py` (new — the
  pre-declared acceptance battery), `bond_ddm_live_probe.py` (new — paired
  OFF/ON live arms + the §6.3 reachable-range tripwire)
- **Control:** three built-in falsifiers in the battery (an
  `trust_asymmetry=1` unwired control, a near-zero-noise
  threshold-in-costume control, a trial-shuffle corCE control — each must
  FAIL the real bar for the run to count), plus the lever-OFF arm as the
  live control
- **Status:** active — mechanism validated; **opt-in until the architect
  sets the final physics constants** (they are his hand, not the system's)

## Question

Architect brief (2026-07-16): replace the instantaneous bond-formation
quality gate with a temporal accumulator — integration-to-bound with leak,
noise, and an asymmetric drift (mechanism lifted from Armstrong & Vlasov,
PNAS 2026; substrate-free mechanism + acceptance signatures only, no
neuroanatomy claimed). Does the mechanism hold on this codebase, and does it
buy the three declared payoffs (structural trickle/burst robustness, native
deny-vs-earn asymmetry, adversarial telemetry)?

## Deviations from the brief (the brief's Claude had no codebase access)

1. **The premise was stale.** The brief targets the
   `coherence_mean ≈ −0.01 vs 0.10` miscalibration — that was resolved
   2026-07-09 from a different side (formation already had the
   `allow_rate` escape; establishment was blocked by growth currency, now
   field-alignment). This build is therefore a **robustness upgrade** to
   the formation gate, not a bug fix.
2. **Evidence driver corrected.** The brief drives drift with per-source
   coherence — the structurally-dead marginal (F7/F8/F9 disease). Drift
   here rides the live signals: absolute v0.3 `field_alignment` on
   injecting decisions (allow full-weight; allow_weakened/monitor at 0.20 —
   weak *positive*, per the attribution rule: ambient systemic weakening is
   not the source's fault), and the trust-penalty magnitudes as negative
   evidence on blocking decisions (reject −0.3 / quarantine −0.5 /
   sacred_shield −1.0) — one shared severity economy.
3. **Placement corrected.** The brief puts `V(t)` in the Generator↔Watcher
   reflective loop. In this codebase bond evidence arrives as
   `GovernanceFeedback` in `RelationalBondManager` — the accumulator lives
   in its pre-bond path, downstream of `arbitrate()`, exactly where the
   instantaneous gate it replaces lived. Nothing about the gate ordering,
   attribution, or trust posture moves.
4. **Scope holds:** the accumulator replaces only the *quality* disjunction.
   The structural formation preconditions (temporal depth, crystal
   footprint) still gate at commit time — an ACCEPT crossing without a
   crystal pins V at the bound (evidence must be *sustained* while the
   footprint catches up) rather than committing early or being forgotten.
   Establishment/demotion untouched (Fix 0-B territory, out of scope).

## Mechanism (as built)

`agents/bond_accumulator.py`, per candidate source, one step per feedback:

```
V ← V + (μ − leak·V) + σ·randn()          (Euler–Maruyama, dt = 1)
μ  = g₊·max(c,0) − g₋·max(−c,0),  g₋/g₊ = trust_asymmetry
V ≥ B_accept → ACCEPT   V ≤ B_reject → REJECT_ACTIVE   steps > T_max → REJECT_TIMEOUT
```

Placeholders (architect-set; calibrated, not decided): `g₊ 0.05`,
`trust_asymmetry 60` (the trust economy's 40–80× band midpoint),
`leak 0.02`, `σ 0.02`, `B_accept 1.0`, `B_reject −0.5`, `V0 0.0`,
`T_max 400`, weak-evidence factor `0.20`. Two designed correspondences:
the minimum crossing time `B_accept/g₊ = 20` steps reproduces the classical
interaction threshold, and the OU stationary noise sd `σ/√(2·leak) = 0.10`
puts the accept bound 5.1 sd above the trickle equilibrium and 5 sd above
pure noise. During calibration the initial weak factor (0.25) left the
trickle gap at 3.9 sd and ~1% of 2000-step trickle trials crossed —
measured, then closed to 0/200 at 0.20. σ is load-bearing the other way
too: `σ = 0` is rejected at construction (a noiseless accumulator is a
threshold in an accumulator costume — the varCE signature cannot exist).

## Result

**Synthetic battery — 13/13 pre-declared signatures, falsifiers behaving
as falsifiers:**

| signature | measured |
|---|---|
| A1 RT (benign mixed stream) | 400/400 accept, mean RT 37.0 steps, sd 5.97, right-skew 0.64 |
| A2 asymmetry (±0.5 evidence) | reject 79× faster than accept; unwired control collapses to 3× |
| S1 varCE | linear rise R² 0.987, slope 2.76e-4 ≈ σ² (4.0e-4); costume control flat (1e-17) |
| S2 corCE | lag corr 0.94/0.86/0.79/0.64 decaying; trial-shuffle destroys it (≈0.00) |
| C1 trickle (sustained weak-positive) | 0/200 bonded over 2000 steps — the leak wins |
| C2 burst (5 max spikes in a dead stream) | 0/200 bonded — one spike moves V by g₊ only |
| C3 structured negative | 200/200 ACTIVELY rejected, median 1 step — a decision, not a timeout |
| C4 noise flood | 0 accepts, timeout modal (200/200) — noise is not betrayal |

C3 vs C4 is the new adversarial telemetry: structured hostility collapses
decisively to the reject bound while pure noise times out high-entropy —
both end in no-bond, but the mechanism now distinguishes them.

**Live arms (dim 64, 800 steps, seed 42):** with the lever ON,
`source_claude` forms through the accumulator at step ~341 (vs ~320
classic when the classic gate fires at all — see below); every formation
is an ACCEPT commitment (candidates retire at commit); trust floors carry
the standard bounded semantics; zero quarantines both arms; and the
composite-coherence reachable range is inside the OFF control's range
(±0.005) — **the accumulator makes no new coherence reachable, so the
standing §6.3 verdict is not re-opened.** The un-bonded sources sit
pinned at `V = B_accept` waiting on their crystal footprint (crystal
starvation in the untrained harness — the known F9 facet), which is the
designed behavior: quality sustained, structure lagging, no early commit.

**Live arms (production dim 128, 800 steps, seed 42):** 5/5. `source_samuel`
forms through the accumulator at step 293 (OFF control: 316 — the DDM is
comparably paced, slightly earlier here because the integral clears while
the classic rate read is still short of its bar); the other three sources
sit pinned at `V = B_accept` awaiting crystals (quality sustained,
structure lagging); composite-coherence reachable range ON
`[0.6400, 0.9725]` vs OFF `[0.6400, 0.9724]` — identical to within 1e-4;
zero quarantines both arms.

**Found along the way — the OFF gate sits on the known wall-clock knife
edge.** Across byte-identical seeded invocations, the OFF control forms
claude's bond in some process runs and not others (allow_rate hovers at
~0.685–0.80 against the 0.80 bar; BACKLOG §7's wall-clock nondeterminism —
time-based flood eviction / timestamp paths — tips it). The DDM arm formed
at step ~341 in every repeat: the integral rides above the jitter that
flips the instantaneous rate read. That is the brief's "wrong variable"
claim showing up unprompted in our own harness.

**Suite:** 18/18 (incl. the new `bond_ddm_invariants` gate, 17 checks),
doc-accuracy 19/19. Lever OFF is the default and consumes no RNG — the
existing baselines are untouched by construction.

## Threats / limits

- The untrained harness's benign traffic is uniformly high-alignment
  (p10 ≥ 0.75), so positive drift is closer to "attendance × quality" than
  a sharp discriminator — same F3 wall as bond growth: no formation
  currency can separate a semantically hostile source at stage A until the
  Wall-1 in-corpus-hostile-vocabulary arm lands. The DDM's defense against
  such a source is the negative-evidence drift (it rides governance
  outcomes, not semantics) and the bound geometry.
- Adversarial patterns are validated on synthetic streams; the live
  adversarial arm (named attacker vs composed runtime, 2026-07-09 harness)
  should be re-run with the lever ON before graduation.
- The accumulator advances one step per the candidate's *own* feedback
  (dt = 1 per-source step), so it is invariant to traffic share — temporal
  depth is per-relationship, not wall-clock. Two consequences to be aware
  of: `T_max` only ever fires for candidates *wandering below the bound*
  (noise); and a candidate pinned at `B_accept` awaiting its crystal
  footprint returns ACCEPT each step and never times out while its
  evidence sustains — deliberate patience, but it means "pinned forever"
  is reachable for a high-quality source that never crystallizes
  (crystal starvation is the known F9 facet, tracked separately).
- Physics constants are placeholders. The asymmetry can be carried by
  drift-gain, bound-distance, or both — currently drift-gain only.

## Open / next (filed in BACKLOG §1)

- Architect sets the final constants and the reset policy; decides
  graduation (all-ON composition gate is the standing bar).
- Re-run the composed-runtime adversarial arm with the lever ON.
- The same DDM shape extends to bond demotion / un-binding (Fix 0-B
  territory) — deliberately not this build.
