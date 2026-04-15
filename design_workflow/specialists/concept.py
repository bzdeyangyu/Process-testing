from __future__ import annotations

from design_workflow.specialists.common import (
    complete_with_llm,
    normalize_style_preferences,
    summarize_brief,
)

def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    styles = normalize_style_preferences(structured_brief)
    primary_style = styles[0] if styles else "科技感"
    concept_options = [
        {
            "name": "未来接口",
            "description": "以数字界面和沉浸媒体墙组织空间认知，突出企业技术能力。",
        },
        {
            "name": "智能剧场",
            "description": "把展厅视作可切换场景的发布空间，强化展示与演示兼容。",
        },
        {
            "name": "品牌实验室",
            "description": "通过开放式互动装置和可见技术细节建立专业信任。",
        },
    ]
    fallback = {
        "status": "ok",
        "output": f"完成概念提炼，主风格为 {primary_style}",
        "theme_statement": "以未来感科技空间承载品牌展示、互动体验与商务接待。",
        "concept_options": concept_options,
        "moodboard_keywords": [primary_style, "未来感", "沉浸式", "秩序感", "品牌展示"],
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是空间概念设计专家，只返回 JSON。",
        user_prompt=(
            "请给出展厅项目的设计主题、3 个概念方向和情绪板关键词。"
            f"\n项目: {summarize_brief(structured_brief)}"
            f"\n目标输出字段: status, output, theme_statement, concept_options, moodboard_keywords"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
