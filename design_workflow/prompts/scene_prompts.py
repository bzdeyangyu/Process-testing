"""
三层 Prompt 体系 - Scene Prompts（情境注入）
动态生成，根据实际输入参数注入，不硬编码数值
"""
from __future__ import annotations


def make_req_parser_scene(brief: str) -> str:
    """根据任务书内容动态生成情境描述"""
    length = len(brief)
    detail_level = "详细描述" if length > 150 else ("基本描述" if length > 50 else "简短说明")
    return (
        f"以下是客户提供的项目任务书（{detail_level}，共 {length} 字）。\n"
        f"请仔细分析，提取所有设计约束条件，对未明确说明的字段做合理推断。\n"
        f"注意：数字字段（面积、预算）以任务书原文为准，不要自行修改。\n\n"
        f"任务书原文：\n{brief}"
    )


def make_material_style_scene(structured_brief: dict) -> str:
    """根据解析后的需求生成材料风格情境"""
    project_type = structured_brief.get("project_type", "展览空间")
    area = structured_brief.get("area_sqm", "未知")
    styles = structured_brief.get("style_preferences", [])
    requirements = structured_brief.get("special_requirements", [])
    audience = structured_brief.get("audience", "公众访客")
    style_hint = "、".join(styles) if styles else "现代简洁"
    req_hint = "、".join(requirements) if requirements else "无特殊要求"
    return (
        f"当前项目：{project_type}，建筑面积约 {area}㎡\n"
        f"客户风格偏好：{style_hint}\n"
        f"特殊功能需求：{req_hint}\n"
        f"目标受众：{audience}\n\n"
        f"请从六大风格体系中选择最匹配的一种，并输出完整的材料色彩方案。"
        f"确保 style_key 与客户偏好高度契合。"
    )


def make_visual_prompt_scene(structured_brief: dict, material_spec: dict) -> str:
    """根据需求和材料规格生成视觉提示词情境——三套方案"""
    project_type = structured_brief.get("project_type", "展览空间")
    area = structured_brief.get("area_sqm", 500)
    style_key = material_spec.get("style_key", "tech-showroom")
    direction = material_spec.get("direction", "")
    palette = material_spec.get("palette", [])
    materials = material_spec.get("materials", [])
    special_req = structured_brief.get("special_requirements", [])

    # 提取色值文本
    color_str = "、".join([f"{c.get('name','')}: {c.get('hex','')}" for c in palette[:3]]) if palette else "默认配色"
    material_str = "、".join(materials[:3]) if materials else "标准材料"
    special_str = "、".join(special_req) if special_req else "无"

    return (
        f"项目概况：{project_type}，面积 {area}㎡，风格方向：{style_key}\n"
        f"设计方向：{direction}\n"
        f"色彩方案：{color_str}\n"
        f"主材清单：{material_str}\n"
        f"特殊需求：{special_str}\n\n"
        f"请为该项目生成三套差异化设计方案的效果图 Prompt：\n"
        f"  方案A（主推方案）：最符合客户偏好，成熟稳健\n"
        f"  方案B（创意方案）：设计感更强，有突破性创意元素\n"
        f"  方案C（经济方案）：材料经济可控，实用为主\n\n"
        f"每套方案需包含 6 类效果图：\n"
        f"  1. 平面图（floor_plan）：俯视概念平面布局\n"
        f"  2. 氛围图（mood_board）：材质光线情绪拼贴\n"
        f"  3. 主效果图1（main_view_1）：主入口/大堂全景\n"
        f"  4. 主效果图2（main_view_2）：核心展区/高潮空间\n"
        f"  5. 节点效果图1（node_view_1）：重要功能节点特写\n"
        f"  6. 节点效果图2（node_view_2）：另一重要节点\n\n"
        f"重要：所有 Prompt 使用英文，禁止使用 --ar、--q 等 Midjourney 参数，"
        f"结尾必须加 photorealistic, 8K resolution, architectural visualization, ultra detailed。"
    )


def make_case_research_scene(structured_brief: dict) -> str:
    project_type = structured_brief.get("project_type", "展览空间")
    area = structured_brief.get("area_sqm", 500)
    styles = structured_brief.get("style_preferences", [])
    style_hint = "、".join(styles) if styles else "现代风格"
    return (
        f"目标项目：{project_type}，面积约 {area}㎡，风格偏好：{style_hint}\n"
        f"请检索与该项目最接近的 3-5 个国内外优秀设计案例，"
        f"重点提炼每个案例中可借鉴的设计策略。"
    )


def make_concept_scene(structured_brief: dict, case_research: dict) -> str:
    project_type = structured_brief.get("project_type", "展览空间")
    styles = structured_brief.get("style_preferences", [])
    requirements = structured_brief.get("special_requirements", [])
    cases = case_research.get("cases", [])
    case_names = "、".join([c.get("case_name", "") for c in cases[:3]]) if cases else "无参考案例"
    return (
        f"项目类型：{project_type}，风格偏好：{'、'.join(styles)}\n"
        f"特殊需求：{'、'.join(requirements)}\n"
        f"参考案例：{case_names}\n\n"
        f"请提出一个有感召力的核心设计概念，统领整个空间叙事。"
    )


def make_storyline_scene(structured_brief: dict, concept: dict) -> str:
    project_type = structured_brief.get("project_type", "展览空间")
    area = structured_brief.get("area_sqm", 500)
    concept_title = concept.get("concept_title", "待定概念")
    return (
        f"项目：{project_type}，面积 {area}㎡\n"
        f"设计概念：《{concept_title}》\n"
        f"请设计完整的空间叙事动线（4-6 章节），确保游览体验有节奏、有高潮。"
    )


def make_zoning_scene(structured_brief: dict, storyline: dict) -> str:
    area = structured_brief.get("area_sqm", 500)
    acts = storyline.get("acts", [])
    act_names = "→".join([a.get("act_name", "") for a in acts]) if acts else "待定"
    return (
        f"总面积：{area}㎡，叙事章节：{act_names}\n"
        f"请将叙事方案转化为功能分区，输出各区面积比例和位置关系。"
    )


# 保持向后兼容：静态字典版本（legacy）
SCENE_PROMPTS = {
    "req_parser": "请仔细分析以下任务书，提取所有量化参数和质性约束。",
    "material_style": "请根据项目需求，从设计库中选择最匹配的风格方向，输出完整材料色彩方案。",
    "visual_prompt": "请为该空间项目生成三套方案各6类效果图的高质量英文 Prompt，用于 CogView AI 生图工具。",
    "case_research": "请检索与该项目类型、风格、规模最接近的3-5个参考案例。",
    "concept": "请基于需求分析和参考案例，提出1个核心设计概念方案。",
    "storyline": "请设计完整的空间叙事动线，从入口到出口形成完整的体验节奏。",
    "zoning": "请将叙事方案转化为功能分区，给出各区面积比例和位置关系。",
    "video_script": "请为该设计方案编写30-60秒推介视频脚本，突出核心体验亮点。",
    "cost_estimate": "请根据空间规格和材料方案，给出合理的造价区间估算。",
    "report": "请将所有设计成果整合为一份专业汇报摘要文件。",
    "feedback": "请整理会议反馈，提取明确的修改决策和行动项。",
    "progress": "请汇总当前项目进度状态。",
}
