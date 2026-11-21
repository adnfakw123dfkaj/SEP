import check_test_approval as g1
import pytest

IMPL = "2026-11-01T10:00:00+00:00"
EARLIER = "2026-11-01T09:00:00+00:00"


def _approval(tests, approved_at=EARLIER, change_id="chg-1"):
    return {"change_id": change_id, "tests": tests, "approved_by": "alice", "approved_at": approved_at}


def test_approved_before_implementation_passes():
    result = g1.check(["src/app/x.py", "tests/test_x.py"], [_approval(["tests/test_x.py"])], IMPL)
    assert result.passed and result.applicable


def test_missing_approval_blocks():
    result = g1.check(["src/app/x.py", "tests/test_x.py"], [], IMPL)
    assert not result.passed
    assert any("missing approval" in v.reason for v in result.violations)


def test_approval_after_implementation_blocks():
    result = g1.check(
        ["src/app/x.py", "tests/test_x.py"],
        [_approval(["tests/test_x.py"], approved_at="2026-11-01T11:00:00+00:00")],
        IMPL,
    )
    assert not result.passed
    assert any("after implementation" in v.reason for v in result.violations)


def test_approval_not_covering_changed_tests_blocks():
    result = g1.check(
        ["src/app/x.py", "tests/test_x.py", "tests/test_y.py"],
        [_approval(["tests/test_x.py"])],
        IMPL,
    )
    assert not result.passed
    assert any("does not cover" in v.reason for v in result.violations)


def test_tests_only_change_not_applicable():
    result = g1.check(["tests/test_x.py"], [], None)
    assert result.applicable is False
    assert result.status == "skipped"


def test_code_change_without_impl_time_fails_closed():
    result = g1.check(["src/app/x.py"], [_approval(["tests/test_x.py"])], None)
    assert not result.passed
    assert any("implementation time" in v.reason for v in result.violations)


@pytest.mark.parametrize("path,expected", [
    ("tests/test_x.py", True),
    ("tradingagents/tests/test_a.py", True),
    ("src/app/x.py", False),
    ("docs/readme.md", False),
])
def test_is_test_path(path, expected):
    assert g1.is_test_path(path) is expected


def test_docs_and_data_files_are_not_code():
    assert g1.is_code_path("docs/ai-use-log.yaml") is False
    assert g1.is_code_path("docs/req/regression-baseline.json") is False
    assert g1.is_code_path("test-cases/gates.md") is False
    assert g1.is_code_path("scripts/gates/check_regression.py") is True
    assert g1.is_code_path("tradingagents/tradingagents/agents/rating.py") is True
    assert g1.is_code_path("tests/gates/test_x.py") is False


def test_docs_only_change_not_applicable():
    result = g1.check(["docs/ai-use-log.yaml", "docs/req/x.json"], [], None)
    assert result.applicable is False
    assert result.status == "skipped"


def test_gate_infrastructure_only_change_not_applicable():
    # Changes only to the gate's own scripts/tests are maintenance, not app
    # behaviour: G1 does not apply even without an approval.
    result = g1.check(
        ["scripts/gates/check_regression.py", "tests/gates/test_gate5_regression.py"],
        [],
        "2026-11-17T10:00:00+00:00",
    )
    assert result.applicable is False
    assert result.status == "skipped"


def test_app_code_plus_gate_infra_still_requires_approval():
    result = g1.check(
        ["tradingagents/tradingagents/agents/rating.py", "scripts/gates/run.py"],
        [],
        "2026-11-17T10:00:00+00:00",
    )
    assert result.applicable is True
    assert not result.passed


def test_gate_infrastructure_test_does_not_need_approval():
    # App code changed (needs approval) plus a gate-infra test (tests/gates/).
    # The approval must cover the app tests but NOT the gate-infra test.
    impl = "2026-11-18T16:00:00+08:00"
    approval = {"change_id": "c", "tests": ["tradingagents/tests/req/test_x.py"],
                "approved_by": "a", "approved_at": "2026-11-18T15:00:00+08:00"}
    result = g1.check(
        ["tradingagents/tradingagents/x.py",
         "tests/gates/test_static_checks.py",
         "tradingagents/tests/req/test_x.py"],
        [approval], impl,
    )
    assert result.passed


def test_valid_approval_ignores_earlier_non_covering_approvals():
    unrelated = _approval(["tests/other.py"], change_id="unrelated")
    valid = _approval(["tests/test_x.py"], change_id="valid")
    result = g1.check(
        ["src/app/x.py", "tests/test_x.py"],
        [unrelated, valid],
        IMPL,
    )
    assert result.passed


def test_app_test_not_covered_still_blocks():
    impl = "2026-11-18T16:00:00+08:00"
    approval = {"change_id": "c", "tests": [], "approved_by": "a",
                "approved_at": "2026-11-18T15:00:00+08:00"}
    result = g1.check(
        ["tradingagents/tradingagents/x.py", "tradingagents/tests/req/test_x.py"],
        [approval], impl,
    )
    assert not result.passed
