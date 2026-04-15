from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from agent_runtime.engine import AgentEngine, EngineRunContext, EngineRunResult
from agent_runtime.storage import SessionSnapshot
from agent_runtime.types import Message, RuntimeState


@dataclass(slots=True)
class SessionView:
    session_id: str
    last_messages: list[Message]
    state: RuntimeState
    is_running: bool


@dataclass(slots=True)
class _ManagedAgent:
    engine: AgentEngine
    lock: asyncio.Lock


@dataclass(slots=True)
class _SessionHandle:
    agent_id: str
    cancel_event: asyncio.Event
    task: asyncio.Task[EngineRunResult]


class AgentRuntime:
    def __init__(self) -> None:
        self._agents: dict[str, _ManagedAgent] = {}
        self._session_to_agent: dict[str, str] = {}
        self._session_handles: dict[str, _SessionHandle] = {}

    def register_agent(self, agent_id: str, factory: Callable[[], AgentEngine]) -> None:
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered")
        self._agents[agent_id] = _ManagedAgent(engine=factory(), lock=asyncio.Lock())

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    async def run(self, agent_id: str, context: EngineRunContext) -> EngineRunResult:
        managed = self._agents[agent_id]
        self._session_to_agent[context.session_id] = agent_id
        async with managed.lock:
            return await managed.engine.run(context)

    async def start(self, agent_id: str, context: EngineRunContext) -> None:
        if context.session_id in self._session_handles:
            raise ValueError(f"Session '{context.session_id}' is already running")

        cancel_event = context.cancel_event
        managed = self._agents[agent_id]
        self._session_to_agent[context.session_id] = agent_id
        task = asyncio.create_task(self.run(agent_id, context))
        self._session_handles[context.session_id] = _SessionHandle(
            agent_id=agent_id,
            cancel_event=cancel_event,
            task=task,
        )
        await asyncio.sleep(0)

    def cancel(self, session_id: str) -> None:
        handle = self._session_handles[session_id]
        handle.cancel_event.set()

    async def wait(self, session_id: str) -> EngineRunResult:
        handle = self._session_handles[session_id]
        try:
            return await handle.task
        finally:
            self._session_handles.pop(session_id, None)

    def get_session_view(self, session_id: str) -> SessionView:
        agent_id = self._session_to_agent[session_id]
        managed = self._agents[agent_id]
        snapshot = managed.engine._deps.session_store.load_session_snapshot(session_id)
        if snapshot is None:
            raise KeyError(f"Unknown session '{session_id}'")
        return _to_session_view(snapshot)


def _to_session_view(snapshot: SessionSnapshot) -> SessionView:
    return SessionView(
        session_id=snapshot.session_id,
        last_messages=snapshot.messages,
        state=snapshot.state,
        is_running=snapshot.is_running,
    )
