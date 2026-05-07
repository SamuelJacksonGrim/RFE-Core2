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

"""
agents/generator.py

Transformer encoder that produces normalized latent vectors from token sequences.

Fixes over v1:
  - VocabEncoder replaces SHA256 tokenizer: deterministic token→id mapping
    with consistent identity across calls, proper PAD/UNK/BOS/EOS specials.
  - src_key_padding_mask passed to TransformerEncoder so attention never
    attends over padding positions.
  - Pre-LN (norm_first=True) for training stability.
  - LayerNorm before and after projection head.
  - Masked mean pooling: PAD tokens excluded from the pool.
  - Xavier init on linear layers, normal init on embeddings.
  - Seed isolated to module init, not mutated globally.
  - encode_batch() for batched inference with automatic padding.
"""

import math
from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class VocabEncoder:
    """
    Deterministic whitespace-level tokenizer with a fixed vocabulary ceiling.

    Token identity is preserved across calls: the same string always maps to
    the same integer ID. Collisions within the reserved slot range are handled
    by linear probing so every unique token gets a unique slot (up to
    vocab_size - len(SPECIAL) distinct tokens before wrapping).

    Special tokens
    --------------
    <PAD>  0   — padding, ignored by attention mask
    <UNK>  1   — unknown / fallback
    <BOS>  2   — beginning of sequence
    <EOS>  3   — end of sequence
    """

    SPECIAL = ["<PAD>", "<UNK>", "<BOS>", "<EOS>"]

    def __init__(self, vocab_size: int = 8192):
        self.vocab_size = vocab_size
        self._tok2id: dict[str, int] = {t: i for i, t in enumerate(self.SPECIAL)}
        self._id2tok: dict[int, str] = {i: t for t, i in self._tok2id.items()}
        self._reserved = set(range(len(self.SPECIAL)))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pad_id(self) -> int:
        return self._tok2id["<PAD>"]

    @property
    def unk_id(self) -> int:
        return self._tok2id["<UNK>"]

    @property
    def bos_id(self) -> int:
        return self._tok2id["<BOS>"]

    @property
    def eos_id(self) -> int:
        return self._tok2id["<EOS>"]

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def token_id(self, token: str) -> int:
        if token in self._tok2id:
            return self._tok2id[token]

        base = len(self.SPECIAL)
        span = self.vocab_size - base
        slot = (hash(token) % span) + base

        # Linear probe to avoid collisions
        probe = slot
        while probe in self._id2tok and self._id2tok[probe] != token:
            probe = (probe - base + 1) % span + base

        self._tok2id[token] = probe
        self._id2tok[probe] = token
        return probe

    def encode(self, tokens: List[str]) -> List[int]:
        return [self.token_id(t) for t in tokens]

    def decode(self, ids: List[int]) -> List[str]:
        return [self._id2tok.get(i, "<UNK>") for i in ids]

    def __len__(self) -> int:
        return self.vocab_size


# ---------------------------------------------------------------------------
# Positional Encoding
# ---------------------------------------------------------------------------

class PositionalEncoding(nn.Module):
    """Standard sinusoidal PE with dropout."""

    def __init__(self, dim: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, dim)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(
            torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        if dim % 2 == 0:
            pe[:, 1::2] = torch.cos(position * div_term)
        else:
            pe[:, 1::2] = torch.cos(position * div_term[:-1])

        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, dim)
        return self.dropout(x + self.pe[:, : x.size(1)])


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class Generator(nn.Module):
    """
    Transformer encoder → normalized latent vector.

    Architecture
    ------------
    Embedding → PositionalEncoding → TransformerEncoder (Pre-LN)
    → masked mean pool → LayerNorm → Projection → LayerNorm → L2 normalize

    Parameters
    ----------
    vocab_size : int
        Vocabulary ceiling for VocabEncoder.
    dim : int
        Model dimension (d_model).
    depth : int
        Number of TransformerEncoderLayer blocks.
    heads : int
        Number of attention heads. Must divide dim evenly.
    ff_mult : int
        Feed-forward inner dimension = dim * ff_mult.
    max_len : int
        Maximum sequence length for positional encoding.
    dropout : float
        Dropout probability used throughout.
    device : str or None
        Force a specific device; defaults to CUDA if available.
    """

    def __init__(
        self,
        vocab_size: int = 8192,
        dim: int = 128,
        depth: int = 4,
        heads: int = 4,
        ff_mult: int = 4,
        max_len: int = 128,
        dropout: float = 0.1,
        device: Optional[str] = None,
    ):
        super().__init__()

        assert dim % heads == 0, f"dim ({dim}) must be divisible by heads ({heads})"

        self.dim = dim
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.vocab = VocabEncoder(vocab_size)

        # Embedding — padding_idx ensures PAD vectors stay zero
        self.embedding = nn.Embedding(
            vocab_size, dim, padding_idx=self.vocab.pad_id
        )

        self.position = PositionalEncoding(dim, max_len, dropout)

        # Pre-LN encoder: norm_first=True applies LayerNorm before
        # attention and feed-forward sublayers (more stable than post-LN).
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=dim,
            nhead=heads,
            dim_feedforward=dim * ff_mult,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=depth,
            enable_nested_tensor=False,
        )

        # Projection head
        self.pre_proj_norm = nn.LayerNorm(dim)
        self.projection = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 2, dim),
        )
        self.post_proj_norm = nn.LayerNorm(dim)

        self._init_weights()
        self.to(self.device)

    # ------------------------------------------------------------------
    # Weight initialization
    # ------------------------------------------------------------------

    def _init_weights(self):
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.02)
        # Zero out the PAD embedding explicitly
        with torch.no_grad():
            self.embedding.weight[self.vocab.pad_id].zero_()

        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    # ------------------------------------------------------------------
    # Padding mask
    # ------------------------------------------------------------------

    def _padding_mask(self, ids: torch.Tensor) -> torch.Tensor:
        """
        Returns BoolTensor of shape (batch, seq) where True = PAD position.
        TransformerEncoder uses True to mean "ignore this position".
        """
        return ids == self.vocab.pad_id

    # ------------------------------------------------------------------
    # Forward (internal, supports gradients)
    # ------------------------------------------------------------------

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """
        ids : LongTensor (batch, seq)
        returns : FloatTensor (batch, dim), L2-normalized
        """
        pad_mask = self._padding_mask(ids)           # (batch, seq)

        emb = self.embedding(ids)                    # (batch, seq, dim)
        emb = self.position(emb)

        latent = self.encoder(emb, src_key_padding_mask=pad_mask)  # (batch, seq, dim)

        # Masked mean pool — exclude PAD from average
        non_pad = (~pad_mask).float().unsqueeze(-1)  # (batch, seq, 1)
        pooled = (latent * non_pad).sum(dim=1) / (non_pad.sum(dim=1) + 1e-8)  # (batch, dim)

        pooled = self.pre_proj_norm(pooled)
        projected = self.projection(pooled)
        projected = self.post_proj_norm(projected)

        return F.normalize(projected, dim=-1)

    # ------------------------------------------------------------------
    # Inference API
    # ------------------------------------------------------------------

    @torch.no_grad()
    def generate(self, tokens: List[str]) -> np.ndarray:
        """
        Encode a single token sequence → normalized numpy vector.

        Parameters
        ----------
        tokens : list of str
            Pre-tokenized input (whitespace-split words, sub-words, etc.)

        Returns
        -------
        np.ndarray, shape (dim,), dtype float32
        """
        ids = self.vocab.encode(tokens)
        x = torch.tensor(ids, dtype=torch.long).unsqueeze(0).to(self.device)
        return self.forward(x).squeeze(0).cpu().numpy()

    @torch.no_grad()
    def encode_batch(self, token_lists: List[List[str]]) -> np.ndarray:
        """
        Encode a batch of token sequences with automatic right-padding.

        Parameters
        ----------
        token_lists : list of list of str

        Returns
        -------
        np.ndarray, shape (batch, dim), dtype float32
        """
        encoded = [self.vocab.encode(tl) for tl in token_lists]
        max_len = max(len(e) for e in encoded)

        padded = [
            e + [self.vocab.pad_id] * (max_len - len(e))
            for e in encoded
        ]
        x = torch.tensor(padded, dtype=torch.long).to(self.device)
        return self.forward(x).cpu().numpy()
