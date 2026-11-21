"""Report fidelity checks (REQ-QUAL-002).

The report is prose a model wrote; these checks make its exact claims auditable
without a human reading every line:

- ``extract_numeric_claims``: pull the numbers out of report text, normalised so
  ``$250``, ``250`` and ``1,200,000`` compare cleanly.
- ``numeric_contradiction_rate``: the fraction of numbers that disagree with the
  verified market snapshot (a claim the snapshot cannot support is a
  contradiction).
- ``citation_support_rate``: the fraction of cited evidence ids that resolve in
  the evidence registry (a citation to a non-existent source is unsupported).
- ``unsupported_claim_rate``: the fraction of substantive claims without a ref.
- ``report_schema_valid``: the report carries the required sections.
- ``numeric_claim_recall``: how many of a golden set of numbers the extractor
  finds (guards against an extractor that silently misses claims).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A number with optional sign, thousands separators, decimals, and an optional
# trailing percent sign. Currency symbols and surrounding text are dropped.
_NUMBER_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*%?")

REQUIRED_SECTIONS = ("rating", "investment thesis")


@dataclass(frozen=True)
class NumericClaim:
    """One number found in report text."""

    raw: str
    normalized: str


def _normalize_number(token: str) -> str:
    """Canonical form for comparison: strip currency/commas/percent, drop +0."""
    t = token.strip().lstrip("$€£¥").replace(",", "")
    if t.endswith("%"):
        t = t[:-1]
    if t.startswith("+"):
        t = t[1:]
    try:
        value = float(t)
    except ValueError:
        return t
    # Integer-valued floats print without a trailing .0 so 250 == 250.0.
    if value == int(value):
        return str(int(value))
    return repr(value)


def extract_numeric_claims(text: str) -> list[NumericClaim]:
    """All numeric claims in ``text``, normalised for comparison."""
    claims = []
    for match in _NUMBER_RE.finditer(text or ""):
        raw = match.group(0)
        claims.append(NumericClaim(raw=raw, normalized=_normalize_number(raw)))
    return claims


def _snapshot_numbers(snapshot: str) -> set[str]:
    """Every number present in a verified market snapshot's text."""
    return {_normalize_number(m.group(0)) for m in _NUMBER_RE.finditer(snapshot or "")}


def numeric_contradiction_rate(reports: list[str], snapshot: str) -> float:
    """Fraction of report numbers that do not appear anywhere in the snapshot.

    A clean report (every number traceable to the snapshot) scores 0.0. A number
    the snapshot never shows — e.g. "close 189.5" against a snapshot close of
    187.2 — is a contradiction.
    """
    allowed = _snapshot_numbers(snapshot)
    total = contradicted = 0
    for report in reports:
        for claim in extract_numeric_claims(report):
            total += 1
            if claim.normalized not in allowed:
                contradicted += 1
    return 0.0 if total == 0 else contradicted / total


def citation_support_rate(ref_ids: list[str], known_ids) -> float:
    """Fraction of cited ids that resolve to a known evidence id."""
    if not ref_ids:
        return 1.0
    known = set(known_ids)
    supported = sum(1 for rid in ref_ids if rid in known)
    return supported / len(ref_ids)


def unsupported_claim_rate(claims: list, refs: list) -> float:
    """Fraction of substantive claims that carry no evidence reference.

    ``claims`` is the claim list; ``refs`` the refs actually attached. When there
    are as many refs as claims, every claim is supported. Fewer refs leave the
    tail unsupported.
    """
    if not claims:
        return 0.0
    supported = min(len(claims), len(refs))
    return (len(claims) - supported) / len(claims)


def report_schema_valid(report: str) -> bool:
    """Whether the report carries the required sections (Rating, Investment Thesis)."""
    lowered = (report or "").lower()
    return all(section in lowered for section in REQUIRED_SECTIONS)


def numeric_claim_recall(text: str, golden: set[str]) -> float:
    """Fraction of the ``golden`` numbers the extractor finds in ``text``."""
    if not golden:
        return 1.0
    found = {claim.normalized for claim in extract_numeric_claims(text)}
    hits = sum(1 for g in golden if _normalize_number(g) in found)
    return hits / len(golden)
