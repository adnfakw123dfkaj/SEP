"""Shared machine-readable contracts for the six-part enhancement.

Importing this package must stay cheap and side-effect free so the safety-path
contract check (``scripts/gates/run_static_checks.py::check_contract``) can
import every ``contracts/*.py`` module cleanly.
"""

from __future__ import annotations

from .claim import ReportClaim
from .cost import (
    Budget,
    CostReport,
    ModelPrice,
    PricePair,
    PriceTable,
    TokenEstimate,
)
from .evidence import EvidenceRef
from .llm_event import CallStatus, LLMCallEvent, RoutePath, UsageSource
from .manifest import RunManifest
from .rating import (
    ALLOWED_RATINGS,
    REVIEW,
    TRADEABLE_RATINGS,
    InMemoryRatingStore,
    Provenance,
    RatingResult,
    ReasonCode,
    coerce_review,
    is_allowed,
)

__all__ = [
    "ALLOWED_RATINGS",
    "Budget",
    "CallStatus",
    "CostReport",
    "EvidenceRef",
    "InMemoryRatingStore",
    "LLMCallEvent",
    "ModelPrice",
    "PricePair",
    "PriceTable",
    "Provenance",
    "ReportClaim",
    "REVIEW",
    "RatingResult",
    "ReasonCode",
    "RoutePath",
    "RunManifest",
    "TRADEABLE_RATINGS",
    "TokenEstimate",
    "UsageSource",
    "coerce_review",
    "is_allowed",
]
