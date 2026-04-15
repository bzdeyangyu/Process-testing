from __future__ import annotations

import inspect
import json
import shlex
import urllib.parse
import urllib.request
from asyncio.subprocess import PIPE
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Awaitable, Callable

from agent_runtime.storage import BlobStore
from agent_runtime.types import ToolResult

ToolHandler = Callable[..., Any] | Callable[..., Awaitable[Any]]


@dataclass(slots=True)
class ToolOutputPolicy:
    max_chars: int


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    handler: ToolHandler
    output_policy: ToolOutputPolicy
    input_schema: dict[str, Any] | None = None


class ToolRegistry:
    def __init__(self, loader: Callable[[], list[ToolSpec]]) -> None:
        self._loader = loader

    def list_tools(self) -> list[ToolSpec]:
        return self._loader()

    def resolve(self, name: str) -> ToolSpec | None:
        for tool in self.list_tools():
            if tool.name == name:
                return tool
        return None


@dataclass(slots=True)
class ExecRequest:
    program: str
    args: list[str]
    cwd: str | None = None
    env: dict[str, str] | None = None


async def materialize_tool_result(
    *,
    tool_name: str,
    output: Any,
    policy: ToolOutputPolicy,
    blob_store: BlobStore,
    call_id: str = "generated",
) -> ToolResult:
    rendered = _render_output(output)
    if len(rendered) > policy.max_chars:
        overflow_ref = await blob_store.write(rendered)
        return ToolResult(
            call_id=call_id,
            name=tool_name,
            output="[stored externally]",
            overflow_ref=overflow_ref,
        )
    return ToolResult(call_id=call_id, name=tool_name, output=rendered)


async def invoke_tool(spec: ToolSpec, arguments: dict[str, Any]) -> Any:
    result = spec.handler(**arguments)
    if inspect.isawaitable(result):
        return await result
    return result


async def run_exec(request: ExecRequest) -> str:
    if not isinstance(request.args, list) or not all(isinstance(arg, str) for arg in request.args):
        raise ValueError("ExecRequest.args must be a list of strings")

    import asyncio

    process = await asyncio.create_subprocess_exec(
        request.program,
        *request.args,
        stdout=PIPE,
        stderr=PIPE,
        cwd=request.cwd,
        env=request.env,
    )
    stdout, stderr = await process.communicate()
    output = stdout.decode("utf-8", errors="replace")
    error_output = stderr.decode("utf-8", errors="replace")
    combined = output if not error_output else f"{output}{error_output}"
    if process.returncode != 0:
        raise RuntimeError(combined.strip() or f"{request.program} exited with {process.returncode}")
    return combined


def create_read_file_tool() -> ToolSpec:
    async def handler(path: str, encoding: str = "utf-8") -> str:
        return Path(path).read_text(encoding=encoding)

    return ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file from disk.",
        handler=handler,
        output_policy=ToolOutputPolicy(max_chars=20_000),
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "encoding": {"type": "string"},
            },
            "required": ["path"],
        },
    )


def create_search_tool() -> ToolSpec:
    async def handler(pattern: str, root: str = ".") -> str:
        matches: list[str] = []
        base = Path(root)
        for file_path in sorted(path for path in base.rglob("*") if path.is_file()):
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for line_no, line in enumerate(content.splitlines(), start=1):
                if pattern in line:
                    relative = file_path.relative_to(base)
                    matches.append(f"{relative}:{line_no}:{line}")
        return "\n".join(matches) if matches else "No matches found."

    return ToolSpec(
        name="search",
        description="Search UTF-8 text files under a directory.",
        handler=handler,
        output_policy=ToolOutputPolicy(max_chars=10_000),
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "root": {"type": "string"},
            },
            "required": ["pattern"],
        },
    )


def create_shell_tool() -> ToolSpec:
    async def handler(command: str, cwd: str | None = None) -> str:
        parts = shlex.split(command, posix=True)
        if not parts:
            raise ValueError("Shell command cannot be empty")
        return await run_exec(ExecRequest(program=parts[0], args=parts[1:], cwd=cwd))

    return ToolSpec(
        name="shell",
        description="Run a command through exec with an argv array.",
        handler=handler,
        output_policy=ToolOutputPolicy(max_chars=15_000),
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
            },
            "required": ["command"],
        },
    )


def create_git_tool() -> ToolSpec:
    async def handler(args: list[str], cwd: str | None = None) -> str:
        return await run_exec(ExecRequest(program="git", args=args, cwd=cwd))

    return ToolSpec(
        name="git",
        description="Run a git subcommand through exec with argv args.",
        handler=handler,
        output_policy=ToolOutputPolicy(max_chars=15_000),
        input_schema={
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "cwd": {"type": "string"},
            },
            "required": ["args"],
        },
    )


def create_web_search_tool(
    transport: Callable[[str, int], Awaitable[str]] | None = None,
) -> ToolSpec:
    effective_transport = transport or duckduckgo_html_transport()

    async def handler(query: str, limit: int = 5) -> str:
        html = await effective_transport(query, limit)
        parser = _DuckDuckGoResultParser(limit=limit)
        parser.feed(html)
        if not parser.results:
            return "No web results found."
        return "\n".join(f"{item['title']} - {item['url']}" for item in parser.results)

    return ToolSpec(
        name="web_search",
        description="Search the web and return top results.",
        handler=handler,
        output_policy=ToolOutputPolicy(max_chars=10_000),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    )


def built_in_tool_specs() -> list[ToolSpec]:
    return [
        create_read_file_tool(),
        create_search_tool(),
        create_shell_tool(),
        create_git_tool(),
        create_web_search_tool(),
    ]


def duckduckgo_html_transport(
    *,
    base_url: str = "https://html.duckduckgo.com/html/",
) -> Callable[[str, int], Awaitable[str]]:
    async def transport(query: str, limit: int) -> str:
        del limit

        def fetch() -> str:
            url = f"{base_url}?{urllib.parse.urlencode({'q': query})}"
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "agent-runtime/0.1",
                },
            )
            with urllib.request.urlopen(request) as response:
                return response.read().decode("utf-8", errors="replace")

        import asyncio

        return await asyncio.to_thread(fetch)

    return transport


def _render_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return str(output)


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self, *, limit: int) -> None:
        super().__init__()
        self._limit = limit
        self._current_href: str | None = None
        self._current_title: list[str] = []
        self.results: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(self.results) >= self._limit or tag != "a":
            return
        attr_map = dict(attrs)
        classes = attr_map.get("class", "")
        href = attr_map.get("href")
        if href and "result-link" in classes:
            self._current_href = href
            self._current_title = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_title.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        title = " ".join(part for part in self._current_title if part).strip()
        if title:
            self.results.append({"title": title, "url": self._current_href})
        self._current_href = None
        self._current_title = []
