from __future__ import annotations

import asyncio

from design_workflow.llm_helpers import request_json
from design_workflow.prompts.exec_prompts import EXEC_PROMPTS
from design_workflow.prompts.scene_prompts import make_req_parser_scene
from design_workflow.prompts.system_prompts import SYSTEM_PROMPTS
from design_workflow.specialists.intake_standard import enrich_to_output_standard
from design_workflow.tools.mock_tools import extract_constraints, parse_brief, validate_requirements


def handle(input_dict: dict) -> dict:
    brief = input_dict["brief"]
    parsed = parse_brief(brief)
    constraints = extract_constraints(brief)

    base_payload = {
        "project_type": parsed["project_type"],
        "area_sqm": parsed["area_sqm"],
        "style_preferences": constraints["style_preferences"],
        "special_requirements": constraints["special_requirements"],
        "audience": parsed["audience"],
        "location": None,
        "budget_cny": None,
        "duration_days": None,
        "key_constraints": [],
    }
    validate_requirements(base_payload)

    llm_client = input_dict.get("llm_client")
    if llm_client is None:
        return enrich_to_output_standard(base_payload)

    scene = make_req_parser_scene(brief)
    result = asyncio.run(
        request_json(
            llm_client=llm_client,
            system_prompt=SYSTEM_PROMPTS["req_parser"],
            user_prompt=f"{scene}\n\n{EXEC_PROMPTS['req_parser']}\n\n任务书内容：\n{brief}",
            fallback=base_payload,
        )
    )
    validate_requirements(result)
    return enrich_to_output_standard(result)
