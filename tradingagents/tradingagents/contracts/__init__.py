"""Shared machine-readable contracts for the six-part enhancement.

This package collects the contract modules each Part defines. Every
``contracts/*.py`` module is cheap and side-effect free so the safety-path
contract check (``scripts/gates/run_static_checks.py::check_contract``) can
import them cleanly.

Part ownership of the modules is per-tree; this ``__init__`` only re-exports
their public names.
"""

from __future__ import annotations

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
    # cost (Part 6)
    "Budget",
    "CostReport",
    "ModelPrice",
    "PricePair",
    "PriceTable",
    "TokenEstimate",
    # evidence / manifest (Part 3)
    "EvidenceRef",
    "RunManifest",
    # llm_event (Part 6)
    "CallStatus",
    "LLMCallEvent",
    "RoutePath",
    "UsageSource",
    # rating (Part 5)
    "ALLOWED_RATINGS",
    "REVIEW",
    "TRADEABLE_RATINGS",
    "InMemoryRatingStore",
    "Provenance",
    "RatingResult",
    "ReasonCode",
    "coerce_review",
    "is_allowed",
]
