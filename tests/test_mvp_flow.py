import json
from pathlib import Path
from tempfile import TemporaryDirectory

from demo.run_mvp import run_mvp


def test_run_mvp_writes_event_log_and_outputs_core_sections() -> None:
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        result = run_mvp(
            brief="为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感。",
            output_dir=output_dir,
            use_real_llm=False,
        )

        log_path = output_dir / "mvp_log.json"
        events = json.loads(log_path.read_text(encoding="utf-8"))

    assert result["structured_brief"]["area_sqm"] == 800
    assert "material_spec" in result
    assert "visual_prompt" in result
    assert len(events) >= 6
    assert {event["topic"] for event in events} >= {"skill.invoke", "task.status"}
