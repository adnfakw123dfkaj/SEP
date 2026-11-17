"""Tests for collect_context.py — base-ref resilience and YAML log parsing.

These cover the remote-only failure modes: a GitHub PR checkout lacks a local
``master`` ref (must not crash), and the AI-use log is YAML (must not be parsed
as JSON).
"""

import sys
from pathlib import Path

GATES = Path(__file__).resolve().parents[2] / "scripts" / "gates"
sys.path.insert(0, str(GATES))

import collect_context as cc  # noqa: E402


def test_missing_base_does_not_crash_changed():
    # A bogus base resolves to None; changed_files returns [] instead of raising.
    assert cc.changed_files("definitely-not-a-ref") == []


def test_missing_base_first_impl_commit_is_none():
    assert cc.first_implementation_commit("definitely-not-a-ref") is None


def test_resolve_base_prefers_existing():
    # HEAD always exists; _resolve_base should find some candidate.
    resolved = cc._resolve_base("definitely-not-a-ref")
    assert resolved is None or isinstance(resolved, str)


def test_log_entries_parses_yaml(tmp_path):
    log = tmp_path / "ai-use-log.yaml"
    log.write_text(
        "entries:\n  - change_id: c1\n    summary: s\n  - change_id: c2\n",
        encoding="utf-8",
    )
    entries = cc.new_log_entries(str(log), "definitely-not-a-ref")
    # No resolvable base -> every current entry counts as new.
    assert [e["change_id"] for e in entries] == ["c1", "c2"]


def test_load_entries_text_handles_bare_list():
    assert cc._load_entries_text("- change_id: x\n") == [{"change_id": "x"}]


def test_load_entries_text_handles_garbage():
    assert cc._load_entries_text("::: not yaml :::\n\t") == []


def test_load_approvals_reads_json_and_yaml(tmp_path):
    (tmp_path / "a.json").write_text('{"change_id":"a"}', encoding="utf-8")
    (tmp_path / "b.yaml").write_text("change_id: b\n", encoding="utf-8")
    records = cc.load_approvals(str(tmp_path))
    ids = sorted(r["change_id"] for r in records)
    assert ids == ["a", "b"]


def test_collect_context_works_without_pyyaml(monkeypatch):
    # Simulate a CI job that forgot to install pyyaml: parsing must not crash.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "yaml" or name.startswith("yaml."):
            raise ModuleNotFoundError("No module named 'yaml'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    # approvals (no files) and log entries must both parse without raising.
    assert isinstance(cc.load_approvals("docs/approvals"), list)
    entries = cc.new_log_entries("docs/ai-use-log.yaml", "doesnotexist")
    assert isinstance(entries, list)
    assert entries  # the committed log has entries


def test_mini_yaml_counts_entries_and_nested_lists():
    text = (
        "entries:\n"
        "  - change_id: a\n"
        "    files_changed:\n"
        "      - x.py\n"
        "      - y.py\n"
        "  - change_id: b\n"
    )
    data = cc._mini_yaml(text)
    assert [e["change_id"] for e in data["entries"]] == ["a", "b"]
    assert data["entries"][0]["files_changed"] == ["x.py", "y.py"]
