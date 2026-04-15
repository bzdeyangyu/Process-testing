from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.schemas import EventEnvelope


class EventLogger:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[dict] = []

    def emit(self, event: EventEnvelope) -> None:
        self._events.append(event.to_dict())

    def dump(self) -> list[dict]:
        self._path.write_text(json.dumps(self._events, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return list(self._events)
