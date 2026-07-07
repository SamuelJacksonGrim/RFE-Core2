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
- **Architect rulings 2026-07-03** (four standing decisions — do not re-litigate;
  `docs/ARCHITECT_RULINGS_2026-07-03.md`, merged in **PR #68**): (1) F8 sacred
  shield goes directional (read=pass, write=shield); (2) **boot-checkpoint
  adoption: ADOPT NOW** — Phase 3 Decision 2 is resolved; (3) λ/W operator-nodes
  are protected-but-not-sacred; (4) suppression/containment levers stay
  **permanently** severed from the baseline (ITG scaffold, ⊘ consumer off-baseline
  is now policy, not pending).
- **F8 half (a) — directional sacred-shield fix** — merged in **PR #68**
  (`ethical_boundary.py`: `sacred_mutation` fires only on all-sacred writes;
  sacred_shield 4/4).
- **Bonded-adversarial probe (F3) — BUILT + first run** — merged in **PR #68**
  (`tests/diagnostic/bonded_adversarial_probe.py` + finding
  `2026-07-04-bonded-adversarial-attack-never-lands.md`).

## 1 · Now — high leverage, unblocked

- [x] ~~**F9: rhythm/energy rescale.**~~ **DONE 2026-07-06** — bands rescaled
  0.5/2/5 → 5/150/300, co-tuned against each band's *pinned-run equilibrium*
  (stabilize placed below its degraded ALLOW_WEAKENED equilibrium — the
  15-trap). Four-band circulation alive at both dims (dream ~25%, was ~0.2%);
  full-system harness re-run as the gate. Exposed two governance-side items
  (warmup trust drain, identity_erosion ambient weakening — added below).
  → `docs/findings/2026-07-06-f9-rhythm-band-rescale.md`
- [ ] **F8 half (b): re-enable the v0.3 CORE-promotion gate.** The ruling is
  issued (directional read/write shield) and half (a) shipped in PR #68; what
  remains is the irreversible sanctification path: re-enable
  `review_core_promotion` on the field-alignment axis, rewrite the handshake
  test, and run a live no-cascade verification (CORE arc completes without
  cascading the contributing source).
  → `docs/ARCHITECT_RULINGS_2026-07-03.md` §1;
  `2026-06-27-core-gate-fix-deferred-sacred-cascade.md`
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
- [x] ~~**Bonded-adversarial probe (F3)** — build it~~ **BUILT + first run
  (PR #68, merged).** Verdict: the question is *not yet answerable* — the attack never
  becomes a signal (hostile ≡ benign at injection, cos ~0.98, 11 seeds). Two
  upstream walls localized. Follow-ups now carry F3:
  → `2026-07-04-bonded-adversarial-attack-never-lands.md`
- [ ] **F3 follow-up — Wall 1 (in-corpus hostile vocabulary arm):** the attack
  words ("erase/betray/dissolve") are out-of-corpus, so they carry no distinct
  direction. Add semantically oppositional vocabulary to the corpus (v1.3
  candidate — ties into §3 recorder-driven growth) and re-run: does a
  *representable* attack separate at stage A?
- [ ] **F3 follow-up — Wall 2 (reflective-loop-ablated re-run):** even a
  stage-A-separated attack is re-collapsed to cos ~0.98 by attractor-pull + the
  loop ("launders betrayal into coherence"). Ablate the loop as in 2026-06-07
  and re-run — the first path to a real GRADIENT-DEFENSE-REAL vs
  RATE-LIMIT-ONLY verdict.
- [x] ~~**Warmup trust drain (found during F9, 2026-07-06)**~~ **ROOT-CAUSED +
  FIXED same day** — the "drain" was the compound-severity quarantine path
  charging systemic (nameless) signals to whichever source was speaking
  (−0.4 trust each → toxic spiral). Fixed by the **attribution rule** in
  `arbitrate()`: quarantine rungs require ≥1 source-attributed signal;
  systemic-only evidence damps (and force-dreams at ≥0.90) but never
  quarantines the speaker. Canonical seeded trajectory now runs clean
  (trust 5.0, quarantine 0). A milder feedback-side drain (negative
  `coherence_impact` deltas during cold phases) may remain — re-measure if
  cold-boot trust ever sags again.
  → `docs/findings/2026-07-06-f9-rhythm-band-rescale.md` §attribution rule
- [ ] **identity_erosion ambient weakening under the live dream band (found
  during F9, 2026-07-06):** benign dream-band expressions widen watcher G/T
  divergence to ~0.33 (threshold 0.30), so the detector emits a systemic
  severity-~0.55 signal that ALLOW_WEAKENs benign traffic — 47% of steps in
  the untrained test harness, 17–26% in the pretrained composed engine. The
  quarantine hair-trigger this created was disarmed by the governance
  **attribution rule** (same-day, see previous item); what remains open is the
  ambient damping tax itself. The detector threshold cannot be recalibrated
  blind: no probe measures its true-positive side (F3 showed attacks don't
  yet become signals at all). When the F3 Wall-1 in-corpus-hostile-vocabulary
  arm lands, measure attack-side G/T divergence and separate the bands.
  Detectors were calibrated in the explore-pinned world.
  → `docs/findings/2026-07-06-f9-rhythm-band-rescale.md`
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
- [ ] **Extend the session checkpoint to the decoder head** — boot currently
  retrains the dream-channel decoder (20 epochs) every start even on resume;
  checkpointing it makes warm boots near-instant.
- [ ] **Implement canonical boot checkpoint (RULED: adopt now).** Architect
  ruling #2 (2026-07-03) resolves Phase 3 Decision 2: train once → save the
  canonical checkpoint → `build_engine()` loads it at boot (fallback to live
  pretraining if absent). Foundation already exists: the `session_persistence`
  resume path in `build_engine` (2026-07-06) is the same load discipline;
  implementation unifies the two. Storage form (in-repo artifact vs first-boot
  cache) settled at implementation.
  → `docs/ARCHITECT_RULINGS_2026-07-03.md` §2

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

- [x] **Post-#68 reconciliation** — DONE 2026-07-06 (same-day merge): main
  merged into this branch (one README tree conflict, both lines kept), the
  2026-07-04 finding's INDEX row confirmed, ruling #4's permanent-severance
  policy stamped into `EXPERIMENTAL_LEVERS.md` (ITG + ⊘ consumer), all gates
  re-run green.

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
