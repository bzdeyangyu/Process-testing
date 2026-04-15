from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm, summarize_brief

def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    area_sqm = structured_brief.get("area_sqm", 800)
    zones = [
        {"name": "入口品牌焦点区", "area_sqm": 90, "purpose": "树立第一印象与欢迎引导"},
        {"name": "企业叙事区", "area_sqm": 130, "purpose": "展示发展历程与技术实力"},
        {"name": "互动体验区", "area_sqm": 180, "purpose": "承载沉浸式交互与演示"},
        {"name": "产品展示区", "area_sqm": 170, "purpose": "集中呈现核心产品与解决方案"},
        {"name": "发布路演区", "area_sqm": 140, "purpose": "支持演讲、媒体发布和临时活动"},
        {"name": "VIP 洽谈区", "area_sqm": 60, "purpose": "高质量接待与商务洽谈"},
    ]
    total_area = sum(zone["area_sqm"] for zone in zones)
    if total_area > area_sqm:
        overflow = total_area - area_sqm
        zones[-2]["area_sqm"] -= overflow
        total_area = sum(zone["area_sqm"] for zone in zones)
    fallback = {
        "status": "ok",
        "output": "完成功能分区与面积配比",
        "zones": zones,
        "circulation_strategy": "入口聚焦 -> 企业叙事 -> 互动体验 -> 产品展示 -> 发布区 -> VIP 洽谈",
        "area_check": {"target_area_sqm": area_sqm, "planned_area_sqm": total_area},
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是展厅功能分区专家，只返回 JSON。",
        user_prompt=(
            "请为展厅输出功能分区、面积表和动线策略。"
            f"\n项目: {summarize_brief(structured_brief)}"
            f"\n目标输出字段: status, output, zones, circulation_strategy, area_check"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
