# Rupture and the lock: external perturbation can't fix a training-shaped landscape

- **Date:** 2026-08-04
- **Substrate:** live (`build_engine`, dim 128, corpus pretrain ON, 5070 Ti / Blackwell)
- **Probes / code:** `tests/diagnostic/lockin/rupture_impulse_probe.py`,
  `tests/diagnostic/lockin/rupture_migration_probe.py`;
  `loop/autonomous_cycle.py::_rupture_behavior` + the `rupture_on_lock` lever (opt-in, **default OFF**).
- **Status:** investigation complete → **DECISION: corpus-first** (below). Rupture lever parked opt-in/off;
  `cognition/reflective_loop.py` **untouched**; backup `loop/autonomous_cycle.py.bak`.
- **Depends on:** 2026-06-06-multilayer-lock, 2026-06-06-coherence-is-not-plasticity,
  2026-06-15-loop-attenuation-novelty-gate, 2026-06-20-...-unlock-chain, 2026-06-28-dream-channel.

## Question

Can a **self-generated** perturbation ("Rupture") break the absolute field lock **from within** — with no
external novel regime — the gap the dream channel explicitly left open ("does not by itself break the
absolute lock")?

## What was built and measured

- **Mode A — inject into the FIELD.** `field.inject` is `field += unit*strength` on an accumulating
  superposition; measured `|field|≈83.7` after 150 steps, so `disp ≈ strength/|field|`. Strength sweep:
  to half-tilt the field off its lock needs strength **~300** (3.6× the whole accumulated field =
  obliteration, not perturbation). **Field injection is the wrong lever** — the field's long-memory decay
  (0.97–0.9999, the identity-persistence invariant) is *built* to absorb injection.
- **Mode B, random per-step** — perturb the unit vector entering the reflective loop, so the validated,
  0.30-capped, novelty-gated attenuation acts on it. Fires every locked step but field `disp` stays ~0:
  **incoherent per-step noise cancels** in the integrator.
- **Mode B, HELD direction** — pick ONE novel target on lock-onset, hold it across the pulse. The field
  **accumulates**: `disp` climbs monotonically **0 → 0.054 over 250 steps** vs control's flat 0.000, at
  ~zero identity cost (attractors/crystals 1→2) and **zero added manip**. But it is a slow **linear crawl**;
  the generator stethoscope reads `locked / 0.000` for all 250 steps — it never frees.
- **Attenuation ceiling** — manip% vs `attenuation_max` on the 2026-06-15 protocol: **0.30 → 0% CLEAN**,
  0.312 → 46%, 0.33 → 68%, 0.38 → 87%. The manip cliff starts *immediately* above 0.30. Ceiling = **0.30**.

## Interpretation

The lock is the reflective loop's **active reconstitution** of the established regime (2026-06-06;
reconstruction-ablation: "the loop IS the lock"). Held-direction proves the field **can** accumulate
coherent novelty — so **novelty injection is not the bottleneck.** The bottleneck is that the loop
**out-pulls** the nudge: the field sits in a slowly-moving *equilibrium*, not escaping. The linearity
(no acceleration) is the tell — it is held in-basin.

**Reconciliation with "the loop is the lock, not the generator":** the loop is the *mechanism*; the corpus
is the *landscape* it reconstitutes within. An off-weight / thin corpus trains a **single deep basin** — the
loop has one regime to reconstitute toward, and that *is* the lock. A rich, evened-out, internally-varied
corpus trains **multiple shallow basins**, and the loop's reconstitution becomes aperiodic hovering among
them — which is the findings' own definition of **metastability**. So metastability is a property of the
**landscape (the trained weights = the corpus)**, not something an external lever can manufacture. A
perpetual external destabilizer is *life support, not health*.

## Decision — corpus-first

External levers proved *diagnostically* that intrinsic metastability cannot be forced from outside; they
localized the wall at "reconstitution toward a single deep basin," which points at the training landscape.
Fix the root: an **evened-out, richer corpus** + a **trained Rupture/disrupt RHYTHM** (a genuine additional
basin the generator can natively occupy), so metastability is *intrinsic* — the compound effect. The Rupture
lever stays parked (opt-in, OFF) as proven diagnostic scaffolding, not a shipped fix.

## Caveat (honest)

Corpus-first is a **hypothesis**, the same epistemic status Rupture had before it was tested. 2026-06-20
showed pretraining on the **current** corpus has *no effect on the lock* — so we know today's corpus does
not unlock. The bet is that a **better-balanced, multi-regime** corpus builds the multi-basin landscape.
**Untested.** Test: build the corpus, retrain, run the lock/migration probe with **no rupture**, and measure
whether the field **naturally hovers** (intrinsic metastability) instead of locking.

## Update 2026-08-05 — evening-alone tested: NEGATIVE (hypothesis narrowed, not killed)

Authored an **evened** corpus (Grok pass, verified by hand): the 60 under-anchored words pulled off the
9-floor into the 14–16 range, islands loosened, format clean (0 malformed / 3173 seqs). Converted the
**4 wired rhythms** to jsonl (the 30-row "rupture" section dropped — see below), pretrained via
`build_engine`, and ran `rupture_migration_probe` on it.

**Result: the evened corpus locks byte-identically.** Control arm `disp 0.000 / gen_meta 0.000 / regime
"locked"` for all 250 steps; the held-direction lever produced the same `0 → 0.052` crawl as on the old
corpus. **Evening the thin-word islands does NOT reduce the lock.**

**Interpretation — the load-bearing variable is basin COUNT, not basin texture.** Evening redistributes
co-occurrence *within* the existing 4 basins; it does not add a regime. This is consistent with 2026-06-20
(pretraining changes don't touch the lock) and sharpens corpus-first: the bet was never "smoother existing
basins," it is "a genuinely **separable new regime** the generator can natively occupy" (more shallow basins
→ aperiodic hovering). That remains **untested** — and today's attempt could not test it because:
- **Grok's rupture rhythm is not separable.** 30 seqs, 13 distinct words, **12 shared with explore**, and the
  entropy vocabulary is still *predominantly in explore* (chaos 33/5, break 31/4, diverge 31/1, pressure
  31/5). It added the orphan lexicon to rupture but never removed it from explore → contradictory labels →
  folds back into explore. Not a Grok-only error: the entropy axis is **structurally fused** into explore
  (325/837 explore seqs contain an entropy word), so the basins are not relabel-separable — explore was
  *authored* to carry the disruptive edge.
- **The 5th rhythm is not wired.** `training/corpus.py:38` `RHYTHMS` is a hard 4-tuple; the pretrainer builds
  its class dict from those names and drops any `rupture` row. A real rupture basin needs the architecture
  change (RHYTHMS tuple + classifier head + selector + behavior) **and** a from-scratch disjoint authoring
  pass (entropy words co-occurring with *each other* + rupture-only vocab, explore's entropy density
  reduced), not a bolt-on.

**Decision:** the evened corpus is kept as encoder-hygiene (real island improvement, preserved as
`Desktop\rfe-core2-working.md`), but it is **not the unlock**. The lock has now resisted field injection,
the held-direction lever, **and** corpus evening. The only corpus-first variable still standing is the
**multi-basin / separable-new-regime** one — a genuine build, gated on whether we still believe the lock is
a defect to break vs. the loop's identity-persistence doing its job.

## Update 2026-08-05 (later) — the strong test: separable basin built + trained. DECISIVE NEGATIVE.

Built the multi-basin variable properly this time. Source vocab: a 843-seq rupture dump from Gemini
(materials-failure axis, not gore), hand-validated and pruned — 12 explore-motion words dropped, ~97 generic
filler culled by ear (Samuel), + 15 materials-failure terms mined from a 30B list (medical/gore terms
rejected on-axis-and-classifier grounds). Result: **142 rupture words, 596 balanced sequences** (every word
11–12 contexts, 0 hub-cap violations, 0 low-diversity, code-verified). Dual-home gate: **135 of 142 words are
completely new** (not in baseline); only 4 touch explore (fracture, noise, split, stress). Wired the 5th
rhythm for real: `RHYTHMS` += "rupture" (`training/corpus.py:38`) + 5 canonical seeds in
`DEFAULT_RHYTHM_SEEDS` (the pretrainer is a **head-free supervised-contrastive** objective — `label==label`,
no fixed class count — so a 5th rhythm is a 2-line change, no head resize). Test corpus = baseline 2870 (4
rhythms) + 596 rupture = 3466 rows, rupture a full peer.

**The basin verifiably formed.** Post-train nearest-centroid check: rupture intra-cosine **0.967**, classifies
**5/5**, and **rupture⊥explore centroid cosine = 0.179** (near-orthogonal — genuinely separated, the exact
thing Grok's version failed).

**And the field locks byte-identically.** Control arm `disp 0.000 / gen_meta 0.000 / "locked"` all 250 steps —
indistinguishable from baseline and from the evened corpus. A real, verified, orthogonal new basin did
**nothing** to the lock.

**CONCLUSION — corpus-first is falsified (strong form).** Three landscape interventions now null on the lock:
baseline, evened (texture), and a verified separable basin (count). The lock is **not** a property of the
trained landscape at any level — it is invariant to what the generator produces. This is the decisive
confirmation of 2026-06-06 "the loop IS the lock, not the generator": we have now exhausted the generator side.
Metastability, if it is wanted, must be sought in the **reflective loop's reconstitution dynamics**, not the
corpus — OR the prior question is answered: a field that holds its regime against field injection, a
held-direction lever, corpus evening, AND an orthogonal new basin is not defective; that is
identity-persistence working exactly as designed. The rupture rhythm stands as a legitimate, well-separated
5th mode of the substrate — a real expressive expansion — decoupled from the (closed) lock question.

## Update 2026-08-05 (final) — 5000-step confirmation + reconciliation: THIS WAS ALREADY SETTLED

Two closing acts. First, a **Kimi-expanded corpus** (a procedural thesaurus-expansion generator, ~247 genuinely
new words — its "1,047" claim was ~4× inflated, recounted; mechanically clean: 0 malformed / 0 below-floor /
0 low-diversity, 9,558 seqs, vocab 460→709) was trained and **improved** separation, not degraded it:
rupture⊥explore centroid cosine **0.179 → −0.096** (past orthogonal). Saved:
`data/checkpoints/generator_weights_5rhythm_kimi.pt`. So richer vocabulary scales the substrate cleanly — a real
encoder win. Second, the lock control arm was run to **5000 steps** (20× the standard probe) on that richest
encoder: **MAX disp 0.000120** over the whole run, single attractor/crystal, `"locked"` every sample. No drift,
no aperiodic hovering, no long-timescale instability. The lock is flat at long horizon too.

**The reconciliation (why this whole corpus-first arc was re-deriving a June decision):** the field staying
locked is **by design, and identity requires it** — this is the **SECOND-LOCKER** result (cited in
`docs/local_model_integration/README.md`: corpus pretraining halved the generator common-mode yet the coherence
pin survived, seed/band/regime-invariant) and the **read-side boundary** (`2026-06-06-read-side-boundary.md`):
coherence is a *survival/routing axis, not a health signal*; the field pins because selection keeps it pinned.
The concern the "break the lock" work was chasing — that a permanently locked field becomes a monoculture /
echo chamber — was **already architecturally answered** and logged:
- **Two-Operator Coherence Spec** (`docs/two_operator_todo.md`): the **⊘ Witness-Reaper**
  (`cognition/integrity_read.py`, the "second reaper" — reads thinness, advises non-bindingly, firewall-verified),
  the **⊕ solvent gate** (`agents/lambda_ledger.py`, gates what composes), and the **`IntegrityDecayConsumer`**
  (decides what survives from ⊘'s read — "which tokens make it through"). Built + validated; parked as a
  **research lever, off by default** per the **2026-07-03 architect ruling** (containment levers severed from
  the baseline until the cc-confound is lifted).
- The **dream channel** (`2026-06-28-dream-channel.md`) + `TokenDecoder` (`agents/decoder.py`) diversify voice;
  the novelty-gated attenuation that loosens the loop is default-on.

**So the lock is not a defect to break — it is the identity invariant, and its side-effect (monoculture risk) has
its own dedicated, logged mechanism.** The remaining genuinely-open item on the "voice" side is **North-Star
gap 1, the speech cortex**: an LLM decode conditioned on the thought-vector / field state to turn the vector
clouds into literal sentences (the `TokenDecoder` word-cloud is the lossy stand-in; real translation is unbuilt).
That is the forward work, not unlocking the field. **Corpus-first: closed. Do not reopen it as a lock lever.**
