from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

from agent_runtime.llm import CompressionSettings, LLMClient, LLMRequest, Summarizer, compress_messages
from agent_runtime.observability import EventSink
from agent_runtime.storage import BlobStore, SessionStore
from agent_runtime.tools import ToolRegistry, invoke_tool, materialize_tool_result
from agent_runtime.types import (
    Checkpoint,
    DecisionEvent,
    DecisionEventKind,
    Message,
    RuntimeState,
    ToolCall,
    ToolResult,
    ensure_tool_protocol,
)


@dataclass(slots=True)
class EngineDependencies:
    llm: LLMClient
    tool_registry: ToolRegistry
    session_store: SessionStore
    blob_store: BlobStore
    summarizer: Summarizer | None = None
    compression: CompressionSettings = field(default_factory=CompressionSettings)
    event_sink: EventSink | None = None


@dataclass(slots=True)
class EngineRunContext:
    session_id: str
    system_prompt: str
    task_goal: str
    user_message: str
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    llm_extra: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class EngineRunResult:
    state: RuntimeState
    output: str
    messages: list[Message]
    events: list[DecisionEvent]


class AgentEngine:
    def __init__(self, deps: EngineDependencies) -> None:
        self._deps = deps
        self._intervention_queues: dict[str, list[Message]] = {}
        self._loop_signatures: dict[str, int] = {}

    def queue_intervention(self, session_id: str, message: Message) -> None:
        self._intervention_queues.setdefault(session_id, []).append(message)

    async def run(self, context: EngineRunContext) -> EngineRunResult:
        messages = [
            Message.system(context.system_prompt),
            Message.user(context.task_goal),
            Message.user(context.user_message),
        ]
        events: list[DecisionEvent] = []
        state = RuntimeState.RUNNING
        self._save(context.session_id, messages, state, is_running=True)

        try:
            while True:
                if context.cancel_event.is_set():
                    state = RuntimeState.CANCELLED
                    return self._finish(context.session_id, state, messages, events, output="")

                available_tools = self._deps.tool_registry.list_tools()
                request_messages = await compress_messages(
                    messages,
                    task_goal=context.task_goal,
                    system_prompt=context.system_prompt,
                    settings=self._deps.compression,
                    summarizer=self._deps.summarizer,
                )
                ensure_tool_protocol(request_messages)
                response = await self._deps.llm.complete(
                    LLMRequest(messages=request_messages, tools=available_tools, extra=context.llm_extra)
                )
                if context.cancel_event.is_set():
                    return self._finish(
                        context.session_id,
                        RuntimeState.CANCELLED,
                        messages,
                        events,
                        output="",
                    )
                assistant_message = response.message
                messages.append(assistant_message)

                if not assistant_message.tool_calls:
                    await self._record_event(
                        events,
                        DecisionEvent(
                            kind=DecisionEventKind.TOOL_EXECUTION_SKIPPED,
                            subject="tools",
                            detail="Assistant returned without tool calls.",
                        ),
                    )
                    if response.requires_confirmation:
                        state = RuntimeState.WAITING_FOR_CONFIRMATION
                    elif response.requires_user_input:
                        state = RuntimeState.WAITING_FOR_USER
                    else:
                        state = RuntimeState.COMPLETED if response.should_stop or assistant_message.content else RuntimeState.WAITING_FOR_USER
                    return self._finish(
                        context.session_id,
                        state,
                        messages,
                        events,
                        output=assistant_message.content,
                    )

                tool_error = await self._execute_tool_calls(
                    context=context,
                    messages=messages,
                    tool_calls=assistant_message.tool_calls,
                    available_tools=available_tools,
                    events=events,
                )
                ensure_tool_protocol(messages)
                self._flush_interventions(context.session_id, messages)
                self._save(context.session_id, messages, RuntimeState.RUNNING, is_running=True)
                if tool_error is not None:
                    if tool_error == "cancelled":
                        return self._finish(
                            context.session_id,
                            RuntimeState.CANCELLED,
                            messages,
                            events,
                            output="",
                        )
                    return self._finish(
                        context.session_id,
                        RuntimeState.ERROR,
                        messages,
                        events,
                        output=tool_error,
                    )
                await asyncio.sleep(0)
        except Exception as exc:
            tool_result = ToolResult(call_id="engine", name="engine", output="", error=str(exc))
            messages.append(Message.tool_result(tool_result))
            await self._record_event(
                events,
                DecisionEvent(
                    kind=DecisionEventKind.TOOL_EXECUTION_FAILED,
                    subject="engine",
                    detail=str(exc),
                ),
            )
            return self._finish(
                context.session_id,
                RuntimeState.ERROR,
                messages,
                events,
                output=str(exc),
            )

    async def _execute_tool_calls(
        self,
        *,
        context: EngineRunContext,
        messages: list[Message],
        tool_calls: list[ToolCall],
        available_tools: list,
        events: list[DecisionEvent],
    ) -> str | None:
        tool_map = {tool.name: tool for tool in available_tools}
        for tool_call in tool_calls:
            await self._record_event(
                events,
                DecisionEvent(
                    kind=DecisionEventKind.TOOL_EXECUTION_TRIGGERED,
                    subject=tool_call.name,
                    detail="Tool execution requested by model.",
                ),
            )
            signature = self._signature(tool_call)
            repeats = self._loop_signatures.get(signature, 0) + 1
            self._loop_signatures[signature] = repeats
            if repeats > 2:
                error = f"Blocked repeated tool call loop for {tool_call.name}"
                messages.append(
                    Message.tool_result(
                        ToolResult(call_id=tool_call.id, name=tool_call.name, output="", error=error)
                    )
                )
                await self._record_event(
                    events,
                    DecisionEvent(
                        kind=DecisionEventKind.TOOL_EXECUTION_BLOCKED,
                        subject=tool_call.name,
                        detail=error,
                    ),
                )
                return error

            spec = tool_map.get(tool_call.name)
            if spec is None:
                error = f"Tool '{tool_call.name}' is not available."
                messages.append(
                    Message.tool_result(
                        ToolResult(call_id=tool_call.id, name=tool_call.name, output="", error=error)
                    )
                )
                await self._record_event(
                    events,
                    DecisionEvent(
                        kind=DecisionEventKind.TOOL_EXECUTION_BLOCKED,
                        subject=tool_call.name,
                        detail=error,
                    ),
                )
                return error

            try:
                output = await invoke_tool(spec, tool_call.arguments)
                tool_result = await materialize_tool_result(
                    tool_name=spec.name,
                    output=output,
                    policy=spec.output_policy,
                    blob_store=self._deps.blob_store,
                    call_id=tool_call.id,
                )
                messages.append(Message.tool_result(tool_result))
            except Exception as exc:
                error = f"Tool '{tool_call.name}' failed: {exc}"
                messages.append(
                    Message.tool_result(
                        ToolResult(call_id=tool_call.id, name=tool_call.name, output="", error=error)
                    )
                )
                await self._record_event(
                    events,
                    DecisionEvent(
                        kind=DecisionEventKind.TOOL_EXECUTION_FAILED,
                        subject=tool_call.name,
                        detail=error,
                    ),
                )
                return error

            if context.cancel_event.is_set():
                return "cancelled"

        return None

    def _flush_interventions(self, session_id: str, messages: list[Message]) -> None:
        queued = self._intervention_queues.pop(session_id, [])
        messages.extend(queued)

    def _save(self, session_id: str, messages: list[Message], state: RuntimeState, *, is_running: bool) -> None:
        self._deps.session_store.save_session_snapshot(
            session_id,
            messages=messages,
            state=state,
            is_running=is_running,
        )
        self._deps.session_store.save_checkpoint(
            Checkpoint(session_id=session_id, state=state, messages=list(messages))
        )

    def _finish(
        self,
        session_id: str,
        state: RuntimeState,
        messages: list[Message],
        events: list[DecisionEvent],
        *,
        output: str,
    ) -> EngineRunResult:
        self._save(session_id, messages, state, is_running=False)
        return EngineRunResult(state=state, output=output, messages=messages, events=events)

    @staticmethod
    def _signature(tool_call: ToolCall) -> str:
        return f"{tool_call.name}:{json.dumps(tool_call.arguments, sort_keys=True, ensure_ascii=True)}"

    async def _record_event(self, events: list[DecisionEvent], event: DecisionEvent) -> None:
        events.append(event)
        if self._deps.event_sink is not None:
            await self._deps.event_sink.record(event)


class EnginePool:
    def __init__(self, factory, size: int = 1) -> None:
        self._factory = factory
        self._lock = asyncio.Lock()
        self._available = [factory() for _ in range(size)]

    @property
    def available_count(self) -> int:
        return len(self._available)

    async def run(self, context: EngineRunContext) -> EngineRunResult:
        engine = await self._take()
        try:
            return await engine.run(context)
        finally:
            await self._give_back(engine)

    async def _take(self) -> AgentEngine:
        async with self._lock:
            if self._available:
                return self._available.pop()
            return self._factory()

    async def _give_back(self, engine: AgentEngine) -> None:
        async with self._lock:
            self._available.append(engine)
