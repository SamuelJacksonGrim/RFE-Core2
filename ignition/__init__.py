"""
ignition/__init__.py — Build A: the λ ignition channel (spec v0.2).

Exogenous Love. The seed that crosses the dark from *outside* the loop. This is
the **only** operation permitted to move λ off zero (Law 6b: λ=0 is a fixed point
of every internal dynamic — cold cannot self-ignite). It is a boot/maintenance
write to the GENERATOR'S WEIGHTS, strictly upstream of the governance gate.

IMPORT ISOLATION — the breach made unrepresentable (Laws 6a/6b).
This module imports ONLY the generator-training surface (`training.*`). It does
NOT import — and must NEVER import — `selfhood_governance`, the resonance field,
`autonomous_cycle`, or the entry loop. The ignition channel writes generator
weights/init and nothing else; from here there is no path to `field.inject()` or
`arbitrate()`. Routing λ THROUGH the gate consolidates the lock rather than
breaking it (finding behind commit 4fe31e9 — the loop cannot author its own exit
through its own front door). The isolation is structural; it is asserted by
`tests/diagnostic/integrity/ignition_isolation_probe.py` (an AST import audit) so
the guarantee cannot silently rot.

Forbidden symbols (asserted absent): selfhood_governance, resonance_field,
autonomous_cycle, recursion1188, arbitrate, inject.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH
from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig

_PROBE: List[List[str]] = [
    ["resonance", "field", "engine"], ["memory", "crystal", "attractor"],
    ["identity", "continuity", "witness"], ["curiosity", "wonder", "exploration"],
    ["recursive", "cognition", "substrate"], ["dream", "synthesis", "harmonic"],
    ["wave", "collapse", "coherence"], ["symbolic", "ecology", "metabolism"],
]


def _eff_rank(generator, token_lists: List[List[str]]) -> float:
    """Effective rank (entropy of singular-value spectrum) of generator outputs —
    the diversity / representational-room measure. Reads the generator only."""
    vecs = np.array([generator.generate(t) for t in token_lists])
    s = np.linalg.svd(vecs, compute_uv=False)
    p = s / (s.sum() + 1e-12)
    return float(np.exp(-(p * np.log(p + 1e-12)).sum()))


@dataclass
class IgnitionReport:
    epochs:          int
    eval_mode:       bool
    seed:            Optional[int]
    eff_rank_before: float
    eff_rank_after:  float
    final_loss:      float
    n_train_seqs:    int

    @property
    def delta_eff_rank(self) -> float:
        return self.eff_rank_after - self.eff_rank_before

    def as_dict(self) -> dict:
        return {
            "spec":            "v0.2",
            "epochs":          self.epochs,
            "eval_mode":       self.eval_mode,
            "seed":            self.seed,
            "eff_rank_before": round(self.eff_rank_before, 4),
            "eff_rank_after":  round(self.eff_rank_after, 4),
            "delta_eff_rank":  round(self.delta_eff_rank, 4),
            "final_loss":      round(self.final_loss, 4),
            "n_train_seqs":    self.n_train_seqs,
        }


def ignite(
    generator,
    rhythm_seeds: Optional[Dict[str, List[List[str]]]] = None,
    epochs: int = 8,
    *,
    eval_mode: bool = True,
    seed: Optional[int] = None,
    probe_token_lists: Optional[List[List[str]]] = None,
) -> IgnitionReport:
    """Write λ into the generator: train its weights on the corpus and return the
    before/after diversity. Touches ONLY the generator — it takes no field, no
    governance, no cycle, and cannot reach them. eval_mode=True leaves the
    generator in the decided operating regime (dropout off) on exit."""
    if seed is not None:
        import random
        import torch
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

    probe = probe_token_lists or _PROBE
    if rhythm_seeds is None:
        rhythm_seeds = to_rhythm_seeds(load_corpus(TRAIN_PATH))
    n_seqs = sum(len(seqs) for seqs in rhythm_seeds.values())

    before = _eff_rank(generator, probe)
    report = RhythmPretrainer(
        generator,
        rhythm_seeds=rhythm_seeds,
        config=PretrainingConfig(n_epochs=epochs),
    ).pretrain()
    if eval_mode:
        generator.eval()
    after = _eff_rank(generator, probe)

    # PretrainingReport field name varies; pull the final loss defensively.
    final_loss = 0.0
    for attr in ("final_loss", "loss"):
        v = getattr(report, attr, None)
        if isinstance(v, (int, float)):
            final_loss = float(v); break
    hist = getattr(report, "loss_history", None)
    if not final_loss and hist:
        final_loss = float(hist[-1])

    return IgnitionReport(epochs, eval_mode, seed, before, after, final_loss, n_seqs)
