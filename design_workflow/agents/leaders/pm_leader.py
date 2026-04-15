from agent_runtime.skill_registry import SkillRegistry


def run(skill_registry: SkillRegistry, payload: dict) -> dict:
    report = skill_registry.invoke("report", payload)
    feedback = skill_registry.invoke("feedback", payload)
    progress = skill_registry.invoke("progress", payload)
    return {
        "report": report,
        "feedback": feedback,
        "progress": progress,
    }
