import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_runtime.api import AgentRuntimeAPI
from agent_runtime.board import ProjectBoardRepository, ProjectBoardTracker
from agent_runtime.engine import AgentEngine, EngineDependencies
from agent_runtime.llm import LLMRequest, LLMResponse
from agent_runtime.runtime import AgentRuntime
from agent_runtime.storage import InMemoryBlobStore, InMemorySessionStore
from agent_runtime.tools import ToolRegistry
from agent_runtime.types import Message


class FastLLM:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(message=Message.assistant("done"), should_stop=True)


class SlowLLM:
    def __init__(self) -> None:
        self._gate = asyncio.Event()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        await self._gate.wait()
        return LLMResponse(message=Message.assistant("done"), should_stop=True)

    def release(self) -> None:
        self._gate.set()


def build_engine(llm) -> AgentEngine:
    return AgentEngine(
        EngineDependencies(
            llm=llm,
            tool_registry=ToolRegistry(loader=lambda: []),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )


def test_api_lists_registered_agents() -> None:
    runtime = AgentRuntime()
    runtime.register_agent("alpha", lambda: build_engine(FastLLM()))
    runtime.register_agent("beta", lambda: build_engine(FastLLM()))
    api = AgentRuntimeAPI(runtime)

    status, payload = asyncio.run(api.handle("GET", "/agents", None))

    assert status == 200
    assert payload == {"agents": ["alpha", "beta"]}


def test_api_starts_session_and_reads_backend_state() -> None:
    runtime = AgentRuntime()
    runtime.register_agent("alpha", lambda: build_engine(FastLLM()))
    api = AgentRuntimeAPI(runtime)

    async def exercise():
        status, payload = await api.handle(
            "POST",
            "/sessions/run",
            {
                "agent_id": "alpha",
                "session_id": "api-1",
                "system_prompt": "You are alpha.",
                "task_goal": "Finish alpha.",
                "user_message": "Go",
            },
        )
        await runtime.wait("api-1")
        session_status, session_payload = await api.handle("GET", "/sessions/api-1", None)
        return status, payload, session_status, session_payload

    status, payload, session_status, session_payload = asyncio.run(exercise())

    assert status == 202
    assert payload["session_id"] == "api-1"
    assert session_status == 200
    assert session_payload["is_running"] is False
    assert session_payload["last_messages"][-1]["content"] == "done"


def test_api_cancels_running_session() -> None:
    llm = SlowLLM()
    runtime = AgentRuntime()
    runtime.register_agent("slow", lambda: build_engine(llm))
    api = AgentRuntimeAPI(runtime)

    async def exercise():
        await api.handle(
            "POST",
            "/sessions/run",
            {
                "agent_id": "slow",
                "session_id": "api-2",
                "system_prompt": "You are slow.",
                "task_goal": "Finish slow.",
                "user_message": "Go",
            },
        )
        cancel_status, cancel_payload = await api.handle("POST", "/sessions/api-2/cancel", None)
        llm.release()
        result = await runtime.wait("api-2")
        session_status, session_payload = await api.handle("GET", "/sessions/api-2", None)
        return cancel_status, cancel_payload, result.state.value, session_status, session_payload

    cancel_status, cancel_payload, result_state, session_status, session_payload = asyncio.run(exercise())

    assert cancel_status == 202
    assert cancel_payload["status"] == "cancelling"
    assert result_state == "cancelled"
    assert session_status == 200
    assert session_payload["state"] == "cancelled"


def test_api_exposes_project_board_snapshots() -> None:
    runtime = AgentRuntime()
    with TemporaryDirectory() as temp_dir:
        board_dir = Path(temp_dir) / "board"
        tracker = ProjectBoardTracker(
            board_dir=board_dir,
            project_id="space-design-workflow",
            project_name="AI空间设计工作流",
            run_id="board-1",
            title="南京展厅总卡",
            brief="南京 800㎡ 企业展厅，科技感。",
            mode="demo",
        )
        tracker.start()
        tracker.finish(
            {
                "structured_brief": {"project_type": "企业展厅设计", "area_sqm": 800},
                "visual_prompt": "Corporate showroom prompt",
            }
        )
        api = AgentRuntimeAPI(runtime, board_repository=ProjectBoardRepository(board_dir))

        list_status, list_payload = asyncio.run(api.handle("GET", "/boards", None))
        detail_status, detail_payload = asyncio.run(api.handle("GET", "/boards/board-1", None))

    assert list_status == 200
    assert list_payload["runs"][0]["run_id"] == "board-1"
    assert detail_status == 200
    assert detail_payload["status"] == "done"
    assert detail_payload["title"] == "南京展厅总卡"
