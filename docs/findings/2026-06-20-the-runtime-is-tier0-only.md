# The switch audit's real headline: the runnable system is Tier 0 only — the tiered stack lives in the test harness

- **Date:** 2026-06-20
- **Spec:** n/a (architecture/runtime audit)
- **Status:** active — a **structural finding**, not a metric. Prompted by Samuel:
  "in almost every doc finding there has been a switch made, and everything is
  turned off. the system is fucked." Auditing the switches surfaced something
  larger than the switches.
- **Method:** read all 32 findings (switch inventory, via subagent) + grep every
  entry point and every `attach_*` call site in the repo.

## Question
Every finding validates a mechanism. Against *what* running system? Where, in code
a person can actually launch, are the tiers and operators composed?

## Result (observed) — the composition exists in exactly one place, and it is the test harness

**No production entry point wires Tier 1/2/3.** `attach_governance()` — the gate
that must precede `attach_value_engine()` — is called in **zero** non-test files:

```
$ grep -rn "attach_governance" --include=*.py . | grep -v "def " | grep -v tests/
(nothing)
```

- **`loop/recursion1188.py`** (CLAUDE.md's first "How to run" command, "the
  autonomous loop") builds: generator (eval-mode, optional corpus pretrain) →
  `AutonomousCycle` → optional `DreamCycle`, then loops `cycle.step(tokens)` over a
  **fixed token list**. It never constructs `SelfhoodGovernance`,
  `ValueEmergenceEngine`, or any Tier 2 subsystem, and never attaches the
  Two-Operator operators (A/B/⊘/consumer). **Tier 0 only.**
- **`api/inference_api.py`, `api/websocket_server.py`** — no `SelfhoodGovernance`,
  `ValueEmergenceEngine`, or `attach_*` for governance/values either.
- **`tests/_common.py::build_full_stack`** is the **only** place Tiers 0+1+2+3 are
  composed (`attach_governance` → `attach_value_engine`). The smoke/integration
  suites run on it and pass (allow_rate 0.99, 46 active values, bonds form, 9/9
  governance routes, 8/8 CORE handshake). So the tiered system **works** — it is
  just exercised only by the test harness.

## Interpretation
This is the deepest form of the "everything is observe-only / nothing gets used"
complaint, and it is correct at the runtime level. CLAUDE.md's tier table says the
tiers are "**all wired into `loop/autonomous_cycle.py`**." That is true as a
*capability*: the `attach_*` methods exist on the cycle. It is false as a *runtime*:
nothing a user can launch calls them. The rich tiered architecture the findings
describe — governance, trust, ethics, rights, bonds, manipulation resistance, value
emergence, and the λ/⊕/⊘ operators — is **assembled only inside `build_full_stack`**,
a function in `tests/`.

So the canonical `python -m loop.recursion1188` does not run "the Recursive Field
Engine" as documented; it runs its Tier-0 substrate looping a fixed token sequence.
Every per-lever switch debate (this whole audit) sits *downstream* of a more basic
gap: **the orchestration that composes the validated tiers into a launchable whole
was never written into an entry point.** That, not the individual flags, is why the
running system is a shell.

This is good news in one specific way: the composition is not a research problem.
It already exists, is proven, and passes its tests. It needs to be lifted out of the
test harness into a real entry point.

## What this does NOT say
- The tiers are not broken — `build_full_stack` + the suites prove they compose and
  run healthy. The gap is wiring, not correctness.
- The Tier-0 loop is not wrong — eval-mode, expression de-collapse (`diversity_blend`),
  and the metastability sinks *are* live in it (those genuinely shipped to default).
- This is not the operators' fault — they are opt-in by design and (the ⊘ consumer)
  blocked on the cc-confound; but they are moot until *any* entry point even runs
  Tier 1+.

## Switch-inventory correction (the audit over-counted "wired")
The findings audit classified Build A (ignition) and Build C (⊘ read) as
"WIRED-DEFAULT / emits every cycle." **Corrected: they are OPT-IN-OFF** — present as
modules/methods, attached nowhere outside tests. The genuinely default-active
mechanisms are: eval-mode, expression de-collapse, the metastability monitors
(observe-only), Fix 0-B's asymmetric reaper gate, the reflective loop, and the
trainer/checkpoint/attractor bug-fixes. Everything labeled an "operator" or "Tier
1/2/3 subsystem" is, at runtime, off — because the entry point never builds it.

## Open / next (the fix is bounded, not research)
- **Write a real entry point** (fix `recursion1188` or add one) that composes Tiers
  0–3 exactly as `build_full_stack` does — `attach_governance` then
  `attach_value_engine` — driven by real multi-source input rather than a fixed
  token list. This alone turns the launchable system from a Tier-0 toy into the
  documented tiered engine. Low-risk: it is the configuration every test already
  passes on.
  **→ DONE (2026-06-20): `build_engine()` is the single composition point**
  (`2026-06-20-ground-truth-pass1-compose-the-runtime.md`); API/WS entry points
  routed through it 2026-06-27 (`2026-06-27-api-entrypoints-tier0-only.md`).
- **Then** decide, per the graduation discipline, which validated levers the default
  composition includes (eval already in; corpus pretrain safe-optional; novelty
  attenuation at its safe ceiling; operators A/B held; ⊘ consumer blocked on cc).
  **→ DECIDED (2026-06-20 → 29): pretrain + attenuation + dream channel graduated
  default-ON; operators stay opt-in** — `docs/EXPERIMENTAL_LEVERS.md`.
- **Upstream truth from the audit:** most dormant *behavioural* levers (novelty
  attenuation's marginal real-token recovery, gnov never firing, the ⊘ cc-confound)
  trace to one cause — the **generator's common-mode / low-rank structure**. The
  real lever is upstream (generator representational diversity: training to depth,
  dim, de-common-moding), not more downstream switches. Stop adding downstream gates.
