"""LangChain callback that turns real provider calls into LLMCallEvent records.

The callback is deliberately independent of Part 1-5: it can be passed to the
existing ``TradingAgentsGraph(callbacks=[...])`` and records whatever the base
provider adapter reports.  Missing provider usage falls back to the local
estimator and is marked ``estimated`` rather than silently dropped.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from tradingagents.contracts.llm_event import (
    CallStatus,
    LLMCallEvent,
    RoutePath,
    UsageSource,
)
from tradingagents.cost.agent_context import current_agent
from tradingagents.cost.estimator import estimate_tokens


@dataclass(frozen=True)
class _CallState:
    started: float
    prompt_text: str
    model: str
    agent_name: str


def _serialized_model(serialized: dict[str, Any], fallback: str) -> str:
    kwargs = serialized.get("kwargs") or {}
    return (
        kwargs.get("model_name")
        or kwargs.get("model")
        or serialized.get("model_name")
        or fallback
    )


def _usage_from_mapping(usage: dict[str, Any]) -> tuple[int, int, int] | None:
    prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion = usage.get("completion_tokens", usage.get("output_tokens"))
    total = usage.get("total_tokens")
    if prompt is None and completion is None and total is None:
        return None
    prompt = int(prompt or 0)
    completion = int(completion or 0)
    total = int(total if total is not None else prompt + completion)
    return prompt, completion, total


def _extract_usage(response: Any) -> tuple[int, int, int] | None:
    llm_output = getattr(response, "llm_output", None) or {}
    if isinstance(llm_output, dict):
        for key in ("token_usage", "usage"):
            usage = llm_output.get(key)
            if isinstance(usage, dict):
                parsed = _usage_from_mapping(usage)
                if parsed is not None:
                    return parsed

    for batch in getattr(response, "generations", []) or []:
        for generation in batch:
            message = getattr(generation, "message", None)
            if message is not None:
                metadata = getattr(message, "usage_metadata", None) or {}
                if isinstance(metadata, dict):
                    parsed = _usage_from_mapping(metadata)
                    if parsed is not None:
                        return parsed
                response_metadata = getattr(message, "response_metadata", None) or {}
                if isinstance(response_metadata, dict):
                    parsed = _usage_from_mapping(
                        response_metadata.get("token_usage") or {}
                    )
                    if parsed is not None:
                        return parsed
    return None


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _extract_text(response: Any) -> str:
    for batch in getattr(response, "generations", []) or []:
        for generation in batch:
            text = getattr(generation, "text", None)
            if text:
                return str(text)
            message = getattr(generation, "message", None)
            if message is not None:
                return _message_text(getattr(message, "content", ""))
    return ""


class CostTrackingCallback(BaseCallbackHandler):
    """Emit one ``LLMCallEvent`` per completed or failed model call."""

    def __init__(
        self,
        *,
        run_id: str,
        on_event: Callable[[LLMCallEvent], None],
        agent_name: str = "unknown",
        provider: str = "unknown",
        route_path: RoutePath = RoutePath.DIRECT,
        cache_hit: bool = False,
        default_model: str = "unknown",
        before_call: Callable[..., None] | None = None,
    ):
        self.run_id = run_id
        self.on_event = on_event
        self.agent_name = agent_name
        self.provider = provider
        self.route_path = route_path
        self.cache_hit = cache_hit
        self.default_model = default_model
        self.before_call = before_call
        self._states: dict[str, _CallState] = {}
        self._lock = threading.Lock()

    def _start(
        self,
        run_id: Any,
        prompt_text: str,
        serialized: dict[str, Any],
    ) -> None:
        model = _serialized_model(serialized, self.default_model)
        if self.before_call is not None:
            self.before_call(model=model, prompt_text=prompt_text)
        state = _CallState(
            started=time.perf_counter(),
            prompt_text=prompt_text,
            model=model,
            agent_name=current_agent() or self.agent_name,
        )
        with self._lock:
            self._states[str(run_id)] = state

    def _take(self, run_id: Any) -> _CallState:
        with self._lock:
            return self._states.pop(
                str(run_id),
                _CallState(
                    started=time.perf_counter(),
                    prompt_text="",
                    model=self.default_model,
                    agent_name=self.agent_name,
                ),
            )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        text = "\n".join(
            _message_text(getattr(message, "content", message))
            for batch in messages
            for message in batch
        )
        self._start(run_id, text, serialized)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        self._start(run_id, "\n".join(prompts), serialized)

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        state = self._take(run_id)
        latency_ms = max(0.0, (time.perf_counter() - state.started) * 1000.0)
        usage = _extract_usage(response)

        if usage is None:
            prompt_tokens = estimate_tokens(state.prompt_text, state.model).input_tokens
            completion_tokens = estimate_tokens(
                _extract_text(response),
                state.model,
            ).input_tokens
            total_tokens = prompt_tokens + completion_tokens
            source = UsageSource.ESTIMATED
        else:
            prompt_tokens, completion_tokens, total_tokens = usage
            source = UsageSource.PROVIDER

        self.on_event(
            LLMCallEvent(
                event_id=str(run_id),
                run_id=self.run_id,
                call_id=str(run_id),
                agent_name=state.agent_name,
                model=state.model,
                provider=self.provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                status=CallStatus.SUCCESS,
                retry_count=0,
                route_path=self.route_path,
                usage_source=source,
                timestamp=datetime.now(UTC),
                cache_hit=self.cache_hit,
            )
        )

    def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        state = self._take(run_id)
        latency_ms = max(0.0, (time.perf_counter() - state.started) * 1000.0)
        self.on_event(
            LLMCallEvent(
                event_id=str(run_id),
                run_id=self.run_id,
                call_id=str(run_id),
                agent_name=state.agent_name,
                model=state.model,
                provider=self.provider,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=latency_ms,
                status=CallStatus.FAILURE,
                retry_count=0,
                route_path=self.route_path,
                usage_source=UsageSource.ESTIMATED,
                timestamp=datetime.now(UTC),
                cache_hit=self.cache_hit,
            )
        )
