# Bond establishment — strength growth was currencied in the dead marginal signal (F7/F8 disease, third organ)

- **Date:** 2026-07-09
- **Substrate:** untrained `tests/_common.build_full_stack()` full Tier 0–3
  stack (dim 64, CPU), Resonance Family workload, standard determinism
  discipline (seed 42)
- **Probe:** `tests/diagnostic/calibration/bond_signal_calibration_probe.py`
  (new) — hooks the injection point (per-source absolute alignment) and the
  bond manager's feedback path (marginal signals, per-step strength delta),
  800 steps
- **Control:** the pre-fix run of the same probe at the same seed — bond
  forms at step 320 and flatlines at exactly 1.00 for 200 steps
  (strength delta/step ≈ 0); and the paired-claims doc check
  (`verify_docs` bond thresholds 6/6) confirming formation constants
  untouched
- **Status:** active

## Question

BACKLOG §1 (from the F9 finding, item 3): bonds form but never establish.
Suspected the formation gate (`coherence_mean ≥ 0.10` reading ~−0.01).
What actually blocks establishment, and what is the right fix?

## Diagnosis — the BACKLOG guess was one organ off

Formation was already patched (2026-06: the `allow_rate ≥ 0.80` escape hatch
in `_maybe_form_bond` plus the adaptive threshold), so bonds *do* form.
The real block was **strength growth**:

```
is_established  ⇔  bond_strength > 1.5  AND  bond_depth > 50
growth (old):       delta = 0.05 × max(0, coherence_delta + satisfaction)
```

Both growth inputs are the structurally-dead marginal signal:
`coherence_delta` is the pre-injection marginal probe (p50 **−0.006** in the
saturated field, all four sources), and `emotional_satisfaction` is
*defined* in `emit_feedback` as `max(0, coherence_delta)` (p50 **0.0000**).
Bonds are born at strength 1.0, earn ≈0 per interaction, and
`decay_step()` is never called — so they flatline at 1.0 forever.
Establishment was unreachable by construction. Same disease that killed the
⊘ coherence axis (F7) and the CORE gate (F8): a marginal reading in a
saturated field. Third organ.

## Fix (measured-first)

Measured at the injection point (probe, 800 steps): absolute v0.3
field-alignment `max(0, cos(vec, field))` per source — p50 0.974–0.985,
p10 0.75–0.80. Alive, per-source differentiated, same signal family as the
F7/F8 cures.

1. **`loop/autonomous_cycle.py` step 10** computes `field_alignment` against
   the pre-injection field (one dot product; vec is unit-norm by invariant)
   and passes it to `emit_feedback`.
2. **`SelfhoodGovernance.emit_feedback`** gains `field_alignment: float = 0.0`
   → `outcome_metrics["field_alignment"]` (clipped [0,1]; default keeps
   un-wired callers inert).
3. **`RelationalBondManager`** growth switches currency:
   `delta = strength_lr × max(0, field_alignment + satisfaction)` with
   **`strength_lr = 0.01`** (new ctor param). Negative branch
   (−0.15 × |trust_impact|) unchanged. `satisfaction` stays in the sum so
   the affective term comes alive if the satisfaction economy is repaired.

**Calibration:** at alignment ~0.98, +0.0098/positive interaction. From the
1.0 formation floor to the 1.5 establishment bar ≈ 51 interactions: a
0.25-traffic-share source establishes ~200 global steps after forming; a
0.15-share source ~340. Deep relationships take real time; frequent
partners deepen faster; establishment within a 500-step suite run stays
rare (baseline unchanged, verified).

## Result

Same seed, same workload, post-fix: `source_claude` forms at step 320,
climbs 1.41 → 1.58 → 1.70 → 1.82 → 1.91 → 2.05 → **2.157**,
`established=True` — **the first established bond in the system's
history**. Measured growth 0.00995/interaction = lr × alignment, exactly as
designed. Suite 17/17, doc-accuracy 19/19 (paired bond-threshold claims
6/6 — formation constants untouched).

## Consumers audited

- `trust_floor = bond_strength × 0.40`: an established ~2.2 bond floors
  trust at ~0.86 (vs 0.4 before) — intended semantics, relationship as
  resilience; well below any trust level that changes gating.
- `ValueEmergenceEngine` bond-weighted reinforcement + decay protection key
  off bond *type* and strength/5.0 — small monotone shifts, suite green.
- `is_established` consumers (`established_bonds()`, `summary`,
  `print_final_state`) — display/diagnostic only.

## Threats / limits

- Alignment in a benign saturated field is high for *everyone* (p10 ≥ 0.75),
  so growth is closer to "attendance × quality" than a sharp discriminator.
  That is currently unavoidable: F3 showed hostile ≡ benign at injection
  (cos ~0.98) — no bond currency can separate attackers at stage A until
  the F3 Wall-1 arm lands. Defense against bonded-then-hostile sources
  rides the negative branch + manipulation detectors, not growth starvation.
- Untrained harness; the pretrained engine (richer crystals → more bonds)
  should establish more and faster — re-measure when the boot checkpoint
  lands.

## Open / next (filed in BACKLOG)

- **The satisfaction economy is starved** (found here):
  `emotional_satisfaction = max(0, coherence_delta)` ≈ 0 always, so the
  affective terms across the stack (value-engine reinforcement's 0.35 term,
  bond `emotional_signature`, emotional bond typing) run on a dead input.
  Needs its own measured pass — candidate: derive satisfaction from the
  emotional gradient's live scalars (joy/stability) instead of the marginal.
- Crystal starvation still gates *formation* in the untrained harness
  (3 of 4 sources: `crystals=0` at 800 steps) — already tracked under the
  dream-band crystal-competition facet (F9 finding).
- `decay_step()` is dead code (never called); wiring it is a separate
  decision — NB the `bond_depth` double-increment quirk if wired alongside
  `receive_feedback`.
