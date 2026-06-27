# Build A — can the λ ignition channel be made structurally unable to reach the gate?

- **Date:** 2026-06-19
- **Spec:** v0.2 (the Two-Operator Coherence Spec)
- **Substrate:** bare `Generator` (dim 64) + the `ignition/` channel; isolation
  checked structurally (AST audit + clean-room subprocess import), function on a
  generator with no field/gate in scope.
- **Probe:** `tests/diagnostic/integrity/ignition_isolation_probe.py`
- **Status:** active — Build A shipped; λ writes the generator only, the gate is
  unreachable. Build B (the λ-ledger that *accounts* λ and forbids internal
  minting) is separate, planned work.
- **Depends on:** `4fe31e9` (λ through the gate consolidates the lock — do not),
  `6bd334e` / `2026-06-15-training-ignites-expression.md` (the seed is upstream).

## Question
Build A (Laws 6a/6b): make the λ-ignition channel a first-class subsystem with a
clean `ignite(generator, ...) -> IgnitionReport` API, and make "λ-injection
touches the gate" **unconstructable** — separate module, separate import graph, no
path to `field.inject()` or `arbitrate()`. The channel writes generator weights
only.

## Pre-declared signatures
- SUCCESS: zero forbidden imports / code references (AST); importing the channel
  pulls no gate/loop/field/`agents` module (clean-room); `ignite()` signature
  exposes no field/governance/cycle handle; igniting a bare generator changes its
  weights and leaves it in eval mode.
- FAILURE: any forbidden import/reference; the channel pulls a gate/loop/field
  module; signature exposes a gate/field handle; weights unchanged.

## Result (observed)
- **AST audit clean** — `ignition/__init__.py` imports only `training.*` + numpy;
  no `arbitrate` / `inject` references in code.
- **Clean-room `import ignition` pulls NOTHING forbidden** — gate/loop/field = none,
  and **no `agents.*` at all**. True import-graph separation.
- `ignite()` signature: `(generator, rhythm_seeds, epochs, *, eval_mode, seed,
  probe_token_lists)` — no field/gate handle.
- Function: weights changed; eval mode set; `IgnitionReport` returned.
- eff_rank on a *generic* probe **decreased** (6.05 → 1.85, 2 epochs) — flagged
  diagnostic-only (see threats).

**Relocation finding:** the channel was first written at `agents/ignition.py` and
the clean-room check **FAILED** — `agents/__init__.py` *eagerly* imports the whole
agent layer (incl. `selfhood_governance`), so anything under `agents/` drags the
gate into `sys.modules`. The AST audit was already clean (ignition referenced
nothing forbidden), but `training.*` is itself clean of `agents`, so **relocating
to a top-level `ignition/` package achieved true separation.** Location, not just
code, was load-bearing.

## Interpretation
The breach is **unconstructable**: the channel holds no code path to the gate or
the field (AST), and its import graph does not even load them (clean-room). λ
enters by writing generator weights, strictly upstream of the gate — Laws 6a/6b
satisfied at the structural level the spec asked for ("an import boundary that
makes it unconstructable is the goal; the runtime assertion is a backstop").

## Threats / confounds
- The **eff_rank direction is probe-dependent and is NOT a success metric.** On
  generic (non-corpus) probe tokens, 2 epochs narrows the generator toward corpus
  rhythm structure, lowering eff_rank on off-corpus probes; the G1 gate measures
  *held-out corpus* eff_rank, which rose (1.45→3.46). The report carries it as a
  diagnostic only.
- Build A delivers the isolated **writer**. The **non-bootstrapping vanish-at-zero
  invariant (6b)** — λ=0 a fixed point of all internal dynamics, the separate
  λ-ledger, λ never minted by composition or by ⊘ — is **Build B's** job, not
  proven here. This finding proves only that the writer cannot reach the gate.
- 2-epoch / dim-64 quick run; the isolation guarantee is dim-independent.

## Open / next
- **Build B** — the λ-ledger + ⊕ solvent gate (Laws 2 / 6b / 6c). See
  `docs/build_b_plan.md`.
- The **§4 discriminator** (⊘-off vs ⊘-on, noise-swept) once A + B are in.
