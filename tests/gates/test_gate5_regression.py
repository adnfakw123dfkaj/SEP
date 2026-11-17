import check_regression as g5

BASELINE = {
    "tests/test_a.py::test_one": "passed",
    "tests/test_a.py::test_two": "passed",
    "tests/test_b.py::test_three": "passed",
}


def test_all_green_passes():
    current = dict(BASELINE)
    result = g5.check(BASELINE, current)
    assert result.passed


def test_newly_failing_prior_test_blocks():
    current = dict(BASELINE, **{"tests/test_a.py::test_one": "failed"})
    result = g5.check(BASELINE, current)
    assert not result.passed
    assert any("regression: failed" in v.reason for v in result.violations)


def test_newly_erroring_test_blocks():
    current = dict(BASELINE, **{"tests/test_b.py::test_three": "error"})
    result = g5.check(BASELINE, current)
    assert not result.passed
    assert any("regression: error" in v.reason for v in result.violations)


def test_missing_previously_passing_test_blocks_without_approval():
    current = dict(BASELINE)
    del current["tests/test_a.py::test_two"]
    result = g5.check(BASELINE, current)
    assert not result.passed
    assert any("deleted without approval" in v.reason for v in result.violations)


def test_missing_previously_passing_test_passes_with_deletion_approval():
    current = dict(BASELINE)
    del current["tests/test_a.py::test_two"]
    approvals = [{"change_id": "c1", "deletes": ["tests/test_a.py::test_two"]}]
    result = g5.check(BASELINE, current, approvals)
    assert result.passed


def test_deletion_approval_for_other_test_does_not_cover():
    current = dict(BASELINE)
    del current["tests/test_a.py::test_two"]
    approvals = [{"change_id": "c1", "deletes": ["tests/test_b.py::test_three"]}]
    result = g5.check(BASELINE, current, approvals)
    assert not result.passed
    assert any("deleted without approval" in v.reason for v in result.violations)


def test_new_passing_tests_do_not_count_as_regression():
    current = dict(BASELINE, **{"tests/test_new.py::test_x": "passed"})
    result = g5.check(BASELINE, current)
    assert result.passed


def test_already_not_passing_baseline_is_ignored():
    baseline = dict(BASELINE, **{"tests/test_c.py::test_skip": "skipped"})
    current = dict(BASELINE)
    result = g5.check(baseline, current)
    assert result.passed
