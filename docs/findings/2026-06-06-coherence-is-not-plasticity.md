# Coherence vs. plasticity — which measures lock-in?

- **Date:** 2026-06-06
- **Substrate:** n/a (conceptual reframe; arose from the multilayer-lock run +
  external review by Raphael/GPT)
- **Probe:** none yet — this finding *defines* the probes to build (gate
  decomposition, attractor migration, coupling test)
- **Status:** active
- **Depends on:** 2026-06-06-multilayer-lock.md (the 85% gate block and the moat),
  2026-06-06-frame-correction.md (the upstream/coherent-field split)

## What this finding changes

It changes the framing of the investigation itself, so it is its own entry, not
a comment on the earlier ones. It retires a question we were about to spend
effort answering.

## The retired question

The "pin vs. band" framing (should the field hold a hard ~0.998 coherence pin or
a softer ~0.85–0.95 floating band?) **conflates two distinct properties**:

- **Field coherence** — a static measure of internal phase alignment.
- **Attractor plasticity** — whether the field's attractor *geometry can migrate*
  in response to persistent, surviving novelty.

Field coherence does not directly measure adaptability:
- A highly coherent field (~0.998) may remain **adaptive** if its attractor can
  migrate when novel structure repeatedly survives.
- A lower-coherence field (~0.90) may still be **rigid** if its attractor
  geometry stays fixed.

So "0.998 vs 0.90" does not measure the thing we were worried about. Lowering the
coherence target would not address rigidity if the rigidity originates elsewhere.

## What was learned

**Coherence ≠ plasticity, but coherence is not necessarily uninvolved either.**
Lock-in should be assessed through **attractor migration**, not static coherence
values. The right question is: when a genuinely new regime repeatedly survives
governance and repeatedly appears in expression, does the field's attractor
center-of-mass move?
- If yes → 0.998 may simply be a successful integrator; the value itself is not
  the lock.
- If no → lowering coherence won't *automatically* restore adaptability; the
  rigidity may originate elsewhere.

**Coupling correction (do not over-clean this into "coherence is irrelevant").**
The earlier draft retired pin-vs-band entirely, treating coherence and plasticity
as cleanly orthogonal. That is too strong if the **magnitude moat** is real (see
`2026-06-06-multilayer-lock.md`: accumulating field swamps novel injection, so
what lands averages ~0.91 cosine even under maximal source diversity). If moat
depth scales with coherence, the structure is:

    higher coherence → larger moat → reduced attractor mobility

So the claim is NOT "coherence directly causes lock-in" (not bought) but
"coherence may contribute to a mechanism that reduces plasticity." The corrected
statement (Raphael's wording):

> Coherence is not itself the measure of adaptability, but it may be one of the
> parameters that influence adaptability through moat formation.

This is testable: demonstrate whether **moat depth scales with coherence and
predicts migration resistance.** If it does, coherence is back in the picture as
an *input* to plasticity (not the proxy for it). If it does not, coherence really
is orthogonal and pin-vs-band stays retired.

## What remains unknown

Can the field's attractor actually migrate under persistent surviving novelty?
Not yet measured. This is the real lock-in test and it replaces the pin-vs-band
framing entirely.

## What must be investigated first (ordering)

**The governance gate must be characterized before the plasticity test can be
read.** Current observation (see `2026-06-06-multilayer-lock.md`): ~**85%** of
diverse internal input is filtered *before* field integration.

This makes the gate a confounder for any plasticity experiment. If the
attractor-migration test is run first and the attractor does **not** move, the
result is nearly uninterpretable — it could mean any of:
- the attractor is rigid;
- the field is rigid;
- the field is adaptive but never received enough surviving novelty;
- the gate filtered the novelty before the field ever saw it.

You must confirm the experiment's *input channel* is functioning before drawing
conclusions from its output.

## Next steps (in order, now operationally specified)

**1. Characterize the 85% gate block — decompose by rejection reason (#3).**
"85% blocked" is uninterpretable alone: 80% redundant-noise + 5% novel rejected
means one thing; 80% novel + 5% noise rejected means the opposite. So instrument
each blocked decision by *why it fired*:
- flood ceiling (rate limit on the source/origin_type),
- coherence-impact threshold (vector too dissonant with current field),
- trust / quarantine (source penalized),
- manipulation-resistance signal.
Output: "X% flood, Y% coherence, Z% trust, W% manipulation." That distribution
tells us whether the gate is correctly rejecting junk or strangling the novelty
the expression stream needs. This is the input-channel check; it must pass before
the migration test is interpretable.

**2. Attractor-plasticity probe — with predeclared observables (#1).**
"Measure migration" is a hypothesis, not an experiment, until these are fixed
*before* the run (discipline #4):
- **What is the attractor center?** (e.g. the field-vector EMA, or the centroid
  of the recent history window — pick and state it.)
- **How is migration measured?** (displacement of that center over the run, in
  cosine or L2.)
- **Over what horizon?** (N steps — and N scaled to the field decay so the
  integrator can actually move, per the gain-sign-check lesson.)
- **Relative to what baseline?** (center displacement under NO surviving novelty
  = natural drift; migration must exceed this control to count.)
Predeclared signatures:
- MIGRATES: center displacement under persistent surviving novelty significantly
  exceeds baseline-drift control → attractor is plastic; 0.998 is a healthy
  integrator.
- RIGID: displacement ≈ baseline-drift even with surviving novelty → attractor
  cannot move; rigidity is real and coherence-tuning alone won't fix it.
- CONFOUNDED: not enough novelty survived the gate to drive the test (→ back to
  step 1), or displacement within noise of the control.

**3. Coupling test (the theory-level question, #2).**
Does moat depth scale with coherence, and does it predict migration resistance?
Sweep field coherence (via the trained-generator-sim spread knob), measure moat
depth (gap between injected-vector diversity and what-actually-lands diversity,
the inputCos metric), and check whether higher coherence → larger moat → less
migration. If yes, coherence re-enters as an input to plasticity; if no, it's
orthogonal and pin-vs-band stays retired.

## Threats / confounds
- Runs: 0 — this finding is **definitional**, not measured. It reframes the
  question and specifies three probes (gate decomposition, plasticity, coupling)
  but none have been run. Its "Learned" claim (coherence ≠ plasticity) is a
  conceptual distinction, not an empirical result; the empirical questions are
  all still open.
- Biggest risk: treating the reframe as if it were settled. It changes *what to
  measure*, not *what is true*. The coupling question (does moat depth scale with
  coherence?) could still pull coherence back in as a real factor.

## Note on epistemic hygiene

Three states are kept deliberately separate here, to avoid treating a hypothesis
as a result:
- **Learned:** coherence ≠ plasticity.
- **Unknown:** can the attractor migrate?
- **Investigate first:** the gate.

(Reframe and three-state formulation: Raphael/GPT, 2026-06-06. Three sharpenings —
operational signatures, coupling/moat correction, gate decomposition: Claude +
Sam, reviewed and the coupling wording finalized by Raphael, 2026-06-06.)
