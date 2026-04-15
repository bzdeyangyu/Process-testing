"""
三层 Prompt 体系 - Exec Prompts（输出格式约束）
严格定义每个 Specialist 的 JSON Schema、字段说明和示例值
参考 Manus Agent 工具定义风格：类型/枚举/必填/约束一应俱全
"""
from __future__ import annotations

EXEC_PROMPTS: dict[str, str] = {

    "req_parser": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块或额外文字：
{
  "project_type": "字符串，展厅类型，如：科技展厅 / 博物馆 / 商业展示空间 / 企业展厅 / 文化展览",
  "area_sqm": 整数，单位平方米，必须是数字而非字符串，如：800,
  "location": "字符串，城市或具体地址，若无则填 null",
  "budget_cny": 数字或 null，单位元，若无则为 null,
  "style_preferences": ["字符串数组，至少1个", "如：科技感、未来感、极简"],
  "special_requirements": ["字符串数组，如：沉浸式体验、互动装置、无障碍设施"],
  "audience": "字符串，目标受众，如：企业客户、专业人士、公众访客",
  "duration_days": 整数或 null，展期天数，永久展或未知则为 null,
  "key_constraints": ["字符串数组，核心约束，如：沉浸式互动体验必须实现"]
}
""",

    "material_style": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块或额外文字：
{
  "style_key": "六选一枚举：tech-showroom / museum-narrative / eco-biophilic / luxury-boutique / industrial-loft / minimalist-zen",
  "palette": [
    {"name": "primary", "hex": "#XXXXXX", "usage": "主色调用途，如：深色基底，营造科技感"},
    {"name": "accent", "hex": "#XXXXXX", "usage": "强调色用途，如：交互高亮元素"},
    {"name": "support", "hex": "#XXXXXX", "usage": "辅助色用途，如：品牌配色"}
  ],
  "materials": [
    "材料名称（使用位置，工艺说明），如：拉丝铝板（墙面饰面，阳极氧化处理）",
    "材料名称（使用位置，工艺说明）",
    "材料名称（使用位置，工艺说明）"
  ],
  "direction": "50-100字中文设计方向描述，说明整体空间调性",
  "lighting_concept": "30-60字照明概念描述，说明光环境策略"
}
""",

    "visual_prompt": """\
请严格返回如下 JSON 格式，输出三套完整方案，不要包含任何 markdown 代码块或额外文字：
{
  "schemes": [
    {
      "scheme_id": "A",
      "scheme_name": "主推方案的中文名称，如：数字极光",
      "scheme_description": "30-50字中文方案特色描述",
      "style_variant": "该方案的风格变体描述，如：成熟科技感",
      "views": [
        {
          "angle": "floor_plan",
          "angle_label": "平面图",
          "prompt": "英文 Prompt：top-down conceptual floor plan of [project type], showing functional zones and circulation paths, [style] interior design layout, architectural diagram style with color zones, clean lines, photorealistic, 8K resolution, architectural visualization, ultra detailed"
        },
        {
          "angle": "mood_board",
          "angle_label": "氛围图",
          "prompt": "英文 Prompt：mood board collage for [project type] interior design, showcasing [materials] textures and [color palette] color scheme, atmospheric lighting details, material samples arrangement, design inspiration board style, photorealistic, 8K resolution, architectural visualization, ultra detailed"
        },
        {
          "angle": "main_view_1",
          "angle_label": "主效果图1",
          "prompt": "英文 Prompt：grand entrance view of [project type], [materials] facade with [lighting] accent lighting, [color] color scheme, immersive atmosphere, wide angle architectural shot, photorealistic, 8K resolution, architectural visualization, ultra detailed"
        },
        {
          "angle": "main_view_2",
          "angle_label": "主效果图2",
          "prompt": "英文 Prompt：central exhibition area of [project type], [feature elements], dramatic [lighting type] lighting, [color palette] tones, visitors experiencing the space, photorealistic, 8K resolution, architectural visualization, ultra detailed"
        },
        {
          "angle": "node_view_1",
          "angle_label": "节点效果图1",
          "prompt": "英文 Prompt：close-up detail shot of [key installation/display element] in [project type], [material] surface texture, [lighting] precision lighting, [color accent] highlight details, photorealistic, 8K resolution, architectural visualization, ultra detailed"
        },
        {
          "angle": "node_view_2",
          "angle_label": "节点效果图2",
          "prompt": "英文 Prompt：[secondary node: lounge/exit/immersive zone] detail in [project type], [material] finishes, [ambient light] soft lighting, [color] warm tones, comfortable atmosphere, photorealistic, 8K resolution, architectural visualization, ultra detailed"
        }
      ]
    },
    {
      "scheme_id": "B",
      "scheme_name": "创意方案的中文名称",
      "scheme_description": "30-50字方案特色描述，强调创意突破点",
      "style_variant": "创意变体描述，如：前卫解构主义",
      "views": [ ... 同上6个视图对象，内容体现方案B的创意差异化 ... ]
    },
    {
      "scheme_id": "C",
      "scheme_name": "经济方案的中文名称",
      "scheme_description": "30-50字方案特色描述，强调经济实用",
      "style_variant": "经济变体描述，如：简洁实用科技感",
      "views": [ ... 同上6个视图对象，内容体现方案C的材料经济性 ... ]
    }
  ]
}

重要约束：
1. 所有 prompt 字段必须是英文
2. 禁止在 prompt 中使用 --ar、--q、--v、--style 等 Midjourney 专属参数
3. 每条 prompt 结尾必须包含：photorealistic, 8K resolution, architectural visualization, ultra detailed
4. 三套方案的 prompt 内容必须有实质性差异，不能只改几个词
5. floor_plan 的 prompt 应强调俯视视角和平面布局
6. mood_board 的 prompt 应强调材质纹理和色彩氛围
""",

    "case_research": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "cases": [
    {
      "case_name": "项目名称",
      "location": "城市，国家",
      "area_sqm": 面积整数,
      "year": 完工年份整数或 null,
      "design_highlight": "设计亮点，不超过50字",
      "style_tags": ["风格标签1", "风格标签2"],
      "reference_url": null
    }
  ],
  "synthesis": "50字以内，提炼这些案例对本项目最有价值的共同设计规律"
}
""",

    "concept": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "concept_title": "概念名称，5-10个汉字，有张力和记忆点",
  "concept_description": "概念描述，100-200字，有文学性和设计感",
  "core_experience": [
    "体验节点1：一句话描述观众在此的核心感受",
    "体验节点2：一句话描述",
    "体验节点3：一句话描述"
  ],
  "design_narrative": "叙事逻辑，说明时间线或空间序列如何展开（进入→发展→高潮→余韵）",
  "visual_metaphor": "视觉隐喻，用一个具体意象概括整个空间（如：光之容器 / 数字森林）"
}
""",

    "storyline": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "storyline_title": "叙事主题名称",
  "acts": [
    {
      "act_name": "章节名称",
      "space_name": "对应空间名称",
      "duration_min": 停留时长整数（分钟）,
      "experience_type": "四选一：观看 / 互动 / 沉浸 / 休憩",
      "emotion_curve": "该章节的情绪关键词，如：好奇→惊叹"
    }
  ],
  "flow_logic": "动线逻辑说明（进入→展开→高潮→结尾），说明各章节之间的转承关系",
  "total_duration_min": 所有章节时长之和整数
}
""",

    "zoning": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "zones": [
    {
      "zone_name": "功能区名称",
      "area_ratio": "百分比字符串，如 25%",
      "function": "功能描述",
      "position": "位置描述：入口区/中央区/侧翼区/深部区/出口区",
      "adjacent_zones": ["相邻区域名称"]
    }
  ],
  "circulation": "主动线描述，说明参观路径的起终点和主要节点",
  "key_nodes": ["入口节点名称", "高潮区节点名称", "出口节点名称"]
}
""",

    "video_script": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "duration_sec": 视频总时长整数（30/45/60之一）,
  "scenes": [
    {
      "scene_no": 场景序号整数,
      "visual": "画面描述，20字以内",
      "narration": "旁白文字，配合画面节奏",
      "duration_sec": 该场景时长整数
    }
  ],
  "bgm_style": "背景音乐风格描述，如：科技感电子配乐，节奏感强",
  "call_to_action": "结尾行动号召语，10字以内"
}
""",

    "cost_estimate": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "total_estimate_cny": 总造价整数（元）,
  "unit_cost_sqm": 每平方米综合造价整数,
  "cost_level": "三选一：普通 / 高端 / 顶级",
  "breakdown": [
    {
      "category": "分项名称，如：主材费",
      "amount_cny": 金额整数,
      "percentage": "占比字符串，如 35%",
      "notes": "说明，如：含拉丝铝板、LED屏"
    }
  ],
  "confidence": "三选一：低 / 中 / 高",
  "notes": "造价估算说明，如：不含软装和AV系统"
}
""",

    "report": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "executive_summary": "执行摘要，200字以内，专业易读",
  "key_highlights": [
    "亮点1：具体可量化或可感知的设计优势",
    "亮点2",
    "亮点3"
  ],
  "next_steps": [
    "下一步行动1：含动词和时间节点，如：提交初步概念方案PPT（3个工作日内）",
    "下一步行动2",
    "下一步行动3"
  ],
  "risks": ["风险提示1", "风险提示2"]
}
""",

    "feedback": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "approved_items": ["已通过的设计决策1", "已通过的决策2"],
  "revision_items": [
    {
      "item": "修改项名称",
      "current_design": "当前方案描述",
      "revision_direction": "修改方向描述",
      "effort": "三选一：小改 / 中改 / 大改"
    }
  ],
  "new_requirements": ["新增需求1（若无则空数组）"],
  "priority": "三选一：high / medium / low"
}
""",

    "progress": """\
请严格返回如下 JSON 格式，不要包含任何 markdown 代码块：
{
  "completed_phases": ["已完成阶段名称列表"],
  "current_phase": "当前正在推进的阶段名称",
  "pending_phases": ["待启动阶段名称列表"],
  "blockers": ["阻碍项描述，若无则空数组"],
  "completion_percentage": 整体完成度百分比整数（0-100）,
  "estimated_completion": "预计完成时间的自然语言描述"
}
""",
}
