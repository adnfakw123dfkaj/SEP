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
import subprocess
import sys
from pathlib import Path

# Paths excluded from "changed files" for gate purposes (noise).
_IGNORED_PREFIXES = (".git/",)


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def changed_files(base: str, head: str = "HEAD") -> list[str]:
    """Files changed between the merge-base of ``base`` and ``head``, and head."""
    merge_base = _git("merge-base", base, head).strip()
    raw = _git("diff", "--name-only", merge_base, head)
    files = [line.strip() for line in raw.splitlines() if line.strip()]
    return [f for f in files if not any(f.startswith(p) for p in _IGNORED_PREFIXES)]


def first_implementation_commit(base: str, head: str = "HEAD") -> str | None:
    """ISO time of the earliest commit in the range that touches a non-test file.

    Excludes test files and docs, so "implementation" means production code. Uses
    author date in ISO-8601 UTC. Returns None if no such commit exists.
    """
    merge_base = _git("merge-base", base, head).strip()
    # Commits oldest-first with their changed files.
    log = _git("log", "--reverse", "--format=%H|%aI", f"{merge_base}..{head}")
    for line in log.splitlines():
        if "|" not in line:
            continue
        sha, iso = line.split("|", 1)
        files = [f for f in _git("show", "--name-only", "--format=", sha).splitlines() if f.strip()]
        if any(_is_implementation_file(f) for f in files):
            return iso
    return None


def _is_implementation_file(path: str) -> bool:
    if path.startswith(("tests/", "docs/", ".github/", "test-cases/")):
        return False
    return path.endswith(".py") or path.startswith("prompts/")


def load_approvals(directory: str = "docs/approvals") -> list[dict]:
    """Read every *.json/*.yaml approval record in ``directory`` (json only here)."""
    path = Path(directory)
    records: list[dict] = []
    if not path.exists():
        return records
    for file in sorted(path.glob("*.json")):
        records.append(json.loads(file.read_text(encoding="utf-8")))
    return records


def new_log_entries(log_path: str, since: str) -> list[dict]:
    """Entries added to the AI-use log since ``since`` (JSON list in the file)."""
    path = Path(log_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", []) if isinstance(data, dict) else data
    # Compare the committed version to the base version; only new ones count.
    try:
        base_text = _git("show", f"{since}:{log_path}")
        base = json.loads(base_text)
        base_entries = base.get("entries", []) if isinstance(base, dict) else base
    except (SystemExit, ValueError):
        base_entries = []
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
