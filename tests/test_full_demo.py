import json
from pathlib import Path
from tempfile import TemporaryDirectory

from demo.run_demo import run_demo


def test_run_demo_produces_full_workflow_outputs_and_images() -> None:
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        result = run_demo(
            brief="为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感。",
            output_dir=output_dir,
            use_real_llm=False,
            image_provider="mock",
        )

        log_path = output_dir / "demo_log.json"
        events = json.loads(log_path.read_text(encoding="utf-8"))
        board_path = output_dir / "board" / "project_board_current.json"
        board = json.loads(board_path.read_text(encoding="utf-8"))
        board_index = json.loads((output_dir / "board" / "project_board_index.json").read_text(encoding="utf-8"))

    assert "structured_brief" in result
    assert "material_spec" in result
    assert "visual_prompt" in result
    assert result["case_research"]["status"] == "ok"
    assert len(result["case_research"]["case_cards"]) == 3
    assert result["concept"]["status"] == "ok"
    assert len(result["concept"]["concept_options"]) == 3
    assert result["storyline"]["status"] == "ok"
    assert len(result["storyline"]["experience_sequence"]) >= 4
    assert result["zoning"]["status"] == "ok"
    assert len(result["zoning"]["zones"]) >= 5
    assert result["video_script"]["status"] == "ok"
    assert len(result["video_script"]["scene_sequence"]) >= 4
    assert result["cost_estimate"]["status"] == "ok"
    assert "total_budget_wan" in result["cost_estimate"]
    assert result["report"]["status"] == "ok"
    assert len(result["report"]["slide_outline"]) >= 4
    assert result["feedback"]["status"] == "ok"
    assert len(result["feedback"]["patch_actions"]) >= 2
    assert result["progress"]["status"] == "ok"
    assert 3 <= len(result["progress"]["milestones"]) <= 5
    assert "generated_schemes" in result
    assert result["generated_schemes"]
    assert all("images" in scheme for scheme in result["generated_schemes"])
    assert len(events) >= 24
    assert board["status"] == "done"
    assert board["overall_progress"] == 100
    assert board["completion_summary"]
    assert any(stage["specialist"] == "image_gen" and stage["status"] == "done" for stage in board["stages"])
    assert any(stage["specialist"] == "report" and stage["status"] == "done" for stage in board["stages"])
    assert any(artifact["key"] == "image_gen" and artifact["ready"] is True for artifact in board["artifacts"])
    assert any(artifact["key"] == "cost_estimate" and artifact["ready"] is True for artifact in board["artifacts"])
    assert board_index["runs"][0]["run_id"] == board["run_id"]
