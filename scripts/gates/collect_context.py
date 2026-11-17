"""Collect the inputs each gate check needs, from git and the CI environment.

The workflow runs this once, then feeds the produced JSON to ``run.py`` for the
gate(s) in scope. Keeping collection here (testable Python) rather than in YAML
keeps the workflow to orchestration.

Sub-commands:
    changed   --base <ref> [--head <ref>]   -> {"changed_files": [...]}
    first-impl-commit --base <ref> [--head <ref>]  -> {"first_implementation_commit": iso|null}
    approvals [--dir docs/approvals]        -> {"approvals": [...]}
    log-entries --path docs/ai-use-log.yaml --since <ref>  -> {"new_log_entries": [...]}
    baseline --path <json>                   -> {"baseline": {...}}  (reads a stored JSON)
    tests --path <json>                      -> {"current": {...}}  (reads pytest-json report)

All output is JSON on stdout. No network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Paths excluded from "changed files" for gate purposes (noise).
_IGNORED_PREFIXES = (".git/",)


def _git(*args: str) -> str | None:
    """Run git; return stdout, or None if the command fails (never raises).

    Gate collection must not crash CI when a ref is missing (e.g. ``master`` is
    not a local ref in a GitHub PR checkout). Callers treat None as "unknown".
    """
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout


def _ref_exists(ref: str) -> bool:
    return _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}") is not None


def _resolve_base(base: str) -> str | None:
    """Resolve a base ref to one that exists locally.

    A GitHub PR checkout often lacks a local ``master`` but has ``origin/master``
    (and ``$GITHUB_BASE_REF`` names the base branch). Try the given name, then
    ``origin/<name>``, then the CI-provided base ref and its remote form.
    """
    candidates = [base, f"origin/{base}"]
    env_base = os.environ.get("GITHUB_BASE_REF")
    if env_base:
        candidates += [env_base, f"origin/{env_base}"]
    for ref in candidates:
        if _ref_exists(ref):
            return ref
    return None


def _merge_base(base: str, head: str = "HEAD") -> str | None:
    resolved = _resolve_base(base)
    if resolved is None:
        return None
    out = _git("merge-base", resolved, head)
    return out.strip() if out else None


def changed_files(base: str, head: str = "HEAD") -> list[str]:
    """Files changed between the merge-base of ``base`` and ``head``, and head.

    If the base ref cannot be resolved, returns an empty list (the workflow is
    then run without a reliable diff; gates that need it degrade rather than
    crash).
    """
    merge_base = _merge_base(base, head)
    if merge_base is None:
        return []
    raw = _git("diff", "--name-only", merge_base, head) or ""
    files = [line.strip() for line in raw.splitlines() if line.strip()]
    return [f for f in files if not any(f.startswith(p) for p in _IGNORED_PREFIXES)]


def first_implementation_commit(base: str, head: str = "HEAD") -> str | None:
    """ISO time of the earliest commit in the range that touches a non-test file.

    Excludes test files and docs, so "implementation" means production code. Uses
    author date in ISO-8601 UTC. Returns None if no such commit exists or the
    base ref cannot be resolved.
    """
    merge_base = _merge_base(base, head)
    if merge_base is None:
        return None
    log = _git("log", "--reverse", "--format=%H|%aI", f"{merge_base}..{head}") or ""
    for line in log.splitlines():
        if "|" not in line:
            continue
        sha, iso = line.split("|", 1)
        files = [f for f in (_git("show", "--name-only", "--format=", sha) or "").splitlines() if f.strip()]
        if any(_is_implementation_file(f) for f in files):
            return iso
    return None


def _is_implementation_file(path: str) -> bool:
    if path.startswith(("tests/", "docs/", ".github/", "test-cases/")):
        return False
    return path.endswith(".py") or path.startswith("prompts/")


def load_approvals(directory: str = "docs/approvals") -> list[dict]:
    """Read every *.json / *.yaml approval record in ``directory``."""
    import yaml

    path = Path(directory)
    records: list[dict] = []
    if not path.exists():
        return records
    for file in sorted(list(path.glob("*.json")) + list(path.glob("*.yaml")) + list(path.glob("*.yml"))):
        text = file.read_text(encoding="utf-8")
        try:
            data = json.loads(text) if file.suffix == ".json" else yaml.safe_load(text)
        except (ValueError, yaml.YAMLError):
            continue
        if isinstance(data, dict):
            records.append(data)
    return records


def _load_entries_text(text: str) -> list[dict]:
    """Parse AI-use-log entries from YAML text (the file is YAML, not JSON)."""
    import yaml

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    if isinstance(data, dict):
        data = data.get("entries", [])
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, dict)]


def new_log_entries(log_path: str, since: str) -> list[dict]:
    """Entries added to the AI-use log since ``since``.

    The log is YAML (``entries:`` list). Only entries not present in the base
    revision count as new. If the base ref cannot be resolved, every current
    entry is treated as new (a code/prompt change with entries present is enough
    for G6, which does not compare against a base).
    """
    path = Path(log_path)
    if not path.exists():
        return []
    entries = _load_entries_text(path.read_text(encoding="utf-8"))

    resolved = _resolve_base(since)
    base_entries: list[dict] = []
    if resolved is not None:
        base_text = _git("show", f"{resolved}:{log_path}")
        if base_text:
            base_entries = _load_entries_text(base_text)

    base_ids = {json.dumps(e, sort_keys=True) for e in base_entries}
    return [e for e in entries if json.dumps(e, sort_keys=True) not in base_ids]


def _main(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write(__doc__ or "")
        return 2
    cmd, rest = argv[0], argv[1:]

    def opt(name: str, default: str) -> str:
        if name in rest:
            return rest[rest.index(name) + 1]
        return default

    if cmd == "changed":
        print(json.dumps({"changed_files": changed_files(opt("--base", "master"), opt("--head", "HEAD"))}))
    elif cmd == "first-impl-commit":
        print(json.dumps({"first_implementation_commit":
                          first_implementation_commit(opt("--base", "master"), opt("--head", "HEAD"))}))
    elif cmd == "approvals":
        print(json.dumps({"approvals": load_approvals(opt("--dir", "docs/approvals"))}))
    elif cmd == "log-entries":
        print(json.dumps({"new_log_entries":
                          new_log_entries(opt("--path", "docs/ai-use-log.yaml"), opt("--since", "master"))}))
    elif cmd == "baseline":
        data = json.loads(Path(opt("--path", "reports/baseline.json")).read_text(encoding="utf-8"))
        print(json.dumps({"baseline": data}))
    elif cmd == "tests":
        data = json.loads(Path(opt("--path", "reports/current.json")).read_text(encoding="utf-8"))
        print(json.dumps({"current": data}))
    elif cmd == "ownership":
        import yaml

        data = yaml.safe_load(Path(opt("--path", "test-cases/ownership.yaml")).read_text(encoding="utf-8"))
        print(json.dumps({"ownership": data}))
    elif cmd == "outcomes":
        # The normalized current outcomes produced by the regression step.
        data = json.loads(Path(opt("--path", "/tmp/current.json")).read_text(encoding="utf-8"))
        outcomes = data.get("current", data) if isinstance(data, dict) else data
        print(json.dumps({"outcomes": outcomes}))
    else:
        sys.stderr.write(f"unknown sub-command: {cmd}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
