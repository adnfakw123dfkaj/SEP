"""Tests for the lightweight safety-path checks (Gate 2 heavy checks)."""

import run_static_checks as sc


def test_run_all_returns_all_checks():
    results = sc.run_all()
    assert set(results) == {"contract", "security", "api_surface", "permission", "dependencies"}


def test_dependencies_passes_when_package_imports():
    import importlib

    try:
        importlib.import_module("tradingagents")
    except Exception:
        import pytest

        pytest.skip("tradingagents not installed in this environment")
    assert sc.check_dependencies() is True


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


def test_permission_passes_when_no_protected_change(monkeypatch):
    monkeypatch.setenv("CHANGED_FILES", "tradingagents/agents/x.py")
    assert sc.check_permission() is True


def test_permission_fails_on_protected_change_without_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "REPO", tmp_path)
    monkeypatch.setenv("CHANGED_FILES", "scripts/gates/run.py")
    # no docs/approvals dir -> fail
    assert sc.check_permission() is False


def test_api_surface_passes_without_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "REPO", tmp_path)
    assert sc.check_api_surface() is True
