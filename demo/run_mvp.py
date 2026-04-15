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

from config import API_KEY, LLM_BASE_URL, MODEL_NAME, OUTPUT_DIR, IMAGE_API_KEY as _CONFIG_IMAGE_API_KEY
from agent_runtime.board import PROJECT_ID, PROJECT_NAME, ProjectBoardTracker
from agent_runtime.logger import EventLogger
from agent_runtime.schemas import EventEnvelope
from agent_runtime.skill_registry import SkillDef, SkillRegistry
from design_workflow.agents.orchestrator import run_mvp_workflow
from design_workflow.llm_client import create_glm_client
from design_workflow.specialists.material_style import handle as material_style_handle
from design_workflow.specialists.req_parser import handle as req_parser_handle
from design_workflow.specialists.visual_prompt import handle as visual_prompt_handle

# ── 图像生成配置 ─────────────────────────────────────────────────────────────
# 优先级：cogview（智谱同账号） > wanx（通义万象需单独 key） > mock（开发测试）
#
# 使用 CogView（推荐，同账号）：
#   export IMAGE_PROVIDER=cogview
#   export IMAGE_API_KEY=<你的智谱 API Key>  （不填则复用 GLM API_KEY）
#
# 使用 通义万象：
#   export IMAGE_PROVIDER=wanx
#   export IMAGE_API_KEY=<你的 DashScope API Key>
#
# Mock 模式（不消耗 API，用占位图）：
#   export IMAGE_PROVIDER=mock
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "cogview")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", _CONFIG_IMAGE_API_KEY)  # 优先环境变量，其次 config 中的生图专用 key


def build_mvp_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register_skill(
        SkillDef(
            name="req_parser",
            description="Parse customer requirement briefs.",
            input_schema={"type": "object", "required": ["brief"]},
            output_schema={"type": "object", "required": ["project_type", "area_sqm"]},
            handler=req_parser_handle,
            upgrade_path="agents/req-parser-agent.md",
            tools=["parse_brief", "extract_constraints", "validate_requirements"],
            hooks=[],
        )
    )
    registry.register_skill(
        SkillDef(
            name="material_style",
            description="Generate material and color guidance.",
            input_schema={"type": "object", "required": ["structured_brief"]},
            output_schema={"type": "object", "required": ["material_spec"]},
            handler=material_style_handle,
            upgrade_path="agents/material-style-agent.md",
            tools=["get_design_spec", "color_palette", "material_spec", "wiki_update"],
            hooks=["PostToolUse"],
        )
    )
    registry.register_skill(
        SkillDef(
            name="visual_prompt",
            description="Compose visual prompts from style constraints.",
            input_schema={"type": "object", "required": ["structured_brief", "material_spec"]},
            output_schema={"type": "object", "required": ["visual_prompt"]},
            handler=visual_prompt_handle,
            upgrade_path="agents/visual-prompt-agent.md",
            tools=["get_design_spec", "style_inject"],
            hooks=[],
        )
    )
    return registry


def run_mvp(
    *,
    brief: str,
    output_dir: Path | None = None,
    use_real_llm: bool = True,
    image_provider: str = IMAGE_PROVIDER,
    image_api_key: str | None = IMAGE_API_KEY,
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
        mode="mvp",
    )
    board_tracker.start()
    logger = EventLogger(effective_output_dir / "mvp_log.json")
    registry = build_mvp_registry()
    llm_client = (
        create_glm_client(api_key=API_KEY, base_url=LLM_BASE_URL, model=MODEL_NAME)
        if use_real_llm
        else None
    )
    try:
        result = run_mvp_workflow(
            brief=brief,
            trace_id=trace_id,
            skill_registry=registry,
            logger=logger,
            use_real_llm=use_real_llm,
            llm_client=llm_client,
            board_tracker=board_tracker,
            image_provider=image_provider,
            image_api_key=image_api_key,
            image_output_dir=effective_output_dir / "renders",
        )
        logger.dump()
        (effective_output_dir / "mvp_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # 将图片生成结果写入 board result 字段，供看板画廊读取
        image_result = {
            "generated_schemes": result.get("generated_schemes", []),
            "generated_images": result.get("generated_images", []),
        }
        board_tracker.finish(result, result=image_result)
        return result
    except Exception as exc:
        board_tracker.fail(f"运行失败：{exc}")
        raise


def emit_status(logger: EventLogger, trace_id: str, producer: str, state: str) -> None:
    logger.emit(
        EventEnvelope(
            trace_id=trace_id,
            topic="task.status",
            event_type=state,
            producer=producer,
            payload={"state": state},
        )
    )


def _build_run_title(brief: str) -> str:
    normalized = " ".join(brief.split())
    return normalized[:40] if len(normalized) > 40 else normalized


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI 空间设计 MVP 工作流")
    parser.add_argument("--brief", default="为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感，要求沉浸式互动体验。")
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM，使用关键词匹配 fallback")
    parser.add_argument("--image-provider", default=IMAGE_PROVIDER, choices=["cogview", "wanx", "mock"])
    parser.add_argument("--image-api-key", default=IMAGE_API_KEY)
    args = parser.parse_args()

    print(f"[MVP] 任务书: {args.brief}")
    print(f"[MVP] LLM: {'关闭(mock)' if args.no_llm else '开启(GLM-4)'}")
    print(f"[MVP] 生图: {args.image_provider}")
    print()

    result = run_mvp(
        brief=args.brief,
        use_real_llm=not args.no_llm,
        image_provider=args.image_provider,
        image_api_key=args.image_api_key,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
