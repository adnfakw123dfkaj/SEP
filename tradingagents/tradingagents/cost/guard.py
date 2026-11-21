"""Pre-call budget enforcement around real LLM runnables.

LangChain's callback manager treats exceptions raised by callbacks as callback
failures and continues the model call.  A budget stop therefore cannot live in
a callback: it must wrap the runnable that performs the provider call, so the
exception propagates through the agent and the graph.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.runnables import Runnable


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    content = getattr(value, "content", value)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def prompt_text(value: Any) -> str:
    """Best-effort text for a prompt, prompt value, or message list."""
    if isinstance(value, str):
        return value
    messages = value.to_messages() if hasattr(value, "to_messages") else value
    if isinstance(messages, (list, tuple)):
        return "\n".join(_content_text(message) for message in messages)
    return _content_text(messages)


class GuardedRunnable(Runnable):
    """A runnable that checks the budget before delegating to its inner call."""

    def __init__(
        self,
        inner: Any,
        *,
        model: str,
        check: Callable[..., None],
    ):
        self.inner = inner
        self.model = model
        self.check = check

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        self.check(model=self.model, prompt_text=prompt_text(input))
        return self.inner.invoke(input, config=config, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


class GuardedLLM(Runnable):
    """A chat-model facade that enforces the budget before every provider call."""

    def __init__(
        self,
        inner: Any,
        *,
        model: str,
        check: Callable[..., None],
    ):
        self.inner = inner
        self.model = model
        self.check = check

    def _guard(self, value: Any) -> None:
        self.check(model=self.model, prompt_text=prompt_text(value))

    def invoke(self, input: Any, config: dict | None = None, **kwargs: Any) -> Any:
        self._guard(input)
        return self.inner.invoke(input, config=config, **kwargs)

    def bind_tools(self, tools: Any, **kwargs: Any) -> GuardedRunnable:
        return GuardedRunnable(
            self.inner.bind_tools(tools, **kwargs),
            model=self.model,
            check=self.check,
        )

    def with_structured_output(self, schema: Any, **kwargs: Any) -> GuardedRunnable:
        return GuardedRunnable(
            self.inner.with_structured_output(schema, **kwargs),
            model=self.model,
            check=self.check,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


__all__ = ["GuardedLLM", "GuardedRunnable", "prompt_text"]
