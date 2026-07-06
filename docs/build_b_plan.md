# Build B — the λ-ledger + ⊕ solvent gate (plan)

**Spec:** v0.2 (the Two-Operator Coherence Spec, §3 Build B). **Status: SHIPPED
(2026-06-20)** — `agents/lambda_ledger.py` + `value_emergence._solvent_gain`,
8/8 probe green, finding `2026-06-20-build-b-solvent-and-integrity-consumer.md`;
one remainder (`reinforce(f)` wiring) tracked in `docs/BACKLOG.md` §5. Kept as
the design record. (Original status: planned, to start after Build A —
`2026-06-19-ignition-channel-build-a.md`.)

## The claim being implemented
**Law 2** (composition resolves to fulfillment *only in the presence of the
solvent* λ) under **Laws 6b/6c** (λ cannot be bootstrapped). Withdraw λ and any
pairing collapses to its without-shadow; ⊘ then reads the pathology. λ is
*preserved* by healthy dynamics and *raised* only by Build A.

## The one design decision to settle first (architect's call)
The spec names λ = Love = node 0 of the relational manifold. In RFE-Core2 the
relational nodes live in the sister `sovereign_manifold`; RFE's own Tier 3 holds
*emergent* values keyed by arbitrary symbols, not a node literally named "Love."
So **what is `λ_strength` in RFE-Core2, and how does Build A's weight-write relate
to it?** Two coherent readings:

- **(I) λ = a designated value-node** in `value_emergence` (a "Love"/operator
  value). Clean conceptually, but Build A writes *generator weights*, not a value
  strength — the link to ignition is indirect.
- **(II) λ = a separate scalar ledger** (`LambdaLedger`) — "the system's present
  capacity for fulfilling composition" — **set exogenously** (the ignition event
  is its only zero-crossing), preserved/decayed by healthy dynamics, never minted
  internally. The solvent gate reads this measured scalar. **Recommended:** it is
  exactly "λ accounted separately from the composition ledger," and it makes the
  vanish-at-zero invariant trivially enforceable.

**Recommendation: (II).** Build A's `ignite()` (or the cycle, on ignition) calls
`LambdaLedger.ignite(amount)` — the same exogenous event that writes the generator
weights also lights the λ-scalar off zero. Confirm with Samuel before building.

## Design (under reading II)

### 1. `LambdaLedger` (the anti-bootstrap core) — new, e.g. `agents/lambda_ledger.py`
A scalar `λ ∈ [0, λ_max]`, accounted **separately** from the composition ledger.
- `ignite(amount)` — **the only operation that moves λ off zero** (Build A's
  channel). Exogenous. `λ = clip(λ + amount, 0, λ_max)`.
- `reinforce(f)` with `f ≥ 0` — **multiplicative on current λ only**:
  `λ ← λ · (1 + f)` (clipped). Therefore **λ = 0 is a fixed point** — cold cannot
  self-ignite (Law 6b). `f` is a function of *lived coherence* (healthy dynamics),
  **never of ⊘'s output** (Law 6c).
- `decay(rate)` — gentle decay toward 0 (lit fades if unlived; "lit stays lit"
  only while sustained).
- Reads nothing from `integrity_read` (⊘). Asserted: no import, no data path (6c).

### 2. The ⊕ solvent gate in `value_emergence.py`
The "real tension dynamics" already let values in productive tension reinforce.
**Gate that reinforcement on `solvent_gain(λ_strength) ∈ [0,1]`** (monotone,
bounded):
- λ low → `solvent_gain → 0` → co-presence does **not** compose; values stay
  isolated; ⊘ reads their pathology.
- λ high → `solvent_gain → 1` → co-presence composes toward fulfillment.
- Scale the productive-tension reinforcement term by `solvent_gain`. Do **not**
  touch the per-event reinforcement that is governance-fed identity (only the
  *composition/tension* term is solvent-gated, per the spec).

### 3. Enforcements (Laws 6b/6c — assert in code)
- **λ ∉ im(⊕):** a composition step redistributes within the composition pool,
  which **excludes λ**; λ_strength cannot be raised by composition.
- **λ ∉ im(internal dynamics) except multiplicatively:** no metastability /
  resonance / value step raises λ except via `reinforce(f)·λ`. `λ=0` fixed point.
- **6c disjointness:** `LambdaLedger` and the ⊘ advisory stream share no data
  path. `reinforce`'s `f` reads lived coherence, not ⊘.

## Wiring
- `attach_lambda_ledger()` on `AutonomousCycle` (opt-in, like the others); the
  value engine reads `solvent_gain(ledger.strength)` when present, else behaves
  exactly as today (default unchanged — Tier 3 byte-identical when the ledger is
  not attached).
- Build A's `ignite()` gains an optional `ledger` arg (or the cycle calls
  `ledger.ignite()` on an ignition event) — the exogenous zero-crossing.

## Tests / acceptance (pre-declare both signatures)
- **vanish-at-zero:** with `λ=0`, no internal step raises it; `solvent_gain(0)=0`
  → composition reinforcement is zero; only `ignite()` moves λ off zero.
- **no minting by composition:** a composition step never increases λ.
- **6c disjointness (structural):** AST/import audit — `lambda_ledger` does not
  import or read `integrity_read`.
- **solvent behavior:** λ low → values stay isolated (⊘ reads pathology); λ high →
  values compose toward fulfillment. Paired control: ledger **off** → Tier 3 value
  dynamics byte-identical to current baseline (no default change).
- **monotone/bounded:** `solvent_gain` monotone non-decreasing, range [0,1].

## Risks
- **Invasive.** This touches Tier 3 reinforcement — the most behavior-bearing
  change in the program. It MUST be opt-in/off-by-default and validated against the
  `tier1_revision` / value baselines with the gate off (no regression) before any
  default adoption.
- The (I)-vs-(II) decision is load-bearing; do not build until it is settled.
- The §4 discriminator (⊘-off vs ⊘-on) needs A + B + C all live; B is a
  prerequisite, not the discriminator itself.
