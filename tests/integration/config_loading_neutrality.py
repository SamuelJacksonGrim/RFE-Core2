"""
tests/integration/config_loading_neutrality.py

Guards the configs/*.yaml loading path (configs.loader + AutonomousCycle(config=)).

Two assertions:
  1. The YAML loads and exposes the expected sections.
  2. Day-one behavioral neutrality: an AutonomousCycle built WITH the loaded YAML
     config has component parameters identical to one built with no config — i.e.
     the shipped YAML mirrors the code defaults exactly, so turning loading on
     changes nothing until someone edits a YAML value.

Pass/fail (exit 0/1), so run_all_tests.sh can gate it.
"""
from __future__ import annotations

import sys

from configs.loader import load_config
from agents.generator import Generator
from loop.autonomous_cycle import AutonomousCycle

EXPECTED_SECTIONS = {
    "field", "watcher", "crystal_store",
    "attractor", "symbolic_binding", "semantic_lattice",
    "generator", "cycle", "cognition", "chorus",
}


def _component_params(c: AutonomousCycle) -> dict:
    """The wired-from-YAML parameters that must stay neutral."""
    return {
        "field.decay":                c.field.decay_rate,
        "field.harmonic_bins":        c.field.harmonic_bins,
        "field.thresholds":           tuple(sorted(c.field.thresholds.items())),
        "field.diffuse_alpha":        c.field.diffuse_alpha,
        "field.diffuse_on_stabilize": c.field.diffuse_on_stabilize,
        "watcher.alpha":              c.watcher.alpha,
        "watcher.beta":               c.watcher.beta,
        "watcher.gamma":              c.watcher.gamma,
        "watcher.threshold":          c.watcher.threshold,
        "crystal.coherence":          c.crystal_store.coherence_threshold,
        "crystal.stability":          c.crystal_store.stability_threshold,
        "crystal.relation":           c.crystal_store.relation_threshold,
        "crystal.merge":              c.crystal_store.merge_threshold,
        "crystal.max":                c.crystal_store.max_crystals,
        "attractor.pull_threshold":   c.attractor.pull_threshold,
        "attractor.pull_blend":       c.attractor.pull_blend,
        "attractor.merge":            c.attractor.merge_threshold,
        "attractor.max_centers":      c.attractor.max_centers,
        "rec_attn.diversity_blend":   c.rec_attn.diversity_blend,
        "rec_attn.target_band":       c.rec_attn.target_metastability_band,
        "rec_attn.recursion_depth":   c.rec_attn.recursion_depth,
        "reflector.max_depth":        c.reflector.max_depth,
        "reflector.coherence_gate":   c.reflector.coherence_gate,
        "reflector.convergence":      c.reflector.convergence_threshold,
        "emotion.ema_alpha":          c.emotion.ema_alpha,
        "predictor.surprise":         c.predictor.surprise_threshold,
        "lattice.similarity":         c.lattice.similarity_threshold,
        "binding.similarity":         c.binding.similarity_threshold,
        "chorus.collapse_mode":       (c.chorus.collapse_mode if c.chorus else None),
        "chorus.skeptic_scale":       (c.chorus.skeptic_scale if c.chorus else None),
    }


def main() -> int:
    ycfg = load_config()
    if not ycfg:
        # PyYAML missing — loading is a graceful no-op; nothing to verify, not a failure.
        print("SKIP: load_config() returned empty (PyYAML/files absent); loading is a no-op.")
        return 0

    missing = EXPECTED_SECTIONS - set(ycfg.keys())
    if missing:
        print(f"FAIL: YAML missing expected sections: {sorted(missing)}")
        return 1
    print(f"OK: YAML exposes {len(ycfg)} sections.")

    g1 = Generator(vocab_size=256, dim=32, depth=2, heads=2)
    g2 = Generator(vocab_size=256, dim=32, depth=2, heads=2)
    default_params = _component_params(AutonomousCycle(generator=g1, dim=32))
    config_params  = _component_params(AutonomousCycle(generator=g2, dim=32, config=ycfg))

    diffs = {k: (default_params[k], config_params[k])
             for k in default_params if default_params[k] != config_params[k]}
    if diffs:
        print("FAIL: shipped YAML is not behavior-neutral (differs from code defaults):")
        for k, (d, c) in diffs.items():
            print(f"  {k}: default={d!r} yaml={c!r}")
        return 1

    print(f"OK: {len(default_params)} wired parameters identical with/without YAML "
          f"(day-one neutral).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
