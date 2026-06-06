# Read-side boundary — does accumulated feedback reach generation?

- **Date:** 2026-06-06 (establishing run dated June 3)
- **Substrate:** live (Generator-warmed field)
- **Probe:** reinforcement probe with `eval()` dropout control
- **Status:** active
- **Depends on:** — (foundational)

## Question
Do the accumulated feedback signals written to `SymbolState` (coherence,
attractor_strength, crystal_binding, centrality) influence what the Generator
produces — i.e. is there a closed generation↔state feedback loop?

## Pre-declared signatures
- COUPLED (loop exists): generation output changes measurably under repeated
  reinforcement of a symbol's accumulated state.
- DECOUPLED (no loop): generation is identical regardless of accumulated state;
  the state only affects something downstream of generation (survival/decay).
- CONFOUNDED: apparent change that disappears under a no-op control.

## Result (observed)
Naive probe initially showed a generation delta of ~0.63 under reinforcement.
Adding an `eval()` dropout control collapsed it to **delta = 0.0**: generation
**byte-identical** under 1000× reinforcement. The 0.63 was train-mode
nondeterminism (dropout), not feedback.

`Generator.forward()` reads only its learned embedding + encoder weights. The
accumulated feedback signals (coherence, attractor_strength, crystal_binding,
centrality) are read by the decay/reaper retention score and not by
`forward()`.

## Interpretation
The feedback gates **survival in memory**, never generation — so lock-in is
**manufactured by selection, not dynamics.** Survival is currencied by coherence;
coherence rewards alignment; the reaper selects for agreement; the field converges
to / pins at ~0.998. Coherence is a **routing/survival axis, not a health
signal.** This is the mechanism behind the whole metastability program.

**Misread caught:** the 0.63 was nearly accepted as a real coupling. The control
is the only reason it wasn't. Canonical example of "a clean confirming result is
the alarm."

## Threats / confounds
- Runs: 1 (the byte-identical result is exact, so repetition adds little; but the
  *generality* across token classes / longer horizons is untested).
- The control (eval mode) is the load-bearing element; if dropout weren't the
  noise source the 0.63 would need another explanation. Result holds only because
  the control specifically isolated train-mode nondeterminism.
- Conclusion is about the *current* untrained Generator's `forward()`; a future
  architecture that wires accumulated state into generation would invalidate it
  (and Fix 0-A deliberately does exactly that — see below).

## Open / next
- Does survival-by-coherence flatten the *generator/expression* into monoculture
  over long runs? (That is the lock-in that would actually matter — upstream.)
- Fix 0-B (metastability as a counterweight fitness term in reinforcement) is
  the planned remedy; highest-leverage.
