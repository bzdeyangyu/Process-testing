from agent_runtime.skill_registry import SkillRegistry


def run(skill_registry: SkillRegistry, structured_brief: dict, material_spec: dict) -> dict:
    visual_prompt = skill_registry.invoke(
        "visual_prompt",
        {"structured_brief": structured_brief, "material_spec": material_spec},
    )
    video_script = skill_registry.invoke("video_script", {"structured_brief": structured_brief, "material_spec": material_spec})
    cost_estimate = skill_registry.invoke("cost_estimate", {"structured_brief": structured_brief, "material_spec": material_spec})
    return {
        **visual_prompt,
        "video_script": video_script,
        "cost_estimate": cost_estimate,
    }
