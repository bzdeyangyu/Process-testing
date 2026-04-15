from agent_runtime.skill_registry import SkillRegistry


def run(skill_registry: SkillRegistry, structured_brief: dict) -> dict:
    concept = skill_registry.invoke("concept", {"structured_brief": structured_brief})
    storyline = skill_registry.invoke("storyline", {"structured_brief": structured_brief})
    zoning = skill_registry.invoke("zoning", {"structured_brief": structured_brief})
    material = skill_registry.invoke("material_style", {"structured_brief": structured_brief})
    return {
        "concept": concept,
        "storyline": storyline,
        "zoning": zoning,
        **material,
    }
