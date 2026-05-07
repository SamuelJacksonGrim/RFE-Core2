# agents/generator.py
"""
Symbolic Ecology → Transformer Encoder → Latent Vector

Integrates the persistent symbolic ecology from agents.symbolic_memory
with a Transformer-based encoder:

    raw token
        → Canonicalizer
        → SymbolRegistry.register (lifecycle, metadata, residency)
        → SymbolTable (stable_id)
        → AddressSpace.resolve_sid (stable_id → address)
        → Embedding
        → PositionalEncoding
        → TransformerEncoder (Pre-LN)
        → masked mean pool
        → LayerNorm → Projection → LayerNorm
        → (optional) L2 normalize

NOTE ON DECAY:
    The symbolic ecology supports automatic decay of symbol usage, archival,
    and graveyard management. However, decay is NOT invoked automatically
    during forward passes — it must be triggered explicitly by the training
    loop or an external scheduler. Call generator.registry.decay_step()
    periodically (e.g., every N batches or epochs) to activate the
    metabolic lifecycle.
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.symbolic_memory import (
    AddressSpace,
    SymbolRegistry,
    Canonicalizer,
    CanonicalizationMode,
    TokenClass,
    DecayEngine,
    ArchiveStore,
    EmbeddingResidencyManager,
    SymbolTable,
)


# =============================================================================
# Positional Encoding
# =============================================================================

class PositionalEncoding(nn.Module):
    """Standard sinusoidal PE with dropout. Requires even dimension."""

    def __init__(self, dim: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        assert dim % 2 == 0, "PositionalEncoding requires even model dimension"

        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, dim)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(
            torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, dim)
        return self.dropout(x + self.pe[:, : x.size(1)])


# =============================================================================
# Generator
# =============================================================================

class Generator(nn.Module):
    """
    Transformer encoder over a persistent symbolic ecology.

    Parameters
    ----------
    vocab_size : int
        Initial capacity for AddressSpace.
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
    normalize_output : bool
        If True, output vectors are L2-normalized.
    allow_vocab_resize : bool
        Allow AddressSpace to grow and embedding to be resized.
    device : str or None
        Device string; defaults to CUDA if available.
    canonicalization_mode : CanonicalizationMode or None
        Optional canonicalization mode for the Canonicalizer.
    auto_decay_interval : int or None
        If set, automatically invoke registry.decay_step() every N calls to
        generate() or encode_batch(). None means no automatic decay.
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
        normalize_output: bool = True,
        allow_vocab_resize: bool = True,
        device: Optional[str] = None,
        canonicalization_mode: Optional[CanonicalizationMode] = None,
        auto_decay_interval: Optional[int] = None,
    ):
        super().__init__()

        assert dim % heads == 0, f"dim ({dim}) must be divisible by heads ({heads})"
        assert dim % 2 == 0, "Model dimension must be even for positional encoding"

        self.dim = dim
        self.normalize_output = bool(normalize_output)
        self.auto_decay_interval = auto_decay_interval
        self._call_count = 0

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # ---------------------------------------------------------------------
        # Symbolic ecology
        # ---------------------------------------------------------------------

        self.address_space = AddressSpace(
            vocab_size=vocab_size,
            allow_resize=allow_vocab_resize,
        )

        canonicalizer = (
            Canonicalizer(mode=canonicalization_mode)
            if canonicalization_mode is not None
            else Canonicalizer()
        )

        symbol_table = SymbolTable()

        self.registry = SymbolRegistry(
            address_space=self.address_space,
            canonicalizer=canonicalizer,
            decay_engine=DecayEngine(),
            archive_store=ArchiveStore(),
            residency_manager=EmbeddingResidencyManager(),
            symbol_table=symbol_table,
        )

        # SPECIAL ids
        self.pad_id = self.address_space.pad_id
        self.unk_id = self.address_space.unk_id
        self.bos_id = self.address_space.bos_id
        self.eos_id = self.address_space.eos_id

        # ---------------------------------------------------------------------
        # Embedding
        # ---------------------------------------------------------------------

        self.embedding = nn.Embedding(
            self.address_space.vocab_size,
            dim,
            padding_idx=self.pad_id,
        )

        self.position = PositionalEncoding(
            dim,
            max_len=max_len,
            dropout=dropout,
        )

        # ---------------------------------------------------------------------
        # Encoder (Pre-LN)
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
        # Projection head
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
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.02)

        with torch.no_grad():
            self.embedding.weight[self.pad_id].zero_()

        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    # -------------------------------------------------------------------------
    # Optimizer-safe embedding resize
    # -------------------------------------------------------------------------

    def resize_embedding(
        self,
        new_vocab_size: int,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        """
        Expand the embedding matrix to accommodate a larger AddressSpace.

        Preserves existing weights and migrates optimizer state if provided.
        """
        new_vocab_size = int(new_vocab_size)

        if new_vocab_size <= self.embedding.num_embeddings:
            return

        old_embedding = self.embedding

        new_embedding = nn.Embedding(
            new_vocab_size,
            self.dim,
            padding_idx=self.pad_id,
        )

        nn.init.normal_(new_embedding.weight, mean=0.0, std=0.02)

        with torch.no_grad():
            new_embedding.weight[: old_embedding.num_embeddings].copy_(
                old_embedding.weight
            )
            new_embedding.weight[self.pad_id].zero_()

        self.embedding = new_embedding.to(self.device)

        if optimizer is not None:
            # Replace parameter reference in optimizer param_groups
            for group in optimizer.param_groups:
                params = []
                for p in group["params"]:
                    if p is old_embedding.weight:
                        params.append(self.embedding.weight)
                    else:
                        params.append(p)
                group["params"] = params

            # Transfer optimizer state from old to new embedding weight
            if old_embedding.weight in optimizer.state:
                optimizer.state[self.embedding.weight] = optimizer.state.pop(
                    old_embedding.weight
                )

    # -------------------------------------------------------------------------
    # Padding mask
    # -------------------------------------------------------------------------

    def _padding_mask(self, ids: torch.Tensor) -> torch.Tensor:
        """
        Returns BoolTensor of shape (batch, seq) where True = PAD position.
        TransformerEncoder uses True to mean "ignore this position".
        """
        return ids == self.pad_id

    # -------------------------------------------------------------------------
    # Tokens → ids via SymbolRegistry + AddressSpace
    # -------------------------------------------------------------------------

    def _tokens_to_ids(
        self,
        tokens: List[str],
        token_class: TokenClass = TokenClass.LANGUAGE,
    ) -> List[int]:
        """
        Map raw tokens into stable addresses via the symbolic ecology.

        - Canonicalization via SymbolRegistry's Canonicalizer
        - Lifecycle + metadata via SymbolRegistry.register
        - stable_id via SymbolTable
        - address via AddressSpace.resolve_sid

        NOTE: registry.register() already resolves and caches the address in
        state.address, so we use that directly rather than re-resolving.
        """
        ids: List[int] = []
        for t in tokens:
            state = self.registry.register(t, token_class=token_class)
            ids.append(state.address)
        return ids

    # -------------------------------------------------------------------------
    # Automatic decay trigger
    # -------------------------------------------------------------------------

    def _maybe_decay(self):
        """
        Invoke decay_step() if auto_decay_interval is configured.
        Called internally by generate() and encode_batch().
        """
        if self.auto_decay_interval is None:
            return
        self._call_count += 1
        if self._call_count % self.auto_decay_interval == 0:
            self.registry.decay_step()

    # -------------------------------------------------------------------------
    # Forward
    # -------------------------------------------------------------------------

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """
        ids : LongTensor (batch, seq)
        returns : FloatTensor (batch, dim)
            If normalize_output is True, outputs are L2-normalized.
        """
        pad_mask = self._padding_mask(ids)           # (batch, seq)

        emb = self.embedding(ids)                    # (batch, seq, dim)
        emb = self.position(emb)

        latent = self.encoder(
            emb,
            src_key_padding_mask=pad_mask,
        )  # (batch, seq, dim)

        # Masked mean pool — exclude PAD from average
        non_pad = (~pad_mask).float().unsqueeze(-1)  # (batch, seq, 1)
        pooled = (latent * non_pad).sum(dim=1) / (non_pad.sum(dim=1) + 1e-8)

        pooled = self.pre_proj_norm(pooled)
        projected = self.projection(pooled)
        projected = self.post_proj_norm(projected)

        if self.normalize_output:
            return F.normalize(projected, dim=-1)
        else:
            return projected

    # -------------------------------------------------------------------------
    # Inference API
    # -------------------------------------------------------------------------

    @torch.no_grad()
    def generate(
        self,
        tokens: List[str],
        token_class: TokenClass = TokenClass.LANGUAGE,
    ) -> np.ndarray:
        """
        Encode a single token sequence → numpy vector.

        Empty sequences are replaced with a single BOS token.
        """
        if not tokens:
            ids = [self.bos_id]
        else:
            ids = self._tokens_to_ids(tokens, token_class=token_class)

        # Ensure embedding matrix is large enough if AddressSpace grew
        if self.embedding.num_embeddings < self.address_space.vocab_size:
            self.resize_embedding(self.address_space.vocab_size)

        self._maybe_decay()

        x = torch.tensor(ids, dtype=torch.long).unsqueeze(0).to(self.device)
        out = self.forward(x).squeeze(0).cpu().numpy()
        return out

    @torch.no_grad()
    def encode_batch(
        self,
        token_lists: List[List[str]],
        token_class: TokenClass = TokenClass.LANGUAGE,
    ) -> np.ndarray:
        """
        Encode a batch of token sequences with automatic right-padding.

        Empty sequences are replaced with a single BOS token.
        """
        if token_lists is None:
            raise ValueError("token_lists cannot be None")

        if len(token_lists) == 0:
            raise ValueError("token_lists cannot be empty")

        encoded: List[List[int]] = []
        for tl in token_lists:
            if not tl:
                encoded.append([self.bos_id])
            else:
                encoded.append(self._tokens_to_ids(tl, token_class=token_class))

        # Ensure embedding matrix is large enough if AddressSpace grew
        if self.embedding.num_embeddings < self.address_space.vocab_size:
            self.resize_embedding(self.address_space.vocab_size)

        self._maybe_decay()

        max_len = max(len(seq) for seq in encoded)

        padded = [
            seq + [self.pad_id] * (max_len - len(seq))
            for seq in encoded
        ]

        x = torch.tensor(padded, dtype=torch.long).to(self.device)
        out = self.forward(x).cpu().numpy()
        return out

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save_ecology(self, path: str):
        """
        Save the symbolic ecology (registry state) to disk.
        Does NOT save the neural weights — use torch.save() for those.
        """
        self.registry.save(path)

    def load_ecology(self, path: str):
        """
        Load the symbolic ecology (registry state) from disk.
        Replaces the current registry. Ensure the neural weights are compatible.
        """
        self.registry = SymbolRegistry.load(path)
        # Re-sync special token IDs
        self.pad_id = self.registry.address_space.pad_id
        self.unk_id = self.registry.address_space.unk_id
        self.bos_id = self.registry.address_space.bos_id
        self.eos_id = self.registry.address_space.eos_id
