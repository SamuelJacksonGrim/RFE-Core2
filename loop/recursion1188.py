# Copyright 2026 Samuel Jackson Grim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
    # Build autonomous cycle
    # ------------------------------------------------------------------
    cycle = AutonomousCycle(
        generator            = generator,
        dim                  = CONFIG["dim"],
        use_chorus           = CONFIG["use_chorus"],
        maintenance_interval = CONFIG["maintenance_interval"],
        log_interval         = CONFIG["log_interval"],
    )

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
    # Run
    # ------------------------------------------------------------------
    token_seq   = DEFAULT_TOKENS
    n_steps     = CONFIG["n_steps"]
    step_delay  = CONFIG["step_delay"]
    dream_trigger = CONFIG["dream_cycle_trigger"]

    step        = 0
    dream_runs  = 0

    try:
        while True:
            tokens = token_seq[step % len(token_seq)]

            state  = cycle.step(tokens)
            print(state.as_dict())

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
