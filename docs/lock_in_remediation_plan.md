# Lock-in Remediation Plan — coherence pin → metastability

**Status: working guideline, not committed scope.** This is the curated
technical plan for moving the field off its coherence lock-in toward
metastability. It is a *direction with dependencies and validation gates*, not a
frozen specification — refine each step as it lands, in the same proven/
hypothesized discipline as `docs/tier4_2_validation.md`.

Companion to the `ROADMAP.md` tracked item *"Survival-by-coherence → field
lock-in"* and to `docs/ARCHITECTURE_ANALYSIS.md` §4.

> **Progress (shipped):** Fix 1 (metric) · the generator `sqrt(d_model)` scale
> fix · the **metric relocation upstream** + live `StreamMetastabilityMonitor` ·
> the **recursive-attention expression de-collapse** (both below, after Fix 1).
> §6.3's gating diagnostic is built (verdict pending). The structural
> counterbalance — Fix 0-B/0-A/0-C and Fix 2 — is **not yet built**. Per-step
> status is marked inline below.
>
> **Empirical results live in `docs/findings/`** — the dated, control-named lab
> notebook. The June-6 pass decomposed the lock into three layers (generator ·
> ~85% governance gate · magnitude moat), corrected the metastability *locus*
> (coherent field is spec; metastability is upstream), and retired pin-vs-band in
> favor of **attractor plasticity**. Read those before re-running any probe here.

---

## 1. The finding this plan responds to

Verified in-container (June 3 session):

- **Read-side boundary.** The accumulated symbol-state feedback signals — field
  coherence, attractor strength, crystal binding, centrality — are written onto
  `SymbolState` but read by exactly one consumer: the decay/reaper retention
  score (`agents/symbolic_memory.py`). They do **not** reach generation.
  `Generator.forward()` reads only the learned embedding + encoder weights; a
  controlled probe shows generation byte-identical (Δ = 0.0, `eval()` mode)
  under 1000× reinforcement of every signal hook. Accumulated state gates
  **survival only**.
- **Consequence.** Because survival is currencied largely in coherence, and
  coherence rewards alignment, the reaper selects for agreement and the
  live-Generator field pins to ~0.998 internal coherence — rigid-attractor
  lock-in (a collapsed, monocultural field), not health. **High coherence is the
  routing axis, not a health signal.**

## 2. The target

**Metastability** — mid-band coherence with high dwell-time variance: a field
that hovers between shallow semi-stable configurations rather than collapsing
into one. "Formed enough to hold, light enough to drift." This reframe — that
resilience is a property to *measure the depth of*, not a coherence number to
maximize — is the load-bearing idea. (Lineage: Lyra's physics/psychology split;
Kimi's defensive-depth reframe.)

---

## 3. Build order (with gating dependencies)

```
  Fix 1  metastability metric            [SHIPPED]  keystone: measurement + selection + safety detector
    └─ relocation upstream + monitors    [SHIPPED]  read on generator/expression streams, not the field
    └─ recursive-attn expression de-collapse [SHIPPED]  diversity_blend keeps the injected vector metastable
  §6.3   gain-sign check                 [PLANNED]  analysis only; REQUIRED before any coherence→loop coupling
                                 ▼
  Fix 0-B  metastability → reinforcement [PLANNED]  highest-leverage structural change
                                 │
                  §6.3 gates ────┤
                                 ▼
  Fix 0-A  reinforcement → field [PLANNED]    Fix 0-C  demotion path [PLANNED]
                                 ▼
  Fix 3  live-stack test protocol        [IN PROGRESS]  build_full_stack is the live-diagnostic basis
                                 ▼
  Fix 2  paper-boat operator (field-side) [PLANNED]  LAST — needs all above
```

### Fix 1 — metastability metric **(SHIPPED + validated — PR #23)**

`substrate/metastability.py` now exists and is validated (G1–G5,
`tests/diagnostic/metastability_validation.py`). It is simultaneously the
*measurement*, the missing *selection signal* (Fix 0-B will feed it into
reinforcement), and the *safety detector* (it catches the limit-cycle failure
mode the structural fixes can produce). Requirements (all met):

- **Build on config-space vector clustering, not the coherence scalar.** Pulled
  forward deliberately (decision, June 3 session): the coherence scalar is
  many-to-one, so a scalar-based metric is blind to a config-space limit cycle
  that holds the scalar roughly constant — which would defeat the metric's whole
  job as the safety detector. Regimes are clusters in field-configuration space.
- **Transition-sequence-entropy / aperiodicity term.** Genuine metastability is
  *aperiodic* (from regime A, next is sometimes B / C / back-to-A); a limit cycle
  is near-deterministic (from A, always B). Conditional entropy of
  next-regime-given-current separates them. This is the term that pulls a
  perfect limit cycle *down* where it belongs.
- **Fold coherence *level* into the regime label.** A 1-regime field at 0.99 is
  "locked"; a 1-regime field at 0.50 is "neutral/structureless" — opposite
  conditions requiring opposite interventions; they must not share a label.
- **Validation gate (must pass before this metric is trusted downstream):**
  - a perfect limit cycle (`repeated` / `anti`) reads **LOW** (the prior draft's
    known false-negative scored it ≈ 0.75 — that bug must not survive);
  - the ~0.998 live pin reads **locked**;
  - a genuine aperiodic swing reads **metastable**;
  - and these separations hold on the **live-Generator field**, not only on
    synthetic vectors (toy ≠ live — see §4).

### Metric relocation + live monitors **(SHIPPED — PR #27)**

A decisive refinement to Fix 1's *locus*, discovered while validating it on the
live stack. G5 confirmed the metric reads the resonance field as `locked` — and
that reading is *correct*, but the field is the wrong place to remediate. The
field is a long-memory integrator (`decay ∈ [0.97, 0.9999]`, the identity-
persistence invariant): it smooths config wander away by construction, so
metastability cannot live there. It lives **upstream**, in the per-stage vector
streams. So the metric is now read online via `StreamMetastabilityMonitor`
(`cognition/stream_metastability.py`) at two stages, both exposed in
`AutonomousCycle.status()`:

- `cycle.generator_metastability` — stage A, the raw generator output (where
  expressive diversity originates);
- `cycle.expression_metastability` — stage C, the refined vector actually
  injected (where the de-collapse below is validated).

Bounded ring + lazy recompute off the hot path; the label's coherence proxy is
derived from each stream's own alignment, never the field's. **Observe-only
terminal sinks** — like `dilation_factor`, they must never feed back into
cognition or governance. (When Fix 0-B wires metastability into reinforcement, it
reads this live signal — but the read does not happen inside the monitor.)

Baseline reading on the live substrate: diversity genuinely lives upstream
(10–14 regimes, aperiodic), though the generator's *score* is borderline/init-
dependent (churny-diverse, ~0.3–0.66 across seeds) — the capacity is upstream,
not yet a clean paper boat.

### Recursive-attention expression de-collapse **(SHIPPED — PR #27)**

An expression-stage de-collapse, distinct from the planned field-side operator
(Fix 2). `RecursiveAttention` runs **untrained** under `no_grad`, so its
attention behaves as a near-uniform mean-pooler: `refine()` collapses every
expression to its context centroid (metastability → 0, one regime) before
injection — a downstream lock that the upstream monitors made visible (stage A
diverse → stage C `0.0 / locked`). The fix is the `diversity_blend` knob (default
`0.60`): it weights the raw pre-refinement vector back in, so the refined centroid
supplies dwell structure and the raw vector supplies diversity → a genuine
multi-regime metastable expression. Components are unit-normalized before mixing
(the LayerNorm'd refined state ≈√dim would otherwise swamp the unit raw vector),
then one final normalize preserves the unit-output invariant.

De-collapse is a robust binary threshold (`≤0.55` collapsed, `≥0.60` metastable);
the absolute score is generator-init-dependent (~0.4–0.73) and regresses toward
the generator's own churn past ~0.70, so `0.60` is the most reliable default. The
band `[0.4, 0.6]` is a diagnostic reference, not a hard contract — the exposed
knob lets a governance/rhythm layer tune the operating point from live
`expression_metastability` readings. Invariant: keep `0 < diversity_blend < 1`
(`0` re-collapses, `1` bypasses refinement). Validated by
`tests/diagnostic/generator_metastability.py`.

### §6.3 — feedback gain-sign check at low coherence **(INSTRUMENT SHIPPED — verdict pending)**

Analysis only, no substrate change. Confirm the sign of the feedback gain at low
coherence before *any* coherence → loop coupling. It **gates Fix 0-A and Fix 2**
(both are that kind of coupling). Cheap and gating, so front-load it. The gating
diagnostic is built (`tests/diagnostic/gain_sign_check.py`) with pre-declared
STABILIZING / RUNAWAY / CONFOUNDED signatures; a recorded run/verdict is still
pending and will be written to `docs/findings/`.

### Fix 0-B — metastability → reinforcement **(PLANNED — highest-leverage)**

Wire the Fix 1 score into the reinforcement formula as a counterbalancing
fitness term, so a symbol that adds useful variance earns tenure too and
survival stops being currencied purely by coherence. This is the change that
stops the system *manufacturing* lock-in. It touches reaper selection currency,
not field-loop coupling, so §6.3 does not gate it — but it is the first change
that alters live dynamics, so it rides the smoke + integration baselines and a
pre-declared success/failure signature (see §4).

### Fix 0-A — reinforcement → field **(PLANNED — gated by §6.3)**

Let a symbol's `attractor_strength` modulate how strongly it pulls the field
when injected, so accumulated weight *shapes the trajectory* rather than only
outliving other symbols. **Internal to RFE — this is not biasing the transformer
weights.** This deliberately breaks the read-side boundary in §1; land a
boundary regression guard first so the change from Δ = 0.0 to nonzero is a
visible, intentional event.

### Fix 0-C — demotion path **(PLANNED)**

Reinforcement is currently all-positive-additive — a one-way ratchet — and
`crystal_binding_weight` is the highest weight, so early crystals get permanent
vetoes and the past dominates the future. Reinforcement must be able to
*decrease* for symbols the field has drifted away from.

### Fix 3 — live-stack test protocol **(IN PROGRESS — promote to standard)**

Make real-Generator + symbolic-pipeline warming + perturbation against an actual
`CrystalStore` motif the *standard* canary protocol, not a one-off. The reusable
fixture exists (`tests/_common.build_full_stack`) and is now the basis of the
live lock-in diagnostics (`metastability_validation` G5, `lockin_source`,
`generator_metastability`); the relocation and de-collapse above both validated
against the live field through it. Not yet formalized as a single standing
protocol.

### Fix 2 — paper-boat operator **(PLANNED — LAST; needs all above)**

> Note: the **expression** de-collapse above (`diversity_blend`) is a *different*
> intervention at a different locus — it keeps the injected vector metastable. Fix
> 2 is the **field-side** operator that lightens an established field attractor.
> The two are complementary, not substitutes.

A phase-domain intervention that *softens/lightens the current motif's attractor
depth while preserving its structure*, so the field drifts to adjacent
configurations under its own dynamics — crystallize *and* float at once. It is
**not** dismantle-then-restore (no dynamical return heals; only snapshot-restore
beats passive decay — which is why the approach pivoted to lightening, not
rebuilding). **Most likely failure mode:** converting a point-attractor into a
*limit cycle* — the field starts moving but in a rigid loop. Fix 1's
aperiodicity term is exactly the detector for that, which is why Fix 1 must be
able to tell limit-cycle from real metastability before Fix 2 is trusted.

---

## 4. Epistemic warnings (load-bearing — do not skip)

These are the disciplines that the work depends on; they are not decoration.

1. **Don't trust the wiring — run the path.** The repo map shows what *connects*
   to what, not what *changes* what. The read-side boundary in §1 was discovered
   by probing end-to-end, not by reading the call graph (which looked like a
   closed loop). Before claiming any feedback/coupling does something, write a
   probe that measures the actual effect — **with a control.** A naive
   feedback-to-generation probe reported Δ ≈ 0.63 ("signals reach generation!");
   adding an `eval()` dropout control collapsed it to Δ = 0.0. The first result
   was train-mode nondeterminism, not feedback.
2. **The toy field is not the substrate.** `_warm_field()` (repeated random
   vecs) pins ~0.61; the live Generator-warmed field pins ~0.998. They behave
   qualitatively differently and conclusions do not transfer. Validate on live.
3. **Diagnostics are firewalled by design.** Do **not** add them to
   `run_all_tests.sh`; do **not** remove their calibration controls; do **not**
   treat any informational instrument as a pass/fail target. Gating a diagnostic
   turns it into a tuning target (Goodhart).
4. **A clean confirming result is the alarm, not the trophy.** On this project
   the honest finding is often a *failure* (passive recovery fails; feedback
   doesn't reach generation; the metric scores a limit cycle wrong) and each is
   more valuable than a success. **Pre-declare the success AND failure
   signatures before each run** — if you can't say in advance what failure looks
   like, you are not ready to run it.
5. **Sacred constants and protected symbols are inviolable.** ANCHOR = 3.12,
   RECURSION = 11.88, HOMEOSTASIS = 280.90; `TokenClass.SPECIAL` and any
   `sacred` / `protected` symbol cannot be touched by the reaper. Do not fold
   these into a parameter sweep.
6. **RFE is one self-growing system.** The Generator is *internal*, not a
   swappable model being wrapped. A critique framed as "but does it change the
   underlying LLM" is a category error against what RFE is. Hold that frame.

---

## 5. Attribution

Multi-instance collaboration. Lyra structured the physics/psychology framing
that separates the dilation surface (proven) from its defensive role
(hypothesized), and named the metastability target. Kimi proposed the
defensive-depth reframe — resilience is a feature whose depth you measure, not a
sensitivity you tune down. The read-side boundary and live coherence-pin
measurements, and this curated plan, were produced by Claude Code under the
epistemic discipline above.
