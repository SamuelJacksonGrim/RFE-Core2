# Fix 0-B — survival stops being bought purely by coherence: the diversity fitness term + the leaky ratchet (opt-in)

- **Date:** 2026-07-18
- **Substrate:** untrained `tests/_common.build_full_stack()` full Tier 0–3
  stack (dim 64, CPU), Resonance Family workload, standard determinism
  discipline (seed 42), paired lever-OFF/lever-ON arms
- **Probe:** `tests/diagnostic/lockin/fix0b_currency_census_probe.py` (new —
  the measure-first ruler), `tests/diagnostic/lockin/fix0b_effect_probe.py`
  (new — paired arms, pre-declared signatures),
  `tests/integration/fix0b_invariants.py` (new, CI-gated, 14 checks)
- **Control:** the lever-OFF arm (identical seed/workload) throughout; the
  effect probe's E1 band is two-sided (a dead term AND a takeover both
  FAIL — the counterweight must neither vanish nor become the new
  currency)
- **Status:** active — mechanism validated at harness scale; **opt-in**
  (`fix0b_diversity_fitness` / `fix0b_binding_leak`, default OFF) pending
  the composed-runtime gates before any graduation

## Question

BACKLOG §1 / `docs/lock_in_remediation_plan.md` §Fix 0-B (highest-leverage
lock-in item): wire the Fix 1 metastability score into the reaper's
reinforcement formula as a fitness term so survival stops being currencied
purely by coherence, and give reinforcement a demotion path (Fix 0-C
mechanism — the one-way ratchet becomes leaky). What does the currency
actually look like today, and does the counterweight land without breaking
the governance economy?

## Census first (measure before change)

The 800-step currency census established three facts the design rides on:

1. **Tenure is bought by coherence-laundered bindings.** attractor_strength
   (38–44% share) + crystal_binding (41–52%) dominate reinforcement —
   both downstream of coherence-gated processes (attractors ≥ 0.88
   composite, crystals ≥ 0.75 coherence). Direct field_coherence is small
   (2–3%) but the lean is real, laundered one layer up.
2. **The shipped novelty counterweight is structurally dead** — fourth
   organ of the F7/F8/F9 saturated-field disease: per-symbol
   `field_coherence` pins ~0.96, so `novelty = 1 − field_coherence ≈ 0`
   by construction. It cannot fire, at any weight.
3. **The stream-level signal is alive.** On the stage-C expression stream,
   `credit = (1 − regime occupancy) × metastability` reads p50 0.233 / p90
   0.532 — the first healthy counterweight currency measured in this arc.
   Weight sizing fell out of the census twice independently: the weight
   each measured class needs for a p90-credit symbol to counterweight
   ~25% of its dominant component is **k = 8.7 × crystal_binding_weight**
   (language 1.3/0.15 ≈ ephemeral 0.26/0.03).

## Mechanism (as built, both levers default OFF)

- **Fitness term** (`fix0b_diversity_fitness`): the stage-C
  `StreamMetastabilityMonitor` gains opt-in incremental regime tracking
  (same clustering rule as `_cluster_configs`, O(k·dim)/step, bounded);
  each step the cycle reads `diversity_credit()` — from OUTSIDE the
  monitor, the plan's sanctioned read path — and EMAs it into the step's
  tokens (`SymbolState.diversity_credit`, [0,1], α=0.05). The EMA is
  **unconditional**, so conformist steps pull credit DOWN (the fitness
  signal is itself leaky, never a second ratchet), and rate beats volume
  (EMA, not a sum — traffic cannot buy the credit). `DecayProfile` gains a
  `diversity_weight` slot (0.0 in every shipped profile);
  `SymbolRegistry.set_diversity_weights(k=8.7)` builds PRIVATE per-registry
  profile copies — module-level DECAY_PROFILES are never mutated.
- **Leaky ratchet** (`fix0b_binding_leak`, the Fix 0-C mechanism): on each
  decay pass, bindings of symbols unrefreshed since the previous pass leak
  multiplicatively (suggested 0.10/pass). Sacred / protected / SPECIAL are
  exempt — the reaper cannot touch them and neither can this.

## Result

**Invariants gate 14/14** (OFF byte-identical; monitors observe-only with
a structural import check; credit bounded/leaky/volume-blind; calibrated
scale verified; leak touches only the unrefreshed, never the exempt).

**Paired effect probe 3/3 pre-declared signatures:**

| | OFF (control) | ON |
|---|---|---|
| diversity share of reinforcement | 0.0% | **15.5%** (declared band 5–40%) |
| injection_rate / quarantines | 1.000 / 0 | 1.000 / 0 |
| stale binding mass (lag > 150) | 401.80 | 400.60 (strictly lower) |
| population / coherence mean | 49 / 0.899 | 49 / 0.898 |

The counterweight lands in-band without taxing the governance economy or
moving the trajectory. The leak's magnitude at harness scale is honestly
small: the 16-phrase workload re-touches almost every symbol between decay
passes and any touch refreshes — only the genuinely dead leaked. Real
long-run churn is where the demotion path has teeth.

## Found along the way (the bigger fish)

1. **The reaper economy is DORMANT at harness scale.** `decay_step()` runs
   only every `decay_interval`-th (10) maintenance call, and maintenance
   fires every 200 cycle steps — first selection pass at cycle step
   ~2000. **Every 500–800-step suite/baseline run in this repo's history
   has executed zero reaper passes** — the survival economy Fix 0-B
   modifies was never exercised by the regression gates (the census's
   all-'active' reaper histogram said this quietly). Same family as the
   runtime-is-Tier0-only trap. Filed in BACKLOG: the suite needs a
   decay-exercising gate; the effect probe sets `decay_interval=1` in
   both arms meanwhile.
2. **Metric correction, recorded per discipline:** the effect probe's E3
   was first declared on stale-bound *count* and failed (25→28) — a
   count-based observable is structurally unable to fall under a
   multiplicative leak (strength never reaches 0) while the fitness term
   legitimately retains more live symbols. Re-declared on stale binding
   *mass* (what the leak actually moves) with the first declaration and
   its failure kept on record here and in the probe docstring.

## Threats / limits

- Harness-scale only so far: untrained dim 64, 800 steps, 4 decay passes.
  The composed pretrained runtime (richer regimes, real churn) is where
  both the credit distribution and the leak magnitude should be
  re-measured — required before any graduation talk (all-ON composition
  gate + adversarial arm, per the standing rule).
- "Refresh" = any touch (`last_seen_step`). A trivially-touched zombie
  keeps its bindings; a stricter refresh criterion (e.g. reinforcement
  above a floor) is an architect-overridable design choice, recorded not
  built.
- The k = 8.7 constant is census-calibrated at dim 64; re-derive from a
  dim-128 census before trusting it there.

## Open / next (filed in BACKLOG §1)

- Composed-runtime arms (all-ON composition + adversarial) with both
  levers ON — the graduation bar.
- Suite-level decay-exercising gate (the dormant-reaper gap).
- Fix 0-A (reinforcement → field) remains separately gated by §6.3.
