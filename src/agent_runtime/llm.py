from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from agent_runtime.tools import ToolSpec
from agent_runtime.types import Message


@dataclass(slots=True)
class LLMRequest:
    messages: list[Message]
    tools: list[ToolSpec] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    model: str | None = None


@dataclass(slots=True)
class LLMResponse:
    message: Message
    should_stop: bool = False
    requires_user_input: bool = False
    requires_confirmation: bool = False


class LLMClient(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...


class Summarizer(Protocol):
    async def summarize(self, request: LLMRequest) -> LLMResponse: ...


@dataclass(slots=True)
class CompressionSettings:
    max_tokens: int = 8_000
    summary_trigger_ratio: float = 0.65


Transport = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def openai_http_transport(
    *,
    api_key: str,
    base_url: str = "https://api.openai.com/v1/chat/completions",
) -> Transport:
    async def transport(payload: dict[str, Any]) -> dict[str, Any]:
        return await _http_post_json(
            base_url,
            payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    return transport


def anthropic_http_transport(
    *,
    api_key: str,
    base_url: str = "https://api.anthropic.com/v1/messages",
    anthropic_version: str = "2023-06-01",
) -> Transport:
    async def transport(payload: dict[str, Any]) -> dict[str, Any]:
        return await _http_post_json(
            base_url,
            payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": anthropic_version,
                "Content-Type": "application/json",
            },
        )

    return transport


@dataclass(slots=True)
class OpenAIAdapter:
    model: str
    transport: Transport

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [_to_openai_message(message) for message in request.messages],
        }
        if request.tools:
            payload["tools"] = [_to_openai_tool(tool) for tool in request.tools]
        payload.update(request.extra)
        raw = await self.transport(payload)
        choice = raw["choices"][0]
        message = choice["message"]
        return LLMResponse(
            message=_from_openai_message(message),
            should_stop=choice.get("finish_reason") not in {"tool_calls"},
        )


@dataclass(slots=True)
class AnthropicAdapter:
    model: str
    transport: Transport

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system_messages = [message.content for message in request.messages if message.role.value == "system"]
        payload: dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [_to_anthropic_message(message) for message in request.messages if message.role.value != "system"],
        }
        if system_messages:
            payload["system"] = "\n".join(system_messages)
        if request.tools:
            payload["tools"] = [_to_anthropic_tool(tool) for tool in request.tools]
        payload.update(request.extra)
        raw = await self.transport(payload)
        return LLMResponse(
            message=_from_anthropic_content(raw.get("content", [])),
            should_stop=raw.get("stop_reason") != "tool_use",
        )


def estimate_tokens(messages: list[Message]) -> int:
    content_size = sum(len(message.content) for message in messages)
    return max(1, content_size // 4)


async def compress_messages(
    messages: list[Message],
    *,
    task_goal: str,
    system_prompt: str,
    settings: CompressionSettings,
    summarizer: Summarizer | None = None,
) -> list[Message]:
    micro_messages = _micro_compress(messages, task_goal=task_goal, system_prompt=system_prompt)
    if estimate_tokens(micro_messages) <= int(settings.max_tokens * settings.summary_trigger_ratio):
        return micro_messages

    if summarizer is None:
        return micro_messages

    summary_request = LLMRequest(messages=micro_messages[2:])
    summary_response = await summarizer.summarize(summary_request)
    return [
        Message.system(system_prompt),
        Message.user(task_goal),
        summary_response.message,
    ]


def _micro_compress(
    messages: list[Message],
    *,
    task_goal: str,
    system_prompt: str,
) -> list[Message]:
    keep_indexes = _latest_tool_exchange_indexes(messages)
    compressed: list[Message] = [Message.system(system_prompt), Message.user(task_goal)]
    for index, message in enumerate(messages):
        if message.role.value == "tool" and index not in keep_indexes:
            continue
        if message.role.value == "assistant" and message.tool_calls and index not in keep_indexes:
            continue
        if message.role.value == "system" and message.content == system_prompt:
            continue
        if message.role.value == "user" and message.content == task_goal:
            continue
        compressed.append(message)
    return compressed


def _latest_tool_exchange_indexes(messages: list[Message]) -> set[int]:
    keep: set[int] = set()
    for index, message in enumerate(messages):
        if not message.tool_calls:
            continue
        expected = len(message.tool_calls)
        following = range(index + 1, index + expected + 1)
        if index + expected >= len(messages):
            continue
        if all(messages[position].tool_result is not None for position in following):
            keep = {index, *following}
    return keep


def _to_openai_message(message: Message) -> dict[str, Any]:
    if message.tool_result is not None:
        result = message.tool_result
        return {
            "role": "tool",
            "tool_call_id": result.call_id,
            "content": result.output if not result.error else result.error,
        }
    payload: dict[str, Any] = {
        "role": message.role.value,
        "content": message.content,
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.name,
                    "arguments": json.dumps(tool_call.arguments, ensure_ascii=True, sort_keys=True),
                },
            }
            for tool_call in message.tool_calls
        ]
    return payload


def _from_openai_message(payload: dict[str, Any]) -> Message:
    content = payload.get("content") or ""
    tool_calls = payload.get("tool_calls") or []
    if tool_calls:
        return Message.assistant(
            content,
            tool_calls=[
                _tool_call_from_payload(
                    call_id=tool_call["id"],
                    name=tool_call["function"]["name"],
                    arguments=tool_call["function"]["arguments"],
                )
                for tool_call in tool_calls
            ],
        )
    return Message.assistant(content)


def _to_openai_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema or {"type": "object", "properties": {}},
        },
    }


def _to_anthropic_message(message: Message) -> dict[str, Any]:
    if message.tool_result is not None:
        result = message.tool_result
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": result.call_id,
                    "content": result.output if not result.error else result.error,
                    "is_error": bool(result.error),
                }
            ],
        }
    payload: dict[str, Any] = {
        "role": message.role.value,
        "content": message.content,
    }
    if message.tool_calls:
        payload["content"] = [{"type": "text", "text": message.content}] + [
            {
                "type": "tool_use",
                "id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.arguments,
            }
            for tool_call in message.tool_calls
        ]
    return payload


def _from_anthropic_content(content_blocks: list[dict[str, Any]]) -> Message:
    text_parts: list[str] = []
    tool_calls = []
    for block in content_blocks:
        if block["type"] == "text":
            text_parts.append(block["text"])
        elif block["type"] == "tool_use":
            tool_calls.append(
                _tool_call_from_payload(
                    call_id=block["id"],
                    name=block["name"],
                    arguments=block["input"],
                )
            )
    return Message.assistant("".join(text_parts), tool_calls=tool_calls or None)


def _to_anthropic_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema or {"type": "object", "properties": {}},
    }


def _tool_call_from_payload(*, call_id: str, name: str, arguments: str | dict[str, Any]):
    parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    from agent_runtime.types import ToolCall

    return ToolCall(id=call_id, name=name, arguments=parsed)


async def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    def send() -> dict[str, Any]:
        request = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {url}: {error_body}") from exc

    import asyncio

    return await asyncio.to_thread(send)
