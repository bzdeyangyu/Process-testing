from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm

def handle(input_dict: dict) -> dict:
    style_key = input_dict.get("style_key", "tech-showroom")
    fallback = {
        "status": "ok",
        "output": "完成客户反馈影响分析",
        "feedback_summary": "若客户要求降低科技冷感，可优先调整灯光色温、材质肌理和接待区氛围。",
        "impact_stages": ["material_style", "visual_prompt", "report"],
        "patch_actions": [
            f"在 {style_key} 风格基础上增加更温和的中性色和木质触感。",
            "弱化过强的媒体炫技表达，保留品牌焦点与互动主装置。",
            "同步更新汇报摘要中的体验关键词与预算描述。",
        ],
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是客户反馈修订专家，只返回 JSON。",
        user_prompt=(
            "请分析客户反馈会影响哪些阶段，并给出定向修订动作。"
            f"\n当前汇报: {input_dict.get('report', {})}"
            f"\n目标输出字段: status, output, feedback_summary, impact_stages, patch_actions"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
