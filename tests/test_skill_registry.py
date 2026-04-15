from agent_runtime.skill_registry import SkillDef, SkillRegistry


def test_skill_registry_registers_and_invokes_skill() -> None:
    registry = SkillRegistry()

    def handle(input_dict: dict) -> dict:
        return {"result": input_dict["value"].upper()}

    registry.register_skill(
        SkillDef(
            name="upper",
            description="Uppercase a value.",
            input_schema={"type": "object", "required": ["value"]},
            output_schema={"type": "object", "required": ["result"]},
            handler=handle,
            upgrade_path="agents/upper-agent.md",
            tools=["noop"],
            hooks=[],
        )
    )

    result = registry.invoke("upper", {"value": "hello"})

    assert result == {"result": "HELLO"}
    assert registry.list_skills() == ["upper"]
