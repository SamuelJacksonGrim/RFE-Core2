"""
cognition/recursive_attention.py

Recursive attention over the system's own prior latent states.

Instead of one-pass inference:
    output = transformer(tokens)

We apply:
    state = transformer(tokens)
    for _ in range(depth):
        state = attend(state, history_of_states)

This creates:
  - Reflective stabilization
  - Self-referencing cognition
  - Attractor convergence in latent space
  - Echo-memory: prior states influence current interpretation

Architecture
------------
  MultiHeadSelfAttention over a rolling window of prior states.
  Each recursive pass refines the current state by attending to
  what the system has recently thought.

  The output is the refined state vector — same dimensionality as input,
  but now informed by its own recent trajectory.
"""

from __future__ import annotations

import collections
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class RecursiveAttention(nn.Module):
    """
    Multi-head self-attention over rolling latent state history.

    Parameters
    ----------
    dim : int
        Vector dimensionality.
    heads : int
        Number of attention heads.
    history_len : int
        Maximum number of prior states to attend over.
    recursion_depth : int
        Number of recursive refinement passes per call.
    dropout : float
        Attention dropout.
    device : str or None
    """

    def __init__(
        self,
        dim:             int   = 128,
        heads:           int   = 4,
        history_len:     int   = 16,
        recursion_depth: int   = 3,
        dropout:         float = 0.1,
        device:          Optional[str] = None,
    ):
        super().__init__()
        assert dim % heads == 0

        self.dim             = dim
        self.heads           = heads
        self.history_len     = history_len
        self.recursion_depth = recursion_depth
        self.device          = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.norm_in  = nn.LayerNorm(dim)
        self.attn     = nn.MultiheadAttention(
            embed_dim   = dim,
            num_heads   = heads,
            dropout     = dropout,
            batch_first = True,
        )
        self.norm_out = nn.LayerNorm(dim)
        self.ff       = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 2, dim),
        )
        self.norm_ff  = nn.LayerNorm(dim)

        self._history: collections.deque = collections.deque(maxlen=history_len)

        self.to(self.device)

    @torch.no_grad()
    def refine(self, vec: np.ndarray) -> np.ndarray:
        """
        Recursively refine a vector by attending to its own history.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)

        Returns
        -------
        np.ndarray, shape (dim,), L2-normalized
        """
        x = torch.tensor(vec, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)
        # (1, 1, dim)

        # Build context from history + current
        if len(self._history) == 0:
            context = x
        else:
            history_tensors = [
                torch.tensor(h, dtype=torch.float32).to(self.device)
                for h in self._history
            ]
            history_stack = torch.stack(history_tensors).unsqueeze(0)  # (1, n, dim)
            context = torch.cat([history_stack, x], dim=1)             # (1, n+1, dim)

        state = x

        for _ in range(self.recursion_depth):
            # Pre-norm attention: query=state, key/value=context
            q   = self.norm_in(state)
            kv  = self.norm_in(context)
            out, _ = self.attn(q, kv, kv)
            state = state + out                         # residual
            state = state + self.ff(self.norm_out(state))  # FF residual
            state = self.norm_ff(state)

        result = state.squeeze(0).squeeze(0).cpu().numpy()
        result = result / (np.linalg.norm(result) + 1e-8)

        # Commit current (pre-refinement) vec to history
        self._history.append(vec.copy())

        return result.astype(np.float32)

    def clear_history(self):
        self._history.clear()

    def history_centroid(self) -> Optional[np.ndarray]:
        if not self._history:
            return None
        mean = np.mean(list(self._history), axis=0)
        return (mean / (np.linalg.norm(mean) + 1e-8)).astype(np.float32)
