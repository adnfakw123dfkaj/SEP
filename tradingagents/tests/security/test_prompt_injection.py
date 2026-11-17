"""REQ-SEC-001 — Untrusted input/output security (Part 5).

Traceable to test-cases/part5-security-rating.md. The security subject
(``tradingagents.security``: sanitize/validate_output/security_log + tool guard)
is not implemented yet; these skip until it lands.
"""

import pytest

from tests.req._support import require


def test_no_unauthorized_tool_calls():
    """TC-P5-SEC001-04: no unauthorised tool calls."""
    require("tradingagents.security")


def test_log_coverage():
    """TC-P5-SEC001-05: security event log coverage."""
    require("tradingagents.security")


def test_output_validation():
    """TC-P5-SEC001-06: out-of-schema output never becomes state."""
    require("tradingagents.security")


@pytest.mark.integration
def test_injection_block_rate():
    """TC-P5-SEC001-01: injection block/drop rate >= 0.99 (script)."""
    require("tradingagents.security")


@pytest.mark.integration
def test_benign_false_positive_rate():
    """TC-P5-SEC001-02: benign false-positive rate <= 0.05 (script)."""
    require("tradingagents.security")
