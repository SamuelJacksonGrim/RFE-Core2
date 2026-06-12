"""
agents/generator.py

Symbolic Ecology → Transformer Encoder → Latent Vector
Phase 2: Lifecycle Governance

Integrates the persistent symbolic ecology (agents.symbolic_memory) with a
Transformer encoder. The Generator is not merely an inference engine — it
is the interface between the symbolic metabolism and the embedding space.

Architecture
------------
    raw token
        → CanonicalizationPipeline          (symbolic_memory)
        → SymbolRegistry.register           (lifecycle, binding signals)
        → SymbolTable                       (stable_id — sacred)
        → AddressSpace.resolve_sid          (address — disposable)
        → Embedding[address]
        → PositionalEncoding
        → TransformerEncoder (Pre-LN)
        → masked mean pool
        → LayerNorm → Projection → LayerNorm
        → L2 normalize (optional)

Lifecycle governance
--------------------
    maintenance_step()
        Master maintenance entry point. Runs decay, checks for pending
        compaction, triggers compact_embeddings() if needed, handles
        deferred resize. Call periodically — NOT on every forward pass.

    compact_embeddings(report, optimizer)
        Optimizer-safe embedding weight migration using a CompactionReport
        remap. Remaps weights in-place, updates optimizer state, then
        calls registry.acknowledge_compaction() to apply the address remap.

    scheduled_decay_and_reap()
        Explicit decay trigger. Also called internally by maintenance_step().

    resize_embedding(new_vocab_size, optimizer)
        Grow the embedding matrix. Preserves existing weights and migrates
        optimizer state if provided.

Decay scheduling
----------------
    auto_decay_interval : int or None
        If set, maintenance_step() is called automatically every N calls
        to generate() or encode_batch(). None = manual scheduling only.

    decay_interval : int
        How many maintenance_step() calls between decay_step() invocations.
        Separates the maintenance heartbeat from the metabolism rate.

Deferred resize
---------------
    deferred_resize_threshold : float
        AddressSpace occupancy fraction above which a resize is deferred
        until the next maintenance cycle rather than triggered mid-inference.
        Prevents resize latency spikes during hot inference paths.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from agents.symbolic_memory import (
    AddressSpace,
    ArchiveStore,
    CanonicalizationPipeline,
    CompactionReport,
    ColdStoragePolicy,
    EmbeddingResidencyManager,
    ReaperEngine,
    ReaperConfig,
    CompactionManager,
    SymbolRegistry,
    SymbolTable,
    TokenClass,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Positional Encoding
# =============================================================================

class PositionalEncoding(nn.Module):
    """Standard sinusoidal PE. Requires even model dimension."""

    def __init__(self, dim: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        assert dim % 2 == 0, "PositionalEncoding requires even model dimension."
        self.dropout = nn.Dropout(p=dropout)

        pe       = torch.zeros(max_len, dim)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(
            torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
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
        Initial AddressSpace capacity.
    dim : int
        Model dimension (d_model). Must be even.
    depth : int
        Number of TransformerEncoderLayer blocks.
    heads : int
        Attention heads. Must divide dim.
    ff_mult : int
        Feed-forward inner dim = dim * ff_mult.
    max_len : int
        Maximum sequence length for positional encoding.
    dropout : float
        Dropout used throughout.
    normalize_output : bool
        If True, outputs are L2-normalized.
    allow_vocab_resize : bool
        Allow AddressSpace to grow dynamically.
    deferred_resize_threshold : float
        Occupancy fraction above which resize is deferred to maintenance_step()
        rather than triggered inline during inference.
    device : str or None
        Compute device. Defaults to CUDA if available.
    auto_decay_interval : int or None
        If set, maintenance_step() fires automatically every N calls to
        generate() / encode_batch(). None = manual scheduling only.
    decay_interval : int
        How many maintenance_step() calls trigger one decay_step().
    pipeline : CanonicalizationPipeline or None
        Custom canonicalization pipeline. Defaults to standard pipeline.
    reaper_config : ReaperConfig or None
        Custom reaper thresholds.
    compaction_threshold : float
        Fragmentation ratio above which compaction is scheduled.
    """

    def __init__(
        self,
        vocab_size:                int   = 8_192,
        dim:                       int   = 128,
        depth:                     int   = 4,
        heads:                     int   = 4,
        ff_mult:                   int   = 4,
        max_len:                   int   = 128,
        dropout:                   float = 0.1,
        normalize_output:          bool  = True,
        allow_vocab_resize:        bool  = True,
        deferred_resize_threshold: float = 0.80,
        device:                    Optional[str]                    = None,
        auto_decay_interval:       Optional[int]                    = None,
        decay_interval:            int                              = 10,
        pipeline:                  Optional[CanonicalizationPipeline] = None,
        reaper_config:             Optional[ReaperConfig]             = None,
        compaction_threshold:      float                            = 0.30,
    ):
        super().__init__()

        assert dim % heads == 0, f"dim ({dim}) must be divisible by heads ({heads})"
        assert dim % 2 == 0,     "dim must be even for PositionalEncoding"

        self.dim                       = dim
        self.normalize_output          = normalize_output
        self.deferred_resize_threshold = deferred_resize_threshold
        self.auto_decay_interval       = auto_decay_interval
        self.decay_interval            = decay_interval
        self.device                    = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # ------------------------------------------------------------------
        # Symbolic ecology
        # ------------------------------------------------------------------

        self.address_space = AddressSpace(
            vocab_size   = vocab_size,
            allow_resize = allow_vocab_resize,
        )

        self.registry = SymbolRegistry(
            address_space      = self.address_space,
            pipeline           = pipeline or CanonicalizationPipeline(),
            reaper             = ReaperEngine(reaper_config),
            compaction_manager = CompactionManager(compaction_threshold),
            archive_store      = ArchiveStore(),
            residency_manager  = EmbeddingResidencyManager(),
            symbol_table       = SymbolTable(),
        )

        # ------------------------------------------------------------------
        # Neural architecture
        # ------------------------------------------------------------------

        self.embedding = nn.Embedding(
            self.address_space.vocab_size,
            dim,
            padding_idx = self.address_space.pad_id,
        )

        self.position = PositionalEncoding(dim, max_len=max_len, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model         = dim,
            nhead           = heads,
            dim_feedforward = dim * ff_mult,
            dropout         = dropout,
            batch_first     = True,
            activation      = "gelu",
            norm_first      = True,
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers           = depth,
            enable_nested_tensor = False,
        )

        self.pre_proj_norm  = nn.LayerNorm(dim)
        self.projection     = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 2, dim),
        )
        self.post_proj_norm = nn.LayerNorm(dim)

        # ------------------------------------------------------------------
        # Scheduling state
        # ------------------------------------------------------------------

        self._call_count:        int  = 0
        self._maintenance_count: int  = 0
        self._resize_deferred:   bool = False

        self._init_weights()
        self.to(self.device)

    # ==========================================================================
    # Initialization
    # ==========================================================================

    def _init_weights(self):
        # std raised from 0.02 so token identity survives the sqrt(d_model)-scaled
        # mix with positional encoding (see forward()); lands output pairwise
        # cosine near 0.55 — diverse without tipping into near-orthogonal chaos.
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.035)
        with torch.no_grad():
            self.embedding.weight[self.address_space.pad_id].zero_()

        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    # ==========================================================================
    # Forward
    # ==========================================================================

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """
        ids : LongTensor (batch, seq)
        returns : FloatTensor (batch, dim), optionally L2-normalized
        """
        pad_mask = ids == self.address_space.pad_id

        emb    = self.embedding(ids)
        # Scale embeddings by sqrt(d_model) before adding positional encoding
        # (Attention Is All You Need, sec 3.4). Without this, the fixed sinusoidal
        # positional signal (norm ~sqrt(dim)) dominates the small-init token
        # embeddings by ~36x, collapsing all outputs to one direction.
        emb    = emb * math.sqrt(self.dim)
        emb    = self.position(emb)
        latent = self.encoder(emb, src_key_padding_mask=pad_mask)

        non_pad = (~pad_mask).float().unsqueeze(-1)
        pooled  = (latent * non_pad).sum(dim=1) / (non_pad.sum(dim=1) + 1e-8)

        pooled    = self.pre_proj_norm(pooled)
        projected = self.projection(pooled)
        projected = self.post_proj_norm(projected)

        if self.normalize_output:
            return F.normalize(projected, dim=-1)
        return projected

    # ==========================================================================
    # Inference API
    # ==========================================================================

    @torch.no_grad()
    def generate(
        self,
        tokens:      List[str],
        token_class: Optional[TokenClass] = None,
    ) -> np.ndarray:
        """
        Encode a single token sequence → normalized numpy vector.

        Parameters
        ----------
        tokens : list of str
        token_class : TokenClass or None
            Override pipeline class for all tokens.
            Use for Chorus agent differentiation:
              Dreamer    → TokenClass.EPHEMERAL
              Symbolic   → TokenClass.RELATIONAL
              Entity     → TokenClass.ENTITY
        """
        ids = self._tokens_to_ids(tokens or ["<BOS>"], token_class)
        self._ensure_embedding_capacity()
        self._maybe_auto_maintenance()

        x = torch.tensor(ids, dtype=torch.long).unsqueeze(0).to(self.device)
        return self.forward(x).squeeze(0).cpu().numpy()

    @torch.no_grad()
    def encode_batch(
        self,
        token_lists:  List[List[str]],
        token_class:  Optional[TokenClass] = None,
    ) -> np.ndarray:
        """
        Encode a batch with automatic right-padding.

        Returns np.ndarray, shape (batch, dim), float32.
        """
        if not token_lists:
            raise ValueError("token_lists cannot be empty")

        encoded = [
            self._tokens_to_ids(tl or ["<BOS>"], token_class)
            for tl in token_lists
        ]
        self._ensure_embedding_capacity()
        self._maybe_auto_maintenance()

        max_len = max(len(s) for s in encoded)
        pad_id  = self.address_space.pad_id
        padded  = [s + [pad_id] * (max_len - len(s)) for s in encoded]

        x = torch.tensor(padded, dtype=torch.long).to(self.device)
        return self.forward(x).cpu().numpy()

    # ==========================================================================
    # Lifecycle management
    # ==========================================================================

    def maintenance_step(
        self,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        """
        Master maintenance entry point.

        1. Runs scheduled_decay_and_reap() on decay_interval cadence.
        2. Checks for a pending CompactionReport.
        3. Executes compact_embeddings() if compaction is pending.
        4. Executes any deferred resize.

        Call at:
          - End of training epoch
          - Every N batches
          - rhythm == "stabilize" in autonomous_cycle (natural window)
          - Any explicit maintenance checkpoint
        """
        self._maintenance_count += 1

        if self._maintenance_count % self.decay_interval == 0:
            self.scheduled_decay_and_reap()

        report = self.registry.pending_compaction()
        if report is not None:
            self.compact_embeddings(report, optimizer=optimizer)

        if self._resize_deferred:
            self._execute_deferred_resize(optimizer)

    def scheduled_decay_and_reap(self):
        """
        Invoke registry.decay_step() explicitly.

        Applies contextual decay, runs reaper decisions, reclaims addresses,
        and schedules compaction if fragmentation exceeds threshold.
        Safe to call manually for fine-grained scheduling control.
        """
        self.registry.decay_step()
        s = self.registry.stats()
        logger.debug(
            "decay_step: active=%d warm=%d cold=%d graveyard=%d "
            "frag=%.1f%% compaction_pending=%s",
            s["populations"]["active"],
            s["populations"]["warm"],
            s["populations"]["cold"],
            s["populations"]["graveyard"],
            s["fragmentation"] * 100,
            s["populations"]["compaction_pending"],
        )

    def compact_embeddings(
        self,
        report:    CompactionReport,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        """
        Optimizer-safe embedding weight migration for compaction.

        Protocol
        --------
        1. Allocate new embedding matrix of report.new_vocab_size.
        2. Copy all live weights using report.remap (old_addr → new_addr).
        3. Weights without a remap entry stay in place.
        4. Migrate optimizer momentum/variance buffers.
        5. Call registry.acknowledge_compaction() to apply address remap.
        """
        old_embedding  = self.embedding
        old_vocab_size = old_embedding.num_embeddings
        new_vocab_size = report.new_vocab_size

        logger.info(
            "compact_embeddings: %d → %d vocab, %d remapped, %d reclaimed",
            old_vocab_size, new_vocab_size,
            len(report.remap), report.reclaimed_addresses,
        )

        new_embedding = nn.Embedding(
            new_vocab_size, self.dim,
            padding_idx = self.address_space.pad_id,
        )
        nn.init.normal_(new_embedding.weight, mean=0.0, std=0.02)

        with torch.no_grad():
            for old_addr in range(min(old_vocab_size, new_vocab_size)):
                new_addr = report.remap.get(old_addr, old_addr)
                if new_addr < new_vocab_size:
                    new_embedding.weight[new_addr].copy_(
                        old_embedding.weight[old_addr]
                    )
            new_embedding.weight[self.address_space.pad_id].zero_()

        new_embedding = new_embedding.to(self.device)

        if optimizer is not None:
            self._migrate_optimizer_state(
                optimizer,
                old_param = old_embedding.weight,
                new_param = new_embedding.weight,
                remap     = report.remap,
                new_size  = new_vocab_size,
            )

        self.embedding = new_embedding
        self.registry.acknowledge_compaction(report)

        logger.info(
            "compact_embeddings done: vocab=%d frag=%.1f%%",
            new_vocab_size,
            self.address_space.fragmentation_ratio * 100,
        )

    def resize_embedding(
        self,
        new_vocab_size: int,
        optimizer:      Optional[torch.optim.Optimizer] = None,
    ):
        """
        Grow the embedding matrix to new_vocab_size.
        Preserves all existing weights. No-op if already large enough.
        """
        new_vocab_size = int(new_vocab_size)
        if new_vocab_size <= self.embedding.num_embeddings:
            return

        old_embedding = self.embedding
        old_size      = old_embedding.num_embeddings

        logger.info("resize_embedding: %d → %d", old_size, new_vocab_size)

        new_embedding = nn.Embedding(
            new_vocab_size, self.dim,
            padding_idx = self.address_space.pad_id,
        )
        nn.init.normal_(new_embedding.weight, mean=0.0, std=0.02)

        with torch.no_grad():
            new_embedding.weight[:old_size].copy_(old_embedding.weight)
            new_embedding.weight[self.address_space.pad_id].zero_()

        new_embedding = new_embedding.to(self.device)

        if optimizer is not None:
            self._migrate_optimizer_state(
                optimizer,
                old_param = old_embedding.weight,
                new_param = new_embedding.weight,
                remap     = {},
                new_size  = new_vocab_size,
            )

        self.embedding = new_embedding

    # ==========================================================================
    # Internal utilities
    # ==========================================================================

    def _tokens_to_ids(
        self,
        tokens:      List[str],
        token_class: Optional[TokenClass],
    ) -> List[int]:
        return [
            self.registry.register(t, token_class=token_class).address
            for t in tokens
        ]

    def _ensure_embedding_capacity(self):
        """
        Inline capacity check. Defers resize above occupancy threshold to
        avoid latency spikes during hot inference paths.
        """
        if self.embedding.num_embeddings >= self.address_space.vocab_size:
            return

        if self.address_space.occupancy < self.deferred_resize_threshold:
            self.resize_embedding(self.address_space.vocab_size)
        elif not self._resize_deferred:
            logger.info(
                "Resize deferred (occupancy=%.1f%% >= %.1f%%)",
                self.address_space.occupancy * 100,
                self.deferred_resize_threshold * 100,
            )
            self._resize_deferred = True

    def _execute_deferred_resize(
        self,
        optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        if self.embedding.num_embeddings < self.address_space.vocab_size:
            self.resize_embedding(self.address_space.vocab_size, optimizer)
        self._resize_deferred = False

    def _maybe_auto_maintenance(self):
        if self.auto_decay_interval is None:
            return
        self._call_count += 1
        if self._call_count % self.auto_decay_interval == 0:
            self.maintenance_step()

    def _migrate_optimizer_state(
        self,
        optimizer: torch.optim.Optimizer,
        old_param: torch.nn.Parameter,
        new_param: torch.nn.Parameter,
        remap:     Dict[int, int],
        new_size:  int,
    ):
        """
        Row-remapping optimizer state migration.

        Supports Adam-family (exp_avg, exp_avg_sq, max_exp_avg_sq) and
        SGD-with-momentum. Unknown tensor buffers are remapped by row index.
        Non-tensor entries (step counters, scalars) are copied as-is.
        """
        for group in optimizer.param_groups:
            group["params"] = [
                new_param if (p is old_param) else p
                for p in group["params"]
            ]

        old_state = optimizer.state.pop(old_param, None)
        if old_state is None:
            return

        new_state: Dict = {}

        for key, val in old_state.items():
            if not isinstance(val, torch.Tensor):
                new_state[key] = val
                continue

            if val.shape[0] != old_param.shape[0]:
                # Non-row-indexed tensor (e.g. step tensor) — copy directly
                new_state[key] = val
                continue

            new_buf = torch.zeros(
                new_size, *val.shape[1:],
                dtype=val.dtype, device=val.device,
            )
            for old_addr in range(min(val.shape[0], new_size)):
                new_addr = remap.get(old_addr, old_addr)
                if new_addr < new_size:
                    new_buf[new_addr].copy_(val[old_addr])

            new_state[key] = new_buf

        optimizer.state[new_param] = new_state

    # ==========================================================================
    # External signal relay
    # ==========================================================================

    def signal_attractor(self, tokens: List[str], delta: float = 0.5):
        """Relay attractor signal. Call when tokens become attractor centers."""
        for t in tokens:
            self.registry.update_attractor_strength(t, delta)

    def signal_crystal(self, tokens: List[str], delta: float = 0.3):
        """Relay crystal binding signal. Call when tokens crystallize."""
        for t in tokens:
            self.registry.update_crystal_binding(t, delta)

    def signal_coherence(self, tokens: List[str], coherence: float):
        """Relay field coherence from Watcher."""
        for t in tokens:
            self.registry.update_field_coherence(t, coherence)

    def signal_centrality(self, tokens: List[str], centrality: float):
        """Relay topology centrality from TopologicalLog / SemanticLattice."""
        for t in tokens:
            self.registry.update_centrality(t, centrality)

    # ==========================================================================
    # Status and diagnostics
    # ==========================================================================

    def ecology_stats(self) -> dict:
        return self.registry.stats()

    def status(self) -> dict:
        return {
            "embedding_size":    self.embedding.num_embeddings,
            "dim":               self.dim,
            "device":            str(self.device),
            "call_count":        self._call_count,
            "maintenance_count": self._maintenance_count,
            "resize_deferred":   self._resize_deferred,
            "ecology":           self.ecology_stats(),
        }

    # ==========================================================================
    # Persistence
    # ==========================================================================

    def save_ecology(self, path: str):
        """Persist symbolic ecology. Does NOT save neural weights."""
        self.registry.save(path)
        logger.info("Ecology saved → %s", path)

    def load_ecology(self, path: str):
        """
        Load symbolic ecology from disk.
        Resizes embedding matrix if vocab_size has changed.

        Loads IN PLACE: the existing `self.registry` object is preserved and
        its state replaced, never rebound. Attached subsystems
        (SelfhoodGovernance, ValueEmergenceEngine) capture the registry
        reference at construction; rebinding would orphan them onto a stale
        registry — governance lookups go silently stale and value emergence
        dies entirely (every stable_id lookup misses). Verified 2026-06-12.
        """
        loaded = SymbolRegistry.load(path)
        self.registry.__dict__.clear()
        self.registry.__dict__.update(loaded.__dict__)
        self.address_space = self.registry.address_space

        new_vocab = self.address_space.vocab_size
        if self.embedding.num_embeddings != new_vocab:
            self.resize_embedding(new_vocab)

        logger.info("Ecology loaded ← %s", path)

    def save_checkpoint(self, weights_path: str, ecology_path: str):
        """Save neural weights + symbolic ecology."""
        torch.save(self.state_dict(), weights_path)
        self.save_ecology(ecology_path)

    def load_checkpoint(self, weights_path: str, ecology_path: str):
        """Load neural weights + symbolic ecology."""
        self.load_ecology(ecology_path)
        self.load_state_dict(
            torch.load(weights_path, map_location=self.device)
        )
