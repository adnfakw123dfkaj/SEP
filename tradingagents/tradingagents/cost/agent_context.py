"""Per-agent context for cost attribution.

The graph runs several agents through one callback.  A ContextVar carries the
current agent name from the node into the callback, so ``by_agent`` stays
correct without changing agent internals or duplicating LLM clients.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TypeVar

_current_agent: ContextVar[str | None] = ContextVar("current_agent", default=None)

P = ParamSpec("P")
R = TypeVar("R")


def current_agent() -> str | None:
    """The agent name set by the nearest ``agent_scope``, or None."""
    return _current_agent.get()


@contextmanager
def agent_scope(name: str) -> Iterator[None]:
    """Set the current agent for the duration of the block."""
    token = _current_agent.set(name)
    try:
        yield
    finally:
        _current_agent.reset(token)


def with_agent_scope(name: str, fn: Callable[P, R]) -> Callable[P, R]:
    """Wrap a graph node so every LLM call inside it is attributed to ``name``."""

    @wraps(fn)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        with agent_scope(name):
            return fn(*args, **kwargs)

    return wrapped
