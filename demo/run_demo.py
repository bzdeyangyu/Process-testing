from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for candidate in (ROOT_DIR, SRC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from config import API_KEY, LLM_BASE_URL, MODEL_NAME, OUTPUT_DIR
from agent_runtime.board import PROJECT_ID, PROJECT_NAME, ProjectBoardTracker
from agent_runtime.logger import EventLogger
from agent_runtime.skill_registry import SkillDef, SkillRegistry
from design_workflow.agents.orchestrator import run_full_workflow
from design_workflow.llm_client import create_glm_client
from design_workflow.specialists.case_research import handle as case_research_handle
from design_workflow.specialists.concept import handle as concept_handle
from design_workflow.specialists.cost_estimate import handle as cost_estimate_handle
from design_workflow.specialists.feedback import handle as feedback_handle
from design_workflow.specialists.material_style import handle as material_style_handle
from design_workflow.specialists.progress import handle as progress_handle
from design_workflow.specialists.report import handle as report_handle
from design_workflow.specialists.req_parser import handle as req_parser_handle
from design_workflow.specialists.storyline import handle as storyline_handle
from design_workflow.specialists.video_script import handle as video_script_handle
from design_workflow.specialists.visual_prompt import handle as visual_prompt_handle
from design_workflow.specialists.zoning import handle as zoning_handle
from design_workflow.tools.mock_tools import wiki_lint

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "cogview")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", API_KEY)


def build_full_registry() -> SkillRegistry:
    registry = SkillRegistry()
    definitions = [
        ("req_parser", req_parser_handle, ["project_type", "area_sqm"]),
        ("case_research", case_research_handle, ["status", "output"]),
        ("concept", concept_handle, ["status", "output"]),
        ("storyline", storyline_handle, ["status", "output"]),
        ("zoning", zoning_handle, ["status", "output"]),
        ("material_style", material_style_handle, ["material_spec"]),
        ("visual_prompt", visual_prompt_handle, ["visual_prompt"]),
        ("video_script", video_script_handle, ["status", "output"]),
        ("cost_estimate", cost_estimate_handle, ["status", "output"]),
        ("report", report_handle, ["status", "output"]),
        ("feedback", feedback_handle, ["status", "output"]),
        ("progress", progress_handle, ["status", "output"]),
    ]
    for name, handler, required in definitions:
        registry.register_skill(
            SkillDef(
                name=name,
                description=f"{name} specialist",
                input_schema={"type": "object"},
                output_schema={"type": "object", "required": required},
                handler=handler,
                upgrade_path=f"agents/{name.replace('_', '-')}-agent.md",
                tools=[],
                hooks=[],
            )
        )
    return registry


def run_demo(
    *,
    brief: str,
    output_dir: Path | None = None,
    use_real_llm: bool = True,
    image_provider: str = IMAGE_PROVIDER,
    image_api_key: str | None = IMAGE_API_KEY,
    image_max_workers: int | None = None,
) -> dict:
    effective_output_dir = Path(output_dir or OUTPUT_DIR)
    effective_output_dir.mkdir(parents=True, exist_ok=True)
    trace_id = str(uuid4())
    board_tracker = ProjectBoardTracker(
        board_dir=effective_output_dir / "board",
        project_id=PROJECT_ID,
        project_name=PROJECT_NAME,
        run_id=trace_id,
        title=_build_run_title(brief),
        brief=brief,
        mode="demo",
    )
    board_tracker.start()
    logger = EventLogger(effective_output_dir / "demo_log.json")
    registry = build_full_registry()
    llm_client = create_glm_client(api_key=API_KEY, base_url=LLM_BASE_URL, model=MODEL_NAME) if use_real_llm else None
    try:
        result = run_full_workflow(
            brief=brief,
            trace_id=trace_id,
            skill_registry=registry,
            logger=logger,
            llm_client=llm_client,
            board_tracker=board_tracker,
            image_provider=image_provider,
            image_api_key=image_api_key,
            image_output_dir=effective_output_dir / "renders",
            image_max_workers=image_max_workers,
        )
        logger.dump()
        (effective_output_dir / "demo_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (effective_output_dir / "wiki_lint_report.json").write_text(
            json.dumps(wiki_lint(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        image_result = {
            "generated_schemes": result.get("generated_schemes", []),
            "generated_images": result.get("generated_images", []),
        }
        board_tracker.finish(result, result=image_result)
        return result
    except Exception as exc:
        board_tracker.fail(f"运行失败：{exc}")
        raise


def _build_run_title(brief: str) -> str:
    normalized = " ".join(brief.split())
    return normalized[:40] if len(normalized) > 40 else normalized


if __name__ == "__main__":
    sample_brief = "为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感。"
    result = run_demo(brief=sample_brief, use_real_llm=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
