import json
from pathlib import Path
from tempfile import TemporaryDirectory

from demo.sync_mock_project import run_mock_project_sync


def test_run_mock_project_sync_writes_mock_outputs_and_board_snapshot() -> None:
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"

        result = run_mock_project_sync(output_dir=output_dir)

        mock_result_path = output_dir / "mock_project_result.json"
        board_path = output_dir / "board" / "project_board_current.json"
        board_index_path = output_dir / "board" / "project_board_index.json"

        assert mock_result_path.exists()
        assert board_path.exists()
        assert board_index_path.exists()

        stored_result = json.loads(mock_result_path.read_text(encoding="utf-8"))
        board = json.loads(board_path.read_text(encoding="utf-8"))
        board_index = json.loads(board_index_path.read_text(encoding="utf-8"))

    assert result["structured_brief"]["project_type"] == "医疗科技企业展厅"
    assert result["structured_brief"]["location"] == "南京"
    assert result["structured_brief"]["budget_cny"] == {"low": 4_000_000, "high": 8_000_000}
    assert result["concept"]["status"] == "ok"
    assert len(result["concept"]["concept_options"]) == 3
    assert result["zoning"]["status"] == "ok"
    assert len(result["zoning"]["zones"]) >= 5
    assert result["report"]["status"] == "ok"
    assert len(result["report"]["slide_outline"]) >= 5
    assert result["video_script"]["status"] == "ok"
    assert len(result["video_script"]["scene_sequence"]) >= 3

    assert stored_result["project_packet"]["mode"] == "mock"
    assert stored_result["result"]["structured_brief"]["project_type"] == "医疗科技企业展厅"

    assert board["status"] == "done"
    assert board["mode"] == "mock"
    assert "南京" in board["title"]
    assert board["current_situation"].endswith("13/13 个阶段。")
    assert any(stage["specialist"] == "report" and stage["status"] == "done" for stage in board["stages"])
    assert any(stage["specialist"] == "video_script" and stage["status"] == "done" for stage in board["stages"])
    assert any(artifact["key"] == "structured_brief" and artifact["ready"] is True for artifact in board["artifacts"])
    assert any(artifact["key"] == "report" and artifact["ready"] is True for artifact in board["artifacts"])
    assert any(artifact["key"] == "video_script" and artifact["ready"] is True for artifact in board["artifacts"])
    assert board_index["runs"][0]["run_id"] == board["run_id"]
