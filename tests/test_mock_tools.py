from design_workflow.tools.mock_tools import get_design_spec, wiki_lint, wiki_query


def test_get_design_spec_extracts_prompt_and_materials() -> None:
    spec = get_design_spec("tech-showroom")

    assert spec["style_key"] == "tech-showroom"
    assert len(spec["materials"]) >= 3
    assert len(spec["agent_prompt_guide"]) >= 3


def test_wiki_query_and_lint_return_structured_results() -> None:
    content = wiki_query(["materials", "guide"])
    report = wiki_lint()

    assert content is not None
    assert "Materials Guide" in content
    assert report["orphan_pages"] == []
