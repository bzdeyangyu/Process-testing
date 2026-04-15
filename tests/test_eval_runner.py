import json
from pathlib import Path
from tempfile import TemporaryDirectory

from evaluation.run_eval import load_fixtures, run_scope


def test_load_fixtures_reads_json_cases() -> None:
    with TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "case.json"
        fixture.write_text(
            json.dumps(
                {
                    "eval_id": "mvp-001",
                    "scope": "mvp",
                    "skill": "req_parser",
                    "input": {"brief": "800㎡ 科技展厅"},
                    "expected_fields": ["project_type"],
                }
            ),
            encoding="utf-8",
        )

        cases = load_fixtures(Path(temp_dir), scope="mvp")

    assert len(cases) == 1
    assert cases[0]["skill"] == "req_parser"


def test_run_scope_returns_pass_rate_and_failures() -> None:
    with TemporaryDirectory() as temp_dir:
        fixture = Path(temp_dir) / "case.json"
        fixture.write_text(
            json.dumps(
                {
                    "eval_id": "mvp-001",
                    "scope": "mvp",
                    "skill": "req_parser",
                    "input": {"brief": "800㎡ 科技展厅"},
                    "expected_fields": ["project_type", "area_sqm"],
                }
            ),
            encoding="utf-8",
        )

        report = run_scope(fixtures_dir=Path(temp_dir), scope="mvp")

    assert report["pass_rate"] == 1.0
    assert report["failures"] == []
    assert report["workflow_completion_rate"] == 1.0
    assert report["ablation_results"]
