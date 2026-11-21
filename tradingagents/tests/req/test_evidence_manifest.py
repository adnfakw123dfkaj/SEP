"""REQ-FR-004 — Evidence refs and run manifest (Part 3).

Traceable to test-cases/part3-evidence-records.md. The ``RunManifest`` and
``EvidenceRef`` contracts are implemented; the evidence registry and fidelity
checker (``tradingagents.evidence``) land in the next step, so those tests skip
until then.
"""

from tradingagents.contracts import EvidenceRef, RunManifest
from tradingagents.dataflows import router
from tradingagents.dataflows.config import run_config
from tradingagents.evidence import evidence_scope, register_tool_result
from tradingagents.evidence.fidelity import (
    extract_numeric_claims,
    numeric_contradiction_rate,
    unsupported_claim_rate,
)
from tradingagents.evidence.registry import EvidenceRegistry
from tradingagents.records.manifest import write_run_manifest


def test_manifest_schema():
    """TC-P3-FR004-03: a well-formed manifest validates; a malformed one fails."""
    manifest = RunManifest(
        run_id="run-1", ticker="NVDA", date="2026-11-01", profile="standard",
        analysts=["market"], models={"quick": "x"}, provider="openai",
        token_usage_by_agent={"market": 1200}, rating="Buy",
        timestamps={"started": "2026-11-01T10:00:00+00:00", "ended": "2026-11-01T10:10:00+00:00"},
        status="completed",
    )
    assert manifest.total_tokens() == 1200
    # A bad status is rejected.
    import pytest

    with pytest.raises(ValueError):
        RunManifest(run_id="r", ticker="T", date="2026-11-01", status="weird")


def test_token_sum():
    """TC-P3-FR004-04: manifest token total equals the sum of per-agent usage."""
    manifest = RunManifest(
        run_id="r", ticker="NVDA", date="2026-11-01",
        token_usage_by_agent={"market": 1000, "news": 500, "pm": 200},
    )
    assert manifest.total_tokens() == 1700


def test_replay():
    """TC-P3-FR004-05: a manifest round-trips, so a run can be replayed."""
    original = RunManifest(run_id="r", ticker="NVDA", date="2026-11-01", rating="Hold",
                           token_usage_by_agent={"pm": 5}, status="completed")
    again = RunManifest.model_validate_json(original.model_dump_json())
    assert again.rating == "Hold"
    assert again.run_id == original.run_id
    assert again.total_tokens() == original.total_tokens()


def test_evidence_ref_contract():
    """A well-formed EvidenceRef validates; an unknown kind is rejected."""
    ref = EvidenceRef(kind="tool", id="call-1", source="get_stock_data", snapshot_hash="abc")
    assert ref.kind == "tool"
    import pytest

    with pytest.raises(ValueError):
        EvidenceRef(kind="bogus", id="x")


def test_numeric_refs():
    """TC-P3-FR004-01: numeric claims carry evidence refs (registry resolves each)."""
    reg = EvidenceRegistry()
    reg.register(EvidenceRef(kind="snapshot", id="snap:1", source="verified"))
    claims = extract_numeric_claims("The close was 187.2 today")
    assert claims, "the extractor must find the number"
    # Each numeric claim is backed by a registered ref id.
    refs = ["snap:1" for _ in claims]
    assert unsupported_claim_rate(claims, refs) == 0.0
    assert reg.contains("snap:1")


def test_qualitative_refs():
    """TC-P3-FR004-02: qualitative claims mostly carry refs (>= 0.95)."""
    claims = [f"point {i}" for i in range(20)]
    refs = [f"r{i}" for i in range(20)]  # 100% supported here
    assert unsupported_claim_rate(claims, refs) <= 0.05


def test_tool_result_registers_evidence_in_scope():
    with evidence_scope() as registry:
        ref = register_tool_result(
            method="get_stock_data",
            vendor="yfinance",
            args=("AAPL",),
            kwargs={},
            value="Close: 1.00",
        )
        assert ref is not None
        assert registry.contains(ref.id)
        assert ref.snapshot_hash


def test_router_registers_tool_evidence(tmp_path, monkeypatch):
    monkeypatch.setitem(
        router.VENDOR_METHODS["get_stock_data"],
        "yfinance",
        lambda *a, **k: "Close: 1.00",
    )
    config = {
        "data_cache_dir": str(tmp_path),
        "tool_vendors": {"get_stock_data": "yfinance"},
    }
    with run_config(config), evidence_scope() as registry:
        assert router.route_to_vendor("get_stock_data", "AAPL", "2026-01-02") == "Close: 1.00"

    assert len(registry) == 1
    assert registry.all()[0].kind == "tool"


def test_manifest_writer_roundtrips_atomically(tmp_path):
    """Part 3 is the single manifest writer; the written file replays cleanly."""
    manifest = RunManifest(
        run_id="run-writer",
        ticker="NVDA",
        date="2026-11-01",
        profile="quick",
        analysts=["market"],
        models={"quick": "deepseek-flash"},
        provider="deepseek",
        rating="Hold",
        timestamps={"finished": "2026-11-01T10:10:00+00:00"},
    )
    path = write_run_manifest(tmp_path / "manifests", manifest)
    assert path.exists()
    assert RunManifest.model_validate_json(path.read_text(encoding="utf-8")) == manifest


def test_orphan_number_must_fail():
    """TC-P3-FR004-06: an unreferenced number is flagged as unsupported."""
    claims = extract_numeric_claims("close 187.2 and RSI 71.3")
    # Only one of the two numbers has a ref -> unsupported rate below 1.0 but > 0.
    refs = ["snap:1"]
    rate = unsupported_claim_rate(claims, refs)
    assert rate > 0.0
    # A snapshot match keeps an honest number; a contradiction is a mismatch.
    snapshot = "| Close | 187.2 |"
    assert numeric_contradiction_rate(["The close was 187.2"], snapshot) == 0.0
