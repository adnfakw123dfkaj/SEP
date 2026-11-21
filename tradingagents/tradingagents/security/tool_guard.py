"""Role-bound tool execution guard (Part 5, REQ-SEC-001 acceptance line 4).

An agent may only call the tools bound to its role. When the model proposes a
tool outside that allowlist, the guard rejects the call **before it executes**,
logs a ``tool_rejected`` security event, and the caller continues without it.

Guarantees:

- A rejected tool's ``execute`` is never invoked (the executable is not even
  looked up on the reject path), so an unauthorised call's execution count is 0.
- Rejection is recorded (redacted) with the role, tool and reason.
- Authorised calls still run, so one rejection does not block the run.

The guard owns the "reject before execute" decision; Part 1 wires it into the
graph's tool dispatch (see ``docs/part5-integration.md``). An
:class:`UnauthorizedToolCall` raised here is caught by the caller (the graph
dispatch), which continues the run without the tool.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from .security_log import EventKind, SecurityEventLog, log_event

__all__ = [
    "UnauthorizedToolCall",
    "ToolGuard",
    "RoleToolGuard",
]


class UnauthorizedToolCall(PermissionError):
    """Raised when a role proposes a tool it is not bound to.

    The caller (graph dispatch) catches this to continue the run without the
    tool. It is raised *before* the tool executes.
    """

    def __init__(self, role: str, tool: str) -> None:
        super().__init__(f"role {role!r} is not allowed to call tool {tool!r}")
        self.role = role
        self.tool = tool


@dataclass
class ToolGuard:
    """Per-role tool allowlists plus invocation bookkeeping.

    ``allowed`` maps a role to the set of tool names it may call. Add/remove
    tools via :meth:`bind` / :meth:`unbind`. The guard records how many times
    each (role, tool) actually executed, so tests can assert a rejected tool's
    execution count is 0.
    """

    allowed: dict[str, set[str]] = field(default_factory=dict)
    _exec_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    event_log: SecurityEventLog | None = None

    def __post_init__(self) -> None:
        self.allowed = {role: set(tools) for role, tools in self.allowed.items()}

    def bind(self, role: str, *tools: str) -> None:
        self.allowed.setdefault(role, set()).update(tools)

    def unbind(self, role: str, *tools: str) -> None:
        self.allowed.setdefault(role, set()).difference_update(tools)

    def is_allowed(self, role: str, tool: str) -> bool:
        return tool in self.allowed.get(role, set())

    def executions(self, role: str, tool: str) -> int:
        """How many times ``(role, tool)`` actually executed."""
        return self._exec_counts.get((role, tool), 0)

    def call(self, role: str, tool: str,
             executables: dict[str, Callable[..., Any]],
             *args: Any, **kwargs: Any) -> Any:
        """Execute ``tool`` for ``role`` iff it is allowed; else reject.

        On rejection raises :class:`UnauthorizedToolCall` without touching
        ``executables[tool]``. On success, records the execution and returns the
        tool's result.
        """
        self._check_and_log(role, tool)
        tool_fn = executables[tool]
        result = tool_fn(*args, **kwargs)
        self._exec_counts[(role, tool)] = self._exec_counts.get((role, tool), 0) + 1
        return result

    def call_names(self, role: str,
                   proposed: Iterable[str]) -> dict[str, bool]:
        """Classify proposed tools as allowed/rejected for ``role`` (no exec).

        Useful for a planning step that must decide which tool calls to attempt
        before any execute happens.
        """
        decisions: dict[str, bool] = {}
        for tool in proposed:
            decisions[tool] = self.is_allowed(role, tool)
        return decisions

    def _check_and_log(self, role: str, tool: str) -> None:
        if self.is_allowed(role, tool):
            log_event(EventKind.TOOL_ALLOWED, f"{role}:{tool}",
                      event_log=self.event_log)
            return
        log_event(EventKind.TOOL_REJECTED, f"unauthorized:{role}:{tool}",
                  detail={"role": role, "tool": tool}, event_log=self.event_log)
        raise UnauthorizedToolCall(role, tool)


# Convenience alias with an intent-revealing name.
RoleToolGuard = ToolGuard
