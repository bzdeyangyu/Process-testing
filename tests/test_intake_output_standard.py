from pathlib import Path
from tempfile import TemporaryDirectory

from demo.run_mvp import run_mvp
from design_workflow.specialists.req_parser import handle as req_parser_handle


def test_req_parser_builds_output_standard_review_and_follow_up_questions() -> None:
    result = req_parser_handle({
        "brief": "为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感，需要沉浸式互动体验。",
        "llm_client": None,
    })

    review = result["output_standard_review"]

    assert review["standard_id"] == "five-sample-v1"
    assert review["passed"] is False
    assert review["coverage_score"] < 100
    assert review["target_sections"] == ["项目任务书", "场地踏勘资料", "会议决策回灌"]
    assert any("预算" in item for item in review["missing_critical_items"])
    assert any("场地" in item for item in review["missing_critical_items"])
    assert any("会议" in item for item in review["missing_critical_items"])

    questions = result["follow_up_questions"]
    assert len(questions) >= 4
    assert any(question["field"] == "location" for question in questions)
    assert any(question["field"] == "budget_cny" for question in questions)
    assert any(question["field"] == "site_assets" for question in questions)
    assert any(question["field"] == "meeting_feedback" for question in questions)


def test_run_mvp_surfaces_intake_review_for_simple_brief() -> None:
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        result = run_mvp(
            brief="为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感，需要沉浸式互动体验。",
            output_dir=output_dir,
            use_real_llm=False,
            image_provider="mock",
        )

    structured_brief = result["structured_brief"]
    review = structured_brief["output_standard_review"]

    assert review["passed"] is False
    assert review["coverage_score"] < 100
    assert len(structured_brief["follow_up_questions"]) >= 4
    assert len(structured_brief["recommended_retrievals"]) >= 2
