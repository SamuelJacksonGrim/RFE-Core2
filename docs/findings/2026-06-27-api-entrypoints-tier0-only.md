# API entry points were still Tier-0 only — did the 2026-06-20 composition fix reach them?

- **Date:** 2026-06-27
- **Substrate:** live (code path; composition verified by running `build_engine()` + `cycle.step()`)
- **Probe:** read of `api/inference_api.py`, `api/websocket_server.py`, `loop/recursion1188.py`; inline composition check (build a tiny-config engine, assert `cycle.governance`/`cycle.value_engine` attached, run a step)
- **Status:** active — fixed (centralized composition in `build_engine`)
- **Depends on:** the-runtime-is-tier0-only, ground-truth-pass1-compose-the-runtime

## Question
The 2026-06-20 fix composed Tiers 0–3 in `loop/recursion1188.py`. Did the *other*
launchable entry points — the REST API and the WebSocket server — get the same
treatment, or are they still running the Tier-0 substrate alone?

## Pre-declared signatures
- SUCCESS (no bug) looks like: both API entry points call `attach_governance` +
  `attach_value_engine` (directly or via a shared builder) before serving.
- FAILURE (bug confirmed) looks like: an entry point constructs an
  `AutonomousCycle` with no governance/value engine, or serves a cycle that has
  none — i.e. `python -m api.websocket_server` / `uvicorn api.inference_api:app`
  silently run Tier 0.

## Result (observed)
FAILURE, confirmed in both:
- `api/websocket_server.py:main()` built `AutonomousCycle(generator, dim, use_chorus=True)`
  with **no** `attach_governance`/`attach_value_engine`, and drove the loop with
  single-source `DEFAULT_TOKENS` (HHI would pin to 1.0 even if tiers were attached).
- `api/inference_api.py` exposed only a `create_app(cycle, generator)` factory and
  had **no module-level `app`**, so the documented `uvicorn api.inference_api:app`
  had nothing to serve; any caller wiring it by hand inherited the Tier-0 trap.
- `attach_governance` was called in zero non-test files **other than** `recursion1188.py`.

After the fix, an inline check (tiny config, pretrain off) shows
`cycle.governance is not None`, `cycle.value_engine is not None`, and
`cycle.status()` carrying `governance` + `values`; a step runs via the
`source_id`/`origin_type` path the APIs now use.

## Interpretation
This was **entry-point drift**, the same class as the 2026-06-20 finding, one layer
out: composition was copy-built per entry point, so fixing one left the others
behind. The durable fix is to make composition have a single home —
`loop.recursion1188.build_engine(config)` — and route every entry point through
it. The REST `app` is built lazily (PEP 562 `__getattr__`) so plain `import`
stays free of the heavy engine build (`api/__init__.py` imports the module); the
WebSocket loop now drives weighted multi-source so the relational tiers engage;
REST `/step` runs `origin_type="api"` (10/sec flood ceiling — correct for external
callers, vs the loop's `"internal"`).

## Threats / confounds
- Runs: composition check run once at dim 32 (fast, pretrain off). The dim-128
  default path additionally runs corpus pretraining at boot; not exercised here
  (heavy), but `build_engine` is the same code main() already uses in production.
- FastAPI/uvicorn behavior with the lazy `__getattr__` `app` was reasoned about
  (uvicorn resolves `module:app` via `getattr`), not exercised against a live
  uvicorn process in this run.
- Not a measurement of *behavior under load*, only of *composition presence*.

## Open / next
- An integration smoke that actually boots each entry point and asserts Tier-1–3
  state would close the "reasoned, not exercised" gap for uvicorn/websockets.
- Consider a guard/log in `create_app` and `RFEWebSocketServer` that warns if it
  is handed a cycle with no governance attached (defense in depth against future
  hand-built cycles).
