from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from agent_runtime.types import DecisionEvent


class EventSink(Protocol):
    async def record(self, event: DecisionEvent) -> None: ...


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[DecisionEvent] = []

    async def record(self, event: DecisionEvent) -> None:
        self.events.append(event)


class FileEventSink:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def record(self, event: DecisionEvent) -> None:
        payload = asdict(event)
        payload["kind"] = event.kind.value
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
