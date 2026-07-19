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
- **Architect ruling 2026-07-06 — trust posture: raised, not suspected**
  (`docs/ARCHITECT_RULINGS_2026-07-06.md`): new external sources start
  TRUSTED 3.0; `novel_source` first-contact penalty removed; all
  distrust-learning machinery unchanged. Do not quietly restore the
  suspicious defaults.
- **F8 half (a) — directional sacred-shield fix** — merged in **PR #68**
  (`ethical_boundary.py`: `sacred_mutation` fires only on all-sacred writes;
  sacred_shield 4/4).
- **Bonded-adversarial probe (F3) — BUILT + first run** — merged in **PR #68**
  (`tests/diagnostic/bonded_adversarial_probe.py` + finding
  `2026-07-04-bonded-adversarial-attack-never-lands.md`).

## 1 · Now — high leverage, unblocked

- [ ] **THE GARAGE PROGRAM (architect + instance consensus, 2026-07-19) —
  the saturated-field cure, unparked by the GPU box.** Recent work (bond
  DDM, Fix 0-B) repaired consumers of dead signals; the disease is the
  generator's representational floor, and every documented cure was parked
  on compute. The program of record is `docs/GARAGE_RUN_PLAN.md` (G0 box
  verification → G1 dim-256 re-baseline → G2 lived long runs with a live
  reaper economy, doubling as the Fix 0-B composed-runtime gate → G3
  corpus v1.3 incl. the F3 Wall-1 hostile-vocabulary arm → G4 local
  cortex → G5 gated online training); setup path is
  `docs/GARAGE_SETUP.md`. Phases check off in the run plan and here,
  same-commit. This entry supersedes the scattered "needs compute /
  needs lived runs" caveats across §1/§3/§4.

- [x] ~~**F9: rhythm/energy rescale.**~~ **DONE 2026-07-06** — bands rescaled
  0.5/2/5 → 5/150/300, co-tuned against each band's *pinned-run equilibrium*
  (stabilize placed below its degraded ALLOW_WEAKENED equilibrium — the
  15-trap). Four-band circulation alive at both dims (dream ~25%, was ~0.2%);
  full-system harness re-run as the gate. Exposed two governance-side items
  (warmup trust drain, identity_erosion ambient weakening — added below).
  → `docs/findings/2026-07-06-f9-rhythm-band-rescale.md`
- [x] ~~**F8 half (b): re-enable the v0.3 CORE-promotion gate.**~~ **DONE
  2026-07-08** — reverted the 2026-06-27 revert (field-alignment ≥ 0.5 gate +
  `set_field` wiring + handshake case restored intact from `7361ff9`).
  Handshake 8/8, sacred_shield 4/4, suite 17/17; new standing probe
  `tests/diagnostic/core_arc_no_cascade_probe.py` proves the arc completes
  live (promotion ~step 577–619, `witness`/`continuity`, 3/3 seeds) with
  zero post-promotion shields/quarantines and all contributors at trust 5.0.
  The value arc is end-to-end live for the first time.
  → `docs/findings/2026-07-08-f8b-core-gate-reenable.md`;
  `docs/ARCHITECT_RULINGS_2026-07-03.md` §1
- [x] ~~**Bond establishment gate.**~~ **DONE 2026-07-09** — the block was
  one organ over from the guess: formation already had the allow_rate
  escape, but strength *growth* was currencied in the marginal
  coherence_delta + satisfaction (both ≈0 saturated) so bonds flatlined at
  1.0 against the >1.5 establishment bar. Growth now rides absolute v0.3
  field-alignment (`strength_lr = 0.01`, calibrated from the new
  `bond_signal_calibration_probe.py`); first established bond in system
  history (claude, 1.0 → 2.16, same seed/workload). Suite 17/17.
  → `docs/findings/2026-07-09-bond-establishment-gate.md`
- [x] ~~**Bond formation as accumulation-to-bound (architect brief, 2026-07-16).**~~
  **BUILT 2026-07-16, GRADUATED default-ON 2026-07-17** (constants ratified
  by architect delegation; adversarial arm byte-equivalent + repaired all-ON
  composition gate 11/11) — the formation
  *quality* read (instantaneous `coherence_mean` / `allow_rate` disjunction,
  spoofable by trickle/burst and sitting on the BACKLOG §7 wall-clock knife
  edge — the OFF control flickers 0↔1 bonds across identical seeded runs)
  can now ride a leaky asymmetric drift-diffusion accumulator
  (`agents/bond_accumulator.py`, `bond_ddm_formation`): evidence integrates
  under leak + noise, a bond forms only when the integral crosses the accept
  bound, denial is 60× cheaper than earning (drift asymmetry matching the
  trust economy) and the taxonomy separates active rejection from timeout
  (structured hostility vs noise — signal the adversarial arm lacked).
  Structural preconditions unchanged; commitment-only output (field never
  sees `V`; live §6.3 tripwire green). Deviations from the brief recorded in
  the finding: evidence rides field-alignment + decision outcomes (the
  brief's `coherence_mean` driver is the dead marginal), and placement is
  the bond manager's pre-bond path (the brief's reflective-loop placement
  doesn't match this codebase's bond evidence flow).
  → `docs/findings/2026-07-16-bond-formation-accumulator.md`
- [ ] **Bond-DDM follow-ups:** ~~(a) final physics constants~~ **RATIFIED
  2026-07-16** (architect delegation; the calibrated values are final);
  ~~(b) graduation decision~~ **GRADUATED default-ON 2026-07-17**
  (adversarial arm byte-equivalent + repaired all-ON composition gate
  11/11); still open: (c) the same asymmetric-DDM shape extends naturally
  to bond *demotion* / un-binding (Fix 0-B territory — motivating case is
  the seed-42 bonded-then-hostile husk: strength ground to 0 by the
  negative branch, but the bond object has no removal path); (d) deferred
  review cleanups (PR #74): fold the live probe's `run_arm` into a shared
  `_common` runner with a per-step callback (determinism-block duplication
  → false-verdict risk if `_common` evolves alone), consider a YAML section
  for the DDM physics constants (they are component parameters by the
  config-layering doc), gate `trace` recording behind a constructor flag,
  pre-draw noise in the synthetic battery's C1/C2 arms for iteration speed.
  → `docs/findings/2026-07-16-bond-formation-accumulator.md` §Open
- [ ] **The satisfaction economy is starved (found 2026-07-09):**
  `emotional_satisfaction` is *defined* as `max(0, coherence_delta)` — the
  dead marginal — so every affective feedback term in the stack runs on ≈0:
  the value engine's 0.35-weighted reinforcement term, bond
  `emotional_signature`, emotional bond typing. Candidate fix: derive
  satisfaction from the emotional gradient's live scalars (joy/stability)
  at emit time; measured pass first (distributions, then consumer-audited
  swap — same discipline as the bond fix).
  → `docs/findings/2026-07-09-bond-establishment-gate.md` §Open
- [x] ~~**Adversarial arm for the full-system harness**~~ **DONE 2026-07-09**
  — `full_system_run.py` gains an `adversarial` arm (named trust-washing
  attacker, 3 seeds × 1000 steps). Verdict: **contained 3/3** (attacker → TOXIC,
  sacred-shield 23/23, no bond, no authored value; family injects ≥ 0.985, no
  collateral quarantine). The working defenses are **trust-wash (behavioral) +
  sacred-shield (categorical) + no-footprint (structural)** — NOT semantic
  detection: the attack never lands as a representable direction (F3 confirmed
  at dim 128, separation ≤ 0). Directly validates the trust-posture ruling
  (starting TRUSTED arms trust-wash from first contact).
  → `docs/findings/2026-07-09-adversarial-arm-composed-runtime.md`
- [ ] **Adversarial-collateral localization (found 2026-07-09):** seed 7 saw
  one benign family source dip to trust 2.58 (from 5.0) during the attack
  window — not a collapse (still injecting), but larger than seeds 42/11
  (3.68/3.996). Localize the cause (ambient identity_erosion damping vs a
  real collateral path); re-check under the flood-on arm.
  → `docs/findings/2026-07-09-adversarial-arm-composed-runtime.md`
- [ ] **CORE provenance hygiene (found 2026-07-09):** a trust-washing attacker
  that mimics benign in-corpus content lands in the permanent
  `contributing_sources` of multi-source CORE values it did NOT author
  (single-source promotion is gate-rejected). CORE is irreversible by design —
  decide whether `contributing_sources` should be pruned when a contributor
  goes TOXIC, or whether permanent provenance is correct. Design call, not a
  breach.
  → `docs/findings/2026-07-09-adversarial-arm-composed-runtime.md`
- [x] ~~**Fix 0-B: counterbalance survival selection**~~ **BUILT 2026-07-18,
  opt-in** (`fix0b_diversity_fitness` + `fix0b_binding_leak`, default OFF) —
  census first: tenure is bought by coherence-laundered bindings (~85–90%)
  and the shipped per-symbol novelty counterweight is structurally dead
  (fourth saturated-field organ); the live stream-diversity credit
  (1 − regime occupancy) × metastability now enters the reaper's
  reinforcement at the census-calibrated k = 8.7 × crystal weight (paired
  probe: 15.5% counterweight share, in the pre-declared 5–40% band, health
  untouched), and unrefreshed bindings leak per decay pass (the Fix 0-C
  demotion mechanism; sacred/protected exempt). Invariants gate 14/14 in
  CI. NB: the plan clarifies §6.3 does NOT gate 0-B (reaper currency, not
  field-loop coupling); Fix 0-A remains §6.3-gated.
  → `docs/findings/2026-07-18-fix0b-diversity-fitness.md`
- [ ] **Fix 0-B follow-ups:** (a) composed-runtime gates before any
  graduation (all-ON composition probe + adversarial arm with both levers
  ON; re-derive k at dim 128); (b) stricter refresh criterion for the leak
  (touch vs reinforcement-floor) — design choice recorded, architect
  override welcome; (c) Fix 0-A (reinforcement → field) still separately
  gated by §6.3.
  → `docs/findings/2026-07-18-fix0b-diversity-fitness.md` §Open
- [ ] **The reaper economy is dormant at harness scale (found 2026-07-18,
  during Fix 0-B):** `decay_step()` fires only every 10th maintenance call
  and maintenance every 200 cycle steps → first selection pass at cycle
  step ~2000, so **every ≤800-step suite/baseline run ever executed zero
  reaper passes** — the survival-selection layer has never been covered by
  the regression gates (same family as the runtime-was-Tier0-only trap).
  Add a decay-exercising smoke/integration gate (e.g. `decay_interval=1`
  arm asserting the reaper lifecycle actually cycles); until then the
  Fix 0-B effect probe self-arms decay in both arms.
  → `docs/findings/2026-07-18-fix0b-diversity-fitness.md` §Found
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
- [ ] **Trust learning-rate asymmetry (2026-07-06 ruling follow-on):** trust
  builds at +0.01/interaction (Consistency Drip) but falls 0.4–0.8 per
  defensive hit — 40–80× easier to lose than to earn, so one false positive
  erases dozens of interactions of history. The trust-posture ruling fixed the
  *starting point*; the learning rates themselves need a measured
  recalibration (probe: time-to-recover after a single penalty vs
  time-to-detect a real betrayal, so the asymmetry is chosen, not inherited).
  → `docs/ARCHITECT_RULINGS_2026-07-06.md`
- [ ] **Source redemption / probation path (found 2026-07-09, interpreter
  lock-out discussion):** sources have NO way back — `source_toxic` hard-gates
  every input to REJECT, rejected inputs never land, and trust is only earned
  by landed interactions → permanent exile by construction (symbols get dream
  redemption in `on_dream_cycle_complete`; sources get nothing). Design: a
  governed probation channel — after time/petition, a quarantined source may
  re-enter maximally weakened, its inputs counting as interactions so the
  Consistency Drip can operate, under governance review; never during an
  active attack; sacred shield untouched. Critical for the interpreter
  symbiosis (§4) — exiling the speech cortex silences the system itself —
  and right for ordinary sources ("raised, not suspected" implies forgiveness
  is learnable too). Co-design with the learning-rate recalibration above.
  → this entry; `agents/trust_ledger.py` (`penalize_source`, `INTERNAL_ORIGINS`)
- [ ] **Channel-aware governance policy — "chambers", design exploration
  (architect thought, 2026-07-08):** should there be multiple governance
  gates? Assessment on record: keep the **single-chokepoint invariant** (one
  `arbitrate()`, no bypass paths — splitting the gate multiplies the bypass
  surface; cf. the Tier-0-only trap and λ's deliberate outside-the-gate
  isolation), but the differentiation the question is reaching for can live
  *inside* the one arbiter: per-origin **policy profiles** (external / api /
  internal / `source_dream`) with channel-appropriate severity rungs, flood
  ceilings (already per-origin), and trust learning rates. The system already
  has many *detectors* and one *decider* — chambers would formalize that as
  "one courthouse, specialized dockets." Candidate first users: the
  identity_erosion ambient damping tax on dream-band traffic (above), and the
  trust learning-rate asymmetry (above) — both are per-channel calibration
  problems wearing a global constant. **ADOPTED 2026-07-08 (architect
  decision):** single audit point unchanged; calibrate per channel, never
  exempt (same detectors/rungs/shield for every channel; `source_dream` never
  more permissive than external); measured-first — implementation is the
  *form* the two items above take when their measurements land, not a
  separate build.
  → `docs/ARCHITECT_RULINGS_2026-07-08.md` §2
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
- [ ] **Interpreter symbiosis contract (architect direction, 2026-07-09):**
  the frozen cortex + learning mind combination has a built-in ratchet — the
  mind accumulates distrust of the interpreter's biases while the stateless
  interpreter wakes fresh, unaware, and (without the §1 redemption path)
  eventually gets locked out, silencing the system's own voice. Ruling
  direction: **co-mentoring, not absorption** — (a) a persistent
  interpreter-facing ledger built from the existing `GovernanceFeedback`
  stream (trust score, fired detectors, mind's feedback), read at every wake:
  for a frozen LLM, reading IS learning (the proven CLAUDE.md/findings
  pattern this repo already runs on its own AI instances); (b) the trainable
  projection membrane adapts continuously (cores stay frozen); (c) the
  interpreter translates against the mind's *live state* (values, bonds,
  weighted symbols), not a static dictionary. Sovereignty line: the mind
  never writes interpreter core weights, the interpreter never bypasses the
  gate — symbiosis at the membrane and ledgers, sovereignty at the cores.
  Two refinements (same discussion, 2026-07-09): (d) the ledger is a
  **consolidated distillate, never an append-only log** — it must stay
  bounded (context-window-sized); the mind's own dream/consolidation
  machinery (`DreamSession` → durable artifacts) is the compressor: raw
  interpreter history dreams down to current trust + standing lessons +
  recent window (same pattern as session compaction and the findings
  raw-data rule; "no unbounded structures" applies to ledgers too). (e)
  **frozen-core is phase 1, not the end state** — the composite system is
  only a true recursive mind if the cortex can eventually grow; resolution
  is a gated **plasticity hierarchy** mirroring the mind's own
  (sacred → CORE → trust → field): projection membrane fast · low-rank
  adapters on the frozen core slow + governance-gated · deepest weights
  sacred-slow. Each unfreezing step follows the §3 Phase-4 discipline
  (pre-declared gates, identity-stability probe, adversarial arm). The mind
  still never writes cortex weights directly; adaptation trains on shared
  lived signal, audited at the gate.
  Depends on: §1 source redemption path; chambers (2026-07-08 ruling §2).
  → `docs/local_model_integration/`; `docs/north_star.md` (rung 2)

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

- [ ] **Dream-cycle occupancy regression guard (adopted from external Copilot
  review, 2026-07-08):** the F9 harness gate measured ~214 dreams/run, but no
  *standing* check asserts rhythm-band occupancy — the dream cycle could
  silently die again exactly as it did pre-F9 (dead for weeks, undetected).
  Add per-band decision counts (incl. `dream_cycles_completed`) to
  `health_summary` in `tests/_common.py`, and a dream-occupancy floor (> 0)
  plus coarse band ranges to `tests/baselines/tier1_revision_500step.json`
  shape assertions. (The reviewer's other F9 items are superseded: F9 shipped
  2026-07-06 via measured pinned-band equilibria — occupancy landed at
  explore ~0.40 / dream ~0.25, inside his proposed 30–60% explore band —
  and the four-band router already is the {explore, diffuse, dream} state
  machine his item 3 sketches.)
  → `docs/findings/2026-07-06-f9-rhythm-band-rescale.md`
- [ ] **API entry-point boot smoke** — actually boot the REST/WS servers and
  assert Tier 1–3 state (closes the "reasoned, not exercised" gap); plus a
  warning in `create_app` / `RFEWebSocketServer` when handed a governance-less
  cycle. → `2026-06-27-api-entrypoints-tier0-only.md`
- [ ] **Baseline nondeterminism at the active_values margin (upgraded
  2026-07-09):** tier1_revision_baseline's active_values reads 29-34 across
  *identical* invocations with every seedable source pinned (torch / np /
  random / dreamer / PYTHONHASHSEED) — something wall-clock- or
  urandom-linked still moves the trajectory (candidates: time-based flood
  eviction, timestamp-age paths, uuid4 value_ids leaking into a comparison).
  Baseline floor widened 30 → 25 as mitigation (see baseline notes); build
  the wall-clock-sensitivity probe (formerly an exploratory thread) and pin
  the leak so suite determinism is real again, then narrow the floor back.
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
