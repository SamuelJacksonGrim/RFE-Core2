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

Field lock-in was the **lead investigation for two months; it is now SETTLED** — see
`STATE.md` (§ SETTLED) and the findings ledger. Summary:

- **The lock is the reflective loop's active reconstitution, and it is by design** — the
  field is the long-memory identity integrator; the coherence pin is identity persistence,
  not a defect. `2026-06-07-reconstruction-ablation` (core), SECOND-LOCKER
  (`2026-06-12-phase2-fullstack-g2`, `-secondlocker-field-map`).
- **It cannot be unlocked upstream (generator / corpus).** Falsified via baseline / evened
  corpus / a verified separable rupture basin, plus a 5000-step run (`disp ≤ 0.00012`).
  `2026-08-04-rupture-and-the-lock-is-a-landscape-problem`. **Do not reopen.**
- **Metastability, if pursued, lives upstream** on the per-stage streams
  (`generator_metastability` / `expression_metastability`), never on the field.
  `2026-06-06-frame-correction`.

Live remediation items that remain (NOT the lock itself — the healthy-metastability program):

- **Fix 0-B** (metastability as a survival-fitness counterweight) — built, opt-in; gates on a
  composed-runtime run before graduation. `2026-07-18-fix0b-diversity-fitness`.
- **Fix 2** (reflective-loop convergence attenuation, novelty-gated) — **deferred as premature**
  (loosening now admits dropout noise); revive only after the generator presents real diversity.

Full curated plan: `docs/lock_in_remediation_plan.md`. Complete dated arc: `docs/findings/INDEX.md`.

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
