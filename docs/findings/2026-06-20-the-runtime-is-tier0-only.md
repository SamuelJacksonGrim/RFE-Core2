# The runnable system is Tier 0 only — the tiered stack lives in the test harness

- **Date:** 2026-06-20 · **Status:** resolved (structural finding → composition wired)
- **Method:** switch inventory across all findings + grep every entry point / `attach_*` call site
- **Depends on:** — (foundational audit)

**Verdict:** every finding validated a mechanism against a system **no launchable entry point actually
composed**. `attach_governance()` (which must precede `attach_value_engine()`) was called in **zero**
non-test files: `loop/recursion1188.py`, `api/inference_api.py`, `api/websocket_server.py` all ran **Tier 0
only**; Tiers 0–3 were assembled **solely** in `tests/_common.build_full_stack` (which passes: allow 0.99,
46 values, bonds, 9/9 governance, 8/8 CORE). So the tiers **work** — they were just never wired into anything
a user can launch. The gap was orchestration, not correctness.

**Two corrections it also produced:** (1) Build A (ignition) and ⊘ (Build C) were mis-classified
"wired-default" — actually **opt-in-off**, attached nowhere outside tests. (2) The dormant behavioural levers
(novelty attenuation's weak real-token recovery, gnov never firing, the ⊘ cc-confound) all trace to **one**
upstream cause — the generator's common-mode / low-rank structure. **The real lever is upstream (generator
diversity: train to depth/dim/de-common-mode); stop adding downstream gates.**

**Resolution:** `build_engine()` became the single composition point
(`2026-06-20-ground-truth-pass1-compose-the-runtime`); API + WebSocket routed through it
(`2026-06-27-api-entrypoints-tier0-only`). Default levers then graduated (pretrain + attenuation + dream
channel default-ON; operators opt-in) — `docs/EXPERIMENTAL_LEVERS.md`.

*Consolidated 2026-08-05 — verdict + the two corrections preserved; prose trimmed. Full history in git.*
