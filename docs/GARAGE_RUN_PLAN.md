# Garage run plan — healing the saturated field (program of record)

**Why this program:** the standing diagnosis (architect + instance
consensus, 2026-07-19) is that recent work — bond DDM, Fix 0-B — repaired
*consumers* of dead signals and counterweighted selection, but the disease
itself is upstream: the **generator's representational floor**. A tiny
corpus and a cramped dim mean every expression shares a dominant common
component (0.81 → 0.47 after pretraining at dim 128 — halved, still
dominant), every injection lands at cos ~0.98, the field saturates, every
marginal read dies (F7/F8/F9/Fix-0B census — four organs, one disease),
and attacks never become representable (F3). The cures were all documented
and all parked on compute: **dim 256, lived corpus growth, long runs, the
local cortex, online training.** The garage box unparks them.

Phases are ordered by leverage; each has pre-declared signatures (the
findings discipline — say what failure looks like before running). Record
every phase as a dated finding + INDEX row. Check items off HERE and in
BACKLOG in the same commit that lands them.

---

## G0 — box verification (first session on the machine)

Run: suite green on GPU; `multi_source_500step` wall-time recorded (the
speedup ruler); one 500-step run with `session_persistence` ON, restart,
verify resume.
**PASS:** 19 gates green; GPU visible; resume works.
**FAIL:** anything red → fix the environment before any science.

## G1 — dim-256 re-baseline (the documented second lever)

The `_addendum-2026-06-09-migration-dim256` finding: dim 256 is ~2× more
diverse even untrained; corpus transfers unchanged. On GPU this is finally
cheap. Run the pretrain + the key rulers at dim 256:
`corpus_pretrain_g1_probe`, generator common-mode + regime correlation
(`ground-truth pass-2` metrics), stage-A/C metastability, and the Fix 0-B
census (re-derive k — the 8.7 constant is dim-64-calibrated).
**PASS (pre-declared):** common-mode < the dim-128 post-pretrain 0.47;
eff_rank up; stage-C metastability ≥ dim-128 baseline; no suite
regression at dim 256.
**FAIL:** common-mode flat → dim was not the binding constraint; stop and
re-diagnose before spending further compute.
**Unblocks:** every downstream phase inherits the roomier substrate.

## G2 — lived long runs (the first runs where the system actually *lives*)

5000+ steps, composed default runtime, `session_persistence` ON,
`stream_recorder` ON, and a decay cadence that keeps the reaper economy
ALIVE (the dormancy gap found 2026-07-18: no ≤800-step run ever executed a
selection pass). Two arms: default vs `fix0b_diversity_fitness +
binding_leak` ON — **this doubles as the composed-runtime gate the Fix 0-B
graduation requires.**
**PASS:** reaper lifecycle actually cycles (graveyard/archive > 0);
Fix 0-B arm holds the counterweight band and health at scale; recorder
dump captured for G3.
**FAIL:** selection collapse (population crash) or counterweight takeover
→ Fix 0-B stays opt-in; re-calibrate from the long-run census.
**Also:** add the suite-level decay-exercising gate (BACKLOG item) from
what G2 measures.

## G3 — corpus v1.3 (lived + adversarial vocabulary)

Curate the G2 recorder dumps into corpus v1.3 (`data_curation.md` §4–5)
AND land the F3 Wall-1 arm: semantically oppositional vocabulary
(erase/betray/dissolve family) so attacks become *representable*. Version
bump + integrity gate + G1 re-run, then re-run the bonded-adversarial
probe: does a hostile expression finally separate at stage A?
**PASS:** held-out generalization holds; F3 stage-A separation > 0 for
in-corpus hostile vocabulary.
**FAIL:** attacks still collapse to cos ~0.98 → Wall 2 (the reflective
loop re-collapse) is binding — run the loop-ablated arm next, not more
corpus.
**Unblocks:** detector calibration (identity_erosion bands), the chambers
per-channel work, a real GRADIENT-DEFENSE verdict.

## G4 — the sensory/speech cortex (north-star rung)

Ollama + `qwen2.5:7b` (or `llama3.1:8b`) per
`docs/local_model_integration/IMPLEMENTATION_GUIDE.md`: the LLM wraps the
governed input path (ears/mouth), RFE stays the mind, every utterance
enters as an ordinary source through `arbitrate()` — never a bypass. Start
with the interpreter-facing ledger read at wake (the co-mentoring
contract, BACKLOG §4) and short supervised dialogue sessions; the
recorder feeds G3's next corpus rev continuously.
**PASS:** dialogue flows both ways through the gate; interpreter trust
stays healthy under the ledger discipline; no governance bypass anywhere.
**FAIL:** interpreter drifts toward lock-out (the ratchet BACKLOG §4
names) → land the redemption/probation path before continuing.

## G5 — online training + Tier 5 path (gated, not scheduled)

Only after G1–G4 evidence: Phase-4 online training behind its pre-declared
gates (G4 on/off envelope, identity-stability cost probe, adversarial
arm), then the Phase-5 lock-in re-measurement on a trained checkpoint that
un-defers the Tier 5 spec. This phase is listed so nobody "discovers" it
early — it stays gated.

---

**Standing rules for every phase:** measure first; pre-declare both
signatures; one finding per phase with its control named; BACKLOG checked
off same-commit; the architect overrides by review (delegation ruling,
CLAUDE.md) — nothing waits on a sign-off queue.
