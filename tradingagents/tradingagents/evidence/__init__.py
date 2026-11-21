"""Evidence chain: reference registry and report fidelity checks (Part 3)."""

from tradingagents.evidence.context import (
    current_evidence_registry,
    evidence_scope,
    register_tool_result,
)
from tradingagents.evidence.fidelity import (
    NumericClaim,
    citation_support_rate,
    extract_numeric_claims,
    numeric_claim_recall,
    numeric_contradiction_rate,
    report_schema_valid,
    unsupported_claim_rate,
)
from tradingagents.evidence.registry import EvidenceRegistry

__all__ = [
    "EvidenceRegistry",
    "NumericClaim",
    "citation_support_rate",
    "current_evidence_registry",
    "evidence_scope",
    "extract_numeric_claims",
    "numeric_claim_recall",
    "numeric_contradiction_rate",
    "register_tool_result",
    "report_schema_valid",
    "unsupported_claim_rate",
]
