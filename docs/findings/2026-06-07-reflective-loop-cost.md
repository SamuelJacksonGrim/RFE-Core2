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
- **Cliff confounded by the bug.** The band (0.6–1.0) is clean and trustworthy; the
  cliff (≤0.5) is manip-flood + a crash bug, so "where identity truly collapses" is
  not cleanly located. Fix the attractor bug and re-run to sharpen the cliff edge
  (it sits between 0.5 and 0.6).
- Single seed (11), one dim/horizon. The band's monotone plasticity rise and silent
  manip/stable identity are consistent, but no multi-seed sweep yet.
- The band is **narrow** (cliff at ~0.5–0.6): gain 0.6 is near the edge. A finer
  sweep (0.55–0.65) post-bugfix would establish margin.
- Mocked generator; B is a clean coherent pull. Identity metrics are a subset
  (witness scalar + coherence + manip-rate + counts); other identity facets unmeasured.

## Open / next
1. **Fix the `attractor.merge_pass` bug** (separate substrate PR, architect's nod),
   then re-run to characterise the true cliff and the band's margin.
2. **Draft the Fix-2 reframe WITH these numbers** for the architect: *bounded
   conditional attenuation of the reflective loop's convergence gain toward ≈0.6,
   gated on persistent-novelty-surviving*, with the manipulation-signal rate and the
   adversarial convergence guard as safety rails. ROADMAP still unedited on direction.
3. Multi-seed + finer-gain sweep once the bug is out of the way.
