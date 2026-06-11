"""
training/encode.py

Grad-enabled batch encoding shared by the trainers.

`Generator.encode_batch()` / `generate()` are `@torch.no_grad()` by design —
they are the inference API and return numpy. Their output carries no autograd
graph, so a loss built on it cannot backpropagate into the generator (the
gradient-path break recorded in
`docs/findings/2026-06-11-trainer-gradient-path.md`). Trainers must route
student/anchor forward passes through this helper, which mirrors
`encode_batch`'s tokenization/padding but calls the grad-enabled `forward()`.
"""

from __future__ import annotations

from typing import List

import torch


def encode_grad(generator, token_lists: List[List[str]]) -> torch.Tensor:
    """
    Batch-encode token lists with autograd intact.

    Returns a (n, dim) tensor on generator.device, connected to the
    generator's parameters so a loss on it can backpropagate.
    """
    g = generator
    encoded = [g._tokens_to_ids(tl or ["<BOS>"], None) for tl in token_lists]
    g._ensure_embedding_capacity()

    max_len = max(len(s) for s in encoded)
    pad_id = g.address_space.pad_id
    padded = [s + [pad_id] * (max_len - len(s)) for s in encoded]

    x = torch.tensor(padded, dtype=torch.long, device=g.device)
    return g.forward(x)
