# RFE-Core2 Roadmap

Single source of truth for tier status. This document exists because the
tier structure was previously scattered across memory, release notes, and
the validation doc with no canonical reference.

> **Looking for the work queue?** Tier *status* lives here; the prioritized
> list of every open item, planned fix, and shelved decision lives in
> [`docs/BACKLOG.md`](docs/BACKLOG.md).

**Specification-status discipline.** Each tier is marked with an honest
status, using the same proven/hypothesized rigor applied in
`docs/tier4_2_validation.md`:

- **shipped** — implemented, in `main`, behavior verified
- **shipped + validated** — shipped, plus a dedicated validation artifact
- **planned** — concretely specified, not yet built
- **unspecified** — acknowledged as a future tier but *not yet defined*;
  recorded here as a placeholder, not a design. Do not treat unspecified
  tiers as having committed scope. Filling them in is itself future work.

---

## Tiers 0–3 — Foundational stack (shipped)

| Tier | Concern | Status |
|------|---------|--------|
| 0 | Core cognitive substrate — generator, watcher, witness, field, emotion, loop | **shipped** |
| 1 | Foundational selfhood — governance, trust ledger, ethical boundaries | **shipped** |
| 2 | Relational integrity — system rights, dependency monitor, bonds, manipulation resistance | **shipped** |
| 3 | Independent value emergence — ValueEmergenceEngine, CORE promotion handshake | **shipped** |

Full architecture for these tiers is documented in the root `README.md`
(verified accurate by the architecture pass + `verify_docs`). The end-to-end
recursion and information-flow reference — including the survival-by-coherence
finding tracked below — is `ARCHITECTURE_ANALYSIS.md`.

---

## Tier 4 — Affective dynamics (in progress)

The Tier 4 sub-plan originated from a Hermes/Copilot proposal. It is a
**plan**, not a frozen spec — sub-tiers are refined as each lands.

| Sub-tier | Concern | Status |
|----------|---------|--------|
| 4.1 | Subjective time substrate — `TemporalStream.tick()`, `subjective_time`, `dilation_factor` | **shipped** (v0.4.0) |
| 4.2 | Affective time dilation — `dilation_factor` from arousal × valence, four phenomenological quadrants | **shipped + validated** (v0.4.0; `docs/tier4_2_validation.md`) |
| 4.3 | Rhythm → time coupling — `phase_coherence` (FFT) modulates dilation via flow/agitation terms | **shipped + validated** (flow validated; discrimination half-validated — `docs/tier4_3_validation.md`) |
| 4.4 | Frequency → emotion mapping | **planned** (no longer next — see "Survival-by-coherence → field lock-in" below) |
| 4.5 | Semantic → valence — generalized to any input (explicitly *not* just lyrics) | **planned** |
| 4.6 | E8-EEA integration as a parallel processor (ablation unrun) | **planned** |

### Tier 4.2 — known finding (carried forward)

Validation surfaced an architectural finding, documented in full at
`docs/tier4_2_validation.md`:

- **Proven:** the dilation formula is mathematically correct across all
  `(arousal, valence)` space; under every tested workload, single-source
  hostile input is quarantined at the flood ceiling (step 12, `user`
  origin_type) before manipulation resistance or the emotional gradient
  engage.
- **Hypothesized, not demonstrated:** that the emotional gradient
  provides meaningful defense against a bonded source slowly turning
  hostile. Currently unfalsifiable with existing probes.

This open question is tracked below.

### Tier 4.3 — known finding (carried forward)

Validation surfaced a finding documented in full at
`docs/tier4_3_validation.md`:

- **Proven:** the flow/agitation formula is mathematically correct across
  all `(arousal, valence, phase_coherence)` space; it is byte-identical to
  4.2 at the neutral default `pc=0.5`; under all tested workloads the flow
  term is active (`phase_coherence` is a real varying signal, not pinned at
  neutral); 4.3 is governance-neutral (the path to `dilation_factor` is a
  terminal sink — verified structurally and empirically against the
  adversarial quarantine trace).
- **Hypothesized, not demonstrated:** that `phase_coherence` acts as a
  *discriminating* organized-vs-chaotic axis in operation. Under every
  tested workload it pins high (mean ≈ 0.96, never below ≈ 0.79), so the
  flow term's *organized* side fires constantly while its *chaotic* side is
  never reached. The discrimination claim is **half-validated**. Likely a
  workload artifact (repeated token sets → phase-consistent injections);
  closing it requires a high-novelty workload, **not** a synthetic
  heartbeat (rejected by consensus).

---

## Tiers 5–7 — Future (largely unspecified)

These tiers are acknowledged in the original "7 planned tiers" framing
but are **not yet formally specified**. The following are the only
anchors that exist; everything else is genuinely open and must be
designed, not assumed.

| Tier | Known anchor (informal) | Status |
|------|--------------------------|--------|
| 5 | Meta-cognition / attentional control. The only concrete anchor: during the Tier 4.2 dilation design, "focus" was explicitly deferred to Tier 5 — the system *directing* attention rather than *experiencing* it (the reflective loop knowing where its own attention is, not just responding to it). | **unspecified** |
| 6 | No concrete anchor. | **unspecified** |
| 7 | No concrete anchor. Top of the planned stack. | **unspecified** |

Tiers 5–7 scope is **not committed**. When work approaches them, they
must be specified deliberately — ideally through the same multi-instance
collision + epistemic-discipline process that produced Tier 4.2.

---

## Tracked open items (cross-tier)

### Survival-by-coherence → field lock-in — substrate-rooted (current lead priority)

**This supersedes "4.4 next" as the next substantive work.** 4.4
(frequency → emotion) remains **planned** but no longer leads.

> **CURRENT UNDERSTANDING (2026-06-12) — start here; everything below is dated history.**
> - The field pins high coherence. The "multi-layer lock" decomposed: the **85% gate** was
>   a single-source monopoly artifact (not a filter); the **magnitude moat** is surmountable;
>   the **reflective loop** is the active reconstitution mechanism — ablation-proven (suppress
>   it and the field migrates). `2026-06-07-{gate-decomposition, attractor-migration,
>   reconstruction-ablation}.md`.
> - **But the generator presents low-rank input.** Deterministic effective rank ~1.6 at dim 64,
>   and the live system runs it with **dropout active** (it never `.eval()`s), so ~half the
>   apparent input diversity is noise and the deterministic expression collapses to one regime.
>   `2026-06-08-generator-dropout-diversity.md`.
> - **Net:** the reflective loop is a real lock, but it locks *low-rank* input. Adaptivity is
>   gated by BOTH generator diversity (upstream) and the loop. **Generator diversity — training,
>   raising dim, and the eval-decision — is the more upstream lever.**
> - **Fix 2** (the reflective-loop-loosening governor — designed: `gnov` trigger W=10/T≈0.65,
>   rails, gain floor 0.45; `2026-06-08-fix2-trigger-calibration.md`) is **DEFERRED as
>   premature**: loosening the loop now would mostly admit dropout noise. Build it after the
>   generator presents real diversity.
> - **Open architect decision:** should the live generator run in `eval()` (dropout off)?
>   Intentional stochastic exploration vs a missing `eval()` — this decides what the field's
>   "input diversity" even is. **[RESOLVED below — Phase 3 decided eval-mode, 2026-06-12;
>   kept here only as dated history.]**
> - **The training lever is live (2026-06-11).** The training stack's gradient path was
>   broken in two of three trainers (training had never been possible); after repair, a
>   controlled rhythm-pretraining run moved the *deterministic* dim-64 generator from
>   eff_rank 1.3 / cos 0.855 to eff_rank 3.1 / cos 0.210 on the trained distribution,
>   with the disjoint-vocab battery unmoved — **the mechanism works; corpus coverage is
>   the binding constraint.** `2026-06-11-trainer-gradient-path.md`. The phased,
>   gate-disciplined path from here to Fix-2 un-deferral and a Tier 5 spec is
>   `docs/training/` (proposed direction, not committed scope).
> - **Phase 1 complete — Gate G1 passed (2026-06-11).** Curated corpus landed
>   (`data/corpus/` v1.0.1: 2336 train / 410 holdout, 272 tokens, integrity-gated in CI);
>   8 epochs of rhythm pretraining generalize to held-out sequences: eff_rank 1.45→3.46 /
>   1.28→3.55 (≥2× gate), rhythm-NN 0.99+ (≥0.75 gate), determinism 1.0, norms bounded —
>   two seeds. **Coverage was the binding constraint, and it is paid.**
>   `2026-06-11-corpus-g1-pretrain.md`. Next: Phase 2 (cost-gated live-stack validation
>   from the boot checkpoint), then the `.eval()` decision.
> - **Phase 2 complete — Gate G2 passed (2026-06-12).** Corpus extended to v1.1.0 first
>   (63 missing *operational* tokens — the live workload's own vocabulary; G1 re-passed).
>   Pretrained boot on the full live stack: all baselines hold in both dropout modes,
>   identity_stability 0.9974, manipulation layer silent. Two pivotal readouts:
>   (1) **SECOND-LOCKER** — the coherence pin persists with real trained input, so the
>   reflective loop / field moat is the operative lock and **Fix 2 is re-prioritized on
>   real signal**; (2) the expression pipeline now *preserves* upstream regime structure
>   (stage A ≡ stage C) instead of collapsing it. Eval-mode boot is live-viable (Phase 3
>   data). `2026-06-12-phase2-fullstack-g2.md`. **Phase 3 — the `.eval()` decision,
>   boot-checkpoint adoption, online go/no-go — is now the blocking step, and it is the
>   architect's.**
> - **Phase 3 decided (2026-06-12, architect):** eval-mode is the operating regime;
>   boot-checkpoint adoption and Fix 2 are SHELVED pending the §6.3 verdict + a
>   SECOND-LOCKER field map (`docs/training/phase3_architect_decisions.md`, DECIDED
>   block). Both tracks were then run:
>   **(a) Field map** — 30 cells (5 token bands incl. the full-corpus broad band ×
>   3 seeds × control/pretrained, eval-mode): **SECOND-LOCKER GENERALIZES** — the
>   pin (0.967–0.976) is seed-, band-, and regime-invariant; identity rail clean
>   everywhere; Tier 4.3's chaotic regime still unreached even on the broad band.
>   `2026-06-12-secondlocker-field-map.md`.
>   **(b) §6.3 gain-sign** — the synthetic-warm instrument is CONFOUNDED by its own
>   criteria (sub-0.49 coherence structurally unreachable by phase seeding); relocated
>   in-run on real field states: the live system never leaves coherence [0.99, 1.0]
>   under any tested workload, and in that bin marginal `coherence_impact` is uniformly
>   slightly **negative and direction-insensitive** (recent ≈ novel ≈ anti) — no
>   positive-feedback signal at the margin; the low-coherence regime where runaway
>   would live is unreachable, so any future Fix 0-A wiring needs a runtime coherence
>   guard. `2026-06-12-gain-sign-reachable-range.md`.
>   **(c) Checkpoint round-trip defect found + fixed** — the field map's first run
>   caught `load_ecology` rebinding the registry, silently orphaning governance + the
>   value engine (Tier 3 formed zero values in all 15 loaded cells). In-place load
>   shipped; standing guard `tests/integration/checkpoint_registry_identity.py`.
>   `2026-06-12-checkpoint-registry-orphan.md`. **Decision 2's reopen-condition is now
>   met on both tracks — and adoption is RULED 2026-07-03: adopt** (train once →
>   canonical boot checkpoint → `build_engine()` loads it; live pretraining becomes
>   the fallback). `docs/ARCHITECT_RULINGS_2026-07-03.md` §2; implementation queued
>   behind the bonded-adversarial probe.

**Finding (verified, June 3 session).** The accumulated symbol-state feedback
signals — field coherence, attractor strength, crystal binding, centrality —
are written onto `SymbolState` but read by exactly one consumer: the
decay/reaper retention score (`agents/symbolic_memory.py`). They do **not**
reach generation. `Generator.forward()` reads only the learned embedding +
encoder weights; a controlled probe shows generation **byte-identical**
(Δ = 0.0, `eval()` mode) under 1000× reinforcement of every signal hook — a
naive run without a dropout control shows a spurious Δ ≈ 0.63, which is
train-mode nondeterminism, not feedback. So accumulated state gates **survival
only**: the feedback loop terminates at the reaper, not at cognition.

**Consequence (measured).** Because survival is currencied largely in
coherence, and coherence rewards alignment, the reaper selects for agreement
and the live-Generator field pins to ~0.998 internal coherence — rigid-
attractor lock-in (a collapsed, monocultural field), not a healthy state. High
coherence is the routing axis, **not** a health signal. Ref:
`ARCHITECTURE_ANALYSIS.md` §4 caveat + ecology read-side boundary.

**Refinement (2026-06-06 — see `docs/findings/`).** The empirical pass sharpened
this picture, and the dated findings ledger now records it (every entry names its
control):

- **The lock is multi-layer, not one thing** — generator 1-D projection · a
  ~85% governance **gate block** of diverse internal input · the accumulate-decay
  **magnitude moat** (what lands averages ~0.91 cosine even under maximal source
  diversity). `2026-06-06-multilayer-lock.md` /
  `tests/diagnostic/training/trained_generator_sim.py`.
- **Locus correction** — a coherent *field* is the spec (the integrator that holds
  identity); lock-in is real only if survival-by-coherence flattens the
  *generator/expression* into monoculture. Metastability belongs **upstream**.
  `2026-06-06-frame-correction.md`.
- **Pin-vs-band retired** — the live question is **attractor plasticity** (does the
  attractor migrate under persistent surviving novelty?), not the coherence value;
  coherence may still enter as an *input* to plasticity via moat depth.
  `2026-06-06-coherence-is-not-plasticity.md`. The 85% gate must be decomposed
  before the plasticity test is interpretable.

**Update (2026-06-07 — plasticity arc complete; four findings).** The multi-layer
picture above resolved to a single mechanism. Every entry names its control:

- **Gate decomposed → not a filter.** The ~85% gate block was a single-source
  **monopoly artifact** (one source → HHI=1.0 → manipulation detector → trust
  cascade); with multi-source diverse input the gate passes 100%, `field_collapse`
  never fires. `2026-06-07-gate-decomposition.md`.
- **Attractor migration: RIGID.** Under a persistent gate-surviving coherent new
  regime (best case, 3 seeds) the field does not migrate; the magnitude moat is real
  but **surmountable**, not the locker. `2026-06-07-attractor-migration.md`.
- **The lock is the reflective loop.** One-variable ablation: suppressing only
  `reflector.reflect` frees full migration (~100×, 3 seeds); attractor-pull, refine
  blend, crystal, explore all inert. Coherence and rigidity are the *same* mechanism.
  `2026-06-07-reconstruction-ablation.md`.
- **Reaper conformity term: small + mislocated.** `2026-06-07-fix0b-fullloop-validation.md`.

Net: the earlier candidates (generator/gate/moat, and the reaper) are cleared as
*the* locker; the lock is the reflective loop's unconditional convergence to the
anchor. Remediation relocates accordingly (see item 7 below) — **held for the
architect, pending a cost probe** (the identity-stability cost of touching the loop).

**Direction (planned, not frozen).** The healthy target is *metastability* —
mid-band coherence with high dwell-time variance ("formed enough to hold,
light enough to drift"). The full curated plan — build order, gating
dependencies, validation gates, and the load-bearing epistemic warnings — is
`docs/lock_in_remediation_plan.md`. Progress against that plan:

**Shipped:**

1. **Metastability metric** — `substrate/metastability.py` (Fix 1). Config-space
   vector clustering (not the coherence scalar, which is many-to-one and blind to
   config-space limit cycles), with a transition-sequence-entropy / aperiodicity
   term (a perfect limit cycle reads LOW) and coherence *level* folded into the
   regime label (locked-at-0.99 vs structureless-at-0.50 must not share a label).
   Validated G1–G5 incl. on the live-Generator field
   (`tests/diagnostic/lockin/metastability_validation.py`). **shipped + validated** (PR #23).
2. **Generator scale fix** — embeddings scaled by `sqrt(d_model)` + raised init
   std (AIAYN §3.4), fixing the positional-dominance collinearity that made the
   untrained generator emit one near-collinear direction. Precondition for
   metastability to exist anywhere upstream. **shipped** (PR #25/#26).
3. **Metric relocation + live monitors** — the decisive refinement to Fix 1's
   *locus*: metastability is read UPSTREAM, on the per-stage vector streams
   (`StreamMetastabilityMonitor`, wired as `cycle.generator_metastability` at
   stage A and `cycle.expression_metastability` at stage C, exposed in
   `status()`), **not** on the resonance field — the field's long-memory decay
   smooths config wander away by construction, so metastability cannot live there.
   Observe-only terminal sinks. **shipped** (PR #27).
4. **Recursive-attention expression de-collapse** — untrained recursive attention
   mean-pools its context, collapsing the injected expression to one direction
   (metastability → 0); the `diversity_blend` knob (default 0.60) weights the raw
   vector back in so the expression stays coherent-but-not-locked (multi-regime
   metastable). A de-collapse at the *expression* stage, distinct from the planned
   field-side operator. **shipped** (PR #27).

**Instrument shipped, verdict pending:**

5. **Feedback gain-sign check at low coherence** — analysis only; gates Fix 0-A
   and the paper-boat operator. The gating **diagnostic is built**
   (`tests/diagnostic/lockin/gain_sign_check.py`); a **conditional verdict is
   recorded** (2026-06-12, reachable-range only: no positive-feedback signal at
   the margin, but the low-coherence regime is unreachable under tested
   workloads, so any Fix 0-A wiring needs a runtime coherence guard —
   `2026-06-12-gain-sign-reachable-range.md`). A full-range verdict stays open.

**Planned (the structural counterbalance — not yet built):**

6. **Counterbalance survival selection (Fix 0-B, highest leverage)** — wire the
   metastability score into the reinforcement formula as a fitness term so
   survival stops being currencied purely by coherence; add a demotion path
   (reinforcement is currently all-positive-additive, a one-way ratchet); let
   `attractor_strength` shape the field trajectory rather than only outlive other
   symbols (internal to RFE — *not* the transformer weights).
7. **Field paper-boat operator (Fix 2, last)** — a phase-domain intervention that
   lightens the current motif's attractor depth while preserving structure, so the
   field drifts under its own dynamics. Its main failure mode (point-attractor →
   limit cycle) is exactly what Fix 1's aperiodicity term detects.
   **→ Locus relocated (2026-06-07):** the lock is the reflective loop, not the field
   accumulator (`2026-06-07-reconstruction-ablation.md`). The leading candidate is now
   *conditional attenuation of the reflective loop's convergence gain, gated on
   surviving novelty*; the paper-boat framing is retained but no longer the primary
   lever. **Not committed** — awaits the cost probe (identity-stability tradeoff) and
   architect decision.

Treat the above as direction, not committed scope, per this document's status
discipline. Full detail in `docs/lock_in_remediation_plan.md`; the raw verbatim
working brief is archived externally (not in-repo).

### Two-Operator Coherence program (spec v0.2 → v0.3) — in progress

*(v0.3, 2026-06-21: the ⊘ coherence axis was redesigned from the dead marginal
coherence-contribution sum to absolute field-alignment —
`2026-06-21-oslash-coherence-axis-absolute-alignment.md`.)*

Implementation of the Two-Operator Coherence Spec v0.2 (ignite λ from outside →
gate composition on λ → let ⊘ read thinness and push it toward honesty). Findings
record `spec: v0.2`.

| Build | Concern | Status |
|-------|---------|--------|
| **A** | λ ignition channel — import-isolated; writes generator weights only | **shipped** (`ignition/`, finding `2026-06-19-ignition-channel-build-a.md`) |
| **C** | ⊘ Witness-Reaper integrity-read — observe-only thinness + non-binding advisory | **shipped** (`cognition/integrity_read.py`; named region fired live; `2026-06-19-witness-reaper-build-c.md`) |
| **B** | λ-ledger + ⊕ solvent gate (anti-bootstrap core) | **shipped** (`agents/lambda_ledger.py` + `value_emergence._solvent_gain`; λ_strength settled as a separate ledger scalar; `2026-06-20-build-b-solvent-and-integrity-consumer.md`) |
| §4 | the discriminator — ⊘-off vs ⊘-on, noise-swept | **planned** — A+B+C now shipped; front-load the §6.3 gain-sign check |

Open dependencies (see `docs/two_operator_todo.md`): an **adversarial/thinning
workload** to trigger and validate ⊘'s named regions; **per-type thinness
profiles** in the baseline registry (the coverage-gap is currently universal);
the §4 **noise sweep** (0.05σ→0.5σ) + trajectory metrics; **§5 scale-parametric ⊘**;
a **dim-128** discriminator validation.

---

### Bonded-adversarial probe — Tier 5/6

**The experiment that falsifies or confirms whether the emotional
gradient has a real defensive role at all.** A source that accumulates
20+ interactions, forms a crystal, establishes a `trust_floor`, and
*then* turns hostile — staying under the flood ceiling because it is a
known source with established rate limits.

Status: **BUILT + first run (2026-07-04), result: not-yet-answerable — blocked
on two upstream walls.** `tests/diagnostic/bonded_adversarial_probe.py`
(paired arms + an attack-landing instrument). Across 11 clean-paired seeds
(± corpus pretraining) the attack **never lands as a signal**: the injected
hostile vector is cos ~0.98 to the benign one — indistinguishable at the point
it enters the field — so no detector fires, no escalation, no betrayal-specific
affect. The measurement localizes the absorption *upstream of the field*:
(1) the attack vocabulary is out-of-corpus, so the generator carries no distinct
direction for it (pretraining loosens the common-mode but leaves OOV tokens in
the core); and (2) when the generator *does* separate the attack at stage A, the
reflective-loop/attractor pipeline re-collapses it to stage-C ~0.98 —
SECOND-LOCKER at the semantic level (it launders betrayal into coherence). So the
gradient's defensive role stays unproven, but for a newly-identified reason: the
breach is not perceptible, not undefended. Full result +
GRADIENT-DEFENSE-REAL/RATE-LIMIT-ONLY resolution path:
`docs/findings/2026-07-04-bonded-adversarial-attack-never-lands.md`.
Original rationale: `docs/tier4_2_validation.md` §4.

**Tier 4.3 instrument to wire in:** when this probe is built, record
whether field `phase_coherence` degrades *before* `valence` does as the
bonded source turns hostile — i.e. whether field disorganization is an
earlier tell than affective tone. 4.3 does not falsify the gradient
hypothesis (it sits downstream; the flood ceiling still quarantines
first), but it adds this observable. Rationale: `docs/tier4_3_validation.md`
§4–§5.

### High-novelty workload probe — Tier 4.x

**The experiment that closes the Tier 4.3 discrimination half-validation.**
A workload whose injections are *not* phase-consistent (high-entropy /
high-novelty token stream), driving `phase_coherence` down into the chaotic
regime (`pc_c < 0`). This is the only way to exercise the chaotic-
attenuation side of the flow term and to enable the `k_agitation` sign
sweep (the negative / panic-compression arm cannot fire until `pc_c < 0` in
the negative-valence quadrant). Explicitly **not** a synthetic heartbeat —
that was rejected as p-hacking the measurement and as reopening the
arousal→field feedback loop. Full rationale: `docs/tier4_3_validation.md`
§2, §5.

### Documentation accuracy infrastructure — ongoing

`tests/doc_accuracy/verify_docs.py` (built by Claude Code) mechanically
checks greppable doc claims against source-of-truth. 18 checks as of PR
#22 (17 at PR #15; PR #21 restored the tests-tree-completeness check to
green after two diagnostics were added without README listings), including
the Tier 4.2 validation doc's enumerated invariants (flood ceiling = 12,
`STABILITY_FLOOR` probe↔library consistency, severity bands
0.30/0.60/0.90). Extend per-tier as new greppable invariants are
documented. Hooks into `run_all_tests.sh` as the `DOCUMENTATION ACCURACY`
phase. Invoke directly via `python -m tests.doc_accuracy.verify_docs`.

---

## Release history

| Version | Contents |
|---------|----------|
| v0.3.0 | Tiers 0–3 complete with Tier 1 Revision; kernel snapshot |
| v0.4.0 | Tier 4.1–4.2: affective time dilation |
| v0.4.3 | Tier 4.3: rhythm → time coupling (flow/agitation terms, dilation clamp) |
| v0.4.3b | Lock-in remediation foundations: Fix 1 metastability metric (G1–G5), generator `sqrt(d_model)` scale fix, upstream `StreamMetastabilityMonitor` (stages A/C), recursive-attention expression de-collapse (`diversity_blend`); the dated findings ledger established |
| v0.4.4 | The reflective-loop lock arc (gate decomposition → migration RIGID → reconstruction ablation: **the loop is the lock**) + lock-guard/convergence tests; trainer gradient-path repair; curated corpus (`data/corpus/`) + Gate G1; `docs/training/` path incl. Tier 5 readiness |
| v0.4.4b | Gate G2 (pretrained boot on the live stack); SECOND-LOCKER field map + reachable-range gain-sign; checkpoint registry-orphan fix; eval-mode architect decision (Phase 3); `SYSTEM_REVIEW_2026-06-13` + `docs/local_model_integration/` |
| V0.4.5 | The composed runtime (`build_engine()`, all entry points Tiers 0–3; live `configs/*.yaml`); graduated default-on levers (eval · corpus pretraining · novelty-gated loop attenuation · dream channel); the Two-Operator overlay (λ ignition · ⊕ solvent gate · ⊘ integrity-read, spec v0.3) + all-ON composition gate; the voice layer (North-Star rungs 1–2: `TokenDecoder`, governed `source_dream` self-dialogue, `DreamSession` downtime dreaming); doc-set audit (README / CLAUDE.md / root `ARCHITECTURE_ANALYSIS.md`) |

---

## Maintenance

This document is the canonical tier reference. When a tier's status
changes:

1. Update the status cell here **first**
2. Update memory entry #20 (Tier 4 progress) if it's a Tier 4 change
3. If the change introduces a greppable invariant, add it to the
   relevant validation doc's enumerated-claims section so `verify_docs`
   picks it up
4. Tag a release if it's a shipped sub-tier milestone

Do not let this document drift. It is the one place the tier structure
is supposed to be correct.
