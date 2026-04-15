from __future__ import annotations

import json

from agent_runtime.llm import LLMRequest
from agent_runtime.types import Message


async def request_json(
    *,
    llm_client,
    system_prompt: str,
    user_prompt: str,
    fallback: dict,
) -> dict:
    response = await llm_client.complete(
        LLMRequest(
            messages=[
                Message.system(system_prompt),
                Message.user(user_prompt),
            ]
        )
    )
    content = response.message.content.strip()
    try:
        parsed = json.loads(content)
        return _deep_merge(fallback, parsed if isinstance(parsed, dict) else {})
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
                return _deep_merge(fallback, parsed if isinstance(parsed, dict) else {})
            except json.JSONDecodeError:
                pass
        return fallback


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
