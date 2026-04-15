from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from agent_runtime.board import ProjectBoardRepository
from agent_runtime.engine import EngineRunContext
from agent_runtime.runtime import AgentRuntime
from agent_runtime.types import Message


class AgentRuntimeAPI:
    def __init__(self, runtime: AgentRuntime, board_repository: ProjectBoardRepository | None = None) -> None:
        self._runtime = runtime
        self._board_repository = board_repository

    async def handle(self, method: str, path: str, payload: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        if method == "GET" and path == "/agents":
            return 200, {"agents": self._runtime.list_agents()}

        if method == "GET" and path == "/boards":
            if self._board_repository is None:
                return 200, {"runs": []}
            return 200, self._board_repository.list_project_cards()

        if method == "GET" and path == "/boards/current":
            if self._board_repository is None:
                return 404, {"error": "board_not_configured"}
            try:
                return 200, self._board_repository.get_current_project_card()
            except KeyError:
                return 404, {"error": "not_found"}

        if method == "GET" and path.startswith("/boards/"):
            if self._board_repository is None:
                return 404, {"error": "board_not_configured"}
            run_id = path.split("/", 2)[2]
            try:
                return 200, self._board_repository.get_project_card(run_id)
            except KeyError:
                return 404, {"error": "not_found"}

        if method == "POST" and path == "/sessions/run":
            assert payload is not None
            await self._runtime.start(
                payload["agent_id"],
                EngineRunContext(
                    session_id=payload["session_id"],
                    system_prompt=payload["system_prompt"],
                    task_goal=payload["task_goal"],
                    user_message=payload["user_message"],
                ),
            )
            return 202, {"session_id": payload["session_id"], "status": "running"}

        if method == "GET" and path.startswith("/sessions/"):
            session_id = path.split("/", 2)[2]
            session = self._runtime.get_session_view(session_id)
            return 200, {
                "session_id": session.session_id,
                "state": session.state.value,
                "is_running": session.is_running,
                "last_messages": [_message_to_dict(message) for message in session.last_messages],
            }

        if method == "POST" and path.endswith("/cancel") and path.startswith("/sessions/"):
            session_id = path.split("/")[2]
            self._runtime.cancel(session_id)
            return 202, {"session_id": session_id, "status": "cancelling"}

        return 404, {"error": "not_found"}


def create_http_server(host: str, port: int, runtime: AgentRuntime) -> ThreadingHTTPServer:
    api = AgentRuntimeAPI(runtime)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._handle("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._handle("POST")

        def log_message(self, format: str, *args: object) -> None:
            return None

        def _handle(self, method: str) -> None:
            parsed = urlparse(self.path)
            payload = None
            if method == "POST":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                payload = json.loads(raw)
            status, body = _run_sync(api.handle(method, parsed.path, payload))
            encoded = json.dumps(body, ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return ThreadingHTTPServer((host, port), Handler)


def _run_sync(coro):
    try:
        loop = None
        import asyncio

        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    import asyncio

    return asyncio.run(coro)


def _message_to_dict(message: Message) -> dict[str, Any]:
    payload = {
        "role": message.role.value,
        "content": message.content,
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "name": tool_call.name,
                "arguments": tool_call.arguments,
            }
            for tool_call in message.tool_calls
        ]
    if message.tool_result is not None:
        payload["tool_result"] = {
            "call_id": message.tool_result.call_id,
            "name": message.tool_result.name,
            "output": message.tool_result.output,
            "overflow_ref": message.tool_result.overflow_ref,
            "error": message.tool_result.error,
        }
    return payload
