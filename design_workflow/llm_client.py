from __future__ import annotations

from agent_runtime.llm import OpenAIAdapter, openai_http_transport


def create_glm_client(*, api_key: str, base_url: str, model: str) -> OpenAIAdapter:
    normalized = base_url.rstrip("/")
    if not normalized.endswith("/chat/completions"):
        normalized = normalized + "/chat/completions"
    return OpenAIAdapter(model=model, transport=openai_http_transport(api_key=api_key, base_url=normalized))
