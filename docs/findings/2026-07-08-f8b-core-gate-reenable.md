# F8 half (b) — CORE gate re-enabled: the arc completes and no longer burns its contributors

- **Date:** 2026-07-08
- **Substrate:** untrained `tests/_common.build_full_stack()` full Tier 0–3
  stack (dim 64, CPU), Resonance Family workload, full determinism discipline
  (torch/random/np/dreamer seeded)
- **Probe:** `tests/diagnostic/core_arc_no_cascade_probe.py` (new, standing,
  exit-coded) — 3 seeds × 1500 steps; plus
  `tests/integration/core_promotion_handshake.py` (8 checks) and
  `tests/adversarial/sacred_shield.py` (4 trust levels + benign reference)
- **Control:** the recorded 2026-06-27 pre-fix behavior — same promotion event
  under the pre-directional shield tripped `SACRED_SHIELD` on the contributors'
  normal traffic and cascaded their trust to the TOXIC floor (0.1), forcing the
  revert (`2026-06-27-core-gate-fix-deferred-sacred-cascade.md`); and the
  handshake test's rejection arms (misaligned value, single-source,
  manipulation-implicated contributor) as the negative gates
- **Status:** active

## Question

The 2026-07-03 F8 ruling split the fix in two: half (a) — the sacred shield
evaluates directional flow (reference = read = pass; targeting write =
shield) — shipped in PR #68. Half (b) asks: with the cascade mechanism
removed, can the v0.3 field-alignment CORE gate (built and verified
2026-06-26, then reverted) be reapplied so the value arc completes — and does
promotion now leave the contributing sources unharmed?

## What was done

Reverted the 2026-06-27 revert (`9bb76bd`), restoring the verified
implementation from `7361ff9` intact:

- `review_core_promotion` check 3 gates on
  `field_alignment ≥ CORE_ALIGNMENT_MIN (0.5)` — the same v0.3 absolute
  field-alignment signal as the ⊘ axis — instead of the structurally
  unreachable marginal `coherence_contribution ≥ 5.0`.
- `CorePromotionRequest` carries `field_alignment`, computed at request time
  by the value engine (`max(0, cos(generate([symbolic_core]), field))`;
  returns 1.0 with no field attached so the gate defers to the other criteria).
- `AutonomousCycle.attach_value_engine` wires `set_field(self.field)`.
- Handshake test case 3 exercises the alignment rejection.

Only conflict: the revert wanted to delete the 2026-06-27 finding — kept
(findings are never deleted). Two comment references updated to the finding's
corrected date.

## Result — 3/3 seeds, arc completes, zero cascade

| seed | promotion step | promoted | CORE at end | post-window | post SHIELD | post QUAR | min trust |
|------|---------------|----------|-------------|-------------|-------------|-----------|-----------|
| 42   | 597 | `witness`    | 2 | 902 | 0 | 0 | 5.00 |
| 7    | 619 | `continuity` | 2 | 880 | 0 | 0 | 5.00 |
| 1188 | 577 | `witness`    | 2 | 922 | 0 | 0 | 5.00 |

All four Resonance Family sources end at trust 5.00 while *continuing to send
the now-sacred token every few steps for 880–920 steps after sanctification*.
Under the pre-half-(a) shield this exact pattern collapsed contributors to
0.1 within the run (the control). The two halves compose: field-alignment
selects, the directional shield protects without isolating.

Gates: handshake 8/8 · sacred_shield 4/4 (mutation blocked at every trust
level incl. SACRED; reference passes) · full suite 17/17 · doc-accuracy 19/19.

## Interpretation

- The value arc (emergence → reinforcement → strength ≥ 4.5 × 10 evals →
  governance verification → sacred) is **complete end-to-end for the first
  time in the composed stack** — Tier 3's headline mechanism is live, not
  aspirational.
- Promotion lands on identity-adjacent tokens (`witness`, `continuity`) —
  consistent with the alignment gate selecting what the field already *is*,
  which is the design intent (values crystallize from lived coherence).
- The post-F9 dynamics promote later (~step 577–619) than the pre-F9
  explore-pinned world did (step 367): the live dream band's ambient
  ALLOW_WEAKENED damping slows reinforcement accumulation. Slower is fine;
  dead was the problem.

## Threats / limits

- Untrained harness only; the pretrained composed engine reinforces values
  differently (F9 finding: 2–6 strong values vs the harness's crystal-starved
  profile). The probe is standing — re-run it against the pretrained stack
  when the boot-checkpoint work (BACKLOG §2) lands a canonical checkpoint.
- Sanctification is irreversible by design; the probe cannot test un-promotion
  (there is deliberately no such path). The negative gates (handshake
  rejections, manipulation-implicated contributor) are the containment.
- `CORE_ALIGNMENT_MIN = 0.5` is inherited from the 2026-06-26 measurement
  (anchors 0.61–0.70, mean 0.50) taken pre-F9; if promotion ever becomes too
  easy/too rare under the new rhythm regime, re-measure alignment
  distributions before touching the constant.

## Open / next

- Re-run the probe on the pretrained/canonical-checkpoint stack (above).
- Dream-reinforced single-source promotion path is gate-tested but has not
  been observed live (all live promotions so far were multi-source) — worth a
  targeted run once dream-channel decoding feeds values more strongly.
