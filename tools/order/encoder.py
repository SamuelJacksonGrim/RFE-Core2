"""Position-sensitive field encoder. Not a Generator, and not a modified one.

Mean-pool cannot say which token was where. Summing ``e_i + p_i`` does not
fix that: the positional part depends on length, not on order. A trained
transformer under the completion loss is the wrong fix too — the completion
finding showed that training the shared stack returns participation to ~4.

Two readouts, chosen so those failures are not re-run by accident:

``gated``
    Fixed Rademacher signs per position, Hadamard product, then mean.
    ``h = L2(mean_i(e_i * g_i))``. Swapping two tokens changes the sum on
    every coordinate where the signs differ, and training cannot turn the
    gate off because the gate is not a parameter. Sinusoids were not used
    here: the position-0 sinusoid is 0 on every even axis, which would
    delete half of the first token before the pool.

``parallel``
    ``h = L2(unit(mean e) + unit(mean e*g))``. The bag term is the
    mean-pool that already fills dimensions. Each term is re-normalized
    before the add, so a learned scale cannot zero the bag (a LayerNorm
    gamma can). This is a parallel head, not an edit to Generator.forward.

``attn`` / ``attn_parallel``
    One pre-LN transformer layer over ``sqrt(dim) * e + sinusoid``, then a
    mean pool. This is the "small transformer" option. It is NOT
    order-sensitive by construction: ``mean(e_i + p_i)`` is a bag, and the
    layer can learn to ignore position. ``attn_parallel`` keeps the same
    non-erasable bag term beside it.

``mean``
    Plain mean of embeddings. The paired control on the same ordered rows.

Every readout returns one unit-norm vector of ``dim``. That is the field
contract (injection is cosine / add of unit vectors). It is not a Generator
state dict: no ecology, no address space.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

PAD = "<PAD>"
BLANK = "<BLANK>"
READOUTS = ("mean", "gated", "parallel", "attn", "attn_parallel")


def _sinusoid(max_len: int, dim: int) -> torch.Tensor:
    pe = torch.zeros(max_len, dim)
    position = torch.arange(0, max_len).unsqueeze(1).float()
    div = torch.exp(torch.arange(0, dim, 2).float() * (-math.log(10000.0) / dim))
    pe[:, 0::2] = torch.sin(position * div)
    pe[:, 1::2] = torch.cos(position * div)
    return pe


def _rademacher(max_len: int, dim: int, seed: int = 0) -> torch.Tensor:
    generator = torch.Generator()
    generator.manual_seed(seed)
    signs = torch.randint(0, 2, (max_len, dim), generator=generator, dtype=torch.float32)
    return signs.mul_(2).sub_(1)


def _masked_mean(x: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
    mask = valid.unsqueeze(-1).to(dtype=x.dtype)
    denom = mask.sum(dim=1).clamp(min=1.0)
    return (x * mask).sum(dim=1) / denom


class OrderEncoder(nn.Module):
    def __init__(
        self,
        vocab: Sequence[str],
        dim: int,
        readout: str,
        max_len: int = 8,
        device: Optional[str] = None,
    ):
        super().__init__()
        if readout not in READOUTS:
            raise ValueError(f"unknown readout {readout}")
        if dim % 2 != 0 or dim % 4 != 0:
            raise ValueError(f"dim {dim} must be divisible by 4 (attention heads)")
        surface = list(vocab)
        if PAD in surface or BLANK in surface:
            raise ValueError("surface vocab collides with PAD or BLANK")
        if len(surface) != len(set(surface)):
            raise ValueError("duplicate surface token")

        self.dim = dim
        self.readout = readout
        self.max_len = max_len
        self.device_name = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokens: List[str] = [PAD, BLANK] + surface
        self.index: Dict[str, int] = {t: i for i, t in enumerate(self.tokens)}
        self.pad_id = 0
        self.blank_id = 1

        self.embedding = nn.Embedding(len(self.tokens), dim, padding_idx=self.pad_id)
        self.register_buffer("gate", _rademacher(max_len, dim), persistent=True)
        self.register_buffer("pe", _sinusoid(max_len, dim), persistent=True)
        self.layer: Optional[nn.TransformerEncoderLayer]
        if readout.startswith("attn"):
            self.layer = nn.TransformerEncoderLayer(
                d_model=dim,
                nhead=4,
                dim_feedforward=dim * 4,
                dropout=0.0,
                batch_first=True,
                activation="gelu",
                norm_first=True,
            )
        else:
            self.layer = None
        self._init_weights()
        self.to(self.device_name)

    def _init_weights(self) -> None:
        # Same std the Generator uses so a token is not drowned by a positional
        # add. The field vector is L2-normalized, so global scale is not the
        # signal; the std is here so attention's residual starts in range.
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.035)
        with torch.no_grad():
            self.embedding.weight[self.pad_id].zero_()
        if self.layer is None:
            return
        for module in self.layer.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def ids_of(self, tokens: Sequence[str]) -> List[int]:
        if not tokens:
            raise ValueError("empty token list")
        if len(tokens) > self.max_len:
            raise ValueError(f"sequence length {len(tokens)} > max_len {self.max_len}")
        try:
            return [self.index[t] for t in tokens]
        except KeyError as exc:
            raise KeyError(f"token {exc.args[0]!r} is not in the order encoder vocab") from exc

    def pad(self, seqs: Sequence[Sequence[int]]) -> torch.Tensor:
        width = max(len(s) for s in seqs)
        rows = [list(s) + [self.pad_id] * (width - len(s)) for s in seqs]
        return torch.tensor(rows, dtype=torch.long, device=self.embedding.weight.device)

    def _attend(self, emb: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        if self.layer is None:
            raise RuntimeError("attend on a non-attention readout")
        positions = torch.arange(emb.shape[1], device=emb.device)
        x = emb * math.sqrt(self.dim) + self.pe[positions]
        # A row of all-pad is undefined for the softmax. Callers never pad a
        # whole sequence away; still refuse it rather than emit NaN.
        if (~valid).all(dim=1).any():
            raise RuntimeError("attention received an all-pad row")
        return self.layer(x, src_key_padding_mask=~valid)

    def represent(self, ids: torch.Tensor):
        """Return ``(field, bag, ordered)``.

        ``field`` is the unit-norm output. ``bag`` and ``ordered`` are the
        unit-norm terms before a parallel blend, or None when that term is
        not part of the readout. Diagnostic only — training uses ``forward``.
        """
        valid = ids != self.pad_id
        emb = self.embedding(ids)
        positions = torch.arange(ids.shape[1], device=ids.device)
        gated = emb * self.gate[positions]
        bag = _masked_mean(emb, valid)
        ordered_raw = _masked_mean(gated, valid)
        if self.layer is not None:
            ordered_raw = _masked_mean(self._attend(emb, valid), valid)

        bag_u = F.normalize(bag, dim=-1)
        ord_u = F.normalize(ordered_raw, dim=-1)
        if self.readout == "mean":
            field = bag_u
            return field, bag_u, None
        if self.readout == "gated":
            field = ord_u
            return field, None, ord_u
        if self.readout == "attn":
            field = ord_u
            return field, None, ord_u
        if self.readout in ("parallel", "attn_parallel"):
            field = F.normalize(bag_u + ord_u, dim=-1)
            return field, bag_u, ord_u
        raise RuntimeError(self.readout)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        field, _bag, _ordered = self.represent(ids)
        return field

    @torch.no_grad()
    def encode_token_lists(self, token_lists: Sequence[Sequence[str]], batch: int = 256) -> np.ndarray:
        self.eval()
        if not token_lists:
            raise ValueError("token_lists cannot be empty")
        out = []
        for start in range(0, len(token_lists), batch):
            chunk = token_lists[start:start + batch]
            ids = self.pad([self.ids_of(tl) for tl in chunk])
            out.append(self.forward(ids).detach().float().cpu().numpy())
        return np.concatenate(out, axis=0)

    @torch.no_grad()
    def encode_parts(self, token_lists: Sequence[Sequence[str]], batch: int = 256):
        """Unit field, and the bag / order terms where the readout has them."""
        self.eval()
        fields, bags, ords = [], [], []
        for start in range(0, len(token_lists), batch):
            chunk = token_lists[start:start + batch]
            ids = self.pad([self.ids_of(tl) for tl in chunk])
            field, bag, ordered = self.represent(ids)
            fields.append(field.detach().float().cpu().numpy())
            bags.append(None if bag is None else bag.detach().float().cpu().numpy())
            ords.append(None if ordered is None else ordered.detach().float().cpu().numpy())
        field_a = np.concatenate(fields, axis=0)
        bag_a = None if bags[0] is None else np.concatenate(bags, axis=0)
        ord_a = None if ords[0] is None else np.concatenate(ords, axis=0)
        return field_a, bag_a, ord_a


def load_checkpoint(path: str, device: str):
    blob = torch.load(path, map_location=device, weights_only=False)
    enc = OrderEncoder(
        blob["surface_vocab"],
        int(blob["dim"]),
        blob["readout"],
        max_len=int(blob["max_len"]),
        device=device,
    )
    enc.load_state_dict(blob["state_dict"])
    enc.eval()
    head = nn.Linear(int(blob["dim"]), len(blob["head_vocab"]))
    head.load_state_dict(blob["head_state_dict"])
    head.to(device)
    head.eval()
    return enc, head, blob
