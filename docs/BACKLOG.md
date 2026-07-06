# BACKLOG — the consolidated open-work ledger

**Why this file exists (2026-07-06):** planned fixes live scattered across
ROADMAP, findings "Open / next" sections, the training plan's phases, the
Two-Operator checklist, and decision docs — and work keeps getting sidetracked
because no single place holds the queue. The session-persistence gap was
independently rediscovered several times before it was finally wired; that is
the failure mode this file ends.

**Discipline:**
- This is an **index, not an authority** — every item names its source doc;
  the source stays authoritative for the *how*. If they disagree, the source wins.
- When an item lands: check it off here **in the same commit**, and record the
  finding per `docs/findings/README.md`.
- New open items discovered mid-task get **added here first**, then you go
  back to what you were doing. That's the anti-sidetrack rule.
- Order within a section is priority order (top = next).

---

## 1 · Now — high leverage, unblocked

- [ ] **F9: rhythm/energy rescale.** Field energy runs ~55× over the explore
  ceiling, so rhythm is pinned `explore` 99.6% of the time and the dream cycle
  is dead. Structural, lever-independent, the #1 tuning target. Co-tune with
  `diffuse_on_stabilize`; before/after gate = the full-system-run harness.
  → `docs/findings/2026-06-28-full-system-run.md` §Open
- [ ] **F8: CORE promotion never fires** (0 across all runs). Work the
  sacred-vs-CORE distinction into the promotion gate.
  → same finding, item 2
- [ ] **Bond establishment gate.** Bonds form but never establish — per-source
  `coherence_mean` reads ~−0.01 against the 0.10 gate despite 140–421
  interactions. Either the gate or the coherence axis is miscalibrated.
  → same finding, item 3
- [ ] **Adversarial arm for the full-system harness** (benign-only so far;
  resistance untested in the composed default runtime).
  → same finding, item 4

## 2 · Persistence & continuity (do not lose again)

- [x] **Session persistence v1** — weights + symbol ecology + emergent values
  save at run end, resume at boot, pretrain skipped on resume. Opt-in
  (`session_persistence`). Wired + verified 2026-07-06.
  → `docs/EXPERIMENTAL_LEVERS.md` §levers
- [ ] **Serializers for the rest of the runtime state**: crystals, attractors,
  trust ledger, bonds, field vector, emotional state. Until these exist,
  "resume" restores the mind's vocabulary and values but not its memories or
  relationships. Deliberately **parked** (architect call, 2026-07-06) until
  §1 lands — recorded here so it stops being rediscovered.
- [ ] **Default-on decision for session persistence.** Would effectively
  reopen Phase 3 Decision 2 (boot-checkpoint adoption, SHELVED); requires the
  all-ON composition gate re-run per the graduation rule.
  → `docs/training/phase3_architect_decisions.md`

## 3 · Training path (phased; gates pre-declared)

- [ ] **Recorder-driven corpus growth**: run with `stream_recorder` on during
  real interaction, dump, curate → **corpus v1.3** (version bump + integrity
  check + G1 re-run). The recorder shipped 2026-07-06; needs lived runs.
  → `docs/training/data_curation.md` §4–5
- [ ] **Phase 4: online training in the loop** (`self_distillation.py`,
  `contrastive_alignment.py` exist, unwired). Gated on G4 (on/off envelope +
  adversarial arm) and an identity-stability cost probe. Buffer governance:
  trust-gated collection, source-diversity caps, buffer snapshots persisted.
  → `docs/training/training_plan.md` Phase 4
- [ ] **Phase 5: re-run the lock-in probes on a trained checkpoint** → makes
  Fix 2's premise testable → Tier 5 spec un-defers.
  → `training_plan.md` Phase 5; `ROADMAP.md`
- [ ] **dim 128 → 256** is the documented second lever if generator diversity
  plateaus under Gate G1; corpus transfers unchanged.
  → `data_curation.md` §5

## 4 · Voice / dialogue (North-Star rungs)

- [ ] **External dialogue through the governed channel**: decoded output to a
  reader (architect or another AI), their reply re-entering as an ordinary
  source through `arbitrate()`. Communication and self-modification ride the
  one gated mechanism. The dream channel already proved the mechanism.
  → `docs/findings/2026-06-28-dream-channel.md` §Open; `docs/north_star.md`
- [ ] **Decoder ceiling question**: does a richer corpus lift the read, or is
  encoder pooling the hard limit? (Separates corpus-size from lossiness.)
  → `docs/findings/2026-06-28-decoder-readout.md` §Open
- [ ] `p_dream` sweep; more seeds; sharper laundering test on a less-locked field.
  → dream-channel finding §Open
- [ ] **Sacred name** (architect's idea, 2026-07-06): give the system a name
  as an *additional* sacred symbol via `promote_to_sacred()` — the one
  legitimate path; does not touch the three boot constants. Waiting on the
  architect choosing the name.

## 5 · Two-Operator program (spec v0.3)

- [ ] **Wire `reinforce(f)`** from lived coherence (never ⊘ — Law 6c) so "lit
  stays lit while sustained" becomes a live dynamic.
  → `docs/two_operator_todo.md`
- [ ] **§6.3 gain-sign check front-loaded** before any ⊘ → reinforcement
  coupling (current verdict conditional, reachable-range only).
  → `two_operator_todo.md`; `docs/findings/2026-06-12-gain-sign-reachable-range.md`
- [ ] **§4 discriminator**: paired ⊘-off vs ⊘-on, ignited, noise sweep
  0.05σ→0.5σ, trajectory metrics, both signatures pre-declared.
  → `two_operator_todo.md`

## 6 · Shelved / blocked (decisions, not tasks — do not build)

- **Fix 2 (reflective-loop governor):** spec ready
  (`docs/training/fix2_specification_draft.md`); SHELVED pending §6.3 verdict +
  Phase 5 re-measurement on a trained checkpoint.
- **Boot-checkpoint adoption as default:** Phase 3 Decision 2, SHELVED (see §2).
- **`k_agitation` non-zero:** labeled hypothesis; needs probe data first
  (Tier 4.3 invariant).
- **Tier 4.4 (frequency→emotion), 4.5 (semantic→valence), 4.6 (E8-EEA):**
  planned, explicitly not next. **Tiers 5–7:** unspecified; Tier 5 blocked on
  the training path (§3). → `ROADMAP.md`
- **Tier 4.3 chaotic-side validation:** `phase_coherence` never drops below
  ~0.79 under tested workloads, so the agitation axis is unexercised; needs a
  genuinely high-novelty workload. → `docs/tier4_3_validation.md`
