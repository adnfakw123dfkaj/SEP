"""Deterministic claim-level evidence groups for report audits.

Claims are the substantive Markdown blocks in the report.  Each block gets a
stable ``claim_id`` and the run evidence that belongs to its report family.  This
is deliberately evidence-presence attribution, not semantic entailment.
"""

from __future__ import annotations

import re
from typing import Any

from tradingagents.contracts.claim import ReportClaim
from tradingagents.evidence.fidelity import extract_numeric_claims

_MARKET = {
    "get_stock_data",
    "get_indicators",
    "get_stock_stats_indicators_window",
    "get_verified_market_snapshot",
}
_NEWS = {
    "get_news",
    "get_global_news",
    "get_macro_indicators",
    "get_prediction_markets",
}
_FUNDAMENTALS = {
    "get_fundamentals",
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_insider_transactions",
}
_SECTIONS = (
    ("market", "market_report", _MARKET),
    ("sentiment", "sentiment_report", _NEWS),
    ("news", "news_report", _NEWS),
    ("fundamentals", "fundamentals_report", _FUNDAMENTALS),
    ("research", "investment_plan", None),
    ("trader", "trader_investment_plan", None),
    ("decision", "final_trade_decision", None),
)


def _method(source: str) -> str:
    return str(source or "").split(":", 1)[0]


def _blocks(text: str) -> list[str]:
    return [
        block.strip()
        for block in re.split(r"\n\s*\n", text or "")
        if block.strip() and not block.lstrip().startswith("#")
    ]


def build_report_claims(final_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Build stable claim groups with the evidence refs for each section."""
    evidence = list(final_state.get("evidence") or [])
    claims: list[ReportClaim] = []
    for section, state_key, family in _SECTIONS:
        text = final_state.get(state_key) or ""
        if not isinstance(text, str):
            continue
        refs = [
            ref
            for ref in evidence
            if family is None or _method(str(ref.get("source", ""))) in family
        ]
        ref_ids = [str(ref.get("id")) for ref in refs if ref.get("id")]
        snapshot_hashes = sorted(
            {
                str(ref.get("snapshot_hash"))
                for ref in refs
                if ref.get("snapshot_hash")
            }
        )
        for index, block in enumerate(_blocks(text), start=1):
            kind = "numeric" if extract_numeric_claims(block) else "qualitative"
            claims.append(
                ReportClaim(
                    claim_id=f"{section}-{index:04d}",
                    section=section,
                    kind=kind,
                    text=block,
                    evidence_refs=ref_ids,
                    snapshot_hashes=snapshot_hashes,
                )
            )
    return [claim.model_dump(mode="json") for claim in claims]


def claim_evidence_metrics(claims: list[dict[str, Any]]) -> dict[str, Any]:
    """Coverage rates used by the Part 3 quality floor."""
    total = len(claims or [])
    numeric = [claim for claim in claims or [] if claim.get("kind") == "numeric"]
    qualitative = [claim for claim in claims or [] if claim.get("kind") == "qualitative"]
    supported = [claim for claim in claims or [] if claim.get("evidence_refs")]

    return {
        "claim_count": total,
        "numeric_claim_count": len(numeric),
        "qualitative_claim_count": len(qualitative),
        "numeric_claim_evidence_rate": (
            sum(1 for claim in numeric if claim.get("evidence_refs")) / len(numeric)
            if numeric
            else 1.0
        ),
        "qualitative_claim_evidence_rate": (
            sum(1 for claim in qualitative if claim.get("evidence_refs")) / len(qualitative)
            if qualitative
            else 1.0
        ),
        "claim_unsupported_rate": (
            1.0 - len(supported) / total if total else 0.0
        ),
    }


_NUMBER = r"[-+]?\d[\d,]*\.?\d*%?"
_VALUE = rf"({_NUMBER})(?![\d])"
_LABELS = (
    (
        "close",
        rf"\bclose(?:d)?\b(?:\s+on)?(?:\s+\d{{4}}-\d{{2}}-\d{{2}})?"
        rf"(?:\s*(?:price|of|at|was|is|printed|:|=))*\s*\$?{_VALUE}",
    ),
    ("open", rf"\bopen(?:ed)?\b(?:\s*(?:price|of|at|was|is|:|=))*\s*\$?{_VALUE}"),
    (
        "high",
        rf"\b(?:session|day|intraday|daily)\s+high\b"
        rf"(?:\s*(?:at|was|is|:|=))*\s*\$?{_VALUE}",
    ),
    (
        "low",
        rf"\b(?:session|day|intraday|daily)\s+low\b"
        rf"(?:\s*(?:at|was|is|:|=))*\s*\$?{_VALUE}",
    ),
    ("rsi", rf"\brsi\b(?:\s*(?:at|is|of|:|=))*\s*{_VALUE}"),
    ("macds", rf"\bmacd\s+signal\b(?:\s*(?:at|is|of|:|=))*\s*{_VALUE}"),
    ("macdh", rf"\bmacd\s+histogram\b(?:\s*(?:at|is|of|:|=))*\s*{_VALUE}"),
    ("macd", rf"\bmacd\b(?!\s+(?:signal|histogram))(?:\s*(?:at|is|of|:|=))*\s*{_VALUE}"),
    ("atr", rf"\batr\b(?:\s*(?:at|is|of|:|=))*\s*{_VALUE}"),
    ("boll_lb", rf"\blower\s+bollinger\s+band\b(?:\s*(?:at|is|of|:|=|near|around))*\s*\(?{_VALUE}"),
    ("boll_ub", rf"\bupper\s+bollinger\s+band\b(?:\s*(?:at|is|of|:|=|near|around))*\s*\(?{_VALUE}"),
    ("boll", rf"\bboll(?:inger)?\s+(?:middle|basis)\b(?:\s*(?:at|is|of|:|=|near|around))*\s*\(?{_VALUE}"),
    ("close_10_ema", rf"\b10[-\s]*(?:ema|day\s+ema)\b(?:\s*(?:at|is|of|:|=|near|around))*\s*{_VALUE}"),
    ("close_50_sma", rf"\b50[-\s]*(?:sma|day\s+sma)\b(?:\s*(?:at|is|of|:|=|near|around))*\s*{_VALUE}"),
    ("close_200_sma", rf"\b200[-\s]*(?:sma|day\s+sma)\b(?:\s*(?:at|is|of|:|=|near|around))*\s*{_VALUE}"),
    ("vwma", rf"\bvwma\b(?:\s*(?:at|is|of|:|=|near|around))*\s*{_VALUE}"),
)
_SNAPSHOT_FIELDS = {
    "open", "high", "low", "close", "rsi", "macd", "macds", "macdh", "atr",
    "boll", "boll_ub", "boll_lb", "close_10_ema", "close_50_sma",
    "close_200_sma", "vwma",
}


def _number(token: str) -> float | None:
    if token.endswith("%"):
        return None
    try:
        return float(token.replace(",", "").lstrip("$"))
    except ValueError:
        return None


def _snapshot_values(snapshot: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for line in (snapshot or "").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2:
            continue
        field = cells[0].lower().replace("-", "_").replace(" ", "_")
        if field not in _SNAPSHOT_FIELDS:
            continue
        value = _number(cells[1])
        if value is not None:
            values[field] = value
    return values


_HISTORICAL = re.compile(
    r"\d{4}-\d{2}-\d{2}|\b(?:peak|previous|prior|historical|drawdown|since|from)\b",
    re.IGNORECASE,
)


def _labeled_values(text: str) -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []
    for field, pattern in _LABELS:
        for match in re.finditer(pattern, text or "", re.IGNORECASE):
            if field in {"close", "high", "low"}:
                prefix = (text or "")[max(0, match.start() - 30):match.start()]
                if _HISTORICAL.search(prefix):
                    continue
            value = _number(match.group(1))
            if value is not None:
                found.append((field, value))
    return found


def numeric_claim_contradiction(
    claims: list[dict[str, Any]],
    snapshot: str,
    *,
    sections: set[str] | None = None,
) -> dict[str, Any]:
    """Compare labelled market values against the verified snapshot.

    Only explicit label/value pairs such as ``close 125.53`` or ``RSI 15.05``
    are compared.  Derived percentages and unlabelled numbers are ignored, which
    is what keeps this metric from flagging ordinary narrative arithmetic.
    """
    values = _snapshot_values(snapshot)
    checked = contradictions = 0
    details: list[dict[str, Any]] = []
    for claim in claims or []:
        if claim.get("kind") != "numeric":
            continue
        if sections is not None and claim.get("section") not in sections:
            continue
        for field, value in _labeled_values(claim.get("text", "")):
            expected = values.get(field)
            if expected is None:
                continue
            checked += 1
            tolerance = max(0.005, abs(expected) * 0.005)
            if abs(value - expected) > tolerance:
                contradictions += 1
                details.append(
                    {
                        "claim_id": claim.get("claim_id"),
                        "field": field,
                        "reported": value,
                        "snapshot": expected,
                    }
                )
    return {
        "checked": checked,
        "contradictions": contradictions,
        "rate": contradictions / checked if checked else None,
        "details": details[:20],
    }


__all__ = [
    "build_report_claims",
    "claim_evidence_metrics",
    "numeric_claim_contradiction",
]
