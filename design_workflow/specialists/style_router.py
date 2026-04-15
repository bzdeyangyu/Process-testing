from __future__ import annotations

from pathlib import Path

from config import DESIGN_LIB_DIR
from design_workflow.specialists.common import normalize_audience, normalize_style_preferences

STYLE_PROFILES: dict[str, dict[str, list[str]]] = {
    "architectural-viz": {
        "project_type": ["建筑", "地产", "售楼", "规划", "城市展厅", "规划馆", "建筑可视化"],
        "style_preferences": ["理性", "未来", "几何", "建筑感"],
        "special_requirements": ["模型", "城市规划", "沙盘", "外立面"],
        "audience": ["开发商", "投资人", "城市访客"],
    },
    "brand-experience": {
        "project_type": ["品牌展厅", "企业展厅", "品牌馆", "旗舰", "快闪", "活动空间", "showroom"],
        "style_preferences": ["品牌感", "年轻", "时尚", "传播", "沉浸", "未来"],
        "special_requirements": ["品牌展示", "客户接待", "发布活动", "打卡", "传播", "社交", "campaign"],
        "audience": ["品牌客户", "合作伙伴", "消费者", "媒体", "访客"],
    },
    "commercial-exhibition": {
        "project_type": ["商业展陈", "商业展示", "零售", "商场", "招商", "交易会"],
        "style_preferences": ["商业", "高转化", "展示效率"],
        "special_requirements": ["导购", "招商", "货品展示", "陈列"],
        "audience": ["客户", "采购商", "消费者"],
    },
    "cultural-space": {
        "project_type": ["文化空间", "艺术", "公共文化", "展演", "社区文化"],
        "style_preferences": ["文化", "人文", "艺术", "公共"],
        "special_requirements": ["教育", "公共活动", "社区互动"],
        "audience": ["公众", "家庭", "市民"],
    },
    "museum-narrative": {
        "project_type": ["博物馆", "纪念馆", "历史馆", "文博", "展陈馆"],
        "style_preferences": ["叙事", "历史", "文化", "庄重"],
        "special_requirements": ["文物", "档案", "时间线", "教育"],
        "audience": ["学生", "公众", "研究者"],
    },
    "tech-showroom": {
        "project_type": ["科技展厅", "创新中心", "产品体验中心", "数字展厅", "企业展厅", "实验室"],
        "style_preferences": ["科技", "未来", "数字", "极简", "理性"],
        "special_requirements": ["交互", "数字化", "智能", "产品演示", "沉浸式互动"],
        "audience": ["企业客户", "合作伙伴", "技术访客"],
    },
}

FIELD_WEIGHTS = {
    "project_type": 4,
    "style_preferences": 3,
    "special_requirements": 3,
    "audience": 2,
}


def route_style(structured_brief: dict) -> dict:
    available = _available_style_keys()
    project_type = str(structured_brief.get("project_type", ""))
    style_preferences = normalize_style_preferences(structured_brief)
    special_requirements = _normalize_listish(structured_brief.get("special_requirements", []))
    audience = normalize_audience(structured_brief)

    field_values = {
        "project_type": [project_type],
        "style_preferences": style_preferences,
        "special_requirements": special_requirements,
        "audience": audience,
    }

    candidates = []
    for style_key in available:
        profile = STYLE_PROFILES.get(style_key, {})
        score = 0
        reasons: list[str] = []
        for field_name, values in field_values.items():
            field_score, field_reasons = _score_field(
                style_key=style_key,
                field_name=field_name,
                values=values,
                keywords=profile.get(field_name, []),
            )
            score += field_score
            reasons.extend(field_reasons)
        bonus, bonus_reasons = _rule_bonus(style_key, field_values)
        score += bonus
        reasons.extend(bonus_reasons)
        candidates.append({
            "style_key": style_key,
            "score": score,
            "reasons": reasons[:4],
        })

    candidates.sort(key=lambda item: (-item["score"], item["style_key"]))
    selected = candidates[0]["style_key"] if candidates else "tech-showroom"
    confidence = _confidence_label(candidates)
    return {
        "selected_style_key": selected,
        "top_candidates": candidates[:3],
        "confidence": confidence,
        "tone_tags": _tone_tags(structured_brief),
    }


def _available_style_keys() -> list[str]:
    keys = []
    for path in sorted(DESIGN_LIB_DIR.iterdir()):
        if path.is_dir() and (path / "DESIGN.md").exists():
            keys.append(path.name)
    return keys


def _score_field(*, style_key: str, field_name: str, values: list[str], keywords: list[str]) -> tuple[int, list[str]]:
    if not values or not keywords:
        return 0, []
    total = 0
    reasons = []
    field_weight = FIELD_WEIGHTS[field_name]
    for value in values:
        normalized = value.lower()
        for keyword in keywords:
            if keyword.lower() in normalized:
                total += field_weight
                reasons.append(f"{field_name}:{keyword}")
                break
    return total, reasons


def _rule_bonus(style_key: str, field_values: dict[str, list[str]]) -> tuple[int, list[str]]:
    project_type = " ".join(field_values["project_type"])
    special_requirements = " ".join(field_values["special_requirements"])
    audience = " ".join(field_values["audience"])
    style_preferences = " ".join(field_values["style_preferences"])

    bonuses: list[tuple[int, str]] = []
    if style_key == "brand-experience":
        if "企业展厅" in project_type and any(token in special_requirements for token in ["品牌展示", "发布活动", "客户接待", "打卡", "传播"]):
            bonuses.append((8, "rule:enterprise-brand-activation"))
        if any(token in audience for token in ["品牌", "合作伙伴", "媒体", "消费者"]):
            bonuses.append((4, "rule:brand-facing-audience"))
        if any(token in style_preferences for token in ["时尚", "年轻", "未来"]):
            bonuses.append((2, "rule:brand-tone"))
    if style_key == "tech-showroom":
        if any(token in special_requirements for token in ["产品演示", "数字化", "智能", "交互", "沉浸式互动"]):
            bonuses.append((6, "rule:tech-interaction"))
        if any(token in project_type for token in ["科技展厅", "创新中心", "体验中心", "数字展厅"]):
            bonuses.append((6, "rule:tech-project-type"))
        if any(token in style_preferences for token in ["科技", "极简", "理性"]):
            bonuses.append((2, "rule:tech-tone"))
    if style_key == "museum-narrative" and any(token in project_type for token in ["博物馆", "纪念馆", "历史馆"]):
        bonuses.append((10, "rule:museum-project"))
    if style_key == "commercial-exhibition" and any(token in project_type for token in ["商业", "零售", "交易会", "招商"]):
        bonuses.append((8, "rule:commercial-project"))
    if style_key == "cultural-space" and any(token in project_type for token in ["文化空间", "艺术", "公共文化"]):
        bonuses.append((8, "rule:cultural-project"))
    if style_key == "architectural-viz" and any(token in project_type for token in ["建筑", "地产", "规划", "售楼"]):
        bonuses.append((8, "rule:architectural-project"))

    score = sum(item[0] for item in bonuses)
    reasons = [item[1] for item in bonuses]
    return score, reasons


def _confidence_label(candidates: list[dict]) -> str:
    if len(candidates) < 2:
        return "high"
    gap = candidates[0]["score"] - candidates[1]["score"]
    if gap >= 6:
        return "high"
    if gap >= 3:
        return "medium"
    return "low"


def _tone_tags(structured_brief: dict) -> list[str]:
    tags = normalize_style_preferences(structured_brief) + _normalize_listish(structured_brief.get("special_requirements", []))
    seen = []
    for tag in tags:
        if tag and tag not in seen:
            seen.append(tag)
    return seen[:5]


def _normalize_listish(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str):
        return [value]
    return []
