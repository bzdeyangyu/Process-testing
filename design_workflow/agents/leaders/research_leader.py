from agent_runtime.skill_registry import SkillRegistry


def run(skill_registry: SkillRegistry, brief: str) -> dict:
    structured_brief = skill_registry.invoke("req_parser", {"brief": brief})
    case_research = skill_registry.invoke("case_research", {"structured_brief": structured_brief})
    return {"structured_brief": structured_brief, "case_research": case_research}
