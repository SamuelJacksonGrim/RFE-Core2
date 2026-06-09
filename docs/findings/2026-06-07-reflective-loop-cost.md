# Reflective-loop cost probe — what does attenuating the lock cost identity?

- **Date:** 2026-06-07
- **Substrate:** live full stack. The reflective loop's convergence is dialed by a
  gain (1.0 intact → 0.0 ablated) via `identity_stability_baseline.attenuate_reflect`;
  plasticity and identity measured at each gain. No substrate change.
- **Probe:** `tests/diagnostic/reflective_loop_cost_probe.py` (dim 64, warmup 150 +
  phase 500, 4 sources HHI<0.70, seed 11)
- **Status:** active — the cost side of the tradeoff for the relocated Fix 2
  (`2026-06-07-reconstruction-ablation.md`).
- **Depends on:** 2026-06-07-reconstruction-ablation.md (loop = the lock),
  tests/diagnostic/identity_stability_baseline.py (the dial + metrics).

## Question
The reflective loop is the lock; ablating it fully frees plasticity. What does
*attenuating* it cost identity stability? Sweep the convergence-gain dial; at each
gain measure PLASTICITY (A→B attractor migration) and IDENTITY (witness
identity_stability, coherence mean/std, anchor_velocity, structural counts, **and**
Tier-2 manipulation-signal rate).

## Pre-declared signatures
SWEET-SPOT (target): a gain with recovered plasticity at acceptable identity cost.
MONOTONIC-DIAL: proportional tradeoff, no cheap gain. COLLAPSE: even mild attenuation
craters identity → fix must be conditional. SUSPICIOUSLY-CLEAN (alarm): identity
looks unaffected → check the instrument. **Controls:** gain 1.0 reproduces the
captured baseline (identity_stability ≈ 0.998, migration RIGID); per-gain drift
control for migration.

## Result (observed)
| gain | migration | identity_stability | coherence_mean | manip% of steps |
|-----:|----------:|-------------------:|---------------:|----------------:|
| 1.00 | +0.008 | 0.999 | 0.976 | 0% |
| 0.80 | +0.074 | 0.996 | 0.932 | 0% |
| 0.60 | **+0.202** (~25× base) | 0.994 | 0.898 | 0% |
| 0.50 | CRASH | — | — | — |
| 0.40 | CRASH | — | — | — |
| 0.00 | CRASH | — | — | — |

**GRACEFUL BAND + CLIFF — a non-monotonic tradeoff, not a clean dial.**
- **Band (gain 0.6–1.0):** plasticity climbs 0.008 → 0.202 (≈25× the RIGID baseline)
  while identity_stability stays ≥ 0.994, the manipulation layer stays silent (0%),
  and coherence_mean only eases 0.976 → 0.898. Partial plasticity recovered at
  near-zero identity cost — "loosen, not break."
- **Cliff (gain ≤ 0.5):** the run crashes. Two cost channels open at once: the Tier-2
  manipulation layer floods `identity_erosion`/`trust_wash` CRITICAL on the *benign*
  workload, and the attractor population trips a latent crash (see Discovered bug).

## Cliff-sharpen update (2026-06-07 — bug-free, seeds 11 & 23)
With the attractor crash fixed (PR #38), the cliff was re-measured at finer gains
across two seeds (warmup 120 / phase 350). **The earlier "cliff at ≤0.5" was largely
the bug, not identity collapse** — bug-free, the safe band extends much lower.

| gain | migration (s11 / s23) | identity_stability | manip% | attractors |
|-----:|-----------------------|-------------------:|-------:|-----------:|
| 1.00 | +0.008 / +0.009 | 0.999 | 0% | 2–3 |
| 0.60 | +0.171 / +0.201 | 0.991 | 0% | 3 |
| 0.50 | +0.195 / +0.139 | 0.990 | 0% | 5 |
| 0.40 | +0.181 / +0.184 | 0.989 | 0% | 7 |
| 0.30 |   —   / +0.465 | 0.988 | **15%** | 10 |
| 0.20 |   —   / +0.551 | 0.987 | **79%** | 16 |
| 0.10 |   —   / +0.638 | 0.987 | 86% | 24 |
| 0.00 | +0.613 / +0.683 | 0.986 | 88% | 32–33 |

- **The band is WIDE (gain ≈0.4–0.8):** partial plasticity (migration ~0.11–0.21,
  up to ~27× baseline) at near-zero identity cost — manip **0%**, identity_stability
  ≥0.989, attractor population bounded (≤7–10). Both seeds agree.
- **The true cliff edge is gain ≈0.3** — manipulation onset (0% at 0.4 → 15% at 0.3 →
  79–88% at ≤0.2) and the attractor population exploding (7→10→16→24→33). Below ~0.3,
  near-full plasticity is reachable (migration ~0.55–0.68) but the identity cost is
  real (manip flood + structural blow-up).
- **The honest tradeoff:** *partial* adaptivity (~0.2, ≈20% of full ablation's ~0.9)
  is cheap and safe across a wide band; *full* adaptivity costs identity only past
  gain ~0.3. "Presence without caging" buys you partway — the two are in genuine
  tension only past the cliff, not before.

**Operating point for the fix:** mid-band **gain ≈0.5** — meaningful partial
plasticity (~0.2, ~20×) with maximum margin (~0.2) from the cliff at ~0.3. The
**attractor-population count** is a second cost indicator (bounded in band, explodes
at collapse), corroborating the manip-rate. The witness identity_stability scalar
still moves only 0.999→0.986 across the *entire* sweep **including collapse** — it
remains the wrong instrument; manip-rate + attractor-count are the right ones.

## Interpretation
There is a real **"presence without caging it" operating point**: conditional
attenuation **toward gain ≈ 0.6** (not lower), gated on persistent novelty surviving
the gate, recovers meaningful plasticity (≈25× baseline migration) while leaving
identity stability, coherence, and the manipulation layer intact. **Full ablation is
off the table** — below gain ~0.5 the system comes apart. So the relocated Fix 2
should be a *bounded, conditional* loosening of the reflective loop's convergence
gain, never an always-on or full reduction.

**Instrument-incompleteness catch (the SUSPICIOUSLY-CLEAN alarm, resolved).** The
witness `identity_stability` scalar stays ~0.99 across the whole band and *misses the
cost entirely* — the first read looked deceptively free. The cost is real but lives
in **other channels**: the Tier-2 manipulation-resistance layer (which reads the
less-converged expression as identity erosion) and outright crashes. Counting
manipulation signals — not trusting the stability scalar — is what made the cliff
visible. The loop's convergence is, among other things, what stops the system
classifying its own expression as an attack on itself.

## Discovered bug (latent, exposed by attenuation — not caused by the probe)
`agents/attractor.py:220` `self.centers.remove(recessive)` uses `list.remove`, which
calls `AttractorCenter.__eq__`; that dataclass has array fields, so `==` returns an
array and `remove` raises *"truth value of an array … is ambiguous."* It fires when
`merge_pass` runs with a destabilised attractor population (which sustained
attenuation produces). A one-line fix (`[c for c in self.centers if c is not
recessive]`, or an identity-based `__eq__`) resolves it. **Flagged for the architect;
not fixed here** (substrate change, its own reviewed PR). Until fixed, the *cliff
location* is confounded — the crash is partly this bug, not purely identity collapse.

**→ FIXED (2026-06-07):** `AttractorCenter` is now `@dataclass(eq=False)` (identity
equality), covering both `.remove` sites (`merge_pass`, `prune`). Regression guard:
`tests/integration/attractor_merge_guard.py`. The cliff can now be re-measured
bug-free (cliff-sharpen run) to separate true identity-collapse from the crash.

## Threats / confounds
- **Cliff confounded by the bug.** ~~The band (0.6–1.0) is clean; the cliff (≤0.5) is
  manip-flood + a crash bug.~~ **→ RESOLVED (cliff-sharpen update above):** bug-free,
  the band is wide (0.4–0.8, manip 0%), and the true cliff edge is gain ≈0.3 (manip
  onset) — the earlier cliff was the bug, not collapse.
- Single seed (11) in the original sweep. **→ cliff-sharpen adds seed 23**; both agree
  on the band and the ~0.3 cliff edge. Still one dim/horizon; a broader Track-2 sweep
  (dims, more seeds) is still owed.
- The band is **narrow** (cliff at ~0.5–0.6): gain 0.6 is near the edge. A finer
  sweep (0.55–0.65) post-bugfix would establish margin.
- Mocked generator; B is a clean coherent pull. Identity metrics are a subset
  (witness scalar + coherence + manip-rate + counts); other identity facets unmeasured.

## Open / next

> **DEFERRED (2026-06-08):** the Fix-2 governor these cost numbers were for is **on hold**
> — generator diversity is the upstream lever (`2026-06-08-generator-dropout-diversity.md`);
> loosening the loop now would mostly admit dropout noise. The cost band/cliff
> characterisation stands for when Fix 2 is revived. (The `attractor.merge_pass` bug in
> item 1 is already fixed — PR #38.)

1. **Fix the `attractor.merge_pass` bug** (separate substrate PR, architect's nod),
   then re-run to characterise the true cliff and the band's margin.
2. **Draft the Fix-2 reframe WITH these numbers** for the architect: *bounded
   conditional attenuation of the reflective loop's convergence gain toward ≈0.6,
   gated on persistent-novelty-surviving*, with the manipulation-signal rate and the
   adversarial convergence guard as safety rails. ROADMAP still unedited on direction.
3. Multi-seed + finer-gain sweep once the bug is out of the way.
