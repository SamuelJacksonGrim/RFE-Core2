"""
tests/diagnostic/integrity/ignition_isolation_probe.py    (spec: v0.2)

Build-A probe for the λ ignition channel (`ignition/`). Two things to prove:
  1. ISOLATION (the load-bearing law) — the ignition channel cannot reach the
     governance gate, the loop, or the field. Checked three ways:
       (a) AST import audit of ignition/__init__.py — no forbidden imports, no
           arbitrate/inject references in code (AST excludes the docstring prose);
       (b) a clean-room sys.modules check in a SUBPROCESS that imports only
           `ignition` and asserts the gate/loop/field modules — and any agents.* —
           are NOT pulled into the import graph;
       (c) ignite()'s signature exposes no field/governance/cycle handle.
     Routing λ through the gate consolidates the lock (4fe31e9); here it is
     unconstructable, not merely discouraged.
  2. FUNCTION — igniting a bare generator (no field, no gate in scope) writes its
     weights, leaves it in eval mode, and reports its diversity (eff_rank).

PRE-DECLARED SIGNATURES:
  SUCCESS: zero forbidden imports / code refs; importing `ignition` pulls no
    gate/loop/field/agents module; ignite() signature is clean; igniting a bare
    generator changes its weights and sets eval mode.
  FAILURE: any forbidden import/ref; `import ignition` pulls a gate/loop/field
    module; signature exposes a gate/field handle; weights unchanged.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
import ast
import inspect
import subprocess
import sys

sys.path.insert(0, ".")

FORBIDDEN_MODULES = ("selfhood_governance", "resonance_field",
                     "autonomous_cycle", "recursion1188")
FORBIDDEN_SYMS    = {"arbitrate", "inject"}


def _ast_audit(path: str):
    tree = ast.parse(open(path).read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imported.add(n.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    bad_imports = sorted(m for m in imported if any(f in m for f in FORBIDDEN_MODULES))
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_SYMS:
            used.add(node.attr)
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_SYMS:
            used.add(node.id)
    return bad_imports, sorted(used)


def _clean_room_import():
    """Import ONLY `ignition` in a fresh interpreter; report what it pulled."""
    code = (
        "import sys, ignition;"
        "bad=[m for m in ('agents.selfhood_governance','loop.autonomous_cycle',"
        "'substrate.resonance_field') if m in sys.modules];"
        "ag=[k for k in sys.modules if k.startswith('agents')];"
        "print(repr(bad)); print(repr(ag))"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=".")
    lines = r.stdout.strip().splitlines()
    forbidden = eval(lines[0]) if lines else ["<subprocess error>"]
    agents_pulled = eval(lines[1]) if len(lines) > 1 else ["?"]
    return forbidden, agents_pulled, r.stderr.strip()


def main() -> int:
    print("=" * 78)
    print("  λ IGNITION CHANNEL (Build A) — isolation + function   spec: v0.2")
    print("=" * 78)

    bad_imports, used_syms = _ast_audit("ignition/__init__.py")
    forbidden, agents_pulled, err = _clean_room_import()
    transitive_ok = (not forbidden) and (not agents_pulled)

    import ignition
    params = list(inspect.signature(ignition.ignite).parameters)
    sig_ok = not any(p in params for p in ("field", "governance", "cycle", "gate"))

    # function — ignite a bare generator (the gate/field do not exist in this scope)
    from agents.generator import Generator
    g = Generator(vocab_size=4096, dim=64, depth=3, heads=4)
    p0 = next(g.parameters()).detach().clone()
    rep = ignition.ignite(g, epochs=2, seed=7)
    weights_changed = not bool((p0 == next(g.parameters()).detach()).all())
    eval_set = (g.training is False)

    print(f"  forbidden imports (AST):        {bad_imports or 'none'}   -> {'OK' if not bad_imports else 'FAIL'}")
    print(f"  arbitrate/inject in code (AST): {used_syms or 'none'}     -> {'OK' if not used_syms else 'FAIL'}")
    print(f"  clean-room import ignition:     gate/loop/field={forbidden or 'none'}  agents.*={agents_pulled or 'none'}")
    print(f"                                                            -> {'OK' if transitive_ok else 'FAIL'}")
    if err:
        print(f"    (subprocess stderr: {err[-200:]})")
    print(f"  ignite() signature clean:       {params}  -> {'OK' if sig_ok else 'FAIL'}")
    print(f"\n  ignite report: {rep.as_dict()}")
    print(f"  weights changed: {'OK' if weights_changed else 'FAIL'}   eval mode set: {'OK' if eval_set else 'FAIL'}")
    print(f"  eff_rank (generic probe): {rep.eff_rank_before:.2f} -> {rep.eff_rank_after:.2f}  "
          f"(Δ {rep.delta_eff_rank:+.2f}; direction is probe-dependent — diagnostic only, not a gate)")

    verdict = (not bad_imports and not used_syms and transitive_ok and sig_ok
               and weights_changed and eval_set)
    print("\n" + "-" * 78)
    print(f"  VERDICT: {'PASS — λ writes the generator only; the gate is unreachable.' if verdict else 'HOLD — see FAIL above.'}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
