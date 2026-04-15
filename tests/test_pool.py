import asyncio

from agent_runtime.engine import AgentEngine, EngineDependencies, EnginePool, EngineRunContext
from agent_runtime.llm import LLMRequest, LLMResponse
from agent_runtime.storage import InMemoryBlobStore, InMemorySessionStore
from agent_runtime.tools import ToolRegistry
from agent_runtime.types import Message, RuntimeState


class FinalLLM:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(message=Message.assistant("done"), should_stop=True)


def build_engine() -> AgentEngine:
    return AgentEngine(
        EngineDependencies(
            llm=FinalLLM(),
            tool_registry=ToolRegistry(loader=lambda: []),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )


def test_engine_pool_returns_engine_after_successful_run() -> None:
    pool = EnginePool(factory=build_engine, size=1)

    result = asyncio.run(
        pool.run(
            EngineRunContext(
                session_id="pool-1",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    assert result.state is RuntimeState.COMPLETED
    assert pool.available_count == 1


def test_engine_pool_returns_engine_after_cancelled_run() -> None:
    class CancellingLLM:
        async def complete(self, request: LLMRequest) -> LLMResponse:
            request.messages.append(Message.user("side effect"))  # pragma: no cover
            return LLMResponse(message=Message.assistant("done"), should_stop=True)

    def build_cancelling_engine() -> AgentEngine:
        return AgentEngine(
            EngineDependencies(
                llm=CancellingLLM(),
                tool_registry=ToolRegistry(loader=lambda: []),
                session_store=InMemorySessionStore(),
                blob_store=InMemoryBlobStore(),
            )
        )

    pool = EnginePool(factory=build_cancelling_engine, size=1)
    cancel_event = asyncio.Event()
    cancel_event.set()

    result = asyncio.run(
        pool.run(
            EngineRunContext(
                session_id="pool-2",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
                cancel_event=cancel_event,
            )
        )
    )

    assert result.state is RuntimeState.CANCELLED
    assert pool.available_count == 1
