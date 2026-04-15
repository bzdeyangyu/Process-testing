import asyncio

from agent_runtime.engine import AgentEngine, EngineDependencies, EngineRunContext
from agent_runtime.llm import LLMRequest, LLMResponse
from agent_runtime.storage import InMemoryBlobStore, InMemorySessionStore
from agent_runtime.tools import ToolOutputPolicy, ToolRegistry, ToolSpec
from agent_runtime.types import DecisionEventKind, Message, RuntimeState, ToolCall


class FakeLLM:
    def __init__(self) -> None:
        self.calls = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if len(self.calls) == 1:
            return LLMResponse(
                message=Message.assistant(
                    "use tool",
                    tool_calls=[ToolCall(id="call-1", name="echo", arguments={"value": "hi"})],
                )
            )
        return LLMResponse(message=Message.assistant("done"), should_stop=True)


async def echo_tool(value: str) -> str:
    return value


def test_engine_runs_react_loop_and_preserves_tool_protocol() -> None:
    llm = FakeLLM()
    registry = ToolRegistry(
        loader=lambda: [
            ToolSpec(
                name="echo",
                description="Echo a string.",
                handler=echo_tool,
                output_policy=ToolOutputPolicy(max_chars=20),
            )
        ]
    )
    engine = AgentEngine(
        EngineDependencies(
            llm=llm,
            tool_registry=registry,
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )

    result = asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="s1",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    assert result.state is RuntimeState.COMPLETED
    assert result.output == "done"
    assert len(llm.calls) == 2
    second_request_messages = llm.calls[1].messages
    assert second_request_messages[-2].tool_calls is not None
    assert second_request_messages[-1].tool_result is not None


def test_engine_stops_before_next_turn_when_cancelled() -> None:
    llm = FakeLLM()
    registry = ToolRegistry(
        loader=lambda: [
            ToolSpec(
                name="echo",
                description="Echo a string.",
                handler=echo_tool,
                output_policy=ToolOutputPolicy(max_chars=20),
            )
        ]
    )
    engine = AgentEngine(
        EngineDependencies(
            llm=llm,
            tool_registry=registry,
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )
    context = EngineRunContext(
        session_id="s2",
        system_prompt="You are helpful.",
        task_goal="Finish the task.",
        user_message="Say hi",
    )

    async def run_and_cancel():
        task = asyncio.create_task(engine.run(context))
        await asyncio.sleep(0)
        context.cancel_event.set()
        return await task

    result = asyncio.run(run_and_cancel())

    assert result.state is RuntimeState.CANCELLED


def test_engine_emits_decision_events_for_executed_and_blocked_paths() -> None:
    class MissingToolLLM:
        async def complete(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                message=Message.assistant(
                    "missing tool",
                    tool_calls=[ToolCall(id="call-1", name="unknown", arguments={})],
                )
            )

    engine = AgentEngine(
        EngineDependencies(
            llm=MissingToolLLM(),
            tool_registry=ToolRegistry(loader=lambda: []),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )

    result = asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="s3",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    event_kinds = [event.kind for event in result.events]
    assert DecisionEventKind.TOOL_EXECUTION_TRIGGERED in event_kinds
    assert DecisionEventKind.TOOL_EXECUTION_BLOCKED in event_kinds
    assert result.state is RuntimeState.ERROR


def test_engine_reloads_tools_each_turn() -> None:
    class TwoStepLLM:
        def __init__(self) -> None:
            self.turns = 0
            self.requests = []

        async def complete(self, request: LLMRequest) -> LLMResponse:
            self.requests.append(request)
            self.turns += 1
            if self.turns == 1:
                return LLMResponse(
                    message=Message.assistant(
                        "step one",
                        tool_calls=[ToolCall(id="call-1", name="first", arguments={})],
                    )
                )
            if self.turns == 2:
                return LLMResponse(
                    message=Message.assistant(
                        "step two",
                        tool_calls=[ToolCall(id="call-2", name="second", arguments={})],
                    )
                )
            return LLMResponse(message=Message.assistant("done"), should_stop=True)

    load_count = {"value": 0}

    async def first_tool() -> str:
        return "one"

    async def second_tool() -> str:
        return "two"

    def loader():
        load_count["value"] += 1
        if load_count["value"] == 1:
            return [
                ToolSpec(
                    name="first",
                    description="First tool.",
                    handler=first_tool,
                    output_policy=ToolOutputPolicy(max_chars=20),
                )
            ]
        return [
            ToolSpec(
                name="first",
                description="First tool.",
                handler=first_tool,
                output_policy=ToolOutputPolicy(max_chars=20),
            ),
            ToolSpec(
                name="second",
                description="Second tool.",
                handler=second_tool,
                output_policy=ToolOutputPolicy(max_chars=20),
            ),
        ]

    llm = TwoStepLLM()
    engine = AgentEngine(
        EngineDependencies(
            llm=llm,
            tool_registry=ToolRegistry(loader=loader),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )

    result = asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="s4",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    assert result.state is RuntimeState.COMPLETED
    assert load_count["value"] >= 2
    assert [tool.name for tool in llm.requests[0].tools] == ["first"]
    assert [tool.name for tool in llm.requests[1].tools] == ["first", "second"]


def test_engine_blocks_repeated_tool_call_loops() -> None:
    class LoopyLLM:
        async def complete(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                message=Message.assistant(
                    "loop",
                    tool_calls=[ToolCall(id="loop-1", name="echo", arguments={"value": "same"})],
                )
            )

    engine = AgentEngine(
        EngineDependencies(
            llm=LoopyLLM(),
            tool_registry=ToolRegistry(
                loader=lambda: [
                    ToolSpec(
                        name="echo",
                        description="Echo a string.",
                        handler=echo_tool,
                        output_policy=ToolOutputPolicy(max_chars=20),
                    )
                ]
            ),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )

    result = asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="s5",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    assert result.state is RuntimeState.ERROR
    assert any(event.kind is DecisionEventKind.TOOL_EXECUTION_BLOCKED for event in result.events)


def test_engine_flushes_interventions_after_tool_results() -> None:
    class InspectingLLM:
        def __init__(self) -> None:
            self.calls = []

        async def complete(self, request: LLMRequest) -> LLMResponse:
            self.calls.append(request)
            if len(self.calls) == 1:
                return LLMResponse(
                    message=Message.assistant(
                        "use tool",
                        tool_calls=[ToolCall(id="call-1", name="echo", arguments={"value": "hi"})],
                    )
                )
            return LLMResponse(message=Message.assistant("done"), should_stop=True)

    llm = InspectingLLM()
    engine = AgentEngine(
        EngineDependencies(
            llm=llm,
            tool_registry=ToolRegistry(
                loader=lambda: [
                    ToolSpec(
                        name="echo",
                        description="Echo a string.",
                        handler=echo_tool,
                        output_policy=ToolOutputPolicy(max_chars=20),
                    )
                ]
            ),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )
    engine.queue_intervention("s6", Message.user("Please also keep it short."))

    asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="s6",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
            )
        )
    )

    second_request = llm.calls[1].messages
    assert second_request[-3].tool_calls is not None
    assert second_request[-2].tool_result is not None
    assert second_request[-1].content == "Please also keep it short."


def test_engine_marks_run_cancelled_when_stop_arrives_after_tool_execution() -> None:
    class SingleToolLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, request: LLMRequest) -> LLMResponse:
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    message=Message.assistant(
                        "use tool",
                        tool_calls=[ToolCall(id="call-1", name="echo", arguments={})],
                    )
                )
            return LLMResponse(message=Message.assistant("done"), should_stop=True)

    cancel_event = asyncio.Event()

    async def cancelling_tool() -> str:
        cancel_event.set()
        return "done"

    engine = AgentEngine(
        EngineDependencies(
            llm=SingleToolLLM(),
            tool_registry=ToolRegistry(
                loader=lambda: [
                    ToolSpec(
                        name="echo",
                        description="Echo a string.",
                        handler=cancelling_tool,
                        output_policy=ToolOutputPolicy(max_chars=20),
                    )
                ]
            ),
            session_store=InMemorySessionStore(),
            blob_store=InMemoryBlobStore(),
        )
    )

    result = asyncio.run(
        engine.run(
            EngineRunContext(
                session_id="s7",
                system_prompt="You are helpful.",
                task_goal="Finish the task.",
                user_message="Say hi",
                cancel_event=cancel_event,
            )
        )
    )

    assert result.state is RuntimeState.CANCELLED
