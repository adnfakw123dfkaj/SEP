"""Tests for the lightweight safety-path checks (Gate 2 heavy checks)."""

import run_static_checks as sc


def test_run_all_returns_all_checks():
    results = sc.run_all()
    assert set(results) == {"contract", "security", "api_surface", "permission", "dependencies"}


def test_dependencies_passes_when_package_is_present():
    # The check inspects the package on disk (tradingagents/tradingagents/__init__.py
    # declaring __version__), so it is independent of import path/cache state.
    assert sc.check_dependencies() is True


def test_dependencies_fails_when_package_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "REPO", tmp_path)
    assert sc.check_dependencies() is False


def test_contract_passes_without_contract_modules():
    # No tradingagents/contracts package yet -> nothing to violate.
    assert sc.check_contract() is True


def test_security_no_secret_in_repo():
    assert sc.check_security() is True


def test_security_detects_a_secret(tmp_path, monkeypatch):
    # Point REPO at a temp tree containing a secret-like string.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.py").write_text('KEY = "sk-' + "a" * 24 + '"', encoding="utf-8")
    monkeypatch.setattr(sc, "REPO", tmp_path)
    monkeypatch.setattr(sc, "_tracked_files", lambda: [tmp_path / "src" / "x.py"])
    assert sc.check_security() is False


def test_permission_passes_on_clean_workflows():
    # The repo's workflows use least privilege.
    assert sc.check_permission() is True


def test_permission_fails_when_a_workflow_grants_write(tmp_path, monkeypatch):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "bad.yml").write_text("name: x\npermissions:\n  contents: write\n", encoding="utf-8")
    monkeypatch.setattr(sc, "REPO", tmp_path)
    assert sc.check_permission() is False


def test_api_surface_passes_without_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "REPO", tmp_path)
    assert sc.check_api_surface() is True
