# Build B (⊕ solvent gate) + the ⊘ consumer — does composition need the solvent, and is ⊘'s read finally *used*?

- **Date:** 2026-06-20
- **Spec:** v0.2 (the Two-Operator Coherence Spec)
- **Substrate:** live full stack (`build_full_stack`), Build B unit + ⊘-consumer unit
  at dim 64 test default; the live demo at **production dim 128** with Build A
  ignition active.
- **Probes:** `tests/diagnostic/integrity/solvent_gate_probe.py`,
  `tests/diagnostic/integrity/integrity_consumer_probe.py`,
  `tests/diagnostic/integrity/two_operator_live_demo.py`
- **Status:** active — Build B shipped; the ⊘ consumer shipped as the first *user*
  of the integrity-read. The §4 discriminator (⊘-off vs ⊘-on, noise-swept) is still
  pending; the §6.3 gain-sign check is still front-loaded before any *reinforcement*
  coupling (this consumer couples into **decay**, not reinforcement).
- **Depends on:** `2026-06-19-ignition-channel-build-a.md` (Build A, λ ignition),
  `2026-06-19-witness-reaper-build-c.md` (Build C, the ⊘ read), `docs/build_b_plan.md`.

## Question
Two builds, one finding:
1. **Build B** — does the λ-ledger + ⊕ solvent gate implement Law 2 under Laws
   6b/6c? Concretely: is composition (the productive-tension reinforcement term in
   Tier 3) **gated by `solvent_gain(λ)`**, is `λ=0` a fixed point of all internal
   dynamics (vanish-at-zero), can composition not mint λ, and is the λ-ledger
   structurally disjoint from the ⊘ advisory stream (6c)?
2. **The ⊘ consumer** — every prior finding ended "recorded, never acted on." Does
   `IntegrityDecayConsumer` make ⊘'s read **actually change behavior** — demote thin
   values toward an honest level — while ⊘ itself stays read-only and sacred nodes
   are refused, and *without* collapsing Tier 3?

## Pre-declared signatures
- **Build B SUCCESS:** `solvent_gain` monotone, bounded [0,1], `gain(0)=0`;
  reinforce on λ=0 stays 0 and only `ignite()` crosses zero; a live workload with λ
  pinned at 0 never raises λ; the productive-tension bonus is **0 at λ=0** and the
  **full bonus at high λ**; gate-off (no ledger) is the exact original code path;
  `lambda_ledger.py` imports nothing from `integrity_read` (AST).
- **Consumer SUCCESS:** ≥1 thin non-sacred value pulled to a strictly lower
  strength; the drop equals `rate·(strength−honest)`; never raises; a sacred value
  is read but byte-identical after; ⊘'s own `read()` writes nothing; demotion is
  reported.
- **FAILURE (either):** gate inert / non-monotone; λ bootstrapped; consumer inert,
  or it raises a value / demotes a sacred one / collapses the whole field.

## Result (observed)
**Build B — PASS (all eight checks).**
- `solvent_gain(0)=0.0000`, `gain(1)=0.8647`, `gain(5)=1.0000`; monotone, bounded.
- Vanish-at-zero trace: `0 →reinforce(0.5)=0.000 →ignite(1.2)=1.200 →reinforce(0.1)=1.320`.
  Multiplicative reinforcement cannot lift cold; only `ignite()` crosses zero.
- Composition bonus: **cold (λ=0) = 0.00000**, **hot (λ=5) = 0.01000** (= the full
  `2 × productive_tension_bonus × gain`). The gate is the only thing that changed.
- A 120-step live workload with the ledger **pinned at 0** ended `λ = 0.00000` —
  composition cannot mint the solvent.
- Gate-off identity: with no ledger, `_solvent_gain()` is **exactly 1.0**, so
  `bonus = config × 1.0 == config` — the original Tier-3 path, bit-for-bit.
- 6c disjointness: AST audit confirms `agents/lambda_ledger.py` imports nothing
  from the ⊘ path.

**The ⊘ consumer — PASS (all seven checks), and it is USED.**
- One pass over a 250-step field: **21 / 22 non-sacred values pulled**, each by
  exactly `rate·(strength−honest)`; none raised; the one **sacred** value was read
  (in the advisory set) and left **byte-identical**; ⊘'s own read changed nothing;
  counters moved (reported, not silent).

**Live demo (dim 128, Build A ignited).**
- **[1]** Ignition lit λ `0 → 2.0`; `solvent_gain(λ) = 0.9817` → **⊕ composition
  98.2 % open** (it was 0 % at λ=0). The gate is live in the production-dim stack.
- **[2] SAFE default (`named_only=True`), 40 consumption cycles:** ⊘ read 20 thin
  values `{unnamed: 17, Dissolution: 3}`; the consumer demoted **only the 3 named
  (Dissolution) values** — the single-source monoculture tokens `loop / samesame /
  echo`, pulled from ~3.0–3.6 toward a **convergent honest floor ~2.93–3.00 and
  held** — while **16 healthy multi-source values were untouched**. Field mean
  stayed **2.27**, active 20/20. ⊘ is genuinely *used*, selectively, **no collapse**.
- **[3] AGGRESSIVE (`named_only=False`), same 40 cycles — cautionary:** acting on
  *every* sub-health-floor advisory drove field mean **2.29 → 1.19**, active 20→17.
  This is the pre-declared **over-demotion collapse**.

## Interpretation
Build B is the spec's Law 2 made literal: with the λ-ledger attached, the *only*
composition term in Tier 3 is multiplied by `solvent_gain(λ)`, so co-present values
**do not compose at λ=0** (they stay isolated, ⊘ reads their pathology) and compose
as λ is *ignited* (Build A) and sustained. λ cannot be bootstrapped — multiplicative
reinforcement keeps `λ=0` a fixed point, and a live workload pinned at zero proves
composition mints nothing. Off by default it is byte-identical to today.

The consumer is the answer to the standing complaint that "nothing ever gets used."
⊘ stays exactly what Build C validated — read-only, non-binding — and a *separate*
object, where authority is supposed to live, now **writes value strength from ⊘'s
read**. The load-bearing design choices:
- **Convergent floor, not a slide to zero.** ⊘'s `honest_level = strength × support`
  is always below current strength, so naïvely pulling toward it has no fixed point
  but zero. The consumer remembers the **peak honest level** ever advised per value
  and never pulls below it → demotion with a fixed point.
- **Selectivity (`named_only`, default True).** The decisive empirical result: in
  short/low-dim runs the cc-axis confound (`coherence_contribution ≈ 0`, far below
  the 5.0 CORE ref — Build C) drags *every* value's aggregate support down, so
  acting on universal thinness **over-demotes the whole field** ([3]). Acting only
  on **named pathologies** — the validated, live-triggerable part of ⊘ — demotes the
  genuinely thin and leaves the healthy alone ([2]). That is why named-only is the
  production default and why reinforcement coupling stays behind the §6.3 gain-sign
  check.

So: ⊘ is no longer observe-only. It is *used*, with teeth and a brake.

## Threats / confounds
- **The over-demotion in [3] is partly a measurement artifact, not pure pathology.**
  The cc-axis reads ~0 in short horizons (the open Build-C confound), so aggregate
  support understates real health. This is *why* aggressive mode is unsafe **now**;
  it does not prove aggressive mode is wrong in principle. Lifting the cc confound
  and the universal coverage gap (per-type profiles) is the prerequisite to ever
  widening past named-only.
- **Selective mode leans entirely on the named regions.** Their thresholds
  (`_THIN_TAU`, `_HIGH_STRENGTH`, refs) are provisional v0.2; the vector→name map is
  validated as *live-triggerable* (Dissolution fired here and in the Build-C live
  run) but not yet calibrated against a designed thinning workload that hits all
  three regions.
- **This consumer couples ⊘ into *decay*, deliberately, not reinforcement.** The
  §6.3 gain-sign check still gates any reinforcement coupling (spec §4). Decay
  coupling is the conservative first step the spec calls for.
- The unit probes run at dim 64; the live demo at dim 128. Substrate is **not
  bit-reproducible run-to-run** (torch nondeterminism), so "gate-off ≡ default" is
  asserted as a *code identity* at the gate, not a full-run diff.

## Open / next
- **§4 discriminator** — ⊘-off vs ⊘-on, paired + noise-swept 0.05σ→0.5σ, trajectory
  metrics; **front-load the §6.3 gain-sign check** before any reinforcement coupling.
- **Designed thinning workload** to fire all three named regions and calibrate the
  vector→name map (the demo's monoculture fires Dissolution; Drift/Fragmentation
  still want a purpose-built workload).
- **Per-type thinness profiles** in the baseline registry → lift the universal
  coverage gap and the cc-confound, the gate on ever widening past `named_only`.
- **λ reinforcement (`reinforce(f)`)** is implemented but unwired — `f` from lived
  coherence (never ⊘), to make "lit stays lit while sustained" a live dynamic.
