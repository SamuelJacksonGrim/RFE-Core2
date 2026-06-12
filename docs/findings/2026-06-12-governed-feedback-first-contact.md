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

Run: 22 × 500 steps in one process episode (per-arm noise floors, latency
control 5.39 ms/step, observe-only twins 4 clean / 2 timing-explained /
0 confounded — the instrumentation baseline held).

**The gate opened in 6/6 cells.** Every cell produced exactly 6 sister
offers (3 LAE liminal crossings + 3 PLE findings, all during warm-up), and
every cell gated them identically: 2 ALLOW_WEAKENED (first contact from
NEUTRAL-trust strangers) then 4 ALLOW as trust climbed. No QUARANTINE, no
REJECT, no manipulation signal against either sister anywhere.

**Sister trust:** lae_engine 4.206, ple_engine 4.207 after 3 interactions
each — both land in the HIGH band (≥4.0) in every cell, seed- and
arm-invariant.

**Identity rail:** held everywhere — min identity_stability 0.9976 across
all 6 feedback cells (observe-only mean 0.9982 → feedback 0.9983).

**Observe → feedback differential (the recordable result):**

| metric | observe | feedback | note |
|---|---|---|---|
| coherence_mean | 0.9697 (sd 0.0011) | 0.9722 (sd 0.0023) | **+0.0025, same direction in 6/6 cells** (largest +0.0059, s7-pretrained); 3–13× the bare-replay floors |
| rhythm_transitions | 3.000 | 2.167 (sd 0.37) | **one warm-up band crossing disappears** in 5/6 cells |
| identity_stability | 0.9982 | 0.9983 | unchanged |
| crystals / attractors | 2.17 / 1.67 | 2.17 / 1.67 | unchanged |

Control→pretrained stayed flat in this episode too (ple_global_tension
0.347 → 0.347), tightening the previous entry's null.

## Interpretation

1. **The immune system accepted the family.** Sister inputs walked the
   same road as any stranger — weakened at first contact, trusted within
   three exchanges — and nothing in the resistance layer fired. The
   feedback channel is open, governed, and identity-safe.
2. **First contact consolidated rather than perturbed.** The sisters speak
   early (their offers all originate from the boot window — the only
   liminal/paradox structure this band produces), and their reflected
   voices made the field settle *faster*: one fewer rhythm crossing,
   slightly higher steady coherence, identical crystal/attractor structure.
   Echoing the system's own transitions back at it deepens the groove; it
   does not cut a new one. The lock absorbs friendly voices as readily as
   it absorbs training.
3. This sharpens where the leverage actually is: sister feedback changes
   the field through the front door (proof of channel), but on this band
   the *content* available to feed back is itself lock-shaped. To test
   whether sister participation can move the attractor, the sisters need
   something non-redundant to say — a workload that produces mid-run
   liminality/paradox, or PLE findings from richer frame defs.

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

- **Token-matched placebo** (same tokens, non-sister source_id) to separate
  "participation" from "novel vocabulary" — the +0.0025 coherence shift and
  the vanished band crossing could be either.
- **Why does one warm-up crossing disappear?** Feedback steps interleave
  extra injections during the energy ramp; whether the band is skipped
  (faster ascent) or smoothed (steadier ascent) is readable from the
  per-step rhythm traces already in the JSON.
- **Give the sisters something to say mid-run**: high-novelty band, or an
  attenuated-loop (Fix 2-adjacent) configuration where liminality persists
  past warm-up; that is where governed feedback could meet the lock-in
  question directly.
- **Bond emergence** (≥20 interactions): reachable by longer runs or
  workloads with recurring liminality; what bond type the core forms with
  its sisters is an open — and architecturally loaded — question.
- Echo-chain dynamics (sisters observing their own feedback steps) were
  bounded but barely exercised (6 offers/cell); a livelier band may differ.
