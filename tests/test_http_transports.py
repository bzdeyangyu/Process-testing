import asyncio
import json
from urllib.error import HTTPError

from agent_runtime.llm import anthropic_http_transport, openai_http_transport


class FakeHttpResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_openai_http_transport_sets_authorization_and_json_body(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request):
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = request.data.decode("utf-8")
        captured["url"] = request.full_url
        return FakeHttpResponse({"choices": []})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = openai_http_transport(api_key="sk-test", base_url="https://api.openai.com/v1/chat/completions")

    asyncio.run(transport({"model": "gpt-5", "messages": []}))

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer sk-test"
    assert captured["headers"]["content-type"] == "application/json"
    assert json.loads(captured["body"])["model"] == "gpt-5"


def test_anthropic_http_transport_sets_required_headers(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request):
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = request.data.decode("utf-8")
        captured["url"] = request.full_url
        return FakeHttpResponse({"content": [], "stop_reason": "end_turn"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = anthropic_http_transport(api_key="ak-test", base_url="https://api.anthropic.com/v1/messages")

    asyncio.run(transport({"model": "claude", "messages": []}))

    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "ak-test"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert json.loads(captured["body"])["model"] == "claude"


def test_http_transport_raises_runtime_error_with_response_body(monkeypatch) -> None:
    def fake_urlopen(_request):
        raise HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=FakeHttpResponse({"error": {"message": "bad payload"}}),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = openai_http_transport(api_key="sk-test")

    try:
        asyncio.run(transport({"model": "gpt-5", "messages": []}))
    except RuntimeError as exc:
        assert "bad payload" in str(exc)
        assert "400" in str(exc)
    else:
        raise AssertionError("Expected transport to raise on HTTP error")
