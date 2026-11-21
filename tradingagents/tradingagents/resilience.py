"""Typed retry and data fallback decisions."""
from __future__ import annotations

import time
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.cost.enforcement import BudgetExceededError

_event_sink: ContextVar[list[FailureEvent] | None] = ContextVar("fallback_event_sink", default=None)


def record_fallback_event(event: FailureEvent) -> None:
    """Append an event to the active run's sink, when one is bound."""
    sink = _event_sink.get()
    if sink is not None:
        sink.append(event)


class fallback_event_scope:
    """Bind a list that the graph runner can serialize into its RunManifest."""
    def __init__(self, sink: list[FailureEvent]):
        self.sink = sink

    def __enter__(self):
        self.token = _event_sink.set(self.sink)
        return self.sink

    def __exit__(self, exc_type, exc, tb):
        _event_sink.reset(self.token)


class RetryPolicy(BaseModel):
    attempts: int = Field(default=2, ge=1)
    delay_seconds: float = Field(default=0, ge=0)


class FailureEvent(BaseModel):
    kind: str
    source: str
    message: str
    action: str


class FallbackDecision(BaseModel):
    value: Any = None
    available: bool
    confidence_factor: float = Field(default=1.0, ge=0, le=1)
    events: list[FailureEvent] = Field(default_factory=list)
    status: str = "ok"


class _StructuredFallback:
    """Try the primary structured runnable, then the fallback model."""

    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def invoke(self, *args, **kwargs):
        try:
            return self.primary.invoke(*args, **kwargs)
        except BudgetExceededError:
            raise
        except Exception as exc:
            record_fallback_event(FailureEvent(
                kind="llm_failure", source="structured_output",
                message=str(exc), action="cheaper_model",
            ))
            return self.fallback.invoke(*args, **kwargs)


class FallbackLLM:
    """Use a cheaper/fallback model when the primary model call fails."""

    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def invoke(self, *args, **kwargs):
        try:
            return self.primary.invoke(*args, **kwargs)
        except BudgetExceededError:
            raise
        except Exception as exc:
            record_fallback_event(FailureEvent(
                kind="llm_failure", source="primary_model",
                message=str(exc), action="cheaper_model",
            ))
            return self.fallback.invoke(*args, **kwargs)

    def with_structured_output(self, *args, **kwargs):
        return _StructuredFallback(
            self.primary.with_structured_output(*args, **kwargs),
            self.fallback.with_structured_output(*args, **kwargs),
        )

    def __getattr__(self, name):
        return getattr(self.primary, name)


class FallbackRouter:
    def __init__(self, retry: RetryPolicy | None = None):
        self.retry = retry or RetryPolicy()

    def route(self, failure: Exception, context: dict[str, Any]) -> FallbackDecision:
        """Return only a fresh cache value; otherwise an explicit unavailable marker."""
        cache, key = context.get("cache"), context.get("key")
        source = context.get("source", getattr(key, "source", "unknown"))
        if cache is not None and key is not None:
            entry = cache.get(key)
            if entry is not None:
                event = FailureEvent(kind="source_failure", source=source,
                                     message=str(failure), action="fresh_cache")
                record_fallback_event(event)
                return FallbackDecision(value=entry.value, available=True,
                                        confidence_factor=0.8, events=[event], status="degraded")
        event = FailureEvent(kind="source_failure", source=source,
                             message=str(failure), action="unavailable")
        record_fallback_event(event)
        return FallbackDecision(value=f"DATA_UNAVAILABLE: {source} data unavailable",
                                available=False, confidence_factor=0.5,
                                events=[event], status="review")

    def fetch(self, fetch_fn: Callable[[], Any], context: dict[str, Any]) -> FallbackDecision:
        failure = None
        for attempt in range(self.retry.attempts):
            try:
                return FallbackDecision(value=fetch_fn(), available=True)
            except Exception as exc:
                failure = exc
                if attempt + 1 < self.retry.attempts and self.retry.delay_seconds:
                    time.sleep(self.retry.delay_seconds)
        assert failure is not None
        return self.route(failure, context)
