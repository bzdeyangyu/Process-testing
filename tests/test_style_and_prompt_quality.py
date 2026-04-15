from design_workflow.specialists.material_style import handle as material_style_handle
from design_workflow.specialists.visual_prompt import handle as visual_prompt_handle


def test_material_style_routes_brand_experience_for_brand_led_showroom() -> None:
    structured_brief = {
        "project_type": "企业展厅",
        "area_sqm": 800,
        "location": "南京",
        "style_preferences": ["科技感", "未来感"],
        "special_requirements": ["品牌展示", "客户接待", "小型发布活动", "沉浸式互动"],
        "audience": "品牌客户与合作伙伴",
        "key_constraints": [],
    }

    result = material_style_handle({"structured_brief": structured_brief, "llm_client": None})

    assert result["style_key"] == "brand-experience"
    assert result["style_match"]["selected_style_key"] == "brand-experience"
    assert result["style_match"]["top_candidates"][0]["style_key"] == "brand-experience"
    assert any(candidate["style_key"] == "tech-showroom" for candidate in result["style_match"]["top_candidates"])


def test_visual_prompt_compiles_stable_prompts_with_quality_report() -> None:
    structured_brief = {
        "project_type": "企业展厅",
        "area_sqm": 800,
        "location": "南京",
        "style_preferences": ["科技感", "未来感"],
        "special_requirements": ["品牌展示", "客户接待", "小型发布活动", "沉浸式互动"],
        "audience": "品牌客户与合作伙伴",
        "key_constraints": [],
    }
    material = material_style_handle({"structured_brief": structured_brief, "llm_client": None})

    result = visual_prompt_handle({
        "structured_brief": structured_brief,
        "material_spec": material["material_spec"],
        "llm_client": None,
    })

    schemes = result["schemes"]
    assert len(schemes) == 3
    assert len({scheme["views"][2]["prompt"] for scheme in schemes}) == 3

    for scheme in schemes:
        assert len(scheme["views"]) == 6
        for view in scheme["views"]:
            prompt = view["prompt"]
            quality_report = view["quality_report"]
            assert 320 <= len(prompt) <= 460
            assert quality_report["passed"] is True
            assert quality_report["length_ok"] is True
            assert quality_report["required_slots_ok"] is True
            assert quality_report["banned_params_found"] == []
            assert "photorealistic" in prompt.lower()
            assert "8k resolution" in prompt.lower()
            assert "architectural visualization" in prompt.lower()
