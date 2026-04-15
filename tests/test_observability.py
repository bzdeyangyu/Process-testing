import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_runtime.engine import AgentEngine, EngineDependencies, EngineRunContext
from agent_runtime.llm import LLMRequest, LLMResponse
from agent_runtime.observability import FileEventSink, InMemoryEventSink
from agent_runtime.storage import InMemoryBlobStore, InMemorySessionStore
from agent_runtime.tools import ToolRegistry
from agent_runtime.types import DecisionEventKind, Message


class QuietLLM:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(message=Message.assistant("done"), should_stop=True)


def test_in_memory_event_sink_collects_engine_decision_events() -> None:
    sink = InMemoryEventSink()
    engine = AgentEngine(
        EngineDependencies(
            llm=QuietLLM(),
            tool_registry=ToolRegistry(loader=lambda: []),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
            event_sink=sink,
        )
    )

    result = asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="obs-1",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    assert result.events
    assert sink.events
    assert sink.events[0].kind is DecisionEventKind.TOOL_EXECUTION_SKIPPED


def test_file_event_sink_writes_jsonl_records() -> None:
    with TemporaryDirectory() as temp_dir:
        sink = FileEventSink(Path(temp_dir) / "events.jsonl")
        engine = AgentEngine(
            EngineDependencies(
                llm=QuietLLM(),
                tool_registry=ToolRegistry(loader=lambda: []),
                session_store=InMemorySessionStore(),
                blob_store=InMemoryBlobStore(),
                event_sink=sink,
            )
        )

        asyncio.run(
            engine.run(
                EngineRunContext(
                    session_id="obs-2",
                    system_prompt="You are helpful.",
                    task_goal="Finish the task.",
                    user_message="Say hi",
                )
            )
        )

        lines = (Path(temp_dir) / "events.jsonl").read_text(encoding="utf-8").splitlines()
        payload = json.loads(lines[0])
        assert payload["kind"] == "tool_execution_skipped"
        assert payload["subject"] == "tools"
