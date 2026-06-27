# Ground-truth pass 3: evaluate the composed engine BEFORE wiring the operators

- **Date:** 2026-06-20
- **Spec:** n/a (runtime evaluation at production config)
- **Status:** active — an evaluation pass requested by Samuel ("look at the stack
  first and evaluate before wiring anything"). Graduated composed engine (Tiers 0–3,
  pretrain + novelty attenuation), dim 128, 800 steps. Numbers from running it.

## Healthy (verified)
- **Tier 1 trust:** allow_rate 0.99; trust discriminates (an attacker was 82 %
  quarantined and trust-floored in the pass-2 check). Clean sources sit at 5.0.
- **Tier 3 emergence:** 33 values, **17 reached STRONG**, identity-anchored
  (`witness / identity / continuity / anchor / recursion / homeostasis` all at 5.0),
  **zero dissolutions** over the run — steady maturation, no churn.
- **Metastability monitor:** `metastable`, 5 regimes, 0.625 — working (an earlier
  "None" reading was a key-name bug in the eval script, not a defect).
- Loosening active (coherence ~0.93 vs 0.97 bare); HHI 0.28 LOW; no crashes.

## HIGH — two structural cracks under the value layer
**1. CORE promotion is impossible.** `SelfhoodGovernance.review_core_promotion`
(line 502) hard-rejects any candidate with `coherence_contribution < 5.0`. But
`coherence_contribution` is the lifetime sum of *marginal* `coherence_impact`, which
is structurally ≤ 0 in a saturated field (measured: 100 % negative, mean −0.6 to
−1.3). So **no value can ever pass the gate** — the entire CORE tier is unreachable,
and the value arc (emergent → … → STRONG → CORE/sacred) can never complete. This is
the **same dead signal** that broke the ⊘ cc-axis, and it wants the **same fix**:
gate CORE on absolute field-alignment, not the marginal sum. (In the 800-step run the
strongest values reached `consec_core_eligible = 6/10` — they would hit 10 with more
steps and then be silently rejected here forever.)

**2. The rhythm router is pinned to one mode.** Field energy at dim 128 runs
**mean 180, max 284**, but the rhythm bands top out at `explore ≥ 5`
(`stabilize < 0.5 · dream 0.5–2 · reflect 2–5 · explore ≥ 5`, `configs/field.yaml`).
So energy is ~36× above the top threshold and rhythm is **99 % `explore`**;
`dream / reflect / stabilize` are effectively unreachable. Consequences:
- **Dreams never fire** (0 in 800 steps) — the dream-cycle consolidation /
  crystallization pathway is dead, and `dream_reinforced` (a CORE promotion
  criterion) can never accrue.
- "Routes behavior by cognitive rhythm" — a stated core function — collapses to a
  single rhythm. The thresholds were calibrated for a small/normalized energy scale
  that the dim-128 field does not occupy. Either the bands or an energy
  normalization need to match the real distribution.

Both cracks are the same theme: **constants/signals calibrated for an idealized
field (small energy, positive marginal coherence) that the real saturated dim-128
runtime violates.**

## MEDIUM — the relational layer is shallow
Only **2 of 4 sources bonded**, both **`transactional`** (the weakest type, ×0.70).
The dominant source `source_samuel` (313 interactions — the most) **never bonds**:
its `crystal_count = 0`, so it fails the formation gate (`crystals ≥ 1`) despite
saturating interaction count. Bond *depth* (intellectual / emotional / existential)
never emerges over 800 cooperative steps. Worth understanding why the highest-traffic
source crystallizes nothing.

## Recommendation (before any operator is wired)
The operators sit on top of the value layer. Fix the two HIGH cracks first:
1. **CORE coherence gate → absolute field-alignment** (port the v0.3 ⊘ fix to
   `review_core_promotion`), so the value arc can complete.
2. **Rhythm energy calibration** — rescale the bands (or normalize field energy) to
   the real dim-128 distribution, so dream/reflect/stabilize are reachable and the
   dream pathway lives.
Then re-evaluate, then wire A/B/⊘ onto a stack whose own arc actually closes.
The relational-depth question is medium and can follow.
