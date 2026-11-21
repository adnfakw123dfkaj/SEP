"""Composite quality floor for routed and acceptance runs.

The cost gate must not be able to buy savings by silently degrading Part 2's
debate, Part 3's report evidence, or Part 5's output validation.  Each component
is evaluated deterministically from the final run state; the result is persisted
with the run so an audit can see exactly which part failed.
"""

from __future__ import annotations

from typing import Any

from tradingagents.agents.debate.quality import score_debate
from tradingagents.evidence.claims import (
    claim_evidence_metrics,
    numeric_claim_contradiction,
)
from tradingagents.evidence.fidelity import citation_support_rate, report_schema_valid

DEBATE_EVIDENCE_RATE = 1.0
DEBATE_REBUTTAL_COVERAGE = 0.90
DEBATE_UNSUPPORTED_RATE = 0.05
DEBATE_DUPLICATE_RATE = 0.10
CITATION_SUPPORT_RATE = 0.95
NUMERIC_CLAIM_EVIDENCE_RATE = 1.0
QUALITATIVE_CLAIM_EVIDENCE_RATE = 0.95
CLAIM_UNSUPPORTED_RATE = 0.05
NUMERIC_CONTRADICTION_RATE = 0.02


def evaluate_quality_floor(final_state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the nested Part 2 + Part 3 + Part 5 quality floor."""
    failures: list[str] = []
    components: dict[str, Any] = {}

    metrics = score_debate(final_state.get("debate_transcript") or {})
    components["debate_quality_available"] = metrics.quality_available
    components["turns_with_evidence_or_no_new_evidence_rate"] = (
        metrics.turns_with_evidence_or_no_new_evidence_rate
    )
    components["rebuttal_coverage"] = metrics.rebuttal_coverage
    components["unsupported_claim_rate"] = metrics.unsupported_claim_rate
    components["duplicate_claim_rate"] = metrics.duplicate_claim_rate
    if not metrics.quality_available:
        failures.append("debate_quality_unavailable")
    else:
        if metrics.turns_with_evidence_or_no_new_evidence_rate != DEBATE_EVIDENCE_RATE:
            failures.append("debate_evidence_coverage")
        if metrics.rebuttal_coverage is None or metrics.rebuttal_coverage < DEBATE_REBUTTAL_COVERAGE:
            failures.append("debate_rebuttal_coverage")
        if metrics.unsupported_claim_rate is None or metrics.unsupported_claim_rate > DEBATE_UNSUPPORTED_RATE:
            failures.append("debate_unsupported_claim_rate")
        if metrics.duplicate_claim_rate is None or metrics.duplicate_claim_rate > DEBATE_DUPLICATE_RATE:
            failures.append("debate_duplicate_claim_rate")

    report_text = final_state.get("final_trade_decision") or ""
    schema_valid = report_schema_valid(report_text)
    refs = list(final_state.get("evidence_refs") or [])
    known_ids = {
        str(ref.get("id"))
        for ref in (final_state.get("evidence") or [])
        if ref.get("id")
    }
    citation_rate = citation_support_rate(refs, known_ids)
    components["report_schema_valid"] = schema_valid
    components["evidence_refs"] = len(refs)
    components["citation_support_rate"] = citation_rate
    if not schema_valid:
        failures.append("report_schema_invalid")
    if not refs or not known_ids:
        failures.append("report_evidence_missing")
    if citation_rate < CITATION_SUPPORT_RATE:
        failures.append("report_citation_support")

    claim_metrics = claim_evidence_metrics(final_state.get("report_claims") or [])
    components.update(claim_metrics)
    if claim_metrics["claim_count"] == 0:
        failures.append("report_claims_missing")
    if claim_metrics["numeric_claim_evidence_rate"] < NUMERIC_CLAIM_EVIDENCE_RATE:
        failures.append("report_numeric_claim_evidence")
    if claim_metrics["qualitative_claim_evidence_rate"] < QUALITATIVE_CLAIM_EVIDENCE_RATE:
        failures.append("report_qualitative_claim_evidence")
    if claim_metrics["claim_unsupported_rate"] > CLAIM_UNSUPPORTED_RATE:
        failures.append("report_claim_unsupported_rate")

    contradiction = numeric_claim_contradiction(
        final_state.get("report_claims") or [],
        final_state.get("verified_snapshot") or "",
        sections={"decision"},
    )
    components["numeric_contradiction_checked"] = contradiction["checked"]
    components["numeric_contradiction_rate"] = contradiction["rate"]
    components["numeric_contradiction_details"] = contradiction["details"]
    if contradiction["checked"] == 0:
        failures.append("report_numeric_claims_unchecked")
    elif contradiction["rate"] > NUMERIC_CONTRADICTION_RATE:
        failures.append("report_numeric_contradiction")

    validation = final_state.get("output_validation") or {}
    authority = final_state.get("rating_authority") or {}
    output_ok = bool(validation.get("ok"))
    authority_ok = bool(authority) and not bool(authority.get("review_required", True))
    components["output_validation_ok"] = output_ok
    components["rating_authority_ok"] = authority_ok
    if not output_ok:
        failures.append("output_validation")
    if not authority_ok:
        failures.append("rating_authority")

    return {
        "passed": not failures,
        "failures": failures,
        "components": components,
    }


__all__ = ["evaluate_quality_floor"]
