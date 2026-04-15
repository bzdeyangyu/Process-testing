from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from agent_runtime.types import Checkpoint, Message, MessageRole, RuntimeState, ToolCall, ToolResult


class BlobStore(Protocol):
    async def write(self, content: str) -> str: ...

    def read(self, ref: str) -> str: ...


class SessionStore(Protocol):
    def save_checkpoint(self, checkpoint: Checkpoint) -> None: ...

    def load_checkpoint(self, session_id: str) -> Checkpoint | None: ...

    def save_session_snapshot(
        self,
        session_id: str,
        *,
        messages: list[Message],
        state: RuntimeState,
        is_running: bool,
    ) -> None: ...

    def load_session_snapshot(self, session_id: str) -> "SessionSnapshot | None": ...


class InMemoryBlobStore:
    def __init__(self) -> None:
        self._blobs: dict[str, str] = {}

    async def write(self, content: str) -> str:
        ref = f"blob-{uuid4().hex}"
        self._blobs[ref] = content
        return ref

    def read(self, ref: str) -> str:
        return self._blobs[ref]


class FileBlobStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._blob_dir = self._root / "blobs"
        self._blob_dir.mkdir(parents=True, exist_ok=True)

    async def write(self, content: str) -> str:
        ref = f"blob-{uuid4().hex}"
        (self._blob_dir / f"{ref}.txt").write_text(content, encoding="utf-8")
        return ref

    def read(self, ref: str) -> str:
        return (self._blob_dir / f"{ref}.txt").read_text(encoding="utf-8")


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    messages: list[Message]
    state: RuntimeState
    is_running: bool


class InMemorySessionStore:
    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}
        self._snapshots: dict[str, SessionSnapshot] = {}

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        self._checkpoints[checkpoint.session_id] = checkpoint

    def load_checkpoint(self, session_id: str) -> Checkpoint | None:
        return self._checkpoints.get(session_id)

    def save_session_snapshot(
        self,
        session_id: str,
        *,
        messages: list[Message],
        state: RuntimeState,
        is_running: bool,
    ) -> None:
        self._snapshots[session_id] = SessionSnapshot(
            session_id=session_id,
            messages=list(messages),
            state=state,
            is_running=is_running,
        )

    def load_session_snapshot(self, session_id: str) -> SessionSnapshot | None:
        return self._snapshots.get(session_id)


class FileSessionStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._checkpoint_dir = self._root / "checkpoints"
        self._session_dir = self._root / "sessions"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._session_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        payload = {
            "session_id": checkpoint.session_id,
            "state": checkpoint.state.value,
            "messages": [_message_to_dict(message) for message in checkpoint.messages],
        }
        (self._checkpoint_dir / f"{checkpoint.session_id}.json").write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def load_checkpoint(self, session_id: str) -> Checkpoint | None:
        path = self._checkpoint_dir / f"{session_id}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Checkpoint(
            session_id=payload["session_id"],
            state=RuntimeState(payload["state"]),
            messages=[_message_from_dict(message) for message in payload["messages"]],
        )

    def save_session_snapshot(
        self,
        session_id: str,
        *,
        messages: list[Message],
        state: RuntimeState,
        is_running: bool,
    ) -> None:
        payload = {
            "session_id": session_id,
            "messages": [_message_to_dict(message) for message in messages],
            "state": state.value,
            "is_running": is_running,
        }
        (self._session_dir / f"{session_id}.json").write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def load_session_snapshot(self, session_id: str) -> SessionSnapshot | None:
        path = self._session_dir / f"{session_id}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SessionSnapshot(
            session_id=payload["session_id"],
            messages=[_message_from_dict(message) for message in payload["messages"]],
            state=RuntimeState(payload["state"]),
            is_running=payload["is_running"],
        )


def _message_to_dict(message: Message) -> dict:
    return {
        "role": message.role.value,
        "content": message.content,
        "tool_calls": [
            {
                "id": tool_call.id,
                "name": tool_call.name,
                "arguments": tool_call.arguments,
            }
            for tool_call in (message.tool_calls or [])
        ],
        "tool_result": (
            {
                "call_id": message.tool_result.call_id,
                "name": message.tool_result.name,
                "output": message.tool_result.output,
                "overflow_ref": message.tool_result.overflow_ref,
                "error": message.tool_result.error,
            }
            if message.tool_result is not None
            else None
        ),
    }


def _message_from_dict(payload: dict) -> Message:
    tool_result_payload = payload.get("tool_result")
    tool_result = (
        ToolResult(
            call_id=tool_result_payload["call_id"],
            name=tool_result_payload["name"],
            output=tool_result_payload["output"],
            overflow_ref=tool_result_payload.get("overflow_ref"),
            error=tool_result_payload.get("error"),
        )
        if tool_result_payload is not None
        else None
    )
    return Message(
        role=MessageRole(payload["role"]),
        content=payload["content"],
        tool_calls=[
            ToolCall(
                id=tool_call["id"],
                name=tool_call["name"],
                arguments=tool_call["arguments"],
            )
            for tool_call in payload.get("tool_calls", [])
        ]
        or None,
        _tool_result=tool_result,
    )
