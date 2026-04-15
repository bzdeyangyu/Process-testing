from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class RuntimeState(str, Enum):
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class DecisionEventKind(str, Enum):
    TOOL_EXECUTION_TRIGGERED = "tool_execution_triggered"
    TOOL_EXECUTION_SKIPPED = "tool_execution_skipped"
    TOOL_EXECUTION_BLOCKED = "tool_execution_blocked"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    call_id: str
    name: str
    output: str
    overflow_ref: str | None = None
    error: str | None = None


class _ToolResultAccessor:
    def __get__(self, instance: "Message | None", owner: type["Message"]) -> ToolResult | Callable[[ToolResult], "Message"] | None:
        if instance is None:
            def build(result: ToolResult) -> Message:
                return owner(role=MessageRole.TOOL, content=result.output, _tool_result=result)

            return build
        return instance._tool_result


@dataclass(slots=True)
class Message:
    role: MessageRole
    content: str
    tool_calls: list[ToolCall] | None = None
    _tool_result: ToolResult | None = None

    tool_result = _ToolResultAccessor()

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(
        cls,
        content: str,
        tool_calls: list[ToolCall] | None = None,
    ) -> "Message":
        return cls(role=MessageRole.ASSISTANT, content=content, tool_calls=tool_calls)


@dataclass(slots=True)
class DecisionEvent:
    kind: DecisionEventKind
    subject: str
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Checkpoint:
    session_id: str
    state: RuntimeState
    messages: list[Message]


def ensure_tool_protocol(messages: list[Message]) -> None:
    index = 0
    while index < len(messages):
        message = messages[index]
        if message.role is MessageRole.ASSISTANT and message.tool_calls:
            expected = len(message.tool_calls)
            for offset in range(1, expected + 1):
                next_index = index + offset
                if next_index >= len(messages):
                    raise ValueError("assistant tool_calls must be followed by tool_result messages")
                next_message = messages[next_index]
                if next_message.role is not MessageRole.TOOL or next_message.tool_result is None:
                    raise ValueError("assistant tool_calls must be followed immediately by tool_result messages")
            index += expected
        index += 1
