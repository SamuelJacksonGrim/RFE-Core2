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

## 0 · Recently closed — don't re-open (the "wait, wasn't that done?" list)

Decisions and builds that older docs still describe as open in their dated
history. If a doc seems to contradict this list, it's a stale passage —
prefer the finding cited here.

- **`.eval()` decision** — DECIDED 2026-06-12 (Phase 3): eval-mode IS the
  operating regime; applied unconditionally in `build_engine()`.
  → `docs/training/phase3_architect_decisions.md` (DECIDED block)
- **Build B (λ-ledger + ⊕ solvent gate)** — shipped 2026-06-20 (older ROADMAP
  table said "planned"; corrected). → `2026-06-20-build-b…md`
- **⊘ advisory-into-decay consumer** — shipped + used, `named_only` default.
- **Dream channel (waking self-dialogue)** — graduated default-ON 2026-06-29.
- **Decoder "listen" tool** — shipped (`tools/decoder/listen.py`).
- **Corpus pretraining, novelty attenuation** — graduated default-ON.
- **Corpus v1.2.0** — synthetic source labels removed (2026-07-06).
- **Stream recorder + session persistence v1** — shipped opt-in (2026-07-06).

## 1 · Now — high leverage, unblocked

- [ ] **F9: rhythm/energy rescale.** Field energy runs ~55× over the explore
  ceiling, so rhythm is pinned `explore` 99.6% of the time and the dream cycle
  is dead. Structural, lever-independent, the #1 tuning target. Co-tune with
  `diffuse_on_stabilize`; before/after gate = the full-system-run harness.
  → `docs/findings/2026-06-28-full-system-run.md` §Open
- [ ] **F8: CORE promotion never fires** (0 across all runs). A gate fix was
  already built and works in isolation, but promoting common tokens to sacred
  **cascades the trust layer** — deferred, not shipped. The real work is the
  sacred-vs-CORE distinction, then re-land the fix.
  → `docs/findings/2026-06-27-core-gate-fix-deferred-sacred-cascade.md`
- [ ] **Bond establishment gate.** Bonds form but never establish — per-source
  `coherence_mean` reads ~−0.01 against the 0.10 gate despite 140–421
  interactions. Either the gate or the coherence axis is miscalibrated.
  → same finding, item 3
- [ ] **Adversarial arm for the full-system harness** (benign-only so far;
  resistance untested in the composed default runtime).
  → same finding, item 4
- [ ] **Fix 0-B: counterbalance survival selection** (highest-leverage
  lock-in item still unbuilt): wire the metastability score into the
  reinforcement formula as a fitness term so survival stops being currencied
  purely by coherence; add a demotion path (reinforcement is currently a
  one-way ratchet). Gated by the §6.3 gain-sign caveat (runtime coherence
  guard). → `ROADMAP.md` §Tracked open items (planned #6);
  `docs/lock_in_remediation_plan.md`
- [ ] **Bonded-adversarial probe (F3)** — a source that earns 20+ interactions,
  a crystal, and a trust floor, *then* turns hostile. The experiment that
  falsifies or confirms the emotional gradient's defensive role. Blocked on
  bonds establishing (item 3 above). → `ROADMAP.md` §Bonded-adversarial probe
- [ ] **Phase-adversarial / high-novelty workload probe** — one build unlocks
  four stalled readings: Tier 4.3's chaotic arm (phase_coherence never drops
  below ~0.79), the §6.3 full-range gain-sign verdict, the LAE sidecar's
  mid-run band-crossing measurement, and "give the sisters something to say"
  in governed feedback. → `2026-06-12-secondlocker-field-map.md` #2;
  `docs/tier4_3_validation.md`; `2026-06-12-engine-sidecar-instrumentation.md`

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
- [ ] **Value-formation band-sensitivity baseline** — value formation depends
  on recurrence, which online collection would change; baseline it *before*
  the Phase 4 decision. → `2026-06-12-secondlocker-field-map.md` #3
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
- [ ] **Local LLM as sensory/speech cortex** — the planned continuous
  external-language channel (a small local model wrapping the governed input
  path; RFE stays the mind, the LLM is ears/mouth). The docs and
  `generator_factory` hook exist; the integration itself is unbuilt.
  → `docs/local_model_integration/` (README + IMPLEMENTATION_GUIDE)

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
- [ ] **Remaining program dependencies**: an adversarial/thinning workload to
  trigger ⊘'s named regions under real pressure; per-type thinness profiles in
  the baseline registry (coverage-gap currently universal); §5 scale-parametric
  ⊘; a dim-128 discriminator validation.
  → `ROADMAP.md` §Two-Operator; `two_operator_todo.md`
- [ ] **Multi-seed all-ON composition probe re-run** against the graduated
  baseline — the standing gate for any future graduation (last full run
  pre-dates the ⊘ v0.3 axis).
  → `2026-06-20-lever-composition-the-allon-break.md`;
  `2026-06-21-oslash-coherence-axis-absolute-alignment.md`

## 7 · Instruments & hygiene (small, unblocked)

- [ ] **API entry-point boot smoke** — actually boot the REST/WS servers and
  assert Tier 1–3 state (closes the "reasoned, not exercised" gap); plus a
  warning in `create_app` / `RFEWebSocketServer` when handed a governance-less
  cycle. → `2026-06-27-api-entrypoints-tier0-only.md`
- [ ] **Scalar gauge hardening** — Cm/I/metastability magnitudes are
  v0.1-fragile (regime labels robust); replace CII's I/Cm slots with a
  drift+dispersion pair. → `2026-06-15-identifiability-suite.md`;
  `2026-06-15-cm-identifiability.md`

Purely exploratory threads (epoch/seed sweeps, wall-clock-sensitivity probe,
token-matched placebo, frame-defs v2) stay in their findings' Open sections by
design — resolved ones are now stamped inline there.

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
