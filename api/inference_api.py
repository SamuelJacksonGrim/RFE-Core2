"""
api/inference_api.py

FastAPI REST inference API for RFE-Core2.

Endpoints
---------
  POST /generate          Single token sequence → latent vector
  POST /step              One autonomous cycle step
  GET  /status            System status snapshot
  GET  /field             Current field state
  GET  /crystals          Crystal store summary
  GET  /attractors        Attractor basin summary
  GET  /ecology           Generator ecology stats
  POST /dream             Trigger one dream cycle
  POST /maintenance       Trigger generator maintenance step
  DELETE /reset           Reset field (not full system)

Usage
-----
  uvicorn api.inference_api:app --host 0.0.0.0 --port 8000

The `app` symbol is built lazily (PEP 562) the first time it is accessed — e.g.
when uvicorn resolves `api.inference_api:app` — so it composes the FULL tier
stack (Tiers 0-3) via `loop.recursion1188.build_engine()`. Plain
`import api.inference_api` does NOT build the engine. To serve a cycle you
composed yourself, call `create_app(cycle, generator)` directly.

Heads-up: with the default config, `build_engine()` pretrains the generator
(~8 epochs) at boot, and uvicorn builds `app` once **per worker** — so a
multi-worker launch trains once per process. For a fast cold start, serve a
config you control:
  `create_app(*build_engine({**CONFIG, "pretrain_on_corpus": False})[:2])`

Requires: pip install fastapi uvicorn
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not available. Install with: pip install fastapi uvicorn")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

if FASTAPI_AVAILABLE:
    class GenerateRequest(BaseModel):
        tokens: List[str]
        token_class: Optional[str] = None

    class StepRequest(BaseModel):
        tokens: List[str]
        source_id: Optional[str] = None

    class GenerateResponse(BaseModel):
        vector: List[float]
        dim:    int
        tokens: List[str]

    class StepResponse(BaseModel):
        step:             int
        key:              str
        rhythm:           str
        coherence:        float
        relation:         float
        pattern:          str
        prediction_error: float
        field_energy:     float
        crystals:         int
        attractors:       int
        emotion:          str
        elapsed_ms:       float


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(cycle, generator) -> "FastAPI":
    """
    Create and configure the FastAPI application.

    Parameters
    ----------
    cycle : AutonomousCycle
    generator : Generator

    Returns
    -------
    FastAPI app instance
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required. Install with: pip install fastapi uvicorn")

    app = FastAPI(
        title       = "RFE-Core2 Inference API",
        description = "Recursive Field Engine — REST interface",
        version     = "2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"],
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # ----------------------------------------------------------------
    # Endpoints
    # ----------------------------------------------------------------

    @app.get("/")
    def root():
        return {"system": "RFE-Core2", "status": "online"}

    @app.post("/generate", response_model=GenerateResponse)
    def generate(req: GenerateRequest):
        """Encode a token sequence into a latent vector."""
        try:
            from agents.symbolic_memory import TokenClass
            tc = None
            if req.token_class:
                try:
                    tc = TokenClass(req.token_class)
                except ValueError:
                    raise HTTPException(400, f"Unknown token_class: {req.token_class}")

            vec = generator.generate(req.tokens, token_class=tc)
            return GenerateResponse(
                vector = vec.tolist(),
                dim    = len(vec),
                tokens = req.tokens,
            )
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post("/step", response_model=StepResponse)
    def step(req: StepRequest):
        """Execute one autonomous cycle step."""
        try:
            # External clients are rate-limited via origin_type="api" (10/sec
            # flood ceiling). source_id defaults to "api" but a client may
            # supply its own so the relational tiers can distinguish callers.
            state = cycle.step(
                req.tokens,
                source_id   = req.source_id or "api",
                origin_type = "api",
            )
            return StepResponse(
                step             = state.step,
                key              = state.key,
                rhythm           = state.rhythm,
                coherence        = state.coherence,
                relation         = state.relation_composite,
                pattern          = state.relation_pattern,
                prediction_error = state.prediction_error,
                field_energy     = state.field_energy,
                crystals         = state.crystals,
                attractors       = state.attractor_centers,
                emotion          = state.dominant_emotion,
                elapsed_ms       = state.elapsed_ms,
            )
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/status")
    def status():
        """Full system status snapshot."""
        return cycle.status()

    @app.get("/field")
    def field_state():
        """Current resonance field observation."""
        obs = cycle.field.observe()
        return {
            "energy":           obs.energy,
            "rhythm":           obs.rhythm,
            "internal_coherence": obs.internal_coherence,
            "spectral": {
                "dominant_frequency": obs.spectral.dominant_frequency,
                "spectral_entropy":   obs.spectral.spectral_entropy,
                "harmonic_ratio":     obs.spectral.harmonic_ratio,
                "phase_coherence":    obs.spectral.phase_coherence,
            },
            "resonated_sample": obs.resonated[:16].tolist(),
        }

    @app.get("/crystals")
    def crystals():
        """Crystal store summary."""
        return {
            "summary":   cycle.crystal_store.summary(),
            "strongest": [
                {
                    "stability":        c.stability,
                    "activation_count": c.activation_count,
                    "usage":            round(c.usage, 4),
                    "origin_tokens":    c.origin_tokens[:5],
                }
                for c in cycle.crystal_store.strongest(n=10)
            ],
        }

    @app.get("/attractors")
    def attractors():
        """Attractor basin summary."""
        return {
            "summary": cycle.attractor.summary(),
            "centers": [
                {
                    "strength":        round(c.strength, 4),
                    "activation_count": c.activation_count,
                    "usage":           round(c.usage, 4),
                    "origin_tokens":   c.origin_tokens[:5],
                }
                for c in sorted(
                    cycle.attractor.centers,
                    key=lambda c: c.strength,
                    reverse=True,
                )[:10]
            ],
        }

    @app.get("/ecology")
    def ecology():
        """Generator symbolic ecology statistics."""
        return generator.ecology_stats()

    @app.post("/dream")
    def dream():
        """Trigger one dream cycle."""
        try:
            from loop.dream_cycle import DreamCycle
            dc = DreamCycle(
                dreamer       = cycle.dreamer,
                crystal_store = cycle.crystal_store,
                field         = cycle.field,
                attractor     = cycle.attractor,
                n_iterations  = 4,
            )
            report = dc.run(
                emotion   = cycle.emotion,
                watcher   = cycle.watcher,
                anchor    = cycle.witness.current_anchor(),
                generator = generator,
            )
            return {
                "iterations":          report.iterations,
                "products":            len(report.products),
                "injected":            report.injected,
                "crystallized":        report.crystallized,
                "field_energy_before": report.field_energy_before,
                "field_energy_after":  report.field_energy_after,
                "elapsed_s":           report.elapsed_s,
            }
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post("/maintenance")
    def maintenance():
        """Trigger generator maintenance step."""
        generator.maintenance_step()
        return {"status": "maintenance complete", **generator.ecology_stats()}

    @app.delete("/reset/field")
    def reset_field():
        """Reset the resonance field to zero (does not clear memory)."""
        cycle.field.reset()
        return {"status": "field reset", "energy": 0.0}

    return app


# ---------------------------------------------------------------------------
# Lazy module-level `app` (PEP 562) for `uvicorn api.inference_api:app`.
#
# Built on first attribute access — NOT at import — so `import api.inference_api`
# (and `from api.inference_api import create_app`, which api/__init__.py does)
# stays free of the heavy engine build. uvicorn's `getattr(module, "app")`
# triggers the build, composing the full tier stack via build_engine().
# ---------------------------------------------------------------------------

_LAZY_APP = None


def __getattr__(name: str):
    if name == "app":
        global _LAZY_APP
        if _LAZY_APP is None:
            from loop.recursion1188 import build_engine
            generator, cycle, _governance, _value_engine = build_engine()
            _LAZY_APP = create_app(cycle, generator)
        return _LAZY_APP
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
