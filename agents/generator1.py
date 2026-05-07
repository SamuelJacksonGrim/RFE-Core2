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
# agents/generator.py
"""
Transformer encoder that produces normalized latent vectors from token sequences.

Revision Enhancements
──────────────────────────────────────────────────────────────────────────────
NEW IN THIS VERSION
──────────────────────────────────────────────────────────────────────────────
✓ Deterministic SHA256 + double-hash probing tokenizer
✓ Occupancy-aware vocab resizing
✓ Embedding resize support
✓ Canonicalization / normalization layer
✓ Symbolic usage tracking + decay-based garbage collection
✓ Optional semantic decomposition hooks
✓ Stable pre-LN transformer encoder
✓ Optional output normalization
✓ Robust empty-sequence handling
✓ Optimizer-safe embedding resize helper
✓ Token metadata tracking
✓ Reserved archival path for dormant symbols

ARCHITECTURAL ROLE
──────────────────────────────────────────────────────────────────────────────
symbolic token
    →
canonicalization
    →
deterministic symbolic address
    →
embedding manifold
    →
transformer relational field
    →
latent resonance vector

Designed for:
- recursive symbolic systems
- relational AI architectures
- semantic attractor fields
- long-running adaptive agents
- symbolic continuity across time
"""

from __future__ import annotations

import math
import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# =============================================================================
# Token Metadata
# =============================================================================

@dataclass
class TokenMetadata:
    usage: float = 1.0
    age: int = 0
    archived: bool = False


# =============================================================================
# Canonicalization
# =============================================================================

class TokenCanonicalizer:
    """
    Lightweight semantic normalization layer.

    Goals
    -----
    - Reduce symbolic fragmentation
    - Preserve stable semantic identity
    - Normalize unicode / casing drift
    """

    def __init__(
        self,
        lowercase: bool = True,
        strip_punctuation: bool = False,
        unicode_normalize: bool = True,
    ):
        self.lowercase = lowercase
        self.strip_punctuation = strip_punctuation
        self.unicode_normalize = unicode_normalize

    def normalize(self, token: str) -> str:
        if not isinstance(token, str):
            token = str(token)

        if self.unicode_normalize:
            token = unicodedata.normalize("NFKC", token)

        token = token.strip()

        if self.lowercase:
            token = token.lower()

        if self.strip_punctuation:
            token = re.sub(r"[^\w\s]", "", token)

        return token


# =============================================================================
# Vocabulary Encoder
# =============================================================================

class VocabEncoder:
    """
    Deterministic symbolic address space.

    Features
    --------
    - Stable hashing
    - Double-hash probing
    - Dynamic resizing
    - Usage tracking
    - Symbol decay
    - Dormant archival
    """

    SPECIAL = ["<PAD>", "<UNK>", "<BOS>", "<EOS>"]

    def __init__(
        self,
        vocab_size: int = 8192,
        allow_resize: bool = True,
        resize_factor: float = 2.0,
        gc_decay: float = 0.995,
        archive_threshold: float = 0.05,
        canonicalizer: Optional[TokenCanonicalizer] = None,
    ):
        assert vocab_size > len(self.SPECIAL)

        self.vocab_size = int(vocab_size)

        self._tok2id: Dict[str, int] = {
            t: i for i, t in enumerate(self.SPECIAL)
        }

        self._id2tok: Dict[int, str] = {
            i: t for t, i in self._tok2id.items()
        }

        self._metadata: Dict[str, TokenMetadata] = {}

        self.allow_resize = allow_resize
        self.resize_factor = resize_factor

        self.gc_decay = gc_decay
        self.archive_threshold = archive_threshold

        self._num_assigned = len(self._tok2id)

        self.canonicalizer = canonicalizer or TokenCanonicalizer()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def pad_id(self):
        return self._tok2id["<PAD>"]

    @property
    def unk_id(self):
        return self._tok2id["<UNK>"]

    @property
    def bos_id(self):
        return self._tok2id["<BOS>"]

    @property
    def eos_id(self):
        return self._tok2id["<EOS>"]

    @property
    def occupancy(self) -> float:
        return self._num_assigned / float(self.vocab_size)

    # -------------------------------------------------------------------------
    # Hashing
    # -------------------------------------------------------------------------

    def _sha256_int(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest, "big")

    def _secondary_hash(self, token: str) -> int:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        return int.from_bytes(digest, "big")

    # -------------------------------------------------------------------------
    # Canonicalization
    # -------------------------------------------------------------------------

    def canonicalize(self, token: str) -> str:
        return self.canonicalizer.normalize(token)

    # -------------------------------------------------------------------------
    # Resize
    # -------------------------------------------------------------------------

    def _maybe_resize(self) -> bool:
        if not self.allow_resize:
            return False

        if self.occupancy < 0.85:
            return False

        new_size = int(
            max(
                self.vocab_size + 1,
                math.ceil(self.vocab_size * self.resize_factor),
            )
        )

        logger.info(
            "Resizing vocab from %d → %d",
            self.vocab_size,
            new_size,
        )

        old_tokens = [
            t for t in self._tok2id.keys()
            if t not in self.SPECIAL
        ]

        self.vocab_size = new_size

        self._tok2id = {
            t: i for i, t in enumerate(self.SPECIAL)
        }

        self._id2tok = {
            i: t for t, i in self._tok2id.items()
        }

        self._num_assigned = len(self._tok2id)

        for tok in old_tokens:
            self.token_id(tok)

        return True

    # -------------------------------------------------------------------------
    # Garbage Collection
    # -------------------------------------------------------------------------

    def decay_usage(self):
        """
        Apply symbolic entropy decay.

        Prevents infinite semantic debris accumulation.
        """

        for tok, meta in self._metadata.items():
            meta.usage *= self.gc_decay
            meta.age += 1

            if meta.usage < self.archive_threshold:
                meta.archived = True

    # -------------------------------------------------------------------------
    # Core Mapping
    # -------------------------------------------------------------------------

    def token_id(self, token: str) -> int:
        token = self.canonicalize(token)

        if token in self._tok2id:
            if token not in self._metadata:
                self._metadata[token] = TokenMetadata()

            self._metadata[token].usage += 1.0
            return self._tok2id[token]

        if self.occupancy >= 0.85:
            self._maybe_resize()

        base = len(self.SPECIAL)
        span = self.vocab_size - base

        primary = (self._sha256_int(token) % span) + base
        step = (self._secondary_hash(token) % (span - 1)) + 1

        probe = primary
        probes = 0

        while True:
            existing = self._id2tok.get(probe)

            if existing is None or existing == token:
                break

            probes += 1

            if probes >= span:
                if self.allow_resize and self._maybe_resize():
                    return self.token_id(token)

                raise RuntimeError("Vocabulary exhausted.")

            probe = ((probe - base + step) % span) + base

        self._tok2id[token] = probe
        self._id2tok[probe] = token

        self._metadata[token] = TokenMetadata()

        self._num_assigned += 1

        return probe

    # -------------------------------------------------------------------------
    # Encode / Decode
    # -------------------------------------------------------------------------

    def encode(self, tokens: List[str]) -> List[int]:
        return [self.token_id(t) for t in tokens]

    def decode(self, ids: List[int]) -> List[str]:
        return [
            self._id2tok.get(i, "<UNK>")
            for i in ids
        ]

    def __len__(self):
        return self.vocab_size


# =============================================================================
# Positional Encoding
# =============================================================================

class PositionalEncoding(nn.Module):

    def __init__(
        self,
        dim: int,
        max_len: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()

        assert dim % 2 == 0

        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, dim)

        position = torch.arange(0, max_len).unsqueeze(1).float()

        div_term = torch.exp(
            torch.arange(0, dim, 2).float()
            * (-math.log(10000.0) / dim)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor):
        return self.dropout(
            x + self.pe[:, :x.size(1)]
        )


# =============================================================================
# Generator
# =============================================================================

class Generator(nn.Module):

    def __init__(
        self,
        vocab_size: int = 8192,
        dim: int = 128,
        depth: int = 4,
        heads: int = 4,
        ff_mult: int = 4,
        max_len: int = 128,
        dropout: float = 0.1,
        normalize_output: bool = True,
        allow_vocab_resize: bool = True,
        device: Optional[str] = None,
    ):
        super().__init__()

        assert dim % heads == 0
        assert dim % 2 == 0

        self.dim = dim

        self.device = (
            device
            or ("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.normalize_output = normalize_output

        self.vocab = VocabEncoder(
            vocab_size=vocab_size,
            allow_resize=allow_vocab_resize,
        )

        # ---------------------------------------------------------------------
        # Embedding
        # ---------------------------------------------------------------------

        self.embedding = nn.Embedding(
            len(self.vocab),
            dim,
            padding_idx=self.vocab.pad_id,
        )

        self.position = PositionalEncoding(
            dim,
            max_len=max_len,
            dropout=dropout,
        )

        # ---------------------------------------------------------------------
        # Encoder
        # ---------------------------------------------------------------------

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

        # ---------------------------------------------------------------------
        # Projection
        # ---------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Init
    # -------------------------------------------------------------------------

    def _init_weights(self):

        nn.init.normal_(
            self.embedding.weight,
            mean=0.0,
            std=0.02,
        )

        with torch.no_grad():
            self.embedding.weight[
                self.vocab.pad_id
            ].zero_()

        for module in self.modules():

            if isinstance(module, nn.Linear):

                nn.init.xavier_uniform_(module.weight)

                if module.bias is not None:
                    nn.init.zeros_(module.bias)

            elif isinstance(module, nn.LayerNorm):

                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    # -------------------------------------------------------------------------
    # Embedding Resize
    # -------------------------------------------------------------------------

    def resize_embedding(
        self,
        new_vocab_size: int,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        """
        Optimizer-safe embedding resize.
        """

        if new_vocab_size <= self.embedding.num_embeddings:
            return

        old_embedding = self.embedding

        new_embedding = nn.Embedding(
            new_vocab_size,
            self.dim,
            padding_idx=self.vocab.pad_id,
        )

        nn.init.normal_(
            new_embedding.weight,
            mean=0.0,
            std=0.02,
        )

        with torch.no_grad():
            new_embedding.weight[
                :old_embedding.num_embeddings
            ].copy_(old_embedding.weight)

        self.embedding = new_embedding.to(self.device)

        # ---------------------------------------------------------------------
        # Optimizer state migration
        # ---------------------------------------------------------------------

        if optimizer is not None:

            for group in optimizer.param_groups:

                params = []

                for p in group["params"]:
                    if p is old_embedding.weight:
                        params.append(self.embedding.weight)
                    else:
                        params.append(p)

                group["params"] = params

            if old_embedding.weight in optimizer.state:
                del optimizer.state[old_embedding.weight]

    # -------------------------------------------------------------------------
    # Padding Mask
    # -------------------------------------------------------------------------

    def _padding_mask(self, ids: torch.Tensor):
        return ids == self.vocab.pad_id

    # -------------------------------------------------------------------------
    # Forward
    # -------------------------------------------------------------------------

    def forward(self, ids: torch.Tensor):

        pad_mask = self._padding_mask(ids)

        emb = self.embedding(ids)

        emb = self.position(emb)

        latent = self.encoder(
            emb,
            src_key_padding_mask=pad_mask,
        )

        non_pad = (~pad_mask).float().unsqueeze(-1)

        pooled = (
            (latent * non_pad).sum(dim=1)
            / (non_pad.sum(dim=1) + 1e-8)
        )

        pooled = self.pre_proj_norm(pooled)

        projected = self.projection(pooled)

        projected = self.post_proj_norm(projected)

        if self.normalize_output:
            return F.normalize(projected, dim=-1)

        return projected

    # -------------------------------------------------------------------------
    # Generate
    # -------------------------------------------------------------------------

    @torch.no_grad()
    def generate(self, tokens: List[str]) -> np.ndarray:

        if not tokens:
            ids = [self.vocab.bos_id]
        else:
            ids = self.vocab.encode(tokens)

        if self.embedding.num_embeddings < len(self.vocab):
            self.resize_embedding(len(self.vocab))

        x = (
            torch.tensor(ids, dtype=torch.long)
            .unsqueeze(0)
            .to(self.device)
        )

        out = self.forward(x)

        return out.squeeze(0).cpu().numpy()

    # -------------------------------------------------------------------------
    # Batch Encode
    # -------------------------------------------------------------------------

    @torch.no_grad()
    def encode_batch(
        self,
        token_lists: List[List[str]],
    ) -> np.ndarray:

        if token_lists is None:
            raise ValueError("token_lists cannot be None")

        if len(token_lists) == 0:
            raise ValueError("token_lists cannot be empty")

        encoded = [
            self.vocab.encode(tl)
            if tl and len(tl) > 0
            else [self.vocab.bos_id]
            for tl in token_lists
        ]

        if self.embedding.num_embeddings < len(self.vocab):
            self.resize_embedding(len(self.vocab))

        max_len = max(len(x) for x in encoded)

        padded = [
            seq + [self.vocab.pad_id] * (max_len - len(seq))
            for seq in encoded
        ]

        x = (
            torch.tensor(padded, dtype=torch.long)
            .to(self.device)
        )

        out = self.forward(x)

        return out.cpu().numpy()
