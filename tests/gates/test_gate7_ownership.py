"""G7 — ownership gate: a claimed Part's tests must not skip or fail."""

import check_ownership as g7

OWNS = {
    "parts": {
        "part1": {
            "owner": None,
            "enabled": False,
            "tests": ["tradingagents/tests/req/test_profiles.py"],
        },
        "part2": {
            "owner": "bob",
            "enabled": True,
            "tests": ["tradingagents/tests/req/test_debate_protocol.py"],
        },
    }
}

PREFIX = "tradingagents/tests/req/"
P1 = PREFIX + "test_profiles.py::test_profile_matrix"
P2 = PREFIX + "test_debate_protocol.py::test_schema_valid"


def test_unclaimed_part_may_skip():
    # Only part1 (unclaimed) has outcomes; part2 is claimed but give it a pass so
    # the "claimed with no outcomes" rule does not trip.
    outcomes = {P1: "skipped", P2: "passed"}
    result = g7.check(OWNS, outcomes)
    assert result.passed


def test_claimed_part_skip_blocks():
    outcomes = {P2: "skipped"}
    result = g7.check(OWNS, outcomes)
    assert not result.passed
    assert any("skipped" in v.reason for v in result.violations)


def test_claimed_part_passing_ok():
    outcomes = {P2: "passed"}
    result = g7.check(OWNS, outcomes)
    assert result.passed


def test_claimed_part_failure_blocks():
    outcomes = {P2: "failed"}
    result = g7.check(OWNS, outcomes)
    assert not result.passed


def test_claimed_part_error_blocks():
    outcomes = {P2: "error"}
    result = g7.check(OWNS, outcomes)
    assert not result.passed


def test_claimed_part_without_outcomes_blocks():
    result = g7.check(OWNS, {})
    assert not result.passed
    assert any("no test outcomes" in v.reason for v in result.violations)


def test_mixed_claims():
    outcomes = {P1: "skipped", P2: "passed"}
    result = g7.check(OWNS, outcomes)
    assert result.passed  # p1 unclaimed, p2 claimed and green
