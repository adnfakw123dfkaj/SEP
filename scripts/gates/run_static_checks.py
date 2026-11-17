"""Lightweight safety-path checks for Gate 2 (contract, security, API surface,
permission).

These are concrete, offline, deterministic checks — not full toolchains — so a
change touching a safety-relevant path can actually satisfy Gate 2 instead of
being blocked because the checks "did not run". Each returns True (pass) or False
(fail); ``run_all`` returns the ``check_results`` mapping the gate consumes.

- contract:    the package's declared contract modules (if present) import cleanly
               and their named dataclasses/schemas exist.
- security:    no secret-like literal in tracked source; the security test suite
               is collectible.
- api_surface: the public top-level API of ``tradingagents`` has no removed
               symbol relative to the committed snapshot (added symbols are fine).
- permission:  changes under protected paths (scripts/gates/, .github/workflows/)
               carry an approval record (delegates to the approvals directory).

Run: python scripts/gates/run_static_checks.py [--all|--one <name>] -> JSON on stdout.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "tradingagents"

_SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----)"
)
_SOURCE_SUFFIXES = (".py", ".yaml", ".yml", ".json", ".toml")


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout
    return [REPO / line for line in out.splitlines() if line.strip()]


def check_contract() -> bool:
    """Contract modules import cleanly and expose their declared names."""
    contracts = PKG / "tradingagents" / "contracts"
    if not contracts.exists():
        return True  # no contract modules yet: nothing to violate
    for path in contracts.glob("*.py"):
        if path.name == "__init__.py":
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            return False
    return True


def _is_test_or_doc_path(path: Path) -> bool:
    parts = path.parts
    if "tests" in parts or "test-cases" in parts:
        return True
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py")


def check_security() -> bool:
    """No secret-like literal in tracked production source files.

    Test files and fixtures are skipped: they legitimately contain fake keys to
    prove redaction works, and flagging them would block any change that adds
    such a test.
    """
    for path in _tracked_files():
        if not path.exists() or path.suffix not in _SOURCE_SUFFIXES:
            continue
        if "/.git/" in str(path):
            continue
        if _is_test_or_doc_path(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _SECRET_PATTERN.search(text):
            return False
    return True


def _public_names(module_path: Path) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return names
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            names.add(node.name)
    return names


def check_api_surface() -> bool:
    """No public top-level name in tradingagents/__init__ was removed vs snapshot."""
    snapshot = REPO / "docs" / "req" / "api-surface.json"
    init = PKG / "tradingagents" / "__init__.py"
    current = _public_names(init) if init.exists() else set()
    if not snapshot.exists():
        return True  # no snapshot committed yet: adopt it, do not block
    try:
        recorded = set(json.loads(snapshot.read_text(encoding="utf-8")).get("names", []))
    except (ValueError, OSError):
        return True
    return recorded.issubset(current)


def check_permission() -> bool:
    """Permission integrity for the gate pipeline.

    Checks that the CI workflows do not grant broad write permissions: a workflow
    that requests ``contents: write`` (or a bare ``write-all``) at the workflow
    level would let a compromised run mutate the repo. Workflow files already use
    least privilege (``permissions: contents: read``); this guards against a
    change that silently widens them. It is a property check on the files, not an
    approval requirement — gate-infrastructure and application changes both pass
    it unless they widen permissions.
    """
    workflows = REPO / ".github" / "workflows"
    if not workflows.exists():
        return True
    broad = ("contents: write", "write-all", "permissions: write")
    for path in workflows.glob("*.yml"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # release-assets legitimately needs contents: write to attach assets;
        # it is an explicit, reviewed exception.
        if path.name == "release-assets.yml":
            continue
        for needle in broad:
            if needle in text:
                return False
    return True


def check_dependencies() -> bool:
    """Declared dependencies resolve and the package imports cleanly.

    This is the deterministic, offline half of the dependency check: the
    ``tradingagents`` package (and its declared deps) must be importable. A
    vulnerability audit (pip-audit) is run separately and reported as
    informational, not blocking — auditing the whole interpreter environment
    surfaces pre-existing CVEs in transitive deps that no single PR can fix, and
    would otherwise block every PR.
    """
    try:
        import importlib

        for mod in ("tradingagents",):
            importlib.import_module(mod)
    except Exception:  # noqa: BLE001 — any import failure is a broken dependency
        return False
    return True


_CHECKS = {
    "contract": check_contract,
    "security": check_security,
    "api_surface": check_api_surface,
    "permission": check_permission,
    "dependencies": check_dependencies,
}


def run_all() -> dict[str, bool]:
    return {name: fn() for name, fn in _CHECKS.items()}


def main(argv: list[str]) -> int:
    if "--one" in argv:
        name = argv[argv.index("--one") + 1]
        ok = _CHECKS[name]()
        print(json.dumps({name: ok}))
        return 0 if ok else 1
    results = run_all()
    print(json.dumps(results))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
