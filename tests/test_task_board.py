import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_runtime.board import ProjectBoardRepository, ProjectBoardTracker


def test_project_board_tracker_writes_snapshot_and_style_route_details() -> None:
    with TemporaryDirectory() as temp_dir:
        board_dir = Path(temp_dir) / "board"
        tracker = ProjectBoardTracker(
            board_dir=board_dir,
            project_id="space-design-workflow",
            project_name="AI空间设计工作流",
            run_id="run-1",
            title="南京 800㎡ 企业展厅",
            brief="南京 800㎡ 企业展厅，科技感但不要太冷。",
            mode="demo",
        )

        tracker.start()
        tracker.mark_stage_running("req_parser")
        tracker.mark_stage_completed(
            "req_parser",
            {
                "project_type": "企业展厅设计",
                "area_sqm": 800,
                "audience": ["客户", "访客"],
            },
        )
        tracker.mark_stage_running("material_style")
        tracker.mark_stage_completed(
            "material_style",
            {
                "style_key": "brand-experience",
                "palette": [{"name": "primary", "hex": "#6C3EFF"}],
                "material_spec": {
                    "style_key": "brand-experience",
                    "palette": [{"name": "primary", "hex": "#6C3EFF"}],
                },
                "lighting_concept": "强化品牌装置和到达记忆点。",
                "style_match": {
                    "selected_style_key": "brand-experience",
                    "confidence": "medium",
                    "top_candidates": [
                        {"style_key": "brand-experience", "score": 18, "reasons": ["special_requirements:品牌展示"]},
                        {"style_key": "tech-showroom", "score": 14, "reasons": ["style_preferences:科技"]},
                    ],
                    "tone_tags": ["科技感", "未来感", "品牌展示"],
                },
            },
        )
        tracker.finish(
            {
                "structured_brief": {
                    "project_type": "企业展厅设计",
                    "area_sqm": 800,
                },
                "style_key": "brand-experience",
                "material_spec": {"style_key": "brand-experience"},
                "visual_prompt": "Brand-led corporate exhibition hall in Nanjing...",
            }
        )

        snapshot = json.loads((board_dir / "project_board_run-1.json").read_text(encoding="utf-8"))
        history = json.loads((board_dir / "project_board_index.json").read_text(encoding="utf-8"))
        repository = ProjectBoardRepository(board_dir)
        loaded = repository.get_project_card("run-1")

    assert snapshot["status"] == "done"
    assert snapshot["overall_progress"] == 100
    assert snapshot["completion_summary"]
    assert snapshot["current_situation"].startswith("本次项目")
    material_stage = next(stage for stage in snapshot["stages"] if stage["specialist"] == "material_style")
    assert material_stage["output"]["style_key"] == "brand-experience"
    assert material_stage["output"]["style_match"]["selected_style_key"] == "brand-experience"
    assert material_stage["output"]["style_match"]["top_candidates"][0]["style_key"] == "brand-experience"
    assert material_stage["output"]["style_match"]["tone_tags"] == ["科技感", "未来感", "品牌展示"]
    assert any(artifact["key"] == "visual_prompt" and artifact["ready"] is True for artifact in snapshot["artifacts"])
    assert history["runs"][0]["run_id"] == "run-1"
    assert loaded["title"] == "南京 800㎡ 企业展厅"
