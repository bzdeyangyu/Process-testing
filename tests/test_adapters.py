import asyncio

from agent_runtime.llm import AnthropicAdapter, LLMRequest, OpenAIAdapter
from agent_runtime.tools import ToolOutputPolicy, ToolSpec
from agent_runtime.types import Message, ToolCall, ToolResult


class CaptureTransport:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls = []

    async def __call__(self, payload: dict) -> dict:
        self.calls.append(payload)
        return self.response


def build_tools() -> list[ToolSpec]:
    async def echo(value: str) -> str:
        return value

    return [
        ToolSpec(
            name="echo",
            description="Echo input.",
            handler=echo,
            output_policy=ToolOutputPolicy(max_chars=20),
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        )
    ]


def test_openai_adapter_builds_payload_with_tools_and_extra() -> None:
    transport = CaptureTransport(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "done",
                    },
                    "finish_reason": "stop",
                }
            ]
        }
    )
    adapter = OpenAIAdapter(model="gpt-5", transport=transport)

    response = asyncio.run(
        adapter.complete(
            LLMRequest(
                messages=[Message.system("sys"), Message.user("hi")],
                tools=build_tools(),
                extra={"reasoning_effort": "high"},
            )
        )
    )

    payload = transport.calls[0]
    assert payload["model"] == "gpt-5"
    assert payload["reasoning_effort"] == "high"
    assert payload["tools"][0]["function"]["name"] == "echo"
    assert payload["messages"][0]["role"] == "system"
    assert response.message.content == "done"


def test_openai_adapter_parses_tool_calls() -> None:
    transport = CaptureTransport(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "use tool",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "echo",
                                    "arguments": "{\"value\":\"hi\"}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
    )
    adapter = OpenAIAdapter(model="gpt-5", transport=transport)

    response = asyncio.run(adapter.complete(LLMRequest(messages=[Message.user("hi")])))

    assert response.message.tool_calls is not None
    assert response.message.tool_calls[0].name == "echo"
    assert response.message.tool_calls[0].arguments == {"value": "hi"}


def test_anthropic_adapter_builds_payload_with_system_tools_and_thinking() -> None:
    transport = CaptureTransport(
        {
            "content": [{"type": "text", "text": "done"}],
            "stop_reason": "end_turn",
        }
    )
    adapter = AnthropicAdapter(model="claude-sonnet-4-5", transport=transport)

    response = asyncio.run(
        adapter.complete(
            LLMRequest(
                messages=[Message.system("sys"), Message.user("hi")],
                tools=build_tools(),
                extra={"thinking": {"type": "enabled", "budget_tokens": 128}},
            )
        )
    )

    payload = transport.calls[0]
    assert payload["model"] == "claude-sonnet-4-5"
    assert payload["system"] == "sys"
    assert payload["thinking"]["budget_tokens"] == 128
    assert payload["tools"][0]["name"] == "echo"
    assert payload["messages"][0]["role"] == "user"
    assert response.message.content == "done"


def test_anthropic_adapter_parses_tool_use_blocks() -> None:
    transport = CaptureTransport(
        {
            "content": [
                {"type": "text", "text": "use tool"},
                {"type": "tool_use", "id": "call-1", "name": "echo", "input": {"value": "hi"}},
            ],
            "stop_reason": "tool_use",
        }
    )
    adapter = AnthropicAdapter(model="claude-sonnet-4-5", transport=transport)

    response = asyncio.run(
        adapter.complete(
            LLMRequest(
                messages=[
                    Message.user("hi"),
                    Message.tool_result(ToolResult(call_id="call-0", name="prior", output="ok")),
                ]
            )
        )
    )

    assert response.message.tool_calls is not None
    assert response.message.tool_calls[0] == ToolCall(id="call-1", name="echo", arguments={"value": "hi"})
