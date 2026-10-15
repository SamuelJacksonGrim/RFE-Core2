"""
tests/doc_accuracy/hardcoded_dim.py

Guard: field width has one canonical home, and leftover dim literals
outside that home (or disagreeing with it) fail.

Canonical production dim is CONFIG["dim"] in loop/recursion1188.py.
YAML `dim:` keys and production constructor defaults `dim: int = N` are
leftovers that currently duplicate it. When CONFIG is widened (128 → 768)
this script fails until those leftovers are updated. When a new production
`dim` default appears that the census does not know about, it also fails.

This is an inventory lock, not a pytest suite. Run:

    PYTHONUTF8=1 python -m tests.doc_accuracy.hardcoded_dim

Exit 0 = every known field-dim site matches CONFIG, and no unknown
production field-dim site appeared. Exit 1 otherwise.

Coincidental 128s (windows, max_len, batch_size, Jaccard rings) are
reported as INFO and do not fail. tests/ is not scanned: tests/_common.py
deliberately boots dim=64.
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Canonical dim
# ---------------------------------------------------------------------------

CANONICAL_FILE = "loop/recursion1188.py"

# Production Python whose `dim` constructor defaults / PROJ_DIM / explicit
# dim= kwargs are field width. Relative to repo root.
PRODUCTION_PY_ROOTS = (
    "agents",
    "substrate",
    "cognition",
    "loop",
    "interference",
    "api",
)

PRODUCTION_PY_FILES = (
    "tools/voice/qwen_perception.py",
    "tools/voice/repl_qwen.py",
)

YAML_FILES = (
    "configs/field.yaml",
    "configs/recursion.yaml",
    "configs/attractors.yaml",
)

# Names that are field width when assigned at module scope.
FIELD_DIM_ASSIGN_NAMES = frozenset({"PROJ_DIM"})

# Parameter names that are field width.
FIELD_DIM_ARG_NAMES = frozenset({"dim"})

# Calls whose `dim=` keyword is field width (the live mind, not a test).
FIELD_DIM_CALL_FUNCS = frozenset({"build_full_stack", "Generator", "AutonomousCycle"})


# Census of known leftover field-dim sites. New sites fail until added here
# (and to docs/EXPERIMENTAL_LEVERS.md). Values are not stored — they must
# equal CONFIG["dim"].
#
# kind: arg | assign | call | yaml
KNOWN_SITES: Tuple[Tuple[str, str, str], ...] = (
    # file, kind, qualifier
    ("loop/recursion1188.py", "config", "CONFIG.dim"),
    ("configs/field.yaml", "yaml", "field.dim"),
    ("configs/field.yaml", "yaml", "watcher.dim"),
    ("configs/recursion.yaml", "yaml", "generator.dim"),
    ("agents/generator.py", "arg", "Generator.__init__.dim"),
    ("agents/decoder.py", "arg", "TokenDecoder.__init__.dim"),
    ("agents/watcher.py", "arg", "Watcher.__init__.dim"),
    ("agents/witness.py", "arg", "Witness.__init__.dim"),
    ("substrate/resonance_field.py", "arg", "ResonanceField.__init__.dim"),
    ("substrate/temporal_stream.py", "arg", "TemporalStream.__init__.dim"),
    ("substrate/vector_space.py", "arg", "VectorSpace.__init__.dim"),
    ("cognition/recursive_attention.py", "arg", "RecursiveAttention.__init__.dim"),
    ("cognition/predictive_echo.py", "arg", "PredictiveEcho.__init__.dim"),
    ("loop/autonomous_cycle.py", "arg", "AutonomousCycle.__init__.dim"),
    ("tools/voice/qwen_perception.py", "assign", "PROJ_DIM"),
    ("tools/voice/repl_qwen.py", "call", "build_full_stack.dim"),
)


@dataclass
class Hit:
    file: str
    line: int
    kind: str
    qualifier: str
    value: int

    def key(self) -> Tuple[str, str, str]:
        return (self.file, self.kind, self.qualifier)


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _const_int(node: ast.AST) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _const_int(node.operand)
        return None if inner is None else -inner
    return None


def _qualname(stack: List[str], func: str, arg: str) -> str:
    prefix = ".".join(stack + [func]) if stack else func
    return f"{prefix}.{arg}"


class _DimVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str):
        self.relpath = relpath
        self.hits: List[Hit] = []
        self._class_stack: List[str] = []
        self._func_stack: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node)

    def _visit_func(self, node) -> None:
        self._func_stack.append(node.name)
        args = node.args
        # positional-or-keyword defaults sit on the tail of args.args
        positional = list(args.args)
        defaults = list(args.defaults)
        if defaults:
            bound = positional[-len(defaults):]
            for arg, default in zip(bound, defaults):
                if arg.arg in FIELD_DIM_ARG_NAMES:
                    val = _const_int(default)
                    if val is not None:
                        self.hits.append(Hit(
                            file=self.relpath,
                            line=arg.lineno,
                            kind="arg",
                            qualifier=_qualname(self._class_stack, node.name, arg.arg),
                            value=val,
                        ))
        for arg, default in zip(args.kwonlyargs, args.kw_defaults):
            if default is None or arg.arg not in FIELD_DIM_ARG_NAMES:
                continue
            val = _const_int(default)
            if val is not None:
                self.hits.append(Hit(
                    file=self.relpath,
                    line=arg.lineno,
                    kind="arg",
                    qualifier=_qualname(self._class_stack, node.name, arg.arg),
                    value=val,
                ))
        self.generic_visit(node)
        self._func_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        val = _const_int(node.value)
        if val is None:
            self.generic_visit(node)
            return
        # Only module-scope DIM / PROJ_DIM (not inside functions).
        if self._func_stack:
            self.generic_visit(node)
            return
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in FIELD_DIM_ASSIGN_NAMES:
                self.hits.append(Hit(
                    file=self.relpath,
                    line=node.lineno,
                    kind="assign",
                    qualifier=target.id,
                    value=val,
                ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name in FIELD_DIM_CALL_FUNCS:
            for kw in node.keywords:
                if kw.arg in FIELD_DIM_ARG_NAMES:
                    val = _const_int(kw.value)
                    if val is not None:
                        self.hits.append(Hit(
                            file=self.relpath,
                            line=node.lineno,
                            kind="call",
                            qualifier=f"{name}.{kw.arg}",
                            value=val,
                        ))
        self.generic_visit(node)


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def parse_config_dim() -> Tuple[int, int]:
    path = REPO_ROOT / CANONICAL_FILE
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "CONFIG" for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for k, v in zip(node.value.keys, node.value.values):
            if isinstance(k, ast.Constant) and k.value == "dim":
                val = _const_int(v)
                if val is None:
                    raise SystemExit(f"CONFIG['dim'] is not an int literal in {CANONICAL_FILE}")
                return val, node.lineno
    raise SystemExit(f"CONFIG['dim'] not found in {CANONICAL_FILE}")


def scan_python(relpath: str) -> List[Hit]:
    path = REPO_ROOT / relpath
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    visitor = _DimVisitor(relpath)
    visitor.visit(tree)
    return visitor.hits


def scan_yaml(relpath: str) -> List[Hit]:
    path = REPO_ROOT / relpath
    hits: List[Hit] = []
    section_stack: List[Tuple[int, str]] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if ":" not in stripped:
            continue
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.split("#", 1)[0].strip()
        while section_stack and section_stack[-1][0] >= indent:
            section_stack.pop()
        if rest == "":
            section_stack.append((indent, key))
            continue
        if key != "dim":
            continue
        try:
            val = int(rest)
        except ValueError:
            continue
        section = ".".join(s[1] for s in section_stack) if section_stack else ""
        qualifier = f"{section}.dim" if section else "dim"
        hits.append(Hit(file=relpath, line=i, kind="yaml", qualifier=qualifier, value=val))
    return hits


def production_py_files() -> List[str]:
    files: List[str] = []
    for root in PRODUCTION_PY_ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if p.name == "__init__.py":
                continue
            files.append(_rel(p))
    for rel in PRODUCTION_PY_FILES:
        if (REPO_ROOT / rel).is_file():
            files.append(rel)
    return files


def coincidental_128_report(canonical: int) -> List[str]:
    """INFO-only: numeric 128 that is NOT a field-dim site we already track.

    This is a grep-shaped reminder, not a failure. Windows, max_len, batch
    size, and Jaccard rings reuse 128 without being field width.
    """
    interesting = []
    skip_dirs = {
        "tests", "docs", "data", ".git", "__pycache__", "visualization",
    }
    skip_suffix = {".md", ".json", ".jsonl", ".log", ".gz", ".pt", ".npy"}
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = _rel(p)
        parts = Path(rel).parts
        if any(part in skip_dirs for part in parts):
            continue
        if p.suffix in skip_suffix:
            continue
        if p.suffix not in {".py", ".yaml", ".yml"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if "128" not in line:
                continue
            stripped = line.split("#", 1)[0]
            if "128" not in stripped:
                continue
            # Field-dim sites are handled elsewhere.
            if "dim" in stripped.lower() and ("128" in stripped):
                continue
            if "PROJ_DIM" in stripped:
                continue
            interesting.append(f"  {rel}:{i}: {line.strip()[:120]}")
    return interesting


def main() -> int:
    canonical, canon_line = parse_config_dim()
    print(f"canonical field dim: {canonical}  ({CANONICAL_FILE}:{canon_line} CONFIG['dim'])")
    print()

    hits: List[Hit] = [
        Hit(file=CANONICAL_FILE, line=canon_line, kind="config",
            qualifier="CONFIG.dim", value=canonical),
    ]
    for rel in production_py_files():
        hits.extend(scan_python(rel))
    for rel in YAML_FILES:
        hits.extend(scan_yaml(rel))

    # Dedup identical keys (CONFIG.dim is both config-parse and would not
    # also be an arg). Keep first.
    seen = {}
    unique: List[Hit] = []
    for h in hits:
        k = h.key()
        if k in seen:
            continue
        seen[k] = h
        unique.append(h)
    hits = unique

    known_keys = set(KNOWN_SITES)
    found_keys = {h.key() for h in hits}

    failures: List[str] = []

    print("known field-dim sites:")
    for file, kind, qualifier in KNOWN_SITES:
        hit = next((h for h in hits if h.key() == (file, kind, qualifier)), None)
        if hit is None:
            failures.append(
                f"  MISSING census site {file} {kind} {qualifier} "
                f"(stale allowlist — the leftover was removed or renamed)"
            )
            print(f"  ✗ {file}:{kind}:{qualifier}  (not found)")
            continue
        mark = "OK" if hit.value == canonical else "MISMATCH"
        print(f"  {mark:8} {file}:{hit.line}  {qualifier} = {hit.value}")
        if hit.value != canonical:
            failures.append(
                f"  leftover dim {hit.value} at {file}:{hit.line} {qualifier} "
                f"(canonical CONFIG dim is {canonical})"
            )

    unknown = sorted(found_keys - known_keys)
    if unknown:
        print()
        print("unknown production field-dim sites (not in the census allowlist):")
        for key in unknown:
            hit = next(h for h in hits if h.key() == key)
            print(f"  {hit.file}:{hit.line}  {hit.kind} {hit.qualifier} = {hit.value}")
            failures.append(
                f"  NEW field-dim leftover {hit.file}:{hit.line} "
                f"{hit.kind} {hit.qualifier}={hit.value} — add it to "
                f"KNOWN_SITES in this test and to docs/EXPERIMENTAL_LEVERS.md"
            )

    print()
    print("coincidental 128s (INFO, not field dim — not a failure):")
    info = coincidental_128_report(canonical)
    # Keep this short; full dump is noisy. Show a count + a few examples.
    print(f"  {len(info)} source lines contain 128 outside comments/dim sites")
    print("  typical non-width uses: max_len, window, batch_size, history rings")
    print("  see docs/EXPERIMENTAL_LEVERS.md § coincidental 128s")

    print()
    if failures:
        print(f"FAIL ({len(failures)}):")
        for f in failures:
            print(f)
        return 1
    print(f"PASS: {len(KNOWN_SITES)} field-dim sites all equal CONFIG dim={canonical}; no unknowns.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
