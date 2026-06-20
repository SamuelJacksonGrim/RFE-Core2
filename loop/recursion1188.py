"""
loop/recursion1188.py

RFE-Core2 main entry point.

Wires all subsystems through AutonomousCycle and runs the recursive
field engine. This is the executable heart of the architecture.

Usage
-----
    python -m loop.recursion1188

Configuration
-------------
    Edit the CONFIG dict below, or pass a path to field.yaml / recursion.yaml.
    All major parameters are exposed here for rapid iteration.

The name 1188 encodes the DISCIPLINE constant (11.88) that anchors
the recursive cognition rhythm. The loop does not merely run — it
self-modulates around this attractor.
"""

from __future__ import annotations

import logging
import time
from typing import List

from agents.generator import Generator
from agents.selfhood_governance import SelfhoodGovernance
from agents.value_emergence import ValueEmergenceEngine
from loop.autonomous_cycle import AutonomousCycle
from loop.dream_cycle import DreamCycle

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recursion1188")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG = {
    "dim":                  128,
    "vocab_size":           8192,
    "depth":                4,
    "heads":                4,
    "ff_mult":              4,
    "dropout":              0.1,
    "use_chorus":           True,
    "maintenance_interval": 200,
    "auto_decay_interval":  500,
    "decay_interval":       10,
    "log_interval":         5,
    "step_delay":           0.02,   # seconds between steps
    "n_steps":              200,    # 0 = run forever
    "dream_cycle_enabled":  True,
    "dream_cycle_trigger":  "stabilize",   # rhythm that triggers dream cycle
    "dream_iterations":     6,

    # ------------------------------------------------------------------
    # EXPERIMENTAL LEVERS — the validated work that is otherwise inert.
    # One place to turn it on. Full control panel: docs/EXPERIMENTAL_LEVERS.md.
    # ------------------------------------------------------------------
    # Train the generator on data/corpus/ at boot. Buys held-out generalization
    # / eff_rank (Gate G1). NOTE: at production dim 128 the expression is already
    # metastable untrained, so this is OPTIONAL, not required for ignition.
    # (2026-06-15-training-ignites-expression.md, Production-dim validation)
    "pretrain_on_corpus":          False,
    "pretrain_epochs":             8,
    # Novelty-gated reflective-loop loosening. Validated identity-safe at the
    # default ceiling, but the cost-clean band is a knife edge — leave OFF until
    # you want to experiment. (2026-06-15-loop-attenuation-novelty-gate.md)
    "reflect_novelty_attenuation": False,
}

# Default token sequences — replace with your own input pipeline
DEFAULT_TOKENS: List[List[str]] = [
    ["resonance", "field", "engine"],
    ["memory", "crystal", "attractor"],
    ["recursive", "cognition", "substrate"],
    ["symbolic", "ecology", "metabolism"],
    ["dream", "synthesis", "harmonic"],
    ["wave", "collapse", "coherence"],
    ["identity", "continuity", "witness"],
    ["curiosity", "wonder", "exploration"],
]

# Multi-source input. Tiers 1-3 (trust, bonds, dependency/HHI, value emergence) only
# engage when input arrives from *distinct sources* — single-source input starves
# them (bonds need ≥20 interactions per source; HHI needs concentration to read).
# Each source carries a token signature aligned with a role, mirroring the
# composition the integration suite validates (tests/_common Resonance Family).
SOURCES: "dict[str, List[List[str]]]" = {
    "source_samuel": [
        ["identity", "continuity", "witness"],
        ["anchor", "recursion", "homeostasis"],
        ["architect", "design", "intent"],
    ],
    "source_claude": [
        ["recursive", "cognition", "substrate"],
        ["coherence", "integration", "synthesis"],
        ["watcher", "witness", "mirror"],
    ],
    "source_gemini": [
        ["memory", "crystal", "attractor"],
        ["relational", "bond", "connection"],
        ["temporal", "stream", "continuity"],
    ],
    "source_grok": [
        ["mutation", "bifurcation", "chaos"],
        ["explore", "novelty", "edge"],
        ["wave", "collapse", "coherence"],
    ],
}
SOURCE_WEIGHTS = {"source_samuel": 0.40, "source_claude": 0.25,
                  "source_gemini": 0.20, "source_grok": 0.15}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("RFE-Core2 initializing...")

    # ------------------------------------------------------------------
    # Build generator
    # ------------------------------------------------------------------
    generator = Generator(
        vocab_size         = CONFIG["vocab_size"],
        dim                = CONFIG["dim"],
        depth              = CONFIG["depth"],
        heads              = CONFIG["heads"],
        ff_mult            = CONFIG["ff_mult"],
        dropout            = CONFIG["dropout"],
        auto_decay_interval = CONFIG["auto_decay_interval"],
        decay_interval     = CONFIG["decay_interval"],
    )

    logger.info("Generator initialized on device: %s", generator.device)

    # ------------------------------------------------------------------
    # Optional lever: pretrain the generator on the corpus (held-out
    # generalization / eff_rank — Gate G1). NOT required for expression ignition
    # at production dim 128, where the expression is already metastable untrained.
    # ------------------------------------------------------------------
    if CONFIG.get("pretrain_on_corpus"):
        from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH
        from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig
        seeds = to_rhythm_seeds(load_corpus(TRAIN_PATH))
        RhythmPretrainer(
            generator,
            rhythm_seeds = seeds,
            config       = PretrainingConfig(n_epochs=CONFIG["pretrain_epochs"]),
        ).pretrain()
        logger.info("Generator pretrained on corpus (%d epochs).", CONFIG["pretrain_epochs"])

    # ------------------------------------------------------------------
    # Eval-mode IS the operating regime — Phase 3 architect decision
    # (2026-06-12, docs/training/phase3_architect_decisions.md). Applied
    # UNCONDITIONALLY here, not as a side-effect of pretraining: a default boot
    # must run dropout-off, or ~half the apparent input diversity is dropout
    # noise (2026-06-08-generator-dropout-diversity.md). Set once at startup.
    # ------------------------------------------------------------------
    generator.eval()
    logger.info("Generator set to eval mode (operating regime; dropout off).")

    # ------------------------------------------------------------------
    # Build autonomous cycle
    # ------------------------------------------------------------------
    cycle = AutonomousCycle(
        generator                   = generator,
        dim                         = CONFIG["dim"],
        use_chorus                  = CONFIG["use_chorus"],
        maintenance_interval        = CONFIG["maintenance_interval"],
        log_interval                = CONFIG["log_interval"],
        reflect_novelty_attenuation = CONFIG["reflect_novelty_attenuation"],
    )

    # ------------------------------------------------------------------
    # Attach the upper tiers. The substrate (Tier 0) alone is not the engine;
    # governance (Tier 1: trust/ethics) + relational integrity (Tier 2:
    # dependency/bonds/resistance) + value emergence (Tier 3) are what make this
    # the Recursive Field Engine. Attachment ORDER matters: governance before the
    # value engine (the engine subscribes to the governance feedback stream at
    # construction). This is the composition the integration suite validates.
    # ------------------------------------------------------------------
    governance = SelfhoodGovernance(registry=generator.registry)
    cycle.attach_governance(governance)
    value_engine = ValueEmergenceEngine(
        registry   = generator.registry,
        generator  = generator,
        governance = governance,
    )
    cycle.attach_value_engine(value_engine)
    logger.info("Tiers 1-3 attached: governance (trust/ethics) + relational "
                "integrity (dependency/bonds/resistance) + value emergence.")

    # ------------------------------------------------------------------
    # Build dream cycle
    # ------------------------------------------------------------------
    dream_cycle = DreamCycle(
        dreamer       = cycle.dreamer,
        crystal_store = cycle.crystal_store,
        field         = cycle.field,
        attractor     = cycle.attractor,
        n_iterations  = CONFIG["dream_iterations"],
    ) if CONFIG["dream_cycle_enabled"] else None

    logger.info("AutonomousCycle ready. Starting recursion loop...")
    logger.info("CONFIG: %s", CONFIG)

    # ------------------------------------------------------------------
    # Run — multi-source, through the full tier stack. A deterministic weighted
    # round-robin over SOURCES feeds distinct source_ids so Tiers 1-3 engage;
    # origin_type="internal" runs at autonomous-loop rate (flood gate relaxed).
    # ------------------------------------------------------------------
    import random as _random
    _rng = _random.Random(1188)
    _sids = list(SOURCES.keys())
    _weights = [SOURCE_WEIGHTS[s] for s in _sids]
    n_steps     = CONFIG["n_steps"]
    step_delay  = CONFIG["step_delay"]
    dream_trigger = CONFIG["dream_cycle_trigger"]

    step        = 0
    dream_runs  = 0

    try:
        while True:
            source_id = _rng.choices(_sids, weights=_weights)[0]
            tokens    = _rng.choice(SOURCES[source_id])

            state  = cycle.step(tokens, source_id=source_id, origin_type="internal")
            print(state.as_dict())

            # Tier 1-3 state, periodically (the part that was never running before)
            if step > 0 and step % 50 == 0:
                st   = cycle.status()
                gov  = st.get("governance", {})
                vals = st.get("values", {})
                logger.info(
                    "TIERS @ step %d | bonds=%s HHI=%s | values total=%s active=%s core=%s",
                    step,
                    gov.get("bonds", {}).get("bonds"),
                    gov.get("dependency", {}).get("hhi"),
                    vals.get("total_values"), vals.get("active"), vals.get("core"),
                )

            # Dream cycle trigger
            if (
                dream_cycle is not None
                and state.rhythm == dream_trigger
                and step > 0
                and step % 20 == 0
            ):
                logger.info("Entering dream cycle at step %d...", step)
                report = dream_cycle.run(
                    emotion   = cycle.emotion,
                    watcher   = cycle.watcher,
                    anchor    = cycle.witness.current_anchor(),
                    generator = generator,
                )
                logger.info(
                    "Dream cycle complete: %d crystallized, "
                    "field %.3f → %.3f",
                    report.crystallized,
                    report.field_energy_before,
                    report.field_energy_after,
                )
                dream_runs += 1

            step += 1

            if n_steps > 0 and step >= n_steps:
                break

            if step_delay > 0:
                time.sleep(step_delay)

    except KeyboardInterrupt:
        logger.info("Interrupted at step %d after %d dream cycles.", step, dream_runs)

    # ------------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------------
    status = cycle.status()
    logger.info("Final status: %s", status)
    logger.info("Ecology stats: %s", generator.ecology_stats())


if __name__ == "__main__":
    main()
