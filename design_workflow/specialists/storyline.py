from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm, summarize_brief

def handle(input_dict: dict) -> dict:
    structured_brief = input_dict["structured_brief"]
    concept = input_dict.get("concept", {})
    theme_statement = concept.get("theme_statement", "未来感品牌展示")
    experience_sequence = [
        {"zone": "入口引导", "goal": "建立品牌第一印象", "moment": "视觉焦点与品牌标识装置"},
        {"zone": "企业叙事区", "goal": "快速理解企业能力", "moment": "时间轴与核心里程碑"},
        {"zone": "互动体验区", "goal": "让观众主动参与", "moment": "可操作演示与沉浸互动"},
        {"zone": "产品发布区", "goal": "聚焦重点产品", "moment": "媒体发布与讲解展示"},
        {"zone": "VIP 洽谈区", "goal": "完成深度交流", "moment": "相对安静且独立的接待空间"},
    ]
    fallback = {
        "status": "ok",
        "output": "完成空间故事线设计",
        "storyline_title": theme_statement,
        "experience_sequence": experience_sequence,
        "emotional_curve": ["吸引", "理解", "参与", "信任", "转化"],
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是展厅叙事与动线设计专家，只返回 JSON。",
        user_prompt=(
            "请输出展厅参观故事线、体验顺序和情绪曲线。"
            f"\n项目: {summarize_brief(structured_brief)}"
            f"\n概念主题: {theme_statement}"
            f"\n目标输出字段: status, output, storyline_title, experience_sequence, emotional_curve"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
