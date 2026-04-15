from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm

def handle(input_dict: dict) -> dict:
    zoning = input_dict.get("zoning", {})
    material_spec = input_dict.get("material_spec", {})
    zones = zoning.get("zones", [])
    area_sqm = input_dict.get("structured_brief", {}).get("area_sqm", 800)
    budget_breakdown = [
        {"category": "空间基础装修", "low_wan": round(area_sqm * 0.18, 1), "high_wan": round(area_sqm * 0.24, 1)},
        {"category": "展陈装置与媒体", "low_wan": round(area_sqm * 0.16, 1), "high_wan": round(area_sqm * 0.22, 1)},
        {"category": "灯光与智能控制", "low_wan": round(area_sqm * 0.08, 1), "high_wan": round(area_sqm * 0.12, 1)},
        {"category": "软装与接待家具", "low_wan": round(area_sqm * 0.04, 1), "high_wan": round(area_sqm * 0.06, 1)},
    ]
    total_low = round(sum(item["low_wan"] for item in budget_breakdown), 1)
    total_high = round(sum(item["high_wan"] for item in budget_breakdown), 1)
    fallback = {
        "status": "ok",
        "output": "完成造价概算",
        "budget_breakdown": budget_breakdown,
        "total_budget_wan": {"low": total_low, "high": total_high},
        "cost_drivers": [
            f"重点材料: {', '.join(material_spec.get('materials', [])[:3])}",
            f"核心分区数量: {len(zones)}",
            "媒体装置与智能控制系统占较高成本比重",
        ],
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是展厅造价预算专家，只返回 JSON。",
        user_prompt=(
            "请根据面积、分区和材料规格输出概算区间。"
            f"\n分区: {zoning}"
            f"\n材料规格: {material_spec}"
            f"\n目标输出字段: status, output, budget_breakdown, total_budget_wan, cost_drivers"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
