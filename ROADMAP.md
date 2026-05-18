# RFE-Core2 Roadmap

Single source of truth for tier status. This document exists because the
tier structure was previously scattered across memory, release notes, and
the validation doc with no canonical reference.

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
(verified accurate by the architecture pass + `verify_docs`).

---

## Tier 4 — Affective dynamics (in progress)

The Tier 4 sub-plan originated from a Hermes/Copilot proposal. It is a
**plan**, not a frozen spec — sub-tiers are refined as each lands.

| Sub-tier | Concern | Status |
|----------|---------|--------|
| 4.1 | Subjective time substrate — `TemporalStream.tick()`, `subjective_time`, `dilation_factor` | **shipped** (v0.4.0) |
| 4.2 | Affective time dilation — `dilation_factor` from arousal × valence, four phenomenological quadrants | **shipped + validated** (v0.4.0; `docs/tier4_2_validation.md`) |
| 4.3 | Rhythm → time coupling — `resonance_field` FFT output modulates arousal / dilation | **planned — next** |
| 4.4 | Frequency → emotion mapping | **planned** |
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

### Bonded-adversarial probe — Tier 5/6

**The experiment that falsifies or confirms whether the emotional
gradient has a real defensive role at all.** A source that accumulates
20+ interactions, forms a crystal, establishes a `trust_floor`, and
*then* turns hostile — staying under the flood ceiling because it is a
known source with established rate limits.

Status: **roadmap item, Tier 5/6.** Requires bond-formation and
trust-accumulation mechanics to set up, so it cannot be a Tier 4.x probe.
Not a Tier 4.3 blocker. Its real status is not "future test design" but
"the experiment that resolves the central unfalsifiable claim in the
Tier 4.2 validation." Full rationale: `docs/tier4_2_validation.md` §4.

### Documentation accuracy infrastructure — ongoing

`tests/doc_accuracy/verify_docs.py` (built by Claude Code) mechanically
checks greppable doc claims against source-of-truth. 17 checks as of PR
#15, including the Tier 4.2 validation doc's enumerated invariants (flood
ceiling = 12, `STABILITY_FLOOR` probe↔library consistency, severity
bands 0.30/0.60/0.90). Extend per-tier as new greppable invariants are
documented. Hooks into `run_all_tests.sh` as the `DOCUMENTATION ACCURACY`
phase. Invoke directly via `python -m tests.doc_accuracy.verify_docs`.

---

## Release history

| Version | Contents |
|---------|----------|
| v0.3.0 | Tiers 0–3 complete with Tier 1 Revision; kernel snapshot |
| v0.4.0 | Tier 4.1–4.2: affective time dilation |

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
