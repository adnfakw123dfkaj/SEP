import check_static_analysis as g2
import pytest

ALL_OK = {
    "lint": True, "type_check": True, "dependencies": True,
    "contract": True, "security": True, "api_surface": True, "permission": True,
}
ALWAYS_ON = {"lint": True, "type_check": True, "dependencies": True}


def test_required_checks_for_safety_path():
    checks = g2.required_checks(["tradingagents/agents/market_analyst.py"])
    assert set(checks) == set(ALL_OK)


def test_required_checks_for_non_safety_change():
    checks = g2.required_checks(["README.md"])
    assert set(checks) == {"lint", "type_check", "dependencies"}


@pytest.mark.parametrize("failing", ["lint", "type_check", "dependencies"])
def test_always_on_failure_blocks(failing):
    results = dict(ALWAYS_ON)
    results[failing] = False
    result = g2.check(["README.md"], results)
    assert not result.passed
    assert any(failing in v.reason for v in result.violations)


def test_safety_path_with_heavy_check_pass():
    result = g2.check(["tradingagents/security/sanitize.py"], ALL_OK)
    assert result.passed


def test_required_heavy_check_missing_blocks():
    # Safety path changed but contract/etc not reported -> "not run" is a failure.
    result = g2.check(["tradingagents/agents/x.py"], dict(ALWAYS_ON))
    assert not result.passed
    assert any("not run" in v.reason for v in result.violations)


def test_non_safety_skips_heavy_checks():
    # A non-safety change with only always-on results is fine even without heavy.
    result = g2.check(["README.md"], dict(ALWAYS_ON))
    assert result.passed
