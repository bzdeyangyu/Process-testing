from __future__ import annotations

from typing import Any


STANDARD_ID = "five-sample-v1"
TARGET_SECTIONS = ["项目任务书", "场地踏勘资料", "会议决策回灌"]

SECTION_FIELDS = {
    "项目任务书": [
        ("project_type", "项目类型"),
        ("area_sqm", "项目面积"),
        ("location", "项目地点"),
        ("budget_cny", "预算区间"),
        ("audience", "目标受众"),
        ("duration_days", "工期或展期"),
        ("style_preferences", "风格偏好"),
        ("special_requirements", "特殊需求"),
    ],
    "场地踏勘资料": [
        ("site_assets", "场地资料清单"),
        ("site_constraints", "场地硬约束"),
        ("site_opportunities", "场地机会点"),
    ],
    "会议决策回灌": [
        ("meeting_feedback", "会议结论"),
        ("decision_status", "确认与否决项"),
        ("next_revision_focus", "下一轮修改重点"),
    ],
}

QUESTION_BANK = [
    {
        "field": "location",
        "section": "项目任务书",
        "question": "项目具体地点是哪里，至少需要到城市和项目落位建筑信息。",
        "reason": "地点会影响法规、气候、客群和材料施工判断。",
    },
    {
        "field": "budget_cny",
        "section": "项目任务书",
        "question": "项目预算区间是多少，至少需要一个上限或可接受范围。",
        "reason": "没有预算就无法判断方案强度、材质等级和图像输出方向。",
    },
    {
        "field": "duration_days",
        "section": "项目任务书",
        "question": "项目关键时间节点是什么，包含提案时间、施工周期或开馆时间。",
        "reason": "时间会直接影响策略深度、交付批次和实现路径。",
    },
    {
        "field": "site_assets",
        "section": "场地踏勘资料",
        "question": "你现在手里有哪些现场资料，例如 CAD、现场照片、视频、扫描模型或测绘记录。",
        "reason": "没有场地资料就不能输出真实可落地的约束分析。",
    },
    {
        "field": "site_constraints",
        "section": "场地踏勘资料",
        "question": "现场目前已知的硬约束是什么，例如层高、柱网、消防、承重、现状机电或不可拆改条件。",
        "reason": "约束不清会导致后续动线和功能分区失真。",
    },
    {
        "field": "meeting_feedback",
        "section": "会议决策回灌",
        "question": "目前是否已有内部讨论或客户会议结论，如果有，请提供纪要、录音转写或核心决策点。",
        "reason": "没有决策回灌，AI 无法判断哪些方向已被确认或否决。",
    },
]

RETRIEVAL_BANK = [
    {
        "when_missing": "site_assets",
        "source": "项目资料库 / wiki",
        "action": "检索是否已有 CAD、现场照片、踏勘纪要或扫描模型索引。",
    },
    {
        "when_missing": "meeting_feedback",
        "source": "会议纪要库",
        "action": "检索是否已有首轮沟通纪要、录音转写或客户反馈摘要。",
    },
    {
        "when_missing": "budget_cny",
        "source": "商务报价库",
        "action": "检索同类项目报价带或历史立项预算区间，作为预算追问参考。",
    },
]


def enrich_to_output_standard(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    review = build_output_standard_review(enriched)
    enriched["output_standard_review"] = review
    enriched["follow_up_questions"] = build_follow_up_questions(enriched)
    enriched["recommended_retrievals"] = build_recommended_retrievals(enriched)
    enriched["source_status"] = build_source_status(enriched)
    return enriched


def build_output_standard_review(payload: dict[str, Any]) -> dict[str, Any]:
    section_scores: list[dict[str, Any]] = []
    total_fields = 0
    completed_fields = 0
    missing_critical_items: list[str] = []

    for section, fields in SECTION_FIELDS.items():
        present = 0
        missing_labels: list[str] = []
        for field_name, label in fields:
            total_fields += 1
            if _has_value(payload.get(field_name)):
                present += 1
                completed_fields += 1
            else:
                missing_labels.append(label)
                missing_critical_items.append(f"{section}缺少{label}")
        score = int(round((present / len(fields)) * 100)) if fields else 100
        section_scores.append({
            "section": section,
            "score": score,
            "present_count": present,
            "required_count": len(fields),
            "missing_items": missing_labels,
        })

    coverage_score = int(round((completed_fields / total_fields) * 100)) if total_fields else 100
    return {
        "standard_id": STANDARD_ID,
        "target_sections": TARGET_SECTIONS,
        "coverage_score": coverage_score,
        "passed": coverage_score >= 85 and not missing_critical_items,
        "section_scores": section_scores,
        "missing_critical_items": missing_critical_items,
        "comparison_summary": _build_comparison_summary(section_scores, coverage_score),
        "next_step_rule": "未达标时优先追问用户；若用户未提供但企业库已有资料，则调取资料库后再次输出。",
    }


def build_follow_up_questions(payload: dict[str, Any]) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for item in QUESTION_BANK:
        if not _has_value(payload.get(item["field"])):
            questions.append({
                "field": item["field"],
                "section": item["section"],
                "question": item["question"],
                "reason": item["reason"],
            })
    return questions


def build_recommended_retrievals(payload: dict[str, Any]) -> list[dict[str, str]]:
    retrievals: list[dict[str, str]] = []
    for item in RETRIEVAL_BANK:
        if not _has_value(payload.get(item["when_missing"])):
            retrievals.append({
                "field": item["when_missing"],
                "source": item["source"],
                "action": item["action"],
            })
    return retrievals


def build_source_status(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "brief": _section_state(payload, "项目任务书"),
        "site_survey": _section_state(payload, "场地踏勘资料"),
        "meeting_feedback": _section_state(payload, "会议决策回灌"),
    }


def _section_state(payload: dict[str, Any], section: str) -> str:
    fields = SECTION_FIELDS[section]
    present = sum(1 for field_name, _ in fields if _has_value(payload.get(field_name)))
    if present == 0:
        return "missing"
    if present == len(fields):
        return "ready"
    return "partial"


def _build_comparison_summary(section_scores: list[dict[str, Any]], coverage_score: int) -> str:
    weakest = min(section_scores, key=lambda item: item["score"]) if section_scores else None
    if weakest is None:
        return "当前没有可比较内容。"
    return (
        f"当前输出对照五份标准样本的完整度为 {coverage_score} 分，"
        f"最薄弱环节是{weakest['section']}，需要继续补齐。"
    )


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() != "unknown"
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True
