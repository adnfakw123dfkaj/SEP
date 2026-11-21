"""Role-bound tool execution for LangGraph's ToolNode."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest, ToolNode

from .tool_guard import ToolGuard, UnauthorizedToolCall


class GuardedToolNode(ToolNode):
    """A ToolNode that rejects a role's unbound tool before it executes."""

    def __init__(self, tools, *, role: str, guard: ToolGuard | None = None):
        super().__init__(tools)
        self.role = role
        self.guard = guard or ToolGuard(
            allowed={role: {tool.name for tool in tools}}
        )

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
        return super()._execute_tool_sync(request, input_type, config)

    async def _execute_tool_async(
        self,
        request: ToolCallRequest,
        input_type: Literal["list", "dict", "tool_calls"],
        config,
    ):
        rejected = self._check(request)
        if rejected is not None:
            return rejected
        return await super()._execute_tool_async(request, input_type, config)
