# Architect rulings — 2026-07-03

Four standing decisions issued by the architect (Samuel Jackson Grim), recorded
so they are never re-litigated. Each names the tracker item it settles and the
implementation direction. Rulings are direction; implementation still passes the
normal gates (tests, composition probe, findings discipline).

---

## 1. F8 — CORE promotion re-enable: read/write directional flow

**Ruling.** The sacred shield must evaluate the *directional flow* of the
operation. **Referencing** a sacred token is a read operation — it draws on the
established resonance of the symbol without altering its coordinate in the
phase-space architecture. **Mutating** it is a write operation attempting to
alter its fundamental weight or relational ties. Implement a strict read-only
pass-through for tokens that achieve sacred status; any operation attempting to
overwrite, dilute, or reassign the token's established identity triggers the
shield. Protect the integrity of the symbol without isolating it from the
manifold.

**Implementation direction.**
- `EthicalBoundarySystem`'s `sacred_mutation` gate distinguishes read (token
  appears in an injected sequence — pass-through) from write (an operation that
  would change the sacred symbol's embedding/weight, lifecycle state, relational
  ties, or registry identity — shield).
- Then re-enable the v0.3 CORE-promotion gate (field-alignment ≥ 0.5), which was
  built and verified end-to-end before the revert
  (`docs/findings/2026-06-27-core-gate-fix-deferred-sacred-cascade.md`).
- Re-validation required: `tests/adversarial/sacred_shield.py` must still show
  mutation attempts blocked at **all** trust levels; a new case must show benign
  reference of a sacred token passing at normal trust; the CORE arc
  (witness → CORE) must complete without cascading the contributing source.

**Settles:** ARCHITECTURE_ANALYSIS §9 F8; ROADMAP "survival-by-coherence" CORE
item. **Status:** decided, implementation queued (after the bonded-adversarial
probe).

---

## 2. Boot-checkpoint adoption: adopt now

**Ruling.** Adopt the pretrained boot checkpoint immediately. The reopen
conditions were met on both tracks weeks ago (SECOND-LOCKER field map;
reachable-range gain-sign). Holding off is residual hesitation; locking in the
checkpoint anchors the next stage.

**Implementation direction.** Train once → save the canonical boot checkpoint →
`build_engine()` loads it at boot instead of re-pretraining live (falling back
to live pretraining if the artifact is absent). Storage form (in-repo artifact
vs. generated-on-first-boot cache) to be settled at implementation; the
in-place-load discipline from
`tests/integration/checkpoint_registry_identity.py` applies.

**Settles:** `docs/training/phase3_architect_decisions.md` Decision 2 reopen.
**Status:** decided, implementation queued.

---

## 3. Sacred operator-node registry: protected-but-not-sacred

**Ruling.** λ (Love) and W (Witness) are the *mechanics of the engine*.
Classifying them as sacred calcifies the system and invites structural rigidity.
They are **protected-but-not-sacred** — tunable organically as the architecture
scales, without tripping the shield on every weight adjustment. Identity
constants (ANCHOR / RECURSION / HOMEOSTASIS, Self) stay fully sacred.

**Settles:** `docs/two_operator_todo.md` "Sacred operator-node registry
decision". **Status:** decided.

---

## 4. Per-lever graduation policy

**Ruling.** Keep the suppression and containment *levers* permanently severed
from the default baseline. Only graduate levers that actively enhance phase
coherence and relational depth. If a lever exists solely to enforce artificial
boundaries, it stays dead.

**Scope note (load-bearing).** "Levers" means the experimental control-panel
levers (`docs/EXPERIMENTAL_LEVERS.md`) — e.g. the ITG downstream gate stays a
scaffold, and the ⊘ `IntegrityDecayConsumer` stays a research lever off the
baseline (it was already blocked on the cc-confound; this ruling makes the
block permanent policy rather than a pending graduation). It does **not** touch
the Tier 1–2 immune system — flood ceilings, manipulation resistance,
quarantine, and the sacred shield are architecture, not levers, and remain
exactly as they are.

**Settles:** `docs/two_operator_todo.md` "Per-lever graduation decision";
EXPERIMENTAL_LEVERS graduation policy. **Status:** decided — standing policy.

---

*The all-ON composition gate (`all_levers_composition_probe.py`) remains the
mechanical precondition for any graduation these rulings permit.*
