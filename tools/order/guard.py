"""Hash the main checkout. This worktree must not write there.

The other completion arms share ``experiment/completion-objective`` and
``rfe/scratch/completion``. Live corpus and live checkpoints stay in the
main checkout. New files go in this worktree or in ``scratch/order``.
"""

from __future__ import annotations

from pathlib import Path

from tools.completion.live_guard import LIVE, PROTECTED_NAMES, sha256

_CANDIDATES = (
    Path("/mnt/c/Users/spamw/rfe/RFE-Core2"),
    Path(r"C:\Users\spamw\rfe\RFE-Core2"),
)


def main_checkout() -> Path:
    for path in _CANDIDATES:
        if (path / "data" / "corpus" / "rhythm_train.jsonl").is_file():
            return path
    raise SystemExit("main checkout not found; refusing to guess a corpus path")


MAIN = main_checkout()
REPO = Path(__file__).resolve().parents[2]
SCRATCH = MAIN.parent / "scratch" / "order"


def assert_live_intact() -> dict:
    """Hash the main checkout, not this worktree's copies."""
    found = {}
    for rel, expect in LIVE.items():
        path = MAIN / rel
        digest = sha256(path)
        if digest != expect:
            raise SystemExit(f"live file moved: {rel} sha256 {digest} != {expect}")
        found[rel] = digest
    return found


def assert_safe_output(path: Path) -> Path:
    """Refuse the main tree, the other arms' scratch, and protected names."""
    resolved = path.resolve()
    main = MAIN.resolve()
    if resolved == main or main in resolved.parents:
        raise SystemExit(f"refusing to write into the main checkout: {path}")
    other = (main.parent / "scratch" / "completion").resolve()
    if resolved == other or other in resolved.parents:
        raise SystemExit(f"refusing to write the other arm's scratch: {path}")
    if resolved.name in PROTECTED_NAMES:
        raise SystemExit(f"refusing to write protected artifact: {path}")
    return resolved
