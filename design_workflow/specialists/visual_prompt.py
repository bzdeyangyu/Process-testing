from __future__ import annotations

import asyncio

from design_workflow.llm_helpers import request_json
from design_workflow.prompts.specialist_specs import (
    VISUAL_BLUEPRINT_EXEC_PROMPT,
    VISUAL_BLUEPRINT_SYSTEM_PROMPT,
)
from design_workflow.prompts.system_prompts import SYSTEM_PROMPTS
from design_workflow.prompts.scene_prompts import make_visual_prompt_scene
from design_workflow.specialists.prompt_quality import compile_prompt, palette_phrase_from_palette, validate_prompt, repair_prompt
from design_workflow.tools.mock_tools import get_design_spec

VIEW_ANGLES = [
    ("floor_plan", "平面图"),
    ("mood_board", "氛围图"),
    ("main_view_1", "主效果图1"),
    ("main_view_2", "主效果图2"),
    ("node_view_1", "节点效果图1"),
    ("node_view_2", "节点效果图2"),
]

FALLBACK_SCHEMES = [
    {
        "scheme_id": "A",
        "scheme_name": "品牌主推",
        "scheme_description": "围绕品牌识别与到达记忆点展开，强调高完成度、强传播感与客户接待体验。",
        "style_variant": "成熟稳健的主推版本",
        "mood_keywords": ["premium", "immersive", "confident"],
        "feature_focus": "a branded arrival centerpiece",
        "lighting_focus": "controlled contrast lighting with programmable media glow",
    },
    {
        "scheme_id": "B",
        "scheme_name": "叙事强化",
        "scheme_description": "突出空间节奏与场景转折，通过更强的戏剧化节点制造沉浸体验与记忆峰值。",
        "style_variant": "更具戏剧张力的创意版本",
        "mood_keywords": ["dramatic", "cinematic", "layered"],
        "feature_focus": "a narrative media installation",
        "lighting_focus": "dramatic highlights and richer shadow layering",
    },
    {
        "scheme_id": "C",
        "scheme_name": "高效落地",
        "scheme_description": "以成本效率和实施稳定性为优先，保留核心品牌表达与关键互动体验。",
        "style_variant": "更高效可落地的经济版本",
        "mood_keywords": ["clean", "efficient", "refined"],
        "feature_focus": "a clear display spine",
        "lighting_focus": "efficient ambient lighting with precise focal accents",
    },
]


def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    material_spec = input_dict["material_spec"]
    style_key = material_spec.get("style_key", "tech-showroom")
    design_spec = get_design_spec(style_key)

    fallback_blueprints = _fallback_blueprints(material_spec)
    blueprints = fallback_blueprints
    llm_client = input_dict.get("llm_client")
    if llm_client is not None:
        scene = make_visual_prompt_scene(structured_brief, material_spec)
        raw_result = asyncio.run(
            request_json(
                llm_client=llm_client,
                system_prompt=f"{SYSTEM_PROMPTS['visual_prompt']}\n\n{VISUAL_BLUEPRINT_SYSTEM_PROMPT}",
                user_prompt=(
                    f"{scene}\n\n{VISUAL_BLUEPRINT_EXEC_PROMPT}\n\n"
                    f"项目需求={structured_brief}\n"
                    f"材料规格={material_spec}\n"
                    f"设计库参考={design_spec['agent_prompt_guide'][0] if design_spec['agent_prompt_guide'] else ''}"
                ),
                fallback={"summary": fallback_summary(structured_brief), "schemes": fallback_blueprints},
            )
        )
        blueprints = _normalize_blueprints(raw_result.get("schemes", []), fallback_blueprints)
        summary = raw_result.get("summary", fallback_summary(structured_brief))
    else:
        summary = fallback_summary(structured_brief)

    schemes = [
        _compile_scheme(structured_brief=structured_brief, material_spec=material_spec, blueprint=scheme)
        for scheme in blueprints
    ]
    quality_report = _aggregate_quality(schemes)

    return {
        "style_key": style_key,
        "summary": summary,
        "schemes": schemes,
        "visual_prompts": [
            {"angle": view["angle_label"], "prompt": view["prompt"]}
            for view in schemes[0]["views"]
        ],
        "visual_prompt": schemes[0]["views"][2]["prompt"],
        "quality_report": quality_report,
    }


def fallback_summary(structured_brief: dict) -> str:
    project_type = structured_brief.get("project_type", "空间设计")
    return f"{project_type}输出三套可视化方案，每套包含6类视角并通过质量校验。"


def _fallback_blueprints(material_spec: dict) -> list[dict]:
    style_key = material_spec.get("style_key", "tech-showroom")
    style_variant_prefix = style_key.replace("-", " ")
    blueprints = []
    for scheme in FALLBACK_SCHEMES:
        blueprints.append({
            **scheme,
            "style_variant": f"{style_variant_prefix} / {scheme['style_variant']}",
        })
    return blueprints


def _normalize_blueprints(raw_schemes: list, fallback_schemes: list[dict]) -> list[dict]:
    normalized = []
    for index, fallback in enumerate(fallback_schemes):
        raw = raw_schemes[index] if index < len(raw_schemes) and isinstance(raw_schemes[index], dict) else {}
        normalized.append({
            "scheme_id": raw.get("scheme_id", fallback["scheme_id"]),
            "scheme_name": raw.get("scheme_name", fallback["scheme_name"]),
            "scheme_description": raw.get("scheme_description", fallback["scheme_description"]),
            "style_variant": raw.get("style_variant", fallback["style_variant"]),
            "mood_keywords": raw.get("mood_keywords", fallback["mood_keywords"]),
            "feature_focus": raw.get("feature_focus", fallback["feature_focus"]),
            "lighting_focus": raw.get("lighting_focus", fallback["lighting_focus"]),
        })
    return normalized


def _compile_scheme(*, structured_brief: dict, material_spec: dict, blueprint: dict) -> dict:
    palette_phrase = palette_phrase_from_palette(material_spec.get("palette", []))
    material_phrase = ", ".join(material_spec.get("materials", [])[:2]) or "LED acrylic, digital fabric screen"
    lighting_phrase = _to_english_lighting(blueprint.get("lighting_focus") or material_spec.get("lighting_concept", "layered professional lighting"))
    mood_phrase = ", ".join(blueprint.get("mood_keywords", ["immersive", "premium", "refined"])[:2])
    audience_phrase = _to_english_audience(structured_brief.get("audience", "professional visitors"))
    scheme_label = _to_english_variant(blueprint.get("style_variant", "flagship scheme"))
    scheme_description = _to_english_description(blueprint.get("scheme_description", "high-impact branded environment"))
    feature_phrase = blueprint.get("feature_focus", "a spatial brand centerpiece")
    style_label = material_spec.get("style_key", "tech-showroom").replace("-", " ")
    location = structured_brief.get("location")

    # LLM 已按视角结构生成的 views（key: angle → prompt）
    llm_views: dict[str, str] = {}
    for v in blueprint.get("views", []):
        angle = v.get("angle", "")
        prompt = v.get("prompt", "").strip()
        if angle and prompt:
            llm_views[angle] = prompt

    views = []
    for angle, angle_label in VIEW_ANGLES:
        if angle in llm_views:
            # 优先使用 LLM 生成的 prompt，先修复 banned params，再做质量校验
            prompt = repair_prompt(llm_views[angle])
            quality_report = validate_prompt(prompt)
        else:
            # LLM 未提供此视角时，用 compile_prompt 作 fallback
            prompt, quality_report = compile_prompt(
                project_type=structured_brief.get("project_type", "企业展厅"),
                location=location,
                style_label=style_label,
                angle=angle,
                scheme_label=scheme_label,
                scheme_description=scheme_description,
                material_phrase=material_phrase,
                palette_phrase=palette_phrase,
                lighting_phrase=lighting_phrase,
                mood_phrase=mood_phrase,
                audience_phrase=audience_phrase,
                feature_phrase=feature_phrase,
            )
        views.append({
            "angle": angle,
            "angle_label": angle_label,
            "prompt": prompt,
            "quality_report": quality_report,
        })

    passed_count = sum(1 for view in views if view["quality_report"]["passed"])
    return {
        "scheme_id": blueprint["scheme_id"],
        "scheme_name": blueprint["scheme_name"],
        "scheme_description": blueprint["scheme_description"],
        "style_variant": blueprint["style_variant"],
        "views": views,
        "quality_summary": {
            "passed_count": passed_count,
            "total_count": len(views),
            "all_passed": passed_count == len(views),
        },
    }


def _aggregate_quality(schemes: list[dict]) -> dict:
    reports = [view["quality_report"] for scheme in schemes for view in scheme["views"]]
    passed_count = sum(1 for report in reports if report["passed"])
    return {
        "passed_count": passed_count,
        "total_count": len(reports),
        "all_passed": passed_count == len(reports),
        "length_band": "320-460 chars",
    }


def _to_english_lighting(text: str) -> str:
    replacements = {
        "品牌": "brand",
        "动态": "dynamic",
        "对比": "contrast",
        "层次": "layered",
        "重点": "focused",
        "氛围": "ambient",
    }
    return _replace_keywords(text, replacements, default="controlled layered lighting", limit=2)


def _to_english_audience(text: str) -> str:
    replacements = {
        "品牌客户": "brand clients",
        "合作伙伴": "partners",
        "企业客户": "enterprise visitors",
        "访客": "visitors",
        "消费者": "consumers",
        "媒体": "media guests",
    }
    return _replace_keywords(text, replacements, default="professional visitors", limit=2)


def _to_english_variant(text: str) -> str:
    replacements = {
        "主推": "flagship",
        "成熟": "mature",
        "稳健": "confident",
        "创意": "creative",
        "戏剧": "cinematic",
        "经济": "efficient",
        "落地": "practical",
    }
    return _replace_keywords(text, replacements, default="flagship", limit=2)


def _to_english_description(text: str) -> str:
    replacements = {
        "品牌": "brand",
        "记忆点": "memorable focal points",
        "传播": "shareable media presence",
        "空间节奏": "layered spatial rhythm",
        "沉浸": "immersive experience",
        "成本效率": "cost-aware execution",
        "实施稳定性": "delivery stability",
    }
    return _replace_keywords(text, replacements, default="high-impact branded environment", limit=2)


def _replace_keywords(text: str, replacements: dict[str, str], default: str, limit: int | None = None) -> str:
    parts = []
    for source, target in replacements.items():
        if source in text:
            parts.append(target)
    if not parts:
        return default
    unique_parts = list(dict.fromkeys(parts))
    if limit is not None:
        unique_parts = unique_parts[:limit]
    return ", ".join(unique_parts)
