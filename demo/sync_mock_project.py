from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for candidate in (ROOT_DIR, SRC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from config import OUTPUT_DIR
from agent_runtime.board import PROJECT_ID, PROJECT_NAME, ProjectBoardTracker


def run_mock_project_sync(*, output_dir: Path | None = None) -> dict:
    effective_output_dir = Path(output_dir or OUTPUT_DIR)
    project_dir = effective_output_dir / "mock_medical_project"
    project_dir.mkdir(parents=True, exist_ok=True)

    project_packet = _build_mock_project_packet()
    result = _build_mock_result()
    run_id = str(uuid4())
    brief = project_packet["inputs"]["brief_summary"]

    tracker = ProjectBoardTracker(
        board_dir=effective_output_dir / "board",
        project_id=PROJECT_ID,
        project_name=PROJECT_NAME,
        run_id=run_id,
        title="南京 800㎡ 医疗科技政务合作型展厅 Mock",
        brief=brief,
        mode="mock",
    )
    tracker.start()

    stage_outputs = {
        "req_parser": result["structured_brief"],
        "case_research": result["case_research"],
        "concept": result["concept"],
        "storyline": result["storyline"],
        "zoning": result["zoning"],
        "material_style": {
            "style_key": result["style_key"],
            "palette": result["palette"],
            "material_spec": result["material_spec"],
            "lighting_concept": result["lighting_concept"],
        },
        "visual_prompt": {
            "visual_prompt": result["visual_prompt"],
            "schemes": result["schemes"],
            "summary": "基于 mock 方案生成三套视觉提示词方向。",
        },
        "image_gen": {
            "generated_schemes": result["generated_schemes"],
            "scheme_count": len(result["generated_schemes"]),
            "image_count": sum(len(item.get("images", [])) for item in result["generated_schemes"]),
        },
        "video_script": result["video_script"],
        "cost_estimate": result["cost_estimate"],
        "report": result["report"],
        "feedback": result["feedback"],
        "progress": result["progress"],
    }

    for specialist, payload in stage_outputs.items():
        tracker.mark_stage_running(specialist)
        tracker.mark_stage_completed(specialist, payload)

    packet = {"project_packet": project_packet, "result": result}
    (effective_output_dir / "mock_project_result.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (project_dir / "mock_project_result.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (project_dir / "mock_project_summary.md").write_text(
        _build_mock_summary_markdown(project_packet, result),
        encoding="utf-8",
    )

    tracker.finish(result, result={"project_dir": str(project_dir), "generated_schemes": result["generated_schemes"]})
    return result


def _build_mock_project_packet() -> dict:
    return {
        "mode": "mock",
        "assumption_policy": "用户未提供的字段先以测试样本方式 mock，并在成果中显式标记为 mock。",
        "inputs": {
            "brief_summary": "南京产业园新建 800㎡ 医疗科技企业展厅，预算 400-800 万，目标证明公司可承接政府/产业合作。",
            "confirmed_by_user": {
                "client_type": "医疗科技企业",
                "location": "南京",
                "site_type": "普通产业园新建项目",
                "area_sqm": 800,
                "budget_range_cny": {"low": 4_000_000, "high": 8_000_000},
                "target_audience": ["政府领导", "行业客户", "合作伙伴", "来访考察团"],
                "primary_goal": "让来访者相信公司具备承接政府/产业合作的能力",
                "site_assets": [],
            },
            "mocked_for_test": {
                "company_profile": "区域医疗数字化平台与医疗 AI 辅助系统供应商，面向政府和大型医院提供平台型解决方案。",
                "top_showcase_topics": ["平台能力", "政府/医院合作成果", "产业协同与未来布局"],
                "must_include": ["区域医疗平台项目案例", "三甲医院合作案例", "高新资质与专利成果"],
                "visit_motivation": "政务考察 + 产业合作 + 商务接待混合型",
                "spatial_functions": ["序厅", "企业总览", "平台能力区", "合作成果区", "汇报区", "洽谈区"],
                "visual_tone": ["高端可信", "科技未来", "医疗专业"],
                "forbidden_directions": ["过度娱乐化", "纯博物馆化", "过冷实验室感"],
                "meeting_feedback": {
                    "confirmed": ["展厅必须能支撑领导考察", "必须突出合作成果和平台能力"],
                    "rejected": ["不做强秀场型沉浸秀", "不以单一产品陈列为主"],
                    "next_focus": ["强化政务说服力", "形成可讲解的展示主线"],
                },
            },
        },
    }


def _build_mock_result() -> dict:
    structured_brief = {
        "project_type": "医疗科技企业展厅",
        "area_sqm": 800,
        "location": "南京",
        "budget_cny": {"low": 4_000_000, "high": 8_000_000},
        "audience": ["政府领导", "行业客户", "合作伙伴", "来访考察团"],
        "style_preferences": ["高端可信", "科技未来", "医疗专业"],
        "special_requirements": ["接待型讲解动线", "小型汇报功能", "商务洽谈能力", "合作成果展示"],
        "duration_days": None,
        "key_constraints": ["当前无场地资料，本轮不输出真实场地约束，只输出 mock 功能框架。"],
        "output_standard_review": {
            "standard_id": "five-sample-v1",
            "target_sections": ["项目任务书", "场地踏勘资料", "会议决策回灌"],
            "coverage_score": 92,
            "passed": True,
            "section_scores": [
                {"section": "项目任务书", "score": 100, "present_count": 8, "required_count": 8, "missing_items": []},
                {"section": "场地踏勘资料", "score": 75, "present_count": 3, "required_count": 4, "missing_items": ["真实 CAD / 照片未提供，当前为 mock 场地描述"]},
                {"section": "会议决策回灌", "score": 100, "present_count": 3, "required_count": 3, "missing_items": []},
            ],
            "missing_critical_items": [],
            "comparison_summary": "当前 mock 结果已经达到标准样本的大部分结构要求，但场地约束仍需真实资料替换。",
            "next_step_rule": "进入真实项目时优先替换公司资料、案例成果和场地数据，再重新生成。",
        },
        "follow_up_questions": [],
        "recommended_retrievals": [
            {"field": "site_assets", "source": "项目资料库 / wiki", "action": "真实项目阶段补录 CAD、照片、机电与消防条件。"},
            {"field": "company_profile", "source": "企业资料库", "action": "替换 mock 的平台能力与案例成果描述。"},
        ],
        "source_status": {"brief": "ready", "site_survey": "mocked", "meeting_feedback": "mocked"},
        "real_need_summary": {
            "explicit_needs": [
                "建设约 800㎡ 的企业展厅",
                "面向政府领导、行业客户、合作伙伴、来访考察团",
                "预算控制在 400-800 万",
                "证明公司具备承接政府/产业合作的能力",
            ],
            "implicit_needs": [
                "以平台型合作能力替代单点产品陈列",
                "建立高可信、专业、可合作的第一印象",
                "同时支持讲解、汇报、接待、洽谈四类行为",
            ],
        },
    }

    case_research = {
        "status": "ok",
        "output": "已整理可借鉴的医疗科技政务接待型展厅案例。",
        "case_cards": [
            {"case_name": "医疗数字平台展示中心", "design_highlight": "以平台架构墙和区域数据地图建立政府理解入口。"},
            {"case_name": "智慧医院合作体验馆", "design_highlight": "把医院场景演示与合作成果放在同一路线中。"},
            {"case_name": "医疗科技政企合作馆", "design_highlight": "通过资质、案例、生态合作构建可信度闭环。"},
        ],
    }
    concept = {
        "status": "ok",
        "output": "形成三套概念方向。",
        "concept_options": [
            {"name": "可信平台", "summary": "强调平台能力与合作承载力，适合政务考察。"},
            {"name": "医数中枢", "summary": "强调数据流与平台调度，科技表达更强。"},
            {"name": "协同引擎", "summary": "突出政府、医院、企业之间的协同网络。"},
        ],
    }
    storyline = {
        "status": "ok",
        "output": "形成政务接待型讲解主线。",
        "experience_sequence": [
            "序厅建立企业定位与合作价值",
            "平台能力区解释核心技术与系统架构",
            "合作成果区证明真实落地能力",
            "场景解决方案区展示医院和区域应用",
            "未来布局区引向合作想象",
            "洽谈区承接参观后的商务交流",
        ],
    }
    zoning = {
        "status": "ok",
        "output": "完成 mock 分区建议。",
        "zones": [
            {"zone_name": "序厅", "area_ratio": "12%", "function": "建立信任和定位"},
            {"zone_name": "企业总览区", "area_ratio": "16%", "function": "展示企业发展、资质与核心数字"},
            {"zone_name": "平台能力区", "area_ratio": "22%", "function": "展示平台架构、技术能力、核心产品"},
            {"zone_name": "合作成果区", "area_ratio": "18%", "function": "展示政府项目、医院案例与生态合作"},
            {"zone_name": "场景解决方案区", "area_ratio": "16%", "function": "展示智慧医院、区域医疗等应用场景"},
            {"zone_name": "汇报与洽谈区", "area_ratio": "12%", "function": "承接领导接待和商务沟通"},
            {"zone_name": "配套与储藏", "area_ratio": "4%", "function": "设备与运营支持"},
        ],
        "circulation": "入口建立认知，中段建立能力和案例信任，尾段进入合作与洽谈转化。",
        "key_nodes": ["品牌定位墙", "平台能力中枢屏", "政府合作案例台", "洽谈汇报桌"],
    }
    material_style = {
        "style_key": "medical-gov-tech",
        "palette": [
            {"name": "primary", "hex": "#163A70", "usage": "深蓝基底，建立可信和政务接待感"},
            {"name": "accent", "hex": "#4DB6D6", "usage": "科技高亮与数字界面"},
            {"name": "support", "hex": "#E8F0F5", "usage": "洁净医疗背景与留白"},
        ],
        "material_spec": "哑光金属、低反玻璃、医疗白烤漆板与局部透光亚克力组合，整体强调洁净、可信和中高端科技感。",
        "lighting_concept": "以均质基础光建立专业度，在平台中枢和案例节点用冷白重点光强化信息聚焦。",
    }
    visual_prompt = "medical technology enterprise showroom, government cooperation oriented, high-trust reception hall, clean architectural lines, blue-white palette, platform capability wall, hospital collaboration cases, elegant negotiation lounge, photorealistic, 8K resolution, architectural visualization, ultra detailed"
    schemes = [
        {"scheme_id": "A", "scheme_name": "可信平台", "scheme_description": "政务接待优先的主推方案", "style_variant": "成熟稳健", "views": []},
        {"scheme_id": "B", "scheme_name": "医数中枢", "scheme_description": "科技感更强的概念方案", "style_variant": "平台科技感", "views": []},
        {"scheme_id": "C", "scheme_name": "协同引擎", "scheme_description": "合作生态表达更强的方案", "style_variant": "合作网络感", "views": []},
    ]
    generated_schemes = [
        {"scheme_id": "A", "scheme_name": "可信平台", "scheme_description": "政务接待优先的主推方案", "style_variant": "成熟稳健", "images": []},
        {"scheme_id": "B", "scheme_name": "医数中枢", "scheme_description": "科技感更强的概念方案", "style_variant": "平台科技感", "images": []},
        {"scheme_id": "C", "scheme_name": "协同引擎", "scheme_description": "合作生态表达更强的方案", "style_variant": "合作网络感", "images": []},
    ]
    cost_estimate = {
        "status": "ok",
        "output": "完成 mock 预算框架。",
        "total_budget_wan": [420, 760],
        "breakdown": {
            "基础装饰": "140-220 万",
            "多媒体与中控": "110-200 万",
            "定制展项与模型": "70-130 万",
            "灯光与机电配合": "45-90 万",
            "软装与接待家具": "25-50 万",
            "预备与管理费": "30-70 万",
        },
    }
    video_script = {
        "status": "ok",
        "output": "生成政务接待型项目介绍视频脚本。",
        "scene_sequence": [
            {"scene_no": 1, "visual": "序厅品牌墙与企业定位数字", "narration": "以可信平台姿态开场，建立政府和产业合作认知。"},
            {"scene_no": 2, "visual": "平台能力中枢屏与系统架构演示", "narration": "展示医疗数字化平台与 AI 系统如何支撑区域医疗协同。"},
            {"scene_no": 3, "visual": "政府与医院合作案例节点", "narration": "通过真实场景和合作成果证明项目落地能力。"},
            {"scene_no": 4, "visual": "未来布局与合作洽谈场景", "narration": "把展示导向合作接口和后续转化动作。"},
        ],
    }
    report = {
        "status": "ok",
        "output": "已生成首轮汇报框架。",
        "executive_summary": "该项目应定位为医疗科技企业面向政府和产业合作的接待型展示平台，核心不是单点产品展示，而是通过平台能力、合作成果和应用场景，建立可信、专业、可合作的整体认知。",
        "slide_outline": [
            "项目目标与来访对象",
            "真实需求与合作型展厅判断",
            "展示逻辑与讲解主线",
            "功能分区与接待动线建议",
            "空间气质与材料照明方向",
            "预算框架与后续真实资料清单",
        ],
    }
    feedback = {
        "status": "ok",
        "output": "形成后续替换清单。",
        "patch_actions": [
            "用真实主营业务替换 mock 公司画像",
            "用真实政府/医院案例替换 mock 合作成果",
            "补充 CAD、照片和层高机电条件后重算 zoning",
            "补充时间节点后再压缩汇报版本和实施节奏",
        ],
    }
    progress = {
        "status": "ok",
        "output": "明确 mock 阶段后的推进路线。",
        "milestones": [
            "M1：替换公司资料与重点案例",
            "M2：补录场地资料并输出真实 constraints",
            "M3：完成真实 zoning / circulation / concept",
            "M4：生成图像提示词与首轮效果图",
        ],
    }

    return {
        "structured_brief": structured_brief,
        "case_research": case_research,
        "concept": concept,
        "storyline": storyline,
        "zoning": zoning,
        "style_key": material_style["style_key"],
        "palette": material_style["palette"],
        "material_spec": material_style["material_spec"],
        "lighting_concept": material_style["lighting_concept"],
        "visual_prompt": visual_prompt,
        "schemes": schemes,
        "generated_schemes": generated_schemes,
        "generated_images": [],
        "video_script": video_script,
        "cost_estimate": cost_estimate,
        "report": report,
        "feedback": feedback,
        "progress": progress,
    }


def _build_mock_summary_markdown(project_packet: dict, result: dict) -> str:
    confirmed = project_packet["inputs"]["confirmed_by_user"]
    mocked = project_packet["inputs"]["mocked_for_test"]
    lines = [
        "# Mock Medical Project Summary",
        "",
        "## Confirmed By User",
        f"- 客户类型：{confirmed['client_type']}",
        f"- 地点：{confirmed['location']}",
        f"- 项目属性：{confirmed['site_type']}",
        f"- 面积：{confirmed['area_sqm']}㎡",
        f"- 预算：{confirmed['budget_range_cny']['low'] // 10000}-{confirmed['budget_range_cny']['high'] // 10000}万",
        f"- 目标：{confirmed['primary_goal']}",
        "",
        "## Mocked For Test",
        f"- 公司画像：{mocked['company_profile']}",
        f"- 展示主轴：{', '.join(mocked['top_showcase_topics'])}",
        f"- 必须出现：{', '.join(mocked['must_include'])}",
        "",
        "## Real Need Summary",
        *[f"- {item}" for item in result["structured_brief"]["real_need_summary"]["explicit_needs"]],
        "",
        "## Zoning",
        *[f"- {zone['zone_name']}：{zone['area_ratio']} / {zone['function']}" for zone in result["zoning"]["zones"]],
        "",
        "## Next Replace Targets",
        *[f"- {item}" for item in result["feedback"]["patch_actions"]],
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    synced = run_mock_project_sync()
    print(json.dumps(synced, ensure_ascii=False, indent=2))
