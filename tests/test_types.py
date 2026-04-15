from agent_runtime.types import (
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    ensure_tool_protocol,
)


def test_tool_protocol_requires_direct_tool_result_after_tool_calls() -> None:
    tool_call = ToolCall(id="call-1", name="echo", arguments={"value": "hi"})
    tool_result = ToolResult(call_id="call-1", name="echo", output="hi")

    messages = [
        Message.system("system"),
        Message.assistant("thinking", tool_calls=[tool_call]),
        Message.tool_result(tool_result),
    ]

    ensure_tool_protocol(messages)


def test_tool_protocol_rejects_interleaved_message_after_tool_calls() -> None:
    tool_call = ToolCall(id="call-1", name="echo", arguments={"value": "hi"})
    tool_result = ToolResult(call_id="call-1", name="echo", output="hi")

    messages = [
        Message.assistant("thinking", tool_calls=[tool_call]),
        Message.user("interrupt"),
        Message.tool_result(tool_result),
    ]

    try:
        ensure_tool_protocol(messages)
    except ValueError as exc:
        assert "tool_result" in str(exc)
    else:
        raise AssertionError("Expected protocol validation to fail")


def test_message_tool_result_helper_uses_tool_role() -> None:
    tool_result = ToolResult(call_id="call-1", name="echo", output="hi")

    message = Message.tool_result(tool_result)

    assert message.role is MessageRole.TOOL
    assert message.tool_result == tool_result
