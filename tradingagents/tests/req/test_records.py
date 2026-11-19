"""REQ-INV-001 — Atomic and idempotent decision record (Part 3).

Traceable to test-cases/part3-evidence-records.md TC-P3-INV001-01..06. The
idempotent-append half is verified against the real memory log; the atomic /
versioned / hash halves against ``tradingagents.records``.
"""

import json
import threading

from tradingagents.memory.log import TradingMemoryLog
from tradingagents.records.atomic import record_hash, verify_record, write_record
from tradingagents.records.idempotency import IdempotentStore, record_id


def test_idempotent_append(tmp_path):
    """TC-P3-INV001-02: same (ticker, date) appends only one memory entry."""
    log = TradingMemoryLog({"memory_log_path": str(tmp_path / "memory.md")})
    log.store_decision(ticker="NVDA", trade_date="2026-11-01", final_trade_decision="**Rating**: Buy")
    log.store_decision(ticker="NVDA", trade_date="2026-11-01", final_trade_decision="**Rating**: Buy")
    entries = [e for e in log.load_entries() if e["ticker"] == "NVDA" and e["date"] == "2026-11-01"]
    assert len(entries) == 1


def test_atomic_write_is_complete(tmp_path):
    """TC-P3-INV001-01: a written record is complete and hash-verifiable."""
    target = tmp_path / "rec"
    files = {"manifest.json": json.dumps({"run_id": "r1", "status": "completed"}),
             "reports/complete_report.md": "# Report\nok"}
    digest = write_record(target, files)
    assert digest == verify_record(target)
    assert (target / "manifest.json").read_text(encoding="utf-8") == files["manifest.json"]
    assert (target / "reports" / "complete_report.md").read_text(encoding="utf-8").startswith("# Report")


def test_failed_write_leaves_prior_record_intact(tmp_path):
    """TC-P3-INV001-05: a crash mid-staging keeps the previous record whole."""
    target = tmp_path / "rec"
    write_record(target, {"manifest.json": "v1"})
    good_hash = verify_record(target)

    # Content whose value cannot be encoded to text triggers failure mid-write.
    class Boom:
        def __str__(self):
            raise RuntimeError("boom")

    try:
        write_record(target, {"manifest.json": "v2", "other.txt": Boom()})
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected the write to fail")
    # The previous complete record survives, unchanged.
    assert verify_record(target) == good_hash
    assert (target / "manifest.json").read_text(encoding="utf-8") == "v1"


def test_idempotent_store_skips_duplicate_key(tmp_path):
    """TC-P3-INV001-02: storing the same key twice writes once."""
    store = IdempotentStore(tmp_path)
    rid1, written1 = store.store("NVDA", "2026-11-01", "sig-a", {"manifest.json": "v1"})
    rid2, written2 = store.store("NVDA", "2026-11-01", "sig-a", {"manifest.json": "v2"})
    assert rid1 == rid2
    assert written1 is True and written2 is False
    # The first version is kept, not overwritten.
    assert (tmp_path / rid1 / "manifest.json").read_text(encoding="utf-8") == "v1"


def test_different_signature_is_distinct_version(tmp_path):
    """TC-P3-INV001-03: a different signature yields an independent record."""
    store = IdempotentStore(tmp_path)
    rid_a, _ = store.store("NVDA", "2026-11-01", "sig-a", {"manifest.json": "a"})
    rid_b, _ = store.store("NVDA", "2026-11-01", "sig-b", {"manifest.json": "b"})
    assert rid_a != rid_b
    assert store.contains(rid_a) and store.contains(rid_b)
    # "latest decision" projection is a single deterministic id.
    assert store.latest_for("NVDA", "2026-11-01") in (rid_a, rid_b)


def test_record_hash_detects_tampering(tmp_path):
    """TC-P3-INV001-04: altering a byte changes the completeness hash."""
    target = tmp_path / "rec"
    write_record(target, {"manifest.json": "v1", "reports/x.md": "body"})
    before = verify_record(target)
    (target / "manifest.json").write_text("tampered", encoding="utf-8")
    assert verify_record(target) != before
    assert record_hash({"manifest.json": "v1", "reports/x.md": "body"}) == before


def test_concurrent_writers_one_wins(tmp_path):
    """TC-P3-INV001-06: concurrent same-key writers produce one record."""
    store = IdempotentStore(tmp_path)
    results: list[bool] = []

    def worker():
        _rid, written = store.store("NVDA", "2026-11-01", "sig", {"manifest.json": "x"})
        results.append(written)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1  # exactly one write won
    assert len(list(tmp_path.glob("*/manifest.json"))) == 1


def test_record_id_is_stable():
    assert record_id("NVDA", "2026-11-01", "s") == record_id("nvda", "2026-11-01", "s")
    assert record_id("NVDA", "2026-11-01", "a") != record_id("NVDA", "2026-11-01", "b")
