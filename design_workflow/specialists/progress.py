from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm

def handle(input_dict: dict) -> dict:
    milestones = [
        {"name": "需求对齐与概念确认", "week": 1},
        {"name": "空间方案与视觉输出", "week": 2},
        {"name": "预算校准与汇报交付", "week": 3},
        {"name": "深化设计与实施准备", "week": 4},
    ]
    task_breakdown = [
        "完成需求澄清与案例对标",
        "锁定故事线、分区和材料方向",
        "输出视觉表现、预算与汇报文件",
        "根据客户反馈做定向修订并进入深化",
    ]
    fallback = {
        "status": "ok",
        "output": "完成进度计划与任务拆解",
        "milestones": milestones,
        "task_breakdown": task_breakdown,
        "timeline_weeks": 4,
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是项目进度规划专家，只返回 JSON。",
        user_prompt=(
            "请给出 3-5 个项目里程碑、任务拆解和总周期。"
            f"\n项目上下文: {input_dict.get('report', {})}"
            f"\n目标输出字段: status, output, milestones, task_breakdown, timeline_weeks"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
