from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ThoughtEvent:
    thought_id: str
    trace_id: str
    agent: str
    step: int
    type: str
    content: str
    confidence: float
    timestamp: str


@dataclass(slots=True)
class EventEnvelope:
    topic: str
    event_type: str
    producer: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = ""
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        return asdict(self)
