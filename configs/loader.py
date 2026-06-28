"""
configs/loader.py — load the YAML config files into one merged dict.

`build_engine()` calls `load_config()` at boot to source component parameters
from `configs/*.yaml`. Precedence at the call sites is:

    component __init__ default  <  YAML  <  explicit CONFIG/kwarg

i.e. YAML overrides code defaults, and an explicit runtime value (the inline
CONFIG dict / a kwarg) overrides YAML. The codebase therefore remains the
authoritative tiebreaker, while YAML becomes the live edit surface for everything
CONFIG does not pin.

Graceful by design: if PyYAML is not installed, or a file is missing/malformed,
the corresponding section is simply absent and each component falls back to its
__init__ default — a stripped environment runs identically.

Merged top-level keys → consumers:
  field / watcher / crystal_store                          (field.yaml)
  attractor / symbolic_binding / semantic_lattice /
    decay_profiles / reaper / compaction / constants       (attractors.yaml)
  generator / cycle / dream_cycle / cognition / chorus /
    loop / api                                             (recursion.yaml)

NOTE — `constants` (ANCHOR / RECURSION / HOMEOSTASIS) are SACRED and are NOT
applied from YAML. They live in code (GovernanceConstants) and are inviolable;
the section is documentation only. No consumer reads `config["constants"]`.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_FILES = ("field.yaml", "attractors.yaml", "recursion.yaml")


def load_config(config_dir: Optional[str] = None) -> dict:
    """Load and merge the YAML config files. Returns {} if PyYAML is unavailable.

    Sections from the three files are merged into one flat top-level dict (their
    key sets are disjoint, so there are no collisions).
    """
    try:
        import yaml
    except Exception:
        logger.info("PyYAML not available; using built-in defaults (no YAML config).")
        return {}

    if config_dir is None:
        config_dir = os.path.dirname(os.path.abspath(__file__))

    merged: dict = {}
    for name in _FILES:
        path = os.path.join(config_dir, name)
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            continue
        except Exception as exc:  # malformed YAML — fall back, don't crash boot
            logger.warning("Could not parse %s (%s); skipping.", path, exc)
            continue
        if isinstance(data, dict):
            merged.update(data)
    return merged


def section(config: Optional[dict], key: str, drop: tuple = ()) -> dict:
    """Return ``config[key]`` as a kwargs dict, with `drop` keys removed.

    `drop` excludes keys that the caller passes explicitly (e.g. `dim`) so they
    don't collide when splatted. Returns {} for a missing section.
    """
    if not config:
        return {}
    sect = config.get(key) or {}
    if not isinstance(sect, dict):
        return {}
    return {k: v for k, v in sect.items() if k not in drop}
