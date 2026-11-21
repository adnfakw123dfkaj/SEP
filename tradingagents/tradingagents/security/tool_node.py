"""Role-bound tool execution for LangGraph's ToolNode."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest, ToolNode

from .tool_guard import ToolGuard, UnauthorizedToolCall


def _truncate_text(text: str, limit: int | None) -> str:
    if not limit or len(text) <= limit:
        return text
    head = min(1000, limit // 3)
    tail = max(0, limit - head)
    return (
        text[:head]
        + "\n...[tool output truncated for prompt budget]...\n"
        + text[-tail:]
    )


class GuardedToolNode(ToolNode):
    """A ToolNode that rejects a role's unbound tool before it executes."""

    def __init__(
        self,
        tools,
        *,
        role: str,
        guard: ToolGuard | None = None,
        max_output_chars: int | None = None,
    ):
        super().__init__(tools)
        self.role = role
        self.guard = guard or ToolGuard(
            allowed={role: {tool.name for tool in tools}}
        )
        self.max_output_chars = max_output_chars

    def _budget_result(self, result):
        if isinstance(result, ToolMessage) and isinstance(result.content, str):
            return result.model_copy(
                update={"content": _truncate_text(result.content, self.max_output_chars)}
            )
        return result

    def _reject(self, request: ToolCallRequest) -> ToolMessage:
        call = request.tool_call
        return ToolMessage(
            content=f"Tool {call['name']!r} is not allowed for role {self.role!r}.",
            tool_call_id=call.get("id", ""),
            name=call["name"],
        )

    def _check(self, request: ToolCallRequest) -> ToolMessage | None:
        try:
            self.guard.check(self.role, request.tool_call["name"])
        except UnauthorizedToolCall:
            return self._reject(request)
        return None

    def _execute_tool_sync(
        self,
        request: ToolCallRequest,
        input_type: Literal["list", "dict", "tool_calls"],
        config,
    ):
        rejected = self._check(request)
        if rejected is not None:
            return rejected
        return self._budget_result(super()._execute_tool_sync(request, input_type, config))

    async def _execute_tool_async(
        self,
        request: ToolCallRequest,
        input_type: Literal["list", "dict", "tool_calls"],
        config,
    ):
        rejected = self._check(request)
        if rejected is not None:
            return rejected
        result = await super()._execute_tool_async(request, input_type, config)
        return self._budget_result(result)
