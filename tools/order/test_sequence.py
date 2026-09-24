"""CPU checks for the phase-C sequence encoder. Not a training run.

    python -m tools.order.test_sequence
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import torch

from tools.order.sequence import SequenceEncoder, load_sequence_encoder, role_order_row


def _cos(a, b) -> float:
    a = a / a.norm()
    b = b / b.norm()
    return float((a * b).sum())


def _encoder(dim: int, seed: int = 0, dropout: float = 0.1) -> SequenceEncoder:
    torch.manual_seed(seed)
    return SequenceEncoder(
        ["alpha", "beta", "gamma", "delta"],
        dim=dim,
        depth=2,
        heads=4,
        ff_mult=4,
        dropout=dropout,
        max_content=8,
        device="cpu",
    )


def test_unit_norm_and_pad() -> None:
    enc = _encoder(128)
    enc.eval()
    short = torch.tensor([[1, 2, 3]], dtype=torch.long)
    padded = torch.tensor([[1, 2, 3, 0, 0]], dtype=torch.long)
    a = enc.forward(short)
    b = enc.forward(padded)
    if a.shape != (1, 128) or b.shape != (1, 128):
        raise AssertionError(f"shape {tuple(a.shape)} {tuple(b.shape)}")
    for row in (a, b):
        norm = float(row.detach().norm())
        if abs(norm - 1.0) > 1e-5:
            raise AssertionError(f"norm {norm}")
    gap = float((a - b).abs().max())
    if gap > 1e-5:
        raise AssertionError(f"padding changed the readout by {gap}")


def test_not_a_bag() -> None:
    enc = _encoder(128, seed=1)
    enc.eval()
    left = torch.tensor([[1, 2, 3]], dtype=torch.long)
    right = torch.tensor([[3, 2, 1]], dtype=torch.long)
    z_left = enc.forward(left)
    z_right = enc.forward(right)
    gap = float((z_left - z_right).abs().max())
    if gap < 1e-5:
        raise AssertionError(f"permutation left the readout unchanged ({gap})")
    mean_left = enc.token_embedding_mean(left)
    mean_right = enc.token_embedding_mean(right)
    mean_gap = float((mean_left - mean_right).abs().max())
    if mean_gap > 1e-5:
        raise AssertionError(f"embedding mean is not a bag ({mean_gap})")
    # The published control is that mean. Role order must not change it.
    if _cos(mean_left[0], mean_right[0]) < 0.999:
        raise AssertionError("sorted and reversed means diverged")


def test_early_token_has_grad() -> None:
    enc = _encoder(32, seed=2, dropout=0.0)
    enc.train()
    ids = torch.tensor([[1, 2, 3]], dtype=torch.long)
    enc.forward(ids).sum().backward()
    grad = enc.embedding.weight.grad
    if grad is None or float(grad[1].abs().sum()) <= 0:
        raise AssertionError("position 0 did not receive gradient")
    # The last content token is the slot. It is outside the anchor, and the
    # stack reads a detached embedding, so it must not train that row.
    if float(grad[3].abs().sum()) > 1e-8:
        raise AssertionError(f"slot token received gradient {float(grad[3].abs().sum())}")
    if float(enc.layers[0].qkv.weight.grad.abs().sum()) <= 0:
        raise AssertionError("attention did not receive gradient")
    if float(enc.readout.grad.abs().sum()) <= 0:
        raise AssertionError("readout token did not receive gradient")


def _zero_stack(enc: SequenceEncoder) -> None:
    with torch.no_grad():
        for layer in enc.layers:
            for module in (layer.qkv, layer.proj, layer.ff[0], layer.ff[2]):
                module.weight.zero_()
                if module.bias is not None:
                    module.bias.zero_()


def test_anchor_ignores_the_slot_when_the_stack_is_silent() -> None:
    enc = _encoder(32, seed=4, dropout=0.0)
    enc.eval()
    _zero_stack(enc)
    same = enc.forward(torch.tensor([[1, 2, 3], [1, 2, 4]], dtype=torch.long))
    if float((same[0] - same[1]).abs().max()) > 1e-5:
        raise AssertionError("a different slot token changed the prefix anchor")
    moved = enc.forward(torch.tensor([[1, 2, 3], [1, 3, 2]], dtype=torch.long))
    if float((moved[0] - moved[1]).abs().max()) < 1e-4:
        raise AssertionError("a different kernel left the anchor unchanged")
    only = enc.forward(torch.tensor([[2]], dtype=torch.long))
    if abs(float(only.norm()) - 1.0) > 1e-5:
        raise AssertionError("length-1 anchor is not unit norm")


def test_both_widths_and_roundtrip() -> None:
    for dim in (128, 256):
        enc = _encoder(dim, seed=dim)
        enc.eval()
        ids = torch.tensor([[1, 2, 0, 0], [1, 2, 3, 4]], dtype=torch.long)
        out = enc.forward(ids)
        if out.shape != (2, dim):
            raise AssertionError(tuple(out.shape))
        norms = out.norm(dim=-1)
        if float((norms - 1).abs().max()) > 1e-5:
            raise AssertionError(f"dim {dim} norms {norms.tolist()}")
    enc = _encoder(32, seed=3)
    enc.eval()
    ids = torch.tensor([[1, 4, 2]], dtype=torch.long)
    before = enc.forward(ids).detach()
    with tempfile.TemporaryDirectory() as tmp:
        weights = str(Path(tmp) / "enc.pt")
        meta = Path(tmp) / "enc.json"
        enc.save_checkpoint(weights, str(meta))
        note = meta.read_text(encoding="utf-8")
        if "phase_c_rope_causal" not in note or "mean_pool" not in note:
            raise AssertionError("checkpoint note does not name the readout")
        loaded = load_sequence_encoder(weights, device="cpu")
        after = loaded.forward(ids)
    if float((before - after).abs().max()) > 1e-6:
        raise AssertionError("reload did not reproduce the readout")


def test_role_order_preserves_the_bag() -> None:
    row = {
        "context": ["attractor", "core", "foundation"],
        "kernel": ["foundation", "attractor"],
        "vary": "core",
        "source": "recur",
        "targets": {"stability": 5},
    }
    ordered = role_order_row(row)
    if ordered["context"] != ["foundation", "attractor", "core"]:
        raise AssertionError(ordered["context"])
    if ordered["presentation"] != "role":
        raise AssertionError(ordered["presentation"])
    broad = role_order_row({"context": ["abstain"], "targets": {"anchor": 1}, "source": "broad"})
    if broad["context"] != ["abstain"] or broad["presentation"] != "authored":
        raise AssertionError(broad)
    try:
        role_order_row({
            "context": ["a", "b"],
            "kernel": ["a", "c"],
            "vary": "b",
            "source": "recur",
        })
    except ValueError:
        return
    raise AssertionError("a kernel that changes the bag was accepted")


def main() -> None:
    test_unit_norm_and_pad()
    test_not_a_bag()
    test_early_token_has_grad()
    test_anchor_ignores_the_slot_when_the_stack_is_silent()
    test_both_widths_and_roundtrip()
    test_role_order_preserves_the_bag()
    print("sequence encoder checks passed")


if __name__ == "__main__":
    main()
