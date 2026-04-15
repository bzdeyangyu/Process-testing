import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_runtime.storage import InMemoryBlobStore
from agent_runtime.tools import (
    ExecRequest,
    ToolOutputPolicy,
    create_git_tool,
    create_read_file_tool,
    create_search_tool,
    create_shell_tool,
    create_web_search_tool,
    materialize_tool_result,
    run_exec,
)


def test_tool_result_overflow_is_stored_externally() -> None:
    blob_store = InMemoryBlobStore()
    policy = ToolOutputPolicy(max_chars=5)

    result = asyncio.run(
        materialize_tool_result(
            tool_name="reader",
            output="123456789",
            policy=policy,
            blob_store=blob_store,
        )
    )

    assert result.overflow_ref is not None
    assert result.output == "[stored externally]"
    assert blob_store.read(result.overflow_ref) == "123456789"


def test_run_exec_uses_program_and_args_array() -> None:
    output = asyncio.run(
        run_exec(
            ExecRequest(
                program="python",
                args=["-c", "print('hi')"],
            )
        )
    )

    assert output.strip() == "hi"


def test_run_exec_rejects_string_command_concatenation() -> None:
    try:
        asyncio.run(run_exec(ExecRequest(program="python", args="-c print('hi')")))  # type: ignore[arg-type]
    except ValueError as exc:
        assert "list" in str(exc)
    else:
        raise AssertionError("Expected run_exec to reject string args")


def test_read_file_tool_reads_utf8_content() -> None:
    with TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "note.txt"
        file_path.write_text("line 1\nline 2\n", encoding="utf-8")
        tool = create_read_file_tool()

        output = asyncio.run(tool.handler(path=str(file_path)))

    assert "line 1" in output
    assert "line 2" in output


def test_search_tool_finds_matches_with_line_numbers() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "a.txt").write_text("hello\nneedle here\n", encoding="utf-8")
        (root / "b.txt").write_text("no match\n", encoding="utf-8")
        tool = create_search_tool()

        output = asyncio.run(tool.handler(pattern="needle", root=str(root)))

    assert "a.txt:2:needle here" in output


def test_shell_tool_runs_via_exec_wrapper() -> None:
    tool = create_shell_tool()

    output = asyncio.run(tool.handler(command="python -c \"print('hi')\""))

    assert output.strip() == "hi"


def test_git_tool_runs_git_subcommand() -> None:
    tool = create_git_tool()

    output = asyncio.run(tool.handler(args=["--version"]))

    assert "git version" in output.lower()


def test_web_search_tool_parses_duckduckgo_html_results() -> None:
    html = """
    <html><body>
      <a class="result-link" href="https://example.com/a">Example A</a>
      <a class="result-link" href="https://example.com/b">Example B</a>
    </body></html>
    """

    async def fake_transport(query: str, limit: int) -> str:
        assert query == "agent runtime"
        assert limit == 2
        return html

    tool = create_web_search_tool(transport=fake_transport)

    output = asyncio.run(tool.handler(query="agent runtime", limit=2))

    assert "Example A" in output
    assert "https://example.com/a" in output
