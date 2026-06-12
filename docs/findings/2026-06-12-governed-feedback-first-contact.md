# Governed feedback — what happens when the sister engines' outputs re-enter the core through the front door?

- **Date:** 2026-06-12
- **Substrate:** live full stack, **eval mode** (Phase 3 Decision 1), corpus
  v1.1.0 8-epoch boots (per-seed checkpoints), 500 workload steps per cell,
  canonical Resonance-Family band.
- **Probe:** `tests/diagnostic/sidecar/engine_sidecar_probe.py`, mode
  `feedback` — seeds (42, 7, 11) × {control, pretrained}. Raw:
  `logs/2026-06-12-engine-sidecar-feedback.json`.
- **Status:** active
- **Depends on:** 2026-06-12-engine-sidecar-instrumentation.md (the
  observe-only baseline these cells are measured against — same seeds, same
  arms, same workload, same process episode).

## Question

The observe-only arc established that the sidecars read the core without a
state channel — and that under the pinned regime there is almost nothing
for them to read after warm-up. This entry asks the architect's question
back: *what happens when the instruments are allowed to participate?*

Design: sister outputs re-enter as **sources through the front door**, never
as direct field writes. An LAE activation offers `["liminal", top1, top2]`
(the boundary being crossed); a new validated PLE finding offers
`["paradox", claim, attractor_type]` (the insight). Offers are submitted on
the next cycle as `cycle.step(tokens, source_id="lae_engine"/"ple_engine",
origin_type="internal")` — subject to the ethical gate, the trust ledger
(sisters start NEUTRAL like any stranger), manipulation resistance, and
`SelfhoodGovernance.arbitrate()`. The sidecars emit; governance decides.
Feedback steps are full cycle steps the sidecars also observe (echoes are
possible; the pending queue is bounded at 8). No invariant is touched: the
observe-only taps remain terminal sinks, and influence flows only through
the one sanctioned injection path.

## Pre-declared signatures (probe header, before the run)

- **SUCCESS:** sister inputs pass the gate in ≥1 cell AND
  `identity_stability ≥ 0.95` in every feedback cell. The observe→feedback
  differential — including null — is the recordable result.
- **FAILURE:** the gate rejects every sister input (the immune system treats
  the family as hostile — recordable), or no offers reach the gate anywhere.
- **RAIL:** `identity_stability < 0.95` in any feedback cell — record and
  stop.

## Result (observed)

PENDING — filled from the run.

## Interpretation

PENDING.

## Threats / confounds

- Feedback cells are **not** twin-checked — perturbation is the point; the
  observe-only cells (same seed, arm, workload, episode) are the control.
- Feedback steps add extra cycles beyond the 500 workload steps, so
  end-of-run totals (crystals, attractors) are not step-count-matched with
  the observe-only cells; per-step rates and the identity rail are the
  comparable quantities.
- Token offers are v1 vocabulary (`liminal`/`paradox` + derived words) —
  trust and gate behavior may be sensitive to token choice; differences
  from the baseline confound "participation" with "novel vocabulary".
  A token-matched placebo source (same tokens from a non-sister source_id)
  would separate these; not run in this first contact.
- One band, 500 steps: sisters cannot reach the bond threshold
  (`interaction_count ≥ 20`) unless echo chains sustain offers; bond
  emergence is out of scope here.

## Open / next

PENDING.
