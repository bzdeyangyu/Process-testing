from __future__ import annotations

from design_workflow.specialists.common import (
    complete_with_llm,
    normalize_style_preferences,
    summarize_brief,
)

def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    project_type = structured_brief.get("project_type", "科技展厅")
    area_sqm = structured_brief.get("area_sqm", 800)
    styles = normalize_style_preferences(structured_brief)
    style_hint = styles[0] if styles else "科技感"
    case_cards = [
        {
            "name": "旗舰科技品牌展厅",
            "area_sqm": max(area_sqm - 80, 600),
            "style": style_hint,
            "highlights": ["沉浸式媒体墙", "品牌时间轴", "发布会模式切换"],
            "takeaway": "入口必须先建立记忆点，再展开产品叙事。",
        },
        {
            "name": "企业创新体验中心",
            "area_sqm": area_sqm,
            "style": "未来感",
            "highlights": ["交互演示岛台", "低反玻璃展柜", "智能灯光联动"],
            "takeaway": "互动区与讲解区要保持可切换的视听边界。",
        },
        {
            "name": "城市级品牌展示馆",
            "area_sqm": area_sqm + 150,
            "style": "品牌叙事",
            "highlights": ["空间叙事动线", "VIP 接待区", "可复用展陈模块"],
            "takeaway": "高价值接待场景需要独立且不打断主参观流线。",
        },
    ]
    fallback = {
        "status": "ok",
        "output": f"完成 {project_type} 对标案例研究",
        "case_cards": case_cards,
        "insights": [
            "科技展厅需要兼顾品牌展示、互动体验和接待洽谈三类场景。",
            "入口焦点、主媒体墙和可切换灯光系统是高频成功要素。",
            "案例普遍采用深色基底配高亮科技色，强化沉浸与识别度。",
        ],
        "recommended_case_types": ["旗舰品牌馆", "创新体验中心", "发布型展厅"],
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是展厅案例研究专家，只返回 JSON。",
        user_prompt=(
            "请基于下列项目简报输出 3 个对标案例和 3 条研究洞察。"
            f"\n项目: {summarize_brief(structured_brief)}"
            f"\n目标输出字段: status, output, case_cards, insights, recommended_case_types"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
