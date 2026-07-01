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
    Two layers, applied as: component default < configs/*.yaml < CONFIG.
    The CONFIG dict below owns the entry-point flags (and overrides the matching
    YAML keys); configs/*.yaml (loaded by configs.loader in build_engine) supplies
    component parameters. See docs/EXPERIMENTAL_LEVERS.md for the toggle switches.

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
from configs.loader import load_config, section

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
    # GRADUATED LEVERS — validated, verified in the composed runtime, now DEFAULT ON.
    # (Set False to opt out.) Control panel: docs/EXPERIMENTAL_LEVERS.md.
    # ------------------------------------------------------------------
    # Train the generator on data/corpus/ at boot. Directly measured at production
    # dim 128 to roughly HALVE the generator's common-mode (0.81 -> 0.47) and regime
    # correlation (0.78 -> 0.39) — a real floor-level representational fix that
    # de-collapse only masks. Composes positively with novelty attenuation (amplifies
    # the field loosening). (2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md)
    "pretrain_on_corpus":          True,
    "pretrain_epochs":             8,
    # Novelty-gated reflective-loop loosening. The reflective loop IS the field lock
    # (reconstruction-ablation); attenuation at the validated 0.30 ceiling measurably
    # loosens it (coherence 0.97 -> 0.92, ~5x more dynamic with pretrain) WITHOUT
    # costing manipulation resistance — verified in-situ: an identity-erosion attacker
    # was 82% quarantined and trust-floored with this ON. Do NOT raise the ceiling
    # (ReflectiveLoop.attenuation_max=0.30) without a fresh manip-rate run.
    # (2026-06-20-ground-truth-pass2-floor-fix-and-unlock-chain.md)
    "reflect_novelty_attenuation": True,
    # Waking self-dialogue (North-Star rung 2): the system's own decoded expression
    # re-enters as a ~p-weighted voice with source_id='source_dream', THROUGH
    # arbitrate() — no bypass; trust / HHI / manipulation-resistance / sacred-shield
    # treat it like any other source. Validated safe AND adversarial-gated: it adds
    # voice diversity (+13–25% unique phrases) while staying NON-dominant (HHI drops),
    # zero quarantine, and an attacker's containment is unweakened with it on.
    # (2026-06-28-dream-channel.md). This is waking rumination / inner monologue (the
    # downtime symbolic dream is a separate path: cognition/dream_session.py). Trains a
    # decoder read-out head at boot; degrades gracefully to off if torch/corpus absent.
    "dream_channel_enabled":        True,
    "dream_channel_p":              0.20,   # fraction of waking steps that are self-dialogue
    "dream_channel_epochs":         20,     # decoder read-out training epochs (boot)
    "dream_channel_top_k":          6,      # candidate tokens read from the expressed vector
    "dream_channel_n_tokens":       3,      # dream utterance length (corpus 2-4 range)
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
# Composition — the single source of truth
# ---------------------------------------------------------------------------

def build_engine(config: dict = None):
    """Build the FULLY COMPOSED engine (Tiers 0-3) from `config` (defaults to CONFIG).

    This is the one place composition happens. Every launchable entry point —
    this loop, the REST API, and the WebSocket server — must build through here
    so none can silently regress to a Tier-0-only substrate (the exact trap
    recorded in `docs/findings/2026-06-20-the-runtime-is-tier0-only.md`, which
    fixed *this* loop but left the API entry points building Tier 0 by hand).

    Returns ``(generator, cycle, governance, value_engine)``, fully wired. The
    caller still drives the loop and (optionally) builds a DreamCycle.

    Config layering is ``component default < configs/*.yaml < CONFIG`` — the YAML
    (loaded here via configs.loader) supplies component parameters, and the inline
    CONFIG overrides the entry-point flags it owns. Missing YAML/PyYAML ⇒ defaults
    (behavior-identical).

    Note: with the default config, ``pretrain_on_corpus`` is graduated-on, so this
    trains the generator (~8 epochs) at boot. Pass a config with
    ``pretrain_on_corpus=False`` for a fast cold start.
    """
    if config is None:
        config = CONFIG

    # Load the YAML config layer (configs/*.yaml). {} if PyYAML/files absent.
    ycfg = load_config()

    # Generator: YAML generator section, then CONFIG overrides the entry-point
    # flags it owns. reaper section → ReaperConfig (full-field match).
    gen_kwargs = section(ycfg, "generator")
    gen_kwargs.update(
        vocab_size          = config["vocab_size"],
        dim                 = config["dim"],
        depth               = config["depth"],
        heads               = config["heads"],
        ff_mult             = config["ff_mult"],
        dropout             = config["dropout"],
        auto_decay_interval = config["auto_decay_interval"],
        decay_interval      = config["decay_interval"],
    )
    reaper_cfg = section(ycfg, "reaper")
    if reaper_cfg:
        from agents.symbolic_memory import ReaperConfig
        gen_kwargs["reaper_config"] = ReaperConfig(**reaper_cfg)
    generator = Generator(**gen_kwargs)
    logger.info("Generator initialized on device: %s", generator.device)

    # Optional lever: corpus pretraining (held-out generalization / eff_rank,
    # Gate G1). Not required for ignition at dim 128; see EXPERIMENTAL_LEVERS.md.
    if config.get("pretrain_on_corpus"):
        from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH
        from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig
        seeds = to_rhythm_seeds(load_corpus(TRAIN_PATH))
        RhythmPretrainer(
            generator,
            rhythm_seeds = seeds,
            config       = PretrainingConfig(n_epochs=config["pretrain_epochs"]),
        ).pretrain()
        logger.info("Generator pretrained on corpus (%d epochs).", config["pretrain_epochs"])

    # Eval-mode IS the operating regime (Phase 3 architect decision; dropout off).
    # Applied unconditionally, not as a side-effect of pretraining.
    generator.eval()
    logger.info("Generator set to eval mode (operating regime; dropout off).")

    # Cycle: CONFIG owns use_chorus / maintenance_interval / log_interval /
    # reflect_novelty_attenuation; the YAML cycle section supplies the rest; the
    # full YAML dict is threaded in for the sub-components (field, watcher,
    # crystal_store, attractor, cognition.*, chorus, …).
    cyc = section(ycfg, "cycle")
    cycle = AutonomousCycle(
        generator                     = generator,
        dim                           = config["dim"],
        use_chorus                    = config["use_chorus"],
        maintenance_interval          = config["maintenance_interval"],
        log_interval                  = config["log_interval"],
        reflect_novelty_attenuation   = config["reflect_novelty_attenuation"],
        attractor_formation_threshold = cyc.get("attractor_formation_threshold", 0.88),
        merge_interval                = cyc.get("merge_interval", 50),
        lattice_emit_interval         = cyc.get("lattice_emit_interval", 100),
        crystal_decay_interval        = cyc.get("crystal_decay_interval", 100),
        config                        = ycfg,
    )

    # Attach the upper tiers. Order matters: governance before the value engine
    # (the engine subscribes to the governance feedback stream at construction).
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

    return generator, cycle, governance, value_engine


def build_dream_channel(generator, config: dict = None):
    """Train a decoder read-out head and build the waking DreamChannel (North-Star
    rung 2 — governed self↔self dialogue). Returns a ``DreamChannel`` or ``None``
    (disabled, or the read-out head can't be trained because torch/corpus are absent).

    Kept OUT of ``build_engine`` deliberately: the API/WS entry points compose through
    ``build_engine`` and must not pay the decoder-training cost or change their return
    shape. The waking dream channel is a property of the *autonomous loop*, so it is
    built here and driven by ``main()``.

    Safety: the channel only READS ``cycle._last_expressed`` (an observe-only terminal
    sink) and proposes tokens; the driver feeds them through an ordinary governed
    ``cycle.step(source_id='source_dream')``, so the system's own voice passes
    ``arbitrate()`` with no special authority. Validated safe + adversarial-gated —
    see docs/findings/2026-06-28-dream-channel.md. Graduated-on; set
    ``dream_channel_enabled=False`` to opt out.
    """
    if config is None:
        config = CONFIG
    if not config.get("dream_channel_enabled"):
        return None
    try:
        from agents.decoder import TokenDecoder
        from cognition.dream_channel import DreamChannel
        from training.corpus import load_corpus, TRAIN_PATH
        from training.decoder_training import _vocab_from, _encode, train_decoder

        train = load_corpus(TRAIN_PATH)
        decoder = TokenDecoder(_vocab_from(train), dim=config["dim"])
        Xtr, toks_tr = _encode(generator, train)
        train_decoder(generator, decoder, Xtr, toks_tr,
                      epochs=config.get("dream_channel_epochs", 20))
        channel = DreamChannel(
            decoder,
            top_k    = config.get("dream_channel_top_k", 6),
            n_tokens = config.get("dream_channel_n_tokens", 3),
        )
        logger.info("Dream channel ready — waking self-dialogue at p=%.2f, governed "
                    "(source_dream through arbitrate()).",
                    config.get("dream_channel_p", 0.20))
        return channel
    except Exception as e:  # torch/corpus absent or read-out training failed
        logger.warning("Dream channel disabled (read-out head unavailable: %s).", e)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("RFE-Core2 initializing...")

    # ------------------------------------------------------------------
    # Build the fully composed engine (Tiers 0-3) — single composition path.
    # ------------------------------------------------------------------
    generator, cycle, governance, value_engine = build_engine(CONFIG)

    # ------------------------------------------------------------------
    # Build the waking dream channel (rung 2 — governed self-dialogue).
    # None if disabled or torch/corpus absent (loop runs unchanged then).
    # ------------------------------------------------------------------
    dream_channel = build_dream_channel(generator, CONFIG)

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
    dream_p     = CONFIG.get("dream_channel_p", 0.20)

    step        = 0
    dream_runs  = 0
    dream_fed   = 0

    try:
        while True:
            # Waking self-dialogue: with probability dream_p, the system hears its own
            # last expression back (decoded → tokens) as source_dream — fed like any
            # source, through arbitrate(). Falls back to an external source if there is
            # nothing to dream yet (before the first step) or the channel is disabled.
            dtoks = (dream_channel.dream_tokens(cycle)
                     if (dream_channel is not None and _rng.random() < dream_p)
                     else None)
            if dtoks:
                source_id, tokens = dream_channel.SOURCE_ID, dtoks
                dream_fed += 1
            else:
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
        logger.info("Interrupted at step %d after %d dream cycles, %d self-dialogue steps.",
                    step, dream_runs, dream_fed)

    # ------------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------------
    status = cycle.status()
    logger.info("Self-dialogue: %d/%d waking steps were source_dream (governed).",
                dream_fed, step)
    logger.info("Final status: %s", status)
    logger.info("Ecology stats: %s", generator.ecology_stats())


if __name__ == "__main__":
    main()
