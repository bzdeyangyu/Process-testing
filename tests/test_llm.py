import asyncio

from agent_runtime.llm import (
    CompressionSettings,
    LLMRequest,
    LLMResponse,
    compress_messages,
)
from agent_runtime.types import Message, ToolCall, ToolResult


class FakeSummarizer:
    def __init__(self) -> None:
        self.calls = []

    async def summarize(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(message=Message.assistant("summary"))


def test_compress_messages_prunes_tool_results_before_summarizing() -> None:
    summarizer = FakeSummarizer()
    tool_call = ToolCall(id="call-1", name="search", arguments={"q": "x"})
    tool_result = ToolResult(call_id="call-1", name="search", output="x" * 200)
    messages = [
        Message.system("You are helpful."),
        Message.user("Goal: finish the task."),
        Message.assistant("need tool", tool_calls=[tool_call]),
        Message.tool_result(tool_result),
        Message.user("Continue with a lot of context " * 20),
    ]

    compressed = asyncio.run(
        compress_messages(
            messages,
            task_goal="Goal: finish the task.",
            system_prompt="You are helpful.",
            settings=CompressionSettings(max_tokens=100, summary_trigger_ratio=0.6),
            summarizer=summarizer,
        )
    )

    assert compressed[0].content == "You are helpful."
    assert compressed[1].content == "Goal: finish the task."
    assert all(message.tool_result is None for message in compressed[:-1])
    assert summarizer.calls, "expected auto summary once token budget is exceeded"
