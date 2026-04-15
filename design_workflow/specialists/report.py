from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm, summarize_brief

def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    style_key = input_dict.get("style_key", "tech-showroom")
    total_budget = input_dict.get("cost_estimate", {}).get("total_budget_wan", {"low": 0, "high": 0})
    slide_outline = [
        "项目背景与目标",
        "设计概念与故事线",
        "功能分区与空间动线",
        "材料色彩与视觉效果",
        "预算区间与实施节奏",
    ]
    fallback = {
        "status": "ok",
        "output": "完成汇报提纲与执行摘要",
        "executive_summary": (
            f"项目围绕 {summarize_brief(structured_brief)} 展开，采用 {style_key} 风格，"
            f"预算建议区间为 {total_budget['low']}-{total_budget['high']} 万元。"
        ),
        "slide_outline": slide_outline,
        "core_tables": ["功能分区面积表", "材料规格表", "预算概算表"],
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是展厅汇报整理专家，只返回 JSON。",
        user_prompt=(
            "请输出执行摘要、汇报页大纲和关键表格。"
            f"\n项目: {summarize_brief(structured_brief)}"
            f"\n预算: {total_budget}"
            f"\n目标输出字段: status, output, executive_summary, slide_outline, core_tables"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
