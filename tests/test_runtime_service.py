import asyncio

from agent_runtime.engine import AgentEngine, EngineDependencies, EngineRunContext
from agent_runtime.llm import LLMRequest, LLMResponse
from agent_runtime.runtime import AgentRuntime, SessionView
from agent_runtime.storage import InMemoryBlobStore, InMemorySessionStore
from agent_runtime.tools import ToolRegistry
from agent_runtime.types import Message, RuntimeState


class EchoLLM:
    def __init__(self, text: str) -> None:
        self.text = text

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(message=Message.assistant(self.text), should_stop=True)


class SlowLLM:
    def __init__(self) -> None:
        self._gate = asyncio.Event()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        await self._gate.wait()
        return LLMResponse(message=Message.assistant("done"), should_stop=True)

    def release(self) -> None:
        self._gate.set()


def build_engine(text: str) -> AgentEngine:
    return AgentEngine(
        EngineDependencies(
            llm=EchoLLM(text),
            tool_registry=ToolRegistry(loader=lambda: []),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )


def test_runtime_keeps_agents_isolated() -> None:
    runtime = AgentRuntime()
    runtime.register_agent("alpha", lambda: build_engine("alpha done"))
    runtime.register_agent("beta", lambda: build_engine("beta done"))

    alpha = asyncio.run(
        runtime.run(
            "alpha",
            EngineRunContext(
                session_id="alpha-session",
                system_prompt="You are alpha.",
                task_goal="Finish alpha.",
                user_message="Go",
            ),
        )
    )
    beta = asyncio.run(
        runtime.run(
            "beta",
            EngineRunContext(
                session_id="beta-session",
                system_prompt="You are beta.",
                task_goal="Finish beta.",
                user_message="Go",
            ),
        )
    )

    assert alpha.output == "alpha done"
    assert beta.output == "beta done"
    assert runtime.get_session_view("alpha-session").last_messages[0].content == "You are alpha."
    assert runtime.get_session_view("beta-session").last_messages[0].content == "You are beta."


def test_runtime_reports_backend_session_view_while_running() -> None:
    llm = SlowLLM()
    runtime = AgentRuntime()
    runtime.register_agent(
        "slow",
        lambda: AgentEngine(
            EngineDependencies(
                llm=llm,
                tool_registry=ToolRegistry(loader=lambda: []),
                session_store=InMemorySessionStore(),
                blob_store=InMemoryBlobStore(),
            )
        ),
    )

    async def run_and_inspect():
        task = asyncio.create_task(
            runtime.run(
                "slow",
                EngineRunContext(
                    session_id="slow-session",
                    system_prompt="You are slow.",
                    task_goal="Finish slow.",
                    user_message="Go",
                ),
            )
        )
        await asyncio.sleep(0)
        session_view = runtime.get_session_view("slow-session")
        llm.release()
        result = await task
        return session_view, result, runtime.get_session_view("slow-session")

    during, result, after = asyncio.run(run_and_inspect())

    assert isinstance(during, SessionView)
    assert during.is_running is True
    assert during.state is RuntimeState.RUNNING
    assert result.state is RuntimeState.COMPLETED
    assert after.is_running is False
    assert after.last_messages[-1].content == "done"


def test_runtime_can_start_and_cancel_session_in_background() -> None:
    llm = SlowLLM()
    runtime = AgentRuntime()
    runtime.register_agent(
        "slow",
        lambda: AgentEngine(
            EngineDependencies(
                llm=llm,
                tool_registry=ToolRegistry(loader=lambda: []),
                session_store=InMemorySessionStore(),
                blob_store=InMemoryBlobStore(),
            )
        ),
    )

    async def exercise():
        await runtime.start(
            "slow",
            EngineRunContext(
                session_id="cancel-session",
                system_prompt="You are slow.",
                task_goal="Finish slow.",
                user_message="Go",
            ),
        )
        during = runtime.get_session_view("cancel-session")
        runtime.cancel("cancel-session")
        llm.release()
        result = await runtime.wait("cancel-session")
        return during, result

    during, result = asyncio.run(exercise())

    assert during.is_running is True
    assert result.state is RuntimeState.CANCELLED
