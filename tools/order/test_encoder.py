"""CPU checks. Mean-pool is a bag. The gated pool is not. The toy loss can tell.

Run before any GPU train. A failure here means the metric would be measuring
a bug, not the corpus.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from tools.order.corpus import selftest as corpus_selftest
from tools.order.encoder import BLANK, READOUTS, OrderEncoder


def _cos(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(F.cosine_similarity(a.detach(), b.detach(), dim=-1).mean())


def _pair(enc: OrderEncoder, left: list[str], right: list[str]) -> float:
    enc.eval()
    ids = enc.pad([enc.ids_of(left), enc.ids_of(right)])
    out = enc(ids)
    return _cos(out[:1], out[1:])


def _assert_unit(enc: OrderEncoder, lines: list[list[str]]) -> None:
    z = enc.encode_token_lists(lines)
    norms = (z ** 2).sum(axis=1) ** 0.5
    if abs(float(norms.mean()) - 1.0) > 1e-4:
        raise SystemExit(f"{enc.readout} norm mean {norms.mean()} != 1")
    if float(norms.min()) < 1 - 1e-4 or float(norms.max()) > 1 + 1e-4:
        raise SystemExit(f"{enc.readout} norms not unit: {norms.min()} {norms.max()}")


def test_geometry() -> None:
    torch.manual_seed(0)
    vocab = [f"w{i}" for i in range(12)]
    lines = [
        ["w0", "w1", "w2"],
        ["w3", "w4"],
        ["w5", "w6", "w7", "w8"],
    ]
    for readout in READOUTS:
        enc = OrderEncoder(vocab, dim=32, readout=readout, max_len=8, device="cpu")
        _assert_unit(enc, lines)
        same = _pair(enc, ["w0", "w1", "w2"], ["w0", "w1", "w2"])
        if same < 0.999:
            raise SystemExit(f"{readout} is not deterministic, cosine {same}")
        rev = _pair(enc, ["w0", "w1", "w2"], ["w2", "w1", "w0"])
        bag = _pair(enc, ["w0", BLANK, "w1"], ["w1", BLANK, "w0"])
        print(f"geometry {readout:14s}  reverse {rev:.4f}  blank-swap {bag:.4f}", flush=True)
        if readout == "mean":
            if rev < 0.999 or bag < 0.999:
                raise SystemExit(f"mean readout saw order: reverse {rev} blank {bag}")
        if readout in ("gated", "parallel"):
            # Structural, at init, before any training. Parallel is diluted
            # by the bag term, so the bound is looser than pure gated.
            bound = 0.85 if readout == "gated" else 0.98
            if rev > bound or bag > bound:
                raise SystemExit(
                    f"{readout} is too close to a bag: reverse {rev} blank {bag}"
                )
        if readout == "attn":
            # Not structural. Must not be bitwise-invariant; how far it moves
            # is an empirical fact about the init, recorded for the log.
            if abs(rev - 1.0) < 1e-6:
                raise SystemExit("attn mean-pool is exactly permutation invariant")
    # Pad positions do not enter the gated sum.
    enc = OrderEncoder(vocab, dim=32, readout="gated", max_len=8, device="cpu")
    enc.eval()
    bare = enc.pad([enc.ids_of(["w0", "w1"])])
    # pad() right-pads to the width of its own batch, so the longer row is built explicitly.
    padded = torch.tensor(
        [enc.ids_of(["w0", "w1"]) + [enc.pad_id, enc.pad_id]],
        dtype=torch.long,
    )
    if _cos(enc(bare), enc(padded)) < 0.999:
        raise SystemExit("pad leaked into the gated pool")
    print("geometry ok", flush=True)


def _fit(readout: str, steps: int = 200) -> float:
    torch.manual_seed(0)
    vocab = [f"a{i}" for i in range(8)] + [f"b{i}" for i in range(8)]
    specs = []
    for i in range(8):
        specs.append(([f"a{i}", BLANK, f"b{i}"], 0))
        specs.append(([f"b{i}", BLANK, f"a{i}"], 1))
    enc = OrderEncoder(vocab, dim=32, readout=readout, max_len=8, device="cpu")
    head = nn.Linear(32, 2)
    opt = torch.optim.Adam(list(enc.parameters()) + list(head.parameters()), lr=1e-2)
    targets = torch.tensor([y for _ctx, y in specs], dtype=torch.long)
    ids = enc.pad([enc.ids_of(ctx) for ctx, _y in specs])
    enc.train()
    last = 1e9
    for _ in range(steps):
        opt.zero_grad()
        loss = F.cross_entropy(head(enc(ids)), targets)
        loss.backward()
        opt.step()
        last = float(loss.detach())
    enc.eval()
    with torch.no_grad():
        pred = head(enc(ids)).argmax(-1)
        acc = float((pred == targets).float().mean())
    print(f"toy {readout:14s}  loss {last:.4f}  acc {acc:.3f}", flush=True)
    return last


def test_toy() -> None:
    mean_loss = _fit("mean")
    if mean_loss < 0.5:
        raise SystemExit(f"mean readout separated order conflicts, loss {mean_loss}")
    for readout in ("gated", "parallel", "attn", "attn_parallel"):
        loss = _fit(readout)
        # The data is eight reversed pairs with opposite labels. A readout
        # that can carry order has to fit it. ln(2) is the bag's floor.
        if loss > 0.15:
            raise SystemExit(f"{readout} did not learn an order conflict, loss {loss}")
    print("toy ok", flush=True)


def main() -> int:
    corpus_selftest()
    test_geometry()
    test_toy()
    print("ALL ORDER TESTS PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
