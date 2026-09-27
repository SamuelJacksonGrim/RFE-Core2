"""Causal RoPE sequence encoder. One unit-norm vector. Not a mean pool.

Mean-pool writes z = mean(v_1, ..., v_T). An untrained token is isotropic
noise inside that average, and no later ratio can take it back out. This
module replaces that reduction:

    H = CausalRoPE(v_1, ..., v_T, readout)
    z = L2(H_readout)

RoPE is applied to queries and keys only, so relative position lives in the
attention logits and is not a vector that a pool can cancel. The mask is
causal, so each state is the endpoint of the prefix that produced it. The
summary is a learned readout token appended after the real tokens (pads stay
to its right and are masked). It is not the embedding of whichever content
word happens to sort last, and it is not the embedding mean. Mixing that
mean back in would put the noise into z on purpose, so there is no
embedding-mean residual.

The readout alone walks into the same low-rank basin as an unanchored
stack (participation ~5 by epoch 15, train top-1 stuck near the mode rate).
The anchor that does not put the variable slot back into the centroid is
the mean of every real token except the last. On a role-ordered stem that
is the kernel. A one-token row keeps its only token. The stack reads a
detached copy and is added orthogonal to that anchor, same protection as
the S2 residual, different vector. A full-bag mean would be the dilution
this experiment is here to get out of.

Output is one float vector of the training width, L2 norm 1. That is the
field shape. This is not a Generator, and Generator.forward is not edited.

Recurring-stem rows are stored as sorted bags, which gives position no role.
`role_order_row` presents them as [kernel_0, kernel_1, vary]. The set of
tokens is unchanged, so a mean pool of the same row is the S3 control.
Broad completion rows and live mouth lines keep the order they already have.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

PAD = "<PAD>"
KIND = "phase_c_rope_causal"


def role_order_row(row: dict) -> dict:
    """Stable slot order for a recurring stem. Other rows keep their order.

    Position 0 and 1 are the kernel. Position 2 is the partner. Sorted order
    would move the partner whenever its spelling sorts differently, so the
    slot would not be a position.
    """
    item = dict(row)
    kernel = item.get("kernel")
    vary = item.get("vary")
    if item.get("source") == "recur" and isinstance(kernel, list) and vary:
        ordered = [str(tok) for tok in kernel] + [str(vary)]
        if sorted(ordered) != sorted(item["context"]) or len(ordered) != len(set(ordered)):
            raise ValueError("role order does not preserve the stem bag")
        item["context"] = ordered
        item["presentation"] = "role"
    else:
        item["presentation"] = "authored"
    return item


def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    half = x.shape[-1] // 2
    first, second = x[..., :half], x[..., half:]
    return torch.cat((-second, first), dim=-1)


def _rope_cache(max_pos: int, head_dim: int, base: float = 10000.0):
    inv = 1.0 / (base ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
    freqs = torch.outer(torch.arange(max_pos, dtype=torch.float32), inv)
    cos = torch.cat((freqs.cos(), freqs.cos()), dim=-1)
    sin = torch.cat((freqs.sin(), freqs.sin()), dim=-1)
    return cos, sin


def _apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    # x is (B, H, T, Dh). cos/sin are (B, T, Dh).
    cos = cos[:, None, :, :]
    sin = sin[:, None, :, :]
    return x * cos + _rotate_half(x) * sin


class _Pad:
    def __init__(self, pad_id: int):
        self.pad_id = pad_id


class _Block(nn.Module):
    def __init__(self, dim: int, heads: int, ff_mult: int, dropout: float):
        super().__init__()
        if dim % heads != 0:
            raise ValueError(f"dim {dim} is not divisible by heads {heads}")
        self.heads = heads
        self.head_dim = dim // heads
        if self.head_dim % 2 != 0:
            raise ValueError(f"head dim {self.head_dim} must be even for RoPE")
        self.ln1 = nn.LayerNorm(dim)
        self.ln2 = nn.LayerNorm(dim)
        self.qkv = nn.Linear(dim, 3 * dim)
        self.proj = nn.Linear(dim, dim)
        self.ff = nn.Sequential(
            nn.Linear(dim, ff_mult * dim),
            nn.GELU(),
            nn.Linear(ff_mult * dim, dim),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, allowed: torch.Tensor):
        batch, length, dim = x.shape
        h = self.ln1(x)
        qkv = self.qkv(h).view(batch, length, 3, self.heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        q = _apply_rope(q, cos, sin)
        k = _apply_rope(k, cos, sin)
        scores = torch.matmul(q, k.transpose(-2, -1)) * (self.head_dim ** -0.5)
        scores = scores.masked_fill(~allowed[:, None, :, :], torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores.float(), dim=-1).to(dtype=scores.dtype)
        weights = self.drop(weights)
        mixed = torch.matmul(weights, v)
        mixed = mixed.transpose(1, 2).contiguous().view(batch, length, dim)
        x = x + self.drop(self.proj(mixed))
        x = x + self.drop(self.ff(self.ln2(x)))
        return x


class SequenceEncoder(nn.Module):
    def __init__(
        self,
        vocab: Sequence[str],
        dim: int = 128,
        depth: int = 4,
        heads: int = 4,
        ff_mult: int = 4,
        dropout: float = 0.1,
        max_content: int = 32,
        device: Optional[str] = None,
    ):
        super().__init__()
        if dim % heads != 0 or dim % 2 != 0:
            raise ValueError(f"dim {dim} must be even and divisible by heads {heads}")
        if depth < 1:
            raise ValueError("depth must be at least 1")
        if max_content < 1:
            raise ValueError("max_content must leave room for one token")
        surface = [str(tok) for tok in vocab]
        if PAD in surface:
            raise ValueError("surface vocab collides with <PAD>")
        if len(surface) != len(set(surface)):
            raise ValueError("duplicate surface token")

        self.dim = dim
        self.depth = depth
        self.heads = heads
        self.ff_mult = ff_mult
        self.dropout_p = float(dropout)
        self.max_content = max_content
        self.pad_id = 0
        self.tokens: List[str] = [PAD] + surface
        self.index: Dict[str, int] = {tok: i for i, tok in enumerate(self.tokens)}
        self.address_space = _Pad(self.pad_id)
        # On: field vector is the prefix anchor plus the orthogonal readout.
        # Off: the readout alone, so a measurement can see a collapsed stack
        # instead of mistaking the anchor for one.
        self.embedding_residual = True

        self.embedding = nn.Embedding(len(self.tokens), dim, padding_idx=self.pad_id)
        self.readout = nn.Parameter(torch.empty(dim))
        self.layers = nn.ModuleList(
            [_Block(dim, heads, ff_mult, dropout) for _ in range(depth)]
        )
        # Positions 0..max_content. Content uses 0..length-1. The readout
        # uses `length`, which is max_content when the row is full.
        cos, sin = _rope_cache(max_content + 1, dim // heads)
        self.register_buffer("rope_cos", cos, persistent=True)
        self.register_buffer("rope_sin", sin, persistent=True)
        self._init_weights()
        chosen = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.to(chosen)

    def _init_weights(self) -> None:
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.035)
        nn.init.normal_(self.readout, mean=0.0, std=0.035)
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

    @property
    def device(self):
        return self.embedding.weight.device

    def _tokens_to_ids(self, tokens: Sequence[str], token_class=None) -> List[int]:
        del token_class
        if not tokens:
            raise ValueError("empty token list")
        try:
            return [self.index[tok] for tok in tokens]
        except KeyError as exc:
            raise KeyError(f"token {exc.args[0]!r} is not in the sequence encoder vocab") from exc

    def _ensure_embedding_capacity(self) -> None:
        # Vocab is fixed at init. A new token is a builder bug, not a resize.
        return None

    def token_embedding_mean(self, ids: torch.Tensor) -> torch.Tensor:
        """Masked mean of scaled token embeddings. Diagnostic only.

        Forward does not add this vector. It is the S3 centroid, so a caller
        can see how far the readout moved off it.
        """
        valid = (ids != self.pad_id).unsqueeze(-1).to(dtype=self.embedding.weight.dtype)
        emb = self.embedding(ids) * math.sqrt(self.dim)
        denom = valid.sum(dim=1).clamp(min=1.0)
        return (emb * valid).sum(dim=1) / denom

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        if ids.ndim != 2:
            raise ValueError(f"ids must be (B, T), got {tuple(ids.shape)}")
        if ids.shape[1] > self.max_content:
            raise ValueError(
                f"sequence length {ids.shape[1]} > max_content {self.max_content}"
            )
        if ids.shape[1] == 0:
            raise ValueError("empty sequence")
        valid = ids != self.pad_id
        lengths = valid.sum(dim=1)
        if bool((lengths < 1).any()):
            raise ValueError("sequence has no real tokens")
        if int(lengths.max()) > self.max_content:
            raise ValueError("content length exceeds max_content")

        batch, length = ids.shape
        emb = self.embedding(ids) * math.sqrt(self.dim)
        # The stack must not drag the table into its basin. The anchor below
        # is the path that trains the embeddings.
        stack_emb = emb.detach() if self.embedding_residual else emb
        read = self.readout.view(1, 1, -1).expand(batch, 1, -1) * math.sqrt(self.dim)
        x = torch.cat((stack_emb, read), dim=1)
        read_valid = torch.ones(batch, 1, dtype=torch.bool, device=ids.device)
        full_valid = torch.cat((valid, read_valid), dim=1)

        columns = torch.arange(length, device=ids.device).unsqueeze(0).expand(batch, length)
        positions = torch.cat((columns, lengths.unsqueeze(1)), dim=1)
        cos = self.rope_cos[positions]
        sin = self.rope_sin[positions]

        width = length + 1
        index = torch.arange(width, device=ids.device)
        causal = index.view(1, width, 1) >= index.view(1, 1, width)
        allowed = causal & full_valid.view(batch, 1, width)
        # A pad query is never read. Give it its own key so softmax stays finite.
        allowed = allowed | torch.eye(width, dtype=torch.bool, device=ids.device).unsqueeze(0)

        for layer in self.layers:
            x = layer(x, cos, sin, allowed)
        readout = x[:, -1]
        if not self.embedding_residual:
            return F.normalize(readout, dim=-1)

        columns = torch.arange(length, device=ids.device).unsqueeze(0)
        last = (lengths - 1).unsqueeze(1)
        prefix = valid & (columns != last)
        single = (lengths == 1).unsqueeze(1) & valid
        prefix = prefix | single
        denom = prefix.unsqueeze(-1).to(dtype=emb.dtype).sum(dim=1).clamp(min=1.0)
        anchor = (emb * prefix.unsqueeze(-1).to(dtype=emb.dtype)).sum(dim=1) / denom
        u = F.normalize(anchor, dim=-1)
        s = F.normalize(readout, dim=-1)
        s_orth = s - (s * u).sum(dim=-1, keepdim=True) * u
        return F.normalize(u + s_orth, dim=-1)

    @torch.no_grad()
    def encode_batch(self, token_lists: Sequence[Sequence[str]], token_class=None):
        del token_class
        if not token_lists:
            raise ValueError("token_lists cannot be empty")
        encoded = [self._tokens_to_ids(tl) for tl in token_lists]
        self._ensure_embedding_capacity()
        width = max(len(seq) for seq in encoded)
        padded = [seq + [self.pad_id] * (width - len(seq)) for seq in encoded]
        ids = torch.tensor(padded, dtype=torch.long, device=self.device)
        return self.forward(ids).detach().float().cpu().numpy()

    def save_checkpoint(self, weights_path: str, ecology_path: str) -> None:
        torch.save(
            {
                "kind": KIND,
                "dim": self.dim,
                "depth": self.depth,
                "heads": self.heads,
                "ff_mult": self.ff_mult,
                "dropout": self.dropout_p,
                "max_content": self.max_content,
                "vocab": self.tokens,
                "state_dict": self.state_dict(),
            },
            weights_path,
        )
        meta = {
            "kind": KIND,
            "note": "Not a Generator ecology. Do not load this into the live mind.",
            "dim": self.dim,
            "depth": self.depth,
            "heads": self.heads,
            "ff_mult": self.ff_mult,
            "dropout": self.dropout_p,
            "max_content": self.max_content,
            "vocab_size": len(self.tokens),
            "readout": "causal RoPE readout, orthogonal to the prefix-mean anchor, L2",
            "mean_pool": False,
            "embedding_residual": True,
            "anchor": "mean of every real token except the last; a one-token row keeps that token",
        }
        Path(ecology_path).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def load_sequence_encoder(path: str, device: str = "cpu") -> SequenceEncoder:
    blob = torch.load(path, map_location=device, weights_only=False)
    if blob.get("kind") != KIND:
        raise ValueError(f"{path} is not a {KIND} checkpoint")
    vocab = list(blob["vocab"])
    if not vocab or vocab[0] != PAD:
        raise ValueError("checkpoint vocab must start with <PAD>")
    enc = SequenceEncoder(
        vocab[1:],
        dim=int(blob["dim"]),
        depth=int(blob["depth"]),
        heads=int(blob["heads"]),
        ff_mult=int(blob["ff_mult"]),
        dropout=float(blob["dropout"]),
        max_content=int(blob["max_content"]),
        device=device,
    )
    enc.load_state_dict(blob["state_dict"])
    enc.eval()
    return enc
