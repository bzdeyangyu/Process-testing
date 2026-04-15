from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class SkillDef:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    upgrade_path: str
    tools: list[str]
    hooks: list[str]


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDef] = {}

    def register_skill(self, skill_def: SkillDef) -> None:
        self._skills[skill_def.name] = skill_def

    def invoke(self, skill_name: str, input_dict: dict[str, Any]) -> dict[str, Any]:
        skill = self._skills[skill_name]
        return skill.handler(input_dict)

    def list_skills(self) -> list[str]:
        return sorted(self._skills.keys())
