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
