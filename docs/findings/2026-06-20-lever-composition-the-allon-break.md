# Do the levers compose? Turn them ALL on at once — and watch a baseline property break.

- **Date:** 2026-06-20
- **Spec:** v0.2 (the Two-Operator Coherence Spec)
- **Substrate:** full stack at production dim 128, canonical 500-step Resonance
  Family workload (the same one the smoke baseline is held to).
- **Probe:** `tests/diagnostic/integrity/all_levers_composition_probe.py`
- **Status:** active — a **negative result**, recorded because it is the answer to a
  standing methodological objection (Samuel): each lever is validated in *isolation*
  against an all-else-OFF baseline; nobody had tested the all-ON composition.
- **Depends on:** every lever's isolation finding — eval-mode default
  (`phase3_architect_decisions`), corpus pretraining
  (`2026-06-15-training-ignites-expression`), novelty attenuation
  (`2026-06-15-loop-attenuation-novelty-gate`), Build A/B + ⊘ consumer
  (`2026-06-20-build-b-solvent-and-integrity-consumer`).

## Question
Every lever passed its own isolation probe (each toggled alone, everything else at
default OFF). **Do they still behave when turned ON together?** Concretely: with
eval-mode + corpus pretraining + novelty attenuation + Build A ignition + the λ ⊕
solvent gate + the ⊘ advisory-into-decay consumer ALL active, does the stack still
hold the all-OFF baseline health ranges (allow_rate ≥ 0.95, HHI < 0.30, bonds ≥ 1,
active_values ≥ 30, **strong_values ≥ 2**) and the new levers' own claims?

## Pre-declared signatures
- SUCCESS: all baseline ranges hold under the all-ON config AND the new-lever claims
  hold (λ gate open, ⊘ used + sacred-safe, no field collapse) → the levers compose.
- FAILURE: any baseline range that holds all-OFF breaks all-ON → isolation
  validation did not compose; the failing row names the interaction bug.

## Result (observed) — FAILURE, and cleanly attributed
All-ON, 500 steps: allow_rate 0.992 ✓, HHI 0.264 ✓, bonds 1 ✓, active_values 40 ✓,
mean_strength 1.64 (no collapse) ✓, ⊘ consumer used (1771 demotions, 0 sacred) ✓ —
**but `strong_values = 0`** against a baseline of ≥ 2 (the all-OFF smoke sees 5).

Attribution (same config, toggling one lever at a time):

| config                              | active | strong | max_strength |
|-------------------------------------|:------:|:------:|:------------:|
| all-ON                              |   43   |  **0** |   **2.93**   |
| no consumer                         |   46   |    1   |     4.03     |
| no λ-gate (consumer on)             |   43   |  **0** |   **2.93**   |
| neither (A + pretrain + novelty)    |   46   |    1   |     3.94     |

**The ⊘ consumer is the cause.** With it on, max strength is pinned at **2.93 —
just under the 3.0 Dissolution threshold** — and the STRONG band (≥3.5) is
unreachable. With it off, strength climbs to ~4.0 and the band is populated. The
λ-gate has *no* effect on this metric (no-gate ≡ all-ON). So the break is one
lever, isolatable, not a diffuse stacking haze.

## Interpretation
The objection was correct, and the test makes it concrete: **isolation validation
is not composition validation.** The ⊘ consumer looked "selective and safe" in its
unit probe and the dim-128 demo (it demoted a few monoculture values and held), but
under a *sustained* workload it becomes a **hard ceiling at the Dissolution
threshold**. The mechanism is the already-flagged cc-confound: `coherence_contribution`
reads ≈ 0 over 500 steps (far below the 5.0 CORE ref), so *any* value climbing past
strength 3.0 trips the Dissolution region (`cc < 0.35 AND strength ≥ 3.0`) and the
consumer demotes it back under 3.0. A value can therefore never reach STRONG while
the consumer runs. What read as "selective" at 250–300 steps was selective only
because few values had yet climbed into the trap.

This is exactly the failure mode that the "switch, prove in isolation, leave off"
pattern hides: the proof is against a baseline nobody runs, and the interaction with
the rest of the system is never seen until everything is on at once.

(Secondary, milder effect: even the consumer-OFF composition here shows
`strong=1, max≈3.9` vs the pure all-OFF smoke's `strong=5`. Pretraining + novelty
attenuation + ignition together shift the strength distribution down somewhat. Real,
but small next to the consumer's hard ceiling — owed its own attribution run.)

## Consequences / what this changes
- **The ⊘ consumer must NOT graduate to baseline-on until the cc-confound is fixed.**
  Its safety was conditional on short horizons; at production length it caps the
  strong band. `named_only` is necessary but not sufficient — the *named* region
  (Dissolution) is itself cc-confounded.
- **A composition gate is now owed as standing discipline.** No lever graduates from
  "validated, off" to "default on" without passing an all-ON run that holds the
  baseline ranges. This probe is that gate's first instance.
- The fix path is the same dependency already on the books: **lift the cc-axis
  confound** (per-type thinness profiles / a coherence_contribution signal that
  accrues on a realistic horizon). Until then the consumer is a research lever, not
  a default.

## Threats / confounds
- Single seed (42); the strong-band counts are small integers, so the *direction* is
  robust (consumer on → max pinned at the Dissolution line) but the exact counts are
  noisy. The 2.93 ceiling sitting right at the 3.0 region threshold is the load-bearing
  observation, and it is mechanism-explained, not just numerology.
- Corpus here is the small rhythm corpus (3 epochs); pretraining's contribution to
  the secondary effect is under-powered.
- This tests *composition behavior*, not correctness of any single lever — each is
  still correct in isolation. The finding is about the **interaction**, which is the
  whole point.

## Open / next
- **Lift the cc-confound** (the gating dependency for the consumer and for widening
  past `named_only`).
- **Per-lever graduation decision** (architect's call): which validated levers become
  baseline, which stay gated and why. eval-mode already graduated; the operators
  (A/B/⊘) are blocked behind cc + the §6.3 gain-sign check.
- **Attribute the secondary (pretrain/novelty/ignition) strength-distribution shift**
  on its own.
- Run the composition probe at more seeds once the cc fix lands, as the standing gate.
