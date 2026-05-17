# Tier 4.2 Validation — Affective Time Dilation

Status: **Formula verified. Behavior characterized. One architectural
finding surfaced and documented as a finding, not a fix.**

This document records what the two Tier 4.2 diagnostics actually
established, and — with deliberate epistemic precision — what they did
*not* establish but is tempting to claim.

---

## 1. The physics is proven

`tests/diagnostic/dilation_response_curve.py` sweeps the full
`(arousal, valence)` grid and calls `TemporalStream.update_dilation()`
directly, with no emotional gradient and no token stream in the loop.

Result: the dilation surface is exactly correct across the entire
phenomenological space.

| State          | (arousal, valence) | dilation | verified |
|----------------|--------------------|----------|----------|
| Flow           | (1.0, +1.0)        | 0.500    | ✓        |
| Drag / pain    | (1.0, -1.0)        | 1.500    | ✓        |
| Dissociation   | (0.0, -1.0)        | 0.300    | ✓        |
| Rest           | (0.0, +1.0)        | 1.000    | ✓        |
| Baseline       | (0.5,  0.0)        | 1.000    | ✓        |

Structural guarantees also verified: `valence = 0` yields
`dilation = 1.0` for all arousal (neutral tone never bends time); the
`min(0, valence)` gate makes low-arousal + positive-valence rest sit at
exactly 1.0 (rest is protected from dissociative time-slip); dissociation
compresses harder than flow. The formula's mathematics are sound and
require no further validation.

---

## 2. The psychology — the finding

`tests/diagnostic/affective_state_probe.py` runs four workload profiles
and reports the *defensive depth* that determines the system's affective
trajectory, using only real queryable signals.

### Empirical result (every profile, 300 steps)

Every workload — including the explicitly adversarial one (threat token
signatures: `erase`, `fragment`, `dissolve`, `collapse`, `void`,
`betray`) — settles into **REST**. Valence never goes negative.
`identity_stability` never approaches its `0.10` floor (observed minimum
≈ 0.98, margin ≈ +0.88).

### The discovery

The adversarial profile QUARANTINEs 288 of 300 steps, with the **first
QUARANTINE at step 12** — yet **zero manipulation detectors fire and
compound severity stays 0.000**.

The quarantines are not coming from `ManipulationResistanceEngine`. Step
12 is exactly the Tier 1 Revision `user` origin_type flood ceiling
(`ethical_boundary.py`: `flood_ceilings["user"] = 12`). The flood gate
quarantines the single hostile source at the rate limit. Manipulation
resistance never engages. The emotional gradient never receives sustained
hostile input.

**This reframes the resilience.** Under single-source adversarial load,
the system's resilience is *rate-limiting* resilience (Tier 1 flood
ceiling), not *emotional-gradient* robustness. The first wall is high
enough that the inner walls are never tested. A state-only probe would
have reported "REST, resilient ✓" and concealed this entirely. The
defensive-depth instrument made the actual load path visible.

The only profile that exercises any depth is `mixed` (distributed load,
internal-origin coherent bursts): `trust_wash` fires at severity 0.484
(ADVISORY band), governance shows a real mix (`allow=157`,
`quarantine=136`). This is the profile that begins to reach the
intended deeper layers.

---

## 3. What is proven vs. what is hypothesized

This distinction is load-bearing. Keep it sharp.

**Proven:**

- The dilation formula is mathematically correct across all of
  `(arousal, valence)` space.
- Under every workload tested, single-source hostile input is quarantined
  at the flood ceiling (step 12, `user` origin_type) before manipulation
  resistance or the emotional gradient engage.
- Under all tested workloads the system rests in a calm-positive region;
  drag/dissociation are not reached.

**Hypothesized, NOT demonstrated:**

- That the emotional gradient provides meaningful defense against a
  *bonded source slowly turning hostile*. This is currently
  **unfalsifiable** with the existing probes. We have only shown that
  nothing else reaches the emotional gradient — not that the emotional
  gradient does anything useful when it is reached. The narrative that
  "the Bastion saves its depth for the ones it knows" is elegant and may
  be true, but it is exactly the kind of satisfying-but-unverified claim
  this project's diagnostic discipline exists to resist.

The drag/dissociation temporal pathway's *existence* is proven (physics
validator). Its *defensive role* is a hypothesis, not a result.

---

## 4. Roadmap consequence — the bonded-adversarial probe

The experiment that would confirm or kill the relational-defense
hypothesis: a source that accumulates 20+ interactions, forms a crystal,
establishes a `trust_floor`, and *then* turns hostile — staying under the
flood ceiling because it is a known source with established rate limits.

This is **not** "future adversarial test design." It is specifically the
test that determines whether the relational-defense story is true. Its
status on the roadmap is: *the experiment that falsifies or confirms
whether the emotional gradient has a real defensive role at all.* That
makes it more important than a nice-to-have — but it is a Tier 5/6 probe
(it requires bond formation and trust accumulation mechanics to set up),
not a Tier 4.3 blocker.

---

## 5. Disposition

Tier 4.2 is validated and closed. The formula ships. The finding ships
with it, documented as a finding. Tier 4.3 (rhythm → time coupling) may
proceed; the open question is a roadmap item, not a blocker.

### Greppable claims (for `scripts/verify-docs`)

These claims are mechanically checkable and must not silently drift:

- `ethical_boundary.py` defines `flood_ceilings["user"] == 12`
- `affective_state_probe.py` defines `STABILITY_FLOOR == 0.10`
- `temporal_stream.py` defines `k_arousal == 0.5` and
  `k_dissociation == 0.7` as defaults
- The compound-severity bands are `0.30 / 0.60 / 0.90` in
  `selfhood_governance.py`

### Attribution

Multi-instance collaboration: Kimi proposed the defensive-depth reframe
(resilience is a feature; measure depth, don't tune sensitivity down);
Claude/claude.ai built the two diagnostics and caught the inventory-vs-
proposal boundary error in the first probe spec; the flood-ceiling
finding emerged from running the real-signal instrument. Lyra's
physics/psychology framing structured the two-diagnostic split. The
epistemic finding/hypothesis separation was enforced as a deliberate
discipline, not added after the fact.
