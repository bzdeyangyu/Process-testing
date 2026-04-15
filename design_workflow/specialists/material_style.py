from __future__ import annotations

import asyncio

from design_workflow.llm_helpers import request_json
from design_workflow.prompts.specialist_specs import (
    MATERIAL_STYLE_EXEC_PROMPT,
    MATERIAL_STYLE_SYSTEM_PROMPT,
)
from design_workflow.prompts.system_prompts import SYSTEM_PROMPTS
from design_workflow.prompts.scene_prompts import make_material_style_scene
from design_workflow.specialists.prompt_quality import palette_phrase_from_palette
from design_workflow.specialists.style_router import route_style
from design_workflow.tools.mock_tools import color_palette, get_design_spec, material_spec, wiki_update


def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    style_match = route_style(structured_brief)
    style_key = style_match["selected_style_key"]
    design_spec = get_design_spec(style_key)
    palette = color_palette(design_spec)
    base_material_spec = material_spec(design_spec, palette, structured_brief)
    fallback = {
        "style_key": style_key,
        "palette": palette,
        "materials": base_material_spec["materials"],
        "direction": base_material_spec["direction"],
        "lighting_concept": _default_lighting_concept(style_key),
    }

    wiki_update(
        page_name="material-style-log",
        content=f"{structured_brief.get('project_type', '空间')} -> {style_key}",
        source_agent="material_style",
    )

    llm_client = input_dict.get("llm_client")
    if llm_client is None:
        return _assemble_output(
            structured_brief=structured_brief,
            style_match=style_match,
            payload=fallback,
        )

    scene = make_material_style_scene(structured_brief)
    llm_result = asyncio.run(
        request_json(
            llm_client=llm_client,
            system_prompt=f"{SYSTEM_PROMPTS['material_style']}\n\n{MATERIAL_STYLE_SYSTEM_PROMPT}",
            user_prompt=(
                f"{scene}\n\n{MATERIAL_STYLE_EXEC_PROMPT}\n\n"
                f"selected_style_key={style_key}\n"
                f"top_candidates={style_match['top_candidates']}\n"
                f"tone_tags={style_match['tone_tags']}\n"
                f"项目需求={structured_brief}\n"
                f"设计库参考={design_spec['raw'][:1200]}"
            ),
            fallback=fallback,
        )
    )
    llm_result["style_key"] = style_key
    return _assemble_output(
        structured_brief=structured_brief,
        style_match=style_match,
        payload=llm_result,
    )


def _assemble_output(*, structured_brief: dict, style_match: dict, payload: dict) -> dict:
    palette = payload.get("palette", [])
    materials = payload.get("materials", [])
    direction = payload.get("direction", "")
    lighting_concept = payload.get("lighting_concept", "")
    style_key = payload["style_key"]
    material_payload = {
        "style_key": style_key,
        "project_type": structured_brief.get("project_type", "空间项目"),
        "palette": palette,
        "materials": materials,
        "direction": direction,
        "lighting_concept": lighting_concept,
        "style_match": style_match,
        "tone_tags": style_match["tone_tags"],
        "palette_summary": palette_phrase_from_palette(palette),
    }
    return {
        "style_key": style_key,
        "palette": palette,
        "materials": materials,
        "direction": direction,
        "lighting_concept": lighting_concept,
        "style_match": style_match,
        "material_spec": material_payload,
    }


def _default_lighting_concept(style_key: str) -> str:
    defaults = {
        "brand-experience": "使用可编程动态光强调品牌装置、打卡点与活动节奏，形成强传播感的镜头友好氛围。",
        "tech-showroom": "压低环境光并突出媒体面、交互装置与核心展品，让空间呈现冷静但不冰冷的科技张力。",
        "museum-narrative": "以层次柔和的叙事照明推进参观节奏，重点突出展品、文脉线索与空间停顿点。",
        "commercial-exhibition": "以高效均匀的基础照明配合重点展示灯，兼顾商品识别、动线引导与转化效率。",
        "cultural-space": "采用温和分层光环境强调公共性与停留感，营造开放、包容且具人文温度的场域。",
        "architectural-viz": "以清晰的结构洗墙和模型聚光强化建筑逻辑、尺度感与理性几何秩序。",
    }
    return defaults.get(style_key, "通过分层照明强化主次关系、材质表现和空间节奏。")
