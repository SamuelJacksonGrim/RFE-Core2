# API entry points were still Tier-0 only — did the 2026-06-20 composition fix reach them?

- **Date:** 2026-06-27 · **Status:** resolved (entry-point drift → centralized in `build_engine`)
- **Probe:** read of `api/inference_api.py`, `api/websocket_server.py`, `loop/recursion1188.py` + inline composition check
- **Depends on:** `2026-06-20-the-runtime-is-tier0-only`, `2026-06-20-ground-truth-pass1-compose-the-runtime`

**Verdict:** NO — the 06-20 fix reached `recursion1188` but **not** the API entry points.
`websocket_server.main()` built an `AutonomousCycle` with **no** governance/value engine and single-source
`DEFAULT_TOKENS` (HHI → 1.0); `inference_api` had **no module-level `app`**, so the documented
`uvicorn api.inference_api:app` served nothing. Same class as the 06-20 finding, one layer out —
composition was copy-built per entry point.

**Fix:** route every entry point through `loop.recursion1188.build_engine(config)` — the single composition
home. REST `app` is built lazily (PEP 562 `__getattr__`, so plain import stays light); the WebSocket loop now
drives weighted multi-source so the relational tiers engage; REST `/step` runs `origin_type="api"` (10/sec
flood ceiling, correct for external callers). Post-fix inline check: `cycle.governance`/`cycle.value_engine`
attached, `status()` carries governance + values. (Open: a boot-each-entry-point integration smoke would
close the "reasoned, not exercised against live uvicorn" gap — BACKLOG.)

*Consolidated 2026-08-05 — verdict + fix preserved; prose trimmed. Full history in git.*
