from __future__ import annotations

from design_workflow.specialists.common import complete_with_llm

def handle(input_dict: dict) -> dict:
    visual_prompt = input_dict.get("visual_prompt", "")
    storyline = input_dict.get("storyline", {})
    sequence = storyline.get("experience_sequence", [])
    scene_sequence = [
        {
            "scene": f"Scene {index + 1}",
            "focus": item.get("zone", "展厅节点"),
            "duration_sec": 30 if index < 4 else 20,
            "voiceover": f"镜头展示{item.get('zone', '核心区域')}，强调{item.get('goal', '品牌价值')}。",
        }
        for index, item in enumerate(sequence[:5])
    ]
    fallback = {
        "status": "ok",
        "output": "完成展厅漫游脚本大纲",
        "scene_sequence": scene_sequence,
        "voiceover_style": "专业、克制、面向品牌访客",
        "total_duration_sec": sum(scene["duration_sec"] for scene in scene_sequence),
    }
    return complete_with_llm(
        input_dict=input_dict,
        system_prompt="你是展厅视频分镜脚本专家，只返回 JSON。",
        user_prompt=(
            "请输出展厅漫游脚本，包含镜头顺序、时长与解说。"
            f"\n故事线: {storyline}"
            f"\n视觉描述: {visual_prompt}"
            f"\n目标输出字段: status, output, scene_sequence, voiceover_style, total_duration_sec"
            f"\n参考 fallback: {fallback}"
        ),
        fallback=fallback,
    )
