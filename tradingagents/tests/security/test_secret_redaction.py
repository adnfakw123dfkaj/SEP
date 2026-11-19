"""REQ-INV-004 — No secret leakage (Part 5).

Traceable to test-cases/part5-security-rating.md. The redaction subject
(``tradingagents.security.redaction``) is not implemented yet, but the existing
``dataflows.net.get_scrubbed`` already scrubs keys from HTTP errors and is tested
for real here.
"""

import requests

from tests.req._support import require


def test_existing_scrub_redacts_secret(monkeypatch):
    """A vendor HTTP error has its query key replaced with ***."""
    def boom(*args, **kwargs):
        raise requests.ConnectionError("failed for https://x?key=SECRET123")

    monkeypatch.setattr(requests, "get", boom)
    from tradingagents.dataflows.net import get_scrubbed

    try:
        get_scrubbed("https://x", params={}, timeout=1, secret="SECRET123")
    except requests.ConnectionError as exc:
        assert "SECRET123" not in str(exc)
        assert "***" in str(exc)
    else:
        raise AssertionError("expected ConnectionError")


def test_artifacts():
    """TC-P5-INV004-01: no secrets in logs/reports/manifest."""
    require("tradingagents.security.redaction")


def test_redaction():
    """TC-P5-INV004-02: synthetic secrets fully redacted."""
    require("tradingagents.security.redaction")


def test_prompt_payload():
    """TC-P5-INV004-04: no secrets in the model payload."""
    require("tradingagents.security.redaction")
