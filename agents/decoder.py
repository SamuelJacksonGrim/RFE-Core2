"""
agents/decoder.py — the read-out head: vector → tokens (the reverse of the Generator).

The Generator is an encoder: tokens → one L2-normalized dim-vector. The Decoder adds
the missing half — given a vector (a "thought"), it guesses which tokens would have
produced it. Together they are an autoencoder; the Decoder is trained to reverse the
(frozen) encoder on the existing corpus.

What it is NOT: a sequence model. The encoder mean-pools over the sequence and
L2-normalizes, so token *order* and *magnitude* are not recoverable — the Decoder
predicts a **bag of tokens** (which tokens are present), not their order. That lossiness
is itself a measurement: if the Decoder cannot recover the bag, the encoder is too lossy
(a statement about representational room).

Discipline: this is a TERMINAL SINK, like the Voice tool and the metastability monitors.
It reads the expressed vector and renders tokens; it does NOT write the field, governance,
or any cognitive state. (A future governed "dream channel" — feeding decoded tokens back
in as one source among many through arbitrate() — would be a separate, explicit wiring.)
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class TokenDecoder(nn.Module):
    """Vector → bag-of-tokens distribution.

    Parameters
    ----------
    vocab : sequence of str
        The decoder's own token list (built from the corpus). Index i ↔ vocab[i].
    dim : int
        Input vector dimension (must match the Generator's output dim).
    hidden : int
        Hidden width. A single Linear(dim, vocab) also works; a small hidden layer
        gives the head a little nonlinearity for free. Set hidden=0 for the pure
        linear "lookup table with opinions".
    """

    def __init__(self, vocab: Sequence[str], dim: int = 128, hidden: int = 256,
                 device: Optional[str] = None):
        super().__init__()
        self.tokens: List[str] = list(vocab)
        self.index = {t: i for i, t in enumerate(self.tokens)}
        self.dim = dim
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        v = len(self.tokens)
        if hidden and hidden > 0:
            self.net = nn.Sequential(
                nn.Linear(dim, hidden),
                nn.GELU(),
                nn.Linear(hidden, v),
            )
        else:
            self.net = nn.Linear(dim, v)
        self.to(self.device)

    @property
    def vocab_size(self) -> int:
        return len(self.tokens)

    def forward(self, vec: torch.Tensor) -> torch.Tensor:
        """vec: (B, dim) → logits (B, vocab). Multi-label (sigmoid) head."""
        return self.net(vec)

    def multi_hot(self, token_lists: Sequence[Sequence[str]]) -> torch.Tensor:
        """Build (N, vocab) multi-hot targets from token lists (unknown tokens skipped)."""
        y = torch.zeros(len(token_lists), self.vocab_size, device=self.device)
        for r, toks in enumerate(token_lists):
            for t in toks:
                j = self.index.get(t)
                if j is not None:
                    y[r, j] = 1.0
        return y

    @torch.no_grad()
    def decode(self, vec, top_k: int = 8) -> List[Tuple[str, float]]:
        """Render a single vector to its top-k (token, probability) guesses."""
        self.eval()
        x = torch.as_tensor(vec, dtype=torch.float32, device=self.device)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        probs = torch.sigmoid(self.forward(x))[0]
        k = min(top_k, self.vocab_size)
        vals, idx = probs.topk(k)
        return [(self.tokens[int(i)], float(p)) for p, i in zip(vals, idx)]

    def state(self) -> dict:
        return {"vocab_size": self.vocab_size, "dim": self.dim,
                "params": sum(p.numel() for p in self.parameters())}
