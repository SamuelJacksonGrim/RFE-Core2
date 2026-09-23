"""CPU checks for the completion collator and the residual grad path.

    python -m tools.completion.check_collator

The row check reads the live train corpus and the scratch completion rows.
It does not write either. The residual check builds a tiny generator on CPU.
"""

from __future__ import annotations

import sys

import torch

from agents.generator import Generator
from tools.completion.corpus import content_of, load_jsonl
from tools.completion.live_guard import REPO
from training.completion import (
    IGNORE_INDEX,
    CompletionCollator,
    assert_completion_mask,
    filler_ids_from_labels,
    mode_filler,
    pack_targets,
)
from training.corpus import RHYTHMS, TRAIN_PATH, load_corpus
from training.encode import encode_grad

ROWS_PATH = REPO.parent / "scratch" / "completion" / "completion_train.jsonl"
SURFACE = ["alpha", "beta", "gamma", "delta"]
SEQUENCES = [["alpha", "beta"], ["gamma"], ["beta", "delta", "alpha"]]


def _content_vocab(records) -> list[str]:
    # Same construction as tools.completion.train._content_vocab.
    words = {t for rec in records for t in content_of(rec["tokens"])}
    return sorted(words)


def _fail(message: str) -> None:
    raise SystemExit(message)


def check_rows() -> None:
    if not ROWS_PATH.is_file():
        _fail(f"missing completion rows: {ROWS_PATH}")
    live = load_corpus(TRAIN_PATH)
    vocab = _content_vocab(live)
    index = {token: i for i, token in enumerate(vocab)}
    rhythm_index = {name: i for i, name in enumerate(RHYTHMS)}
    rows = load_jsonl(ROWS_PATH)[:64]
    if len(rows) < 64:
        _fail(f"need 64 completion rows, got {len(rows)}")

    collator = CompletionCollator(index, rhythm_index, "cpu")
    packed = collator(rows)
    fresh = pack_targets([row["target_dist"] for row in rows], index, "cpu")
    diff = float((packed.target_p - fresh).abs().max())
    if diff >= 1e-6:
        _fail(f"collator target_p differs from pack_targets by {diff}")

    filler_ids = filler_ids_from_labels(packed.labels)
    assert_completion_mask(
        packed.labels, packed.stem_lengths, packed.support_ids, filler_ids,
    )
    if packed.labels.shape[0] != 64:
        _fail(f"label batch is {packed.labels.shape}, expected 64 rows")

    for i, row in enumerate(rows):
        context = list(row["context"])
        if packed.contexts[i] != context:
            _fail(f"row {i} encoder input is not the context")
        stem = len(context)
        if not torch.equal(
            packed.labels[i, :stem],
            torch.full((stem,), IGNORE_INDEX, dtype=torch.long),
        ):
            _fail(f"row {i} stem position is not {IGNORE_INDEX}")
        supervised = packed.labels[i] != IGNORE_INDEX
        if int(supervised.sum()) != 1:
            _fail(f"row {i} has {int(supervised.sum())} supervised positions")
        word = vocab[int(filler_ids[i])]
        if word not in row["targets"]:
            _fail(f"row {i} gathered id {int(filler_ids[i])} ({word}) is not a target")
        if word in context:
            _fail(f"row {i} filler {word} leaked into the encoder input")
        if word != mode_filler(row):
            _fail(f"row {i} supervised slot is {word}, mode is {mode_filler(row)}")
        if int(packed.labels[i, stem]) != index[word]:
            _fail(f"row {i} supervised slot is not the mode filler index")
        if stem + 1 < packed.labels.shape[1] and not torch.equal(
            packed.labels[i, stem + 1:],
            torch.full((packed.labels.shape[1] - stem - 1,), IGNORE_INDEX, dtype=torch.long),
        ):
            _fail(f"row {i} pad is not {IGNORE_INDEX}")

    print(
        f"collator ok  rows=64  vocab={len(vocab)}  max_abs_target_p={diff:.3e}",
        flush=True,
    )


def _expect_value_error(label: str, fn) -> None:
    try:
        fn()
    except ValueError:
        return
    _fail(f"mask check did not refuse: {label}")


def check_mask_refuses() -> None:
    _expect_value_error(
        "two supervised positions",
        lambda: filler_ids_from_labels(torch.tensor([[3, 4]])),
    )
    _expect_value_error(
        "zero supervised positions",
        lambda: filler_ids_from_labels(torch.tensor([[IGNORE_INDEX, IGNORE_INDEX]])),
    )

    stem_label = torch.tensor([[5, IGNORE_INDEX]])
    stem_ids = filler_ids_from_labels(stem_label)
    _expect_value_error(
        "stem position supervised",
        lambda: assert_completion_mask(stem_label, torch.tensor([1]), [[5]], stem_ids),
    )

    outside = torch.tensor([[IGNORE_INDEX, 5]])
    outside_ids = filler_ids_from_labels(outside)
    _expect_value_error(
        "filler outside support",
        lambda: assert_completion_mask(outside, torch.tensor([1]), [[1]], outside_ids),
    )
    print("mask refuse ok", flush=True)


def _build_generator(residual: bool) -> Generator:
    torch.manual_seed(0)
    gen = Generator(
        vocab_size=64,
        dim=32,
        depth=2,
        heads=4,
        ff_mult=4,
        dropout=0.0,
        # L2 output makes pow(2).mean() constant, so the embedding grad is noise.
        normalize_output=False,
        device="cpu",
        auto_decay_interval=None,
    )
    gen.embedding_residual = residual
    gen.eval()
    gen.encode_batch([[token] for token in SURFACE])
    gen.train()
    return gen


def _snapshot(gen: Generator) -> dict:
    return {key: value.detach().clone() for key, value in gen.state_dict().items()}


def _embedding_grad(gen: Generator, *, freeze_stack: bool, cut_encoder: bool):
    """One forward from the caller's weights.

    requires_grad=False does not stop the Jacobian through a frozen module.
    The frozen run also detaches the encoder input, which is the cut a stack
    that cannot drag the table actually has. Residual-on already detaches
    inside forward, so the extra cut does not change the embedding grad.
    """
    gen.zero_grad(set_to_none=True)
    for name, param in gen.named_parameters():
        param.requires_grad = (not freeze_stack) or name.startswith("embedding.")

    seen = {}

    def _observe(module, args):
        seen["encoder_input_requires_grad"] = bool(args[0].requires_grad)
        if cut_encoder:
            return (args[0].detach(),) + tuple(args[1:])
        return None

    hook = gen.encoder.register_forward_pre_hook(_observe)
    try:
        out = encode_grad(gen, SEQUENCES)
        loss = out.pow(2).mean()
        if loss.requires_grad:
            loss.backward()
    finally:
        hook.remove()

    if gen.embedding.weight.grad is None:
        emb_grad = torch.zeros_like(gen.embedding.weight)
    else:
        emb_grad = gen.embedding.weight.grad.detach().clone()

    encoder_nonzero = False
    for name, param in gen.named_parameters():
        if not name.startswith("encoder.") or param.grad is None:
            continue
        if float(param.grad.detach().abs().sum()) > 0:
            encoder_nonzero = True
            break
    if "encoder_input_requires_grad" not in seen:
        _fail("encoder pre-hook did not see an input")
    return emb_grad, encoder_nonzero, seen["encoder_input_requires_grad"]


def _pair(gen: Generator):
    state = _snapshot(gen)
    full, encoder_nonzero, encoder_requires = _embedding_grad(
        gen, freeze_stack=False, cut_encoder=False,
    )
    gen.load_state_dict(state)
    frozen, _, _ = _embedding_grad(gen, freeze_stack=True, cut_encoder=True)
    gen.load_state_dict(state)
    return full, frozen, encoder_nonzero, encoder_requires


def check_residual() -> None:
    on = _build_generator(True)
    full, frozen, encoder_nonzero, encoder_requires = _pair(on)
    if encoder_requires:
        _fail("residual-on transformer input requires grad; the table can be dragged")
    if not encoder_nonzero:
        _fail("residual-on full backward produced no encoder grad; the stack is not trained")
    if float(full.abs().max()) < 1e-4:
        _fail("residual-on embedding grad is ~0; the loss does not see the table")
    if not torch.allclose(full, frozen, rtol=1e-4, atol=1e-5):
        diff = float((full - frozen).abs().max())
        _fail(f"residual-on embedding grads differ by {diff}")

    off = _build_generator(False)
    full_off, frozen_off, _, encoder_requires_off = _pair(off)
    if not encoder_requires_off:
        _fail("residual-off transformer input does not require grad")
    if float(full_off.abs().max()) <= 1e-5:
        _fail("residual-off embedding grad is inside atol of 0; the drag is invisible")
    if torch.allclose(full_off, frozen_off, rtol=1e-4, atol=1e-5):
        _fail("residual-off embedding grads matched; the unfixed path did not drag the table")

    print(
        "residual grad ok  "
        f"on_maxdiff={(full - frozen).abs().max().item():.3e}  "
        f"off_maxdiff={(full_off - frozen_off).abs().max().item():.3e}",
        flush=True,
    )


def main() -> int:
    check_rows()
    check_mask_refuses()
    check_residual()
    print("SELF-CHECK PASSED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
