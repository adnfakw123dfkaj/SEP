"""REQ-INV-001 — Atomic and idempotent decision record (Part 3).

Traceable to test-cases/part3-evidence-records.md TC-P3-INV001-01..06. The
atomic-record subject (``tradingagents.records``) is not implemented yet; the
idempotent-append half is verified against the real memory log.
"""

from tests.req._support import require
from tradingagents.memory.log import TradingMemoryLog


def test_idempotent_append(tmp_path):
    """TC-P3-INV001-02: same (ticker, date) appends only one entry.

    Verified against the real memory log, whose store_decision already guards
    idempotency by (date, ticker).
    """
    log = TradingMemoryLog({"memory_log_path": str(tmp_path / "memory.md")})
    log.store_decision(ticker="NVDA", trade_date="2026-11-01", final_trade_decision="**Rating**: Buy")
    log.store_decision(ticker="NVDA", trade_date="2026-11-01", final_trade_decision="**Rating**: Buy")
    entries = [e for e in log.load_entries() if e["ticker"] == "NVDA" and e["date"] == "2026-11-01"]
    assert len(entries) == 1


def test_fault_injection():
    """TC-P3-INV001-01: interrupted write leaves no partial record."""
    require("tradingagents.records")


def test_signature_versions():
    """TC-P3-INV001-03: different signature yields independent versions."""
    require("tradingagents.records")


def test_record_hash():
    """TC-P3-INV001-04: record completeness hash verifies."""
    require("tradingagents.records")


def test_crash_between_files():
    """TC-P3-INV001-05: crash between files leaves prior record intact."""
    require("tradingagents.records")


def test_concurrent_writers():
    """TC-P3-INV001-06: one complete record wins under concurrency."""
    require("tradingagents.records")
