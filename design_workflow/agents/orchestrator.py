from __future__ import annotations

from pathlib import Path

from agent_runtime.logger import EventLogger
from agent_runtime.schemas import EventEnvelope
from agent_runtime.skill_registry import SkillRegistry
from design_workflow.tools.image_gen import generate_image_jobs, generate_images


def run_mvp_workflow(
    *,
    brief: str,
    trace_id: str,
    skill_registry: SkillRegistry,
    logger: EventLogger,
    use_real_llm: bool,
    llm_client=None,
    board_tracker=None,
    image_provider: str = "mock",
    image_api_key: str | None = None,
    image_output_dir=None,
    image_max_workers: int | None = None,
) -> dict:
    del use_real_llm
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="task.status",
        event_type="started",
        producer="orchestrator",
        payload={"phase": "mvp"},
    ))

    structured_brief = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "req_parser",
        {"brief": brief, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    material = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "material_style",
        {"structured_brief": structured_brief, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    visual = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "visual_prompt",
        {
            "structured_brief": structured_brief,
            "material_spec": material["material_spec"],
            "llm_client": llm_client,
        },
        board_tracker=board_tracker,
    )
    image_outputs = _run_image_stage(
        trace_id=trace_id,
        logger=logger,
        visual=visual,
        board_tracker=board_tracker,
        image_provider=image_provider,
        image_api_key=image_api_key,
        image_output_dir=image_output_dir,
        image_max_workers=image_max_workers,
    )

    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="task.status",
        event_type="done",
        producer="orchestrator",
        payload={"phase": "mvp"},
    ))
    return {
        "structured_brief": structured_brief,
        **material,
        **visual,
        **image_outputs,
    }


def run_full_workflow(
    *,
    brief: str,
    trace_id: str,
    skill_registry: SkillRegistry,
    logger: EventLogger,
    llm_client=None,
    board_tracker=None,
    image_provider: str = "mock",
    image_api_key: str | None = None,
    image_output_dir=None,
    image_max_workers: int | None = None,
) -> dict:
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="task.status",
        event_type="started",
        producer="orchestrator",
        payload={"phase": "full"},
    ))

    structured_brief = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "req_parser",
        {"brief": brief, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    case_research = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "case_research",
        {"structured_brief": structured_brief, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    concept = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "concept",
        {"structured_brief": structured_brief, "case_research": case_research, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    storyline = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "storyline",
        {"structured_brief": structured_brief, "concept": concept, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    zoning = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "zoning",
        {"structured_brief": structured_brief, "storyline": storyline, "llm_client": llm_client},
        board_tracker=board_tracker,
    )

    outputs = {
        "structured_brief": structured_brief,
        "case_research": case_research,
        "concept": concept,
        "storyline": storyline,
        "zoning": zoning,
    }

    material = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "material_style",
        {"structured_brief": structured_brief, "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    outputs.update(material)
    visual = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "visual_prompt",
        {"structured_brief": structured_brief, "material_spec": material["material_spec"], "llm_client": llm_client},
        board_tracker=board_tracker,
    )
    outputs.update(visual)
    outputs.update(_run_image_stage(
        trace_id=trace_id,
        logger=logger,
        visual=visual,
        board_tracker=board_tracker,
        image_provider=image_provider,
        image_api_key=image_api_key,
        image_output_dir=image_output_dir,
        image_max_workers=image_max_workers,
    ))
    outputs["video_script"] = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "video_script",
        outputs | {"llm_client": llm_client},
        board_tracker=board_tracker,
    )
    outputs["cost_estimate"] = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "cost_estimate",
        outputs | {"llm_client": llm_client},
        board_tracker=board_tracker,
    )
    outputs["report"] = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "report",
        outputs | {"llm_client": llm_client},
        board_tracker=board_tracker,
    )
    outputs["feedback"] = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "feedback",
        outputs | {"llm_client": llm_client},
        board_tracker=board_tracker,
    )
    outputs["progress"] = _invoke_skill(
        logger,
        trace_id,
        skill_registry,
        "progress",
        outputs | {"llm_client": llm_client},
        board_tracker=board_tracker,
    )

    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="task.status",
        event_type="done",
        producer="orchestrator",
        payload={"phase": "full"},
    ))
    return outputs


def _run_image_stage(
    *,
    trace_id: str,
    logger: EventLogger,
    visual: dict,
    board_tracker=None,
    image_provider: str,
    image_api_key: str | None,
    image_output_dir,
    image_max_workers: int | None,
) -> dict:
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="agent.thought",
        event_type="reasoning",
        producer="image_gen",
        payload={"summary": "开始生成方案效果图", "provider": image_provider},
    ))
    if board_tracker is not None:
        board_tracker.mark_stage_running("image_gen")

    out_dir = Path(image_output_dir) if image_output_dir else None
    schemes = visual.get("schemes", [])
    generated_schemes = []
    total_count = 0

    if schemes:
        jobs = []
        for scheme in schemes:
            scheme_id = scheme.get("scheme_id", "A")
            scheme_name = scheme.get("scheme_name", f"方案{scheme_id}")
            scheme_output_dir = (out_dir / f"scheme_{scheme_id}") if out_dir else None
            views = scheme.get("views", [])
            for view_index, view in enumerate(views):
                prompt = view.get("prompt")
                if not prompt:
                    continue
                jobs.append({
                    "scheme_id": scheme_id,
                    "scheme_name": scheme_name,
                    "scheme_description": scheme.get("scheme_description", ""),
                    "style_variant": scheme.get("style_variant", ""),
                    "prompt": prompt,
                    "angle": view.get("angle_label", view.get("angle", f"视角{view_index + 1}")),
                    "output_dir": scheme_output_dir,
                    "filename": f"render_{view_index + 1}.png",
                    "save_locally": scheme_output_dir is not None,
                })

        logger.emit(EventEnvelope(
            trace_id=trace_id,
            topic="tool.call",
            event_type="planned",
            producer="image_gen",
            payload={"provider": image_provider, "job_count": len(jobs)},
        ))
        generated_images = generate_image_jobs(
            jobs=jobs,
            provider=image_provider,
            api_key=image_api_key,
            max_workers=image_max_workers,
        )
        total_count = len(generated_images)

        grouped: dict[str, dict] = {}
        for job, image in zip(jobs, generated_images):
            scheme_id = job["scheme_id"]
            scheme_entry = grouped.setdefault(
                scheme_id,
                {
                    "scheme_id": scheme_id,
                    "scheme_name": job["scheme_name"],
                    "scheme_description": job["scheme_description"],
                    "style_variant": job["style_variant"],
                    "images": [],
                },
            )
            scheme_entry["images"].append(image)
        generated_schemes = list(grouped.values())
    else:
        visual_prompts_list = visual.get("visual_prompts", [])
        prompt_texts = [item["prompt"] for item in visual_prompts_list if item.get("prompt")]
        if not prompt_texts:
            prompt_texts = [visual.get("visual_prompt", "modern exhibition hall, architectural visualization")]
        images = generate_images(
            prompts=prompt_texts,
            provider=image_provider,
            api_key=image_api_key,
            output_dir=out_dir,
            save_locally=out_dir is not None,
            max_workers=image_max_workers,
        )
        total_count = len(images)
        generated_schemes = [{
            "scheme_id": "A",
            "scheme_name": "方案A",
            "scheme_description": "",
            "style_variant": "",
            "images": images,
        }]

    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="skill.invoke",
        event_type="completed",
        producer="image_gen",
        payload={
            "generated_count": total_count,
            "scheme_count": len(generated_schemes),
            "provider": image_provider,
        },
    ))
    if board_tracker is not None:
        board_tracker.mark_stage_completed("image_gen", {
            "image_count": total_count,
            "scheme_count": len(generated_schemes),
            "generated_schemes": generated_schemes,
        })

    return {
        "generated_schemes": generated_schemes,
        "generated_images": generated_schemes[0]["images"] if generated_schemes else [],
    }


def _invoke_skill(
    logger: EventLogger,
    trace_id: str,
    registry: SkillRegistry,
    skill_name: str,
    payload: dict,
    board_tracker=None,
) -> dict:
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="agent.thought",
        event_type="reasoning",
        producer=skill_name,
        payload={"summary": f"准备执行 {skill_name}", "input_keys": sorted(payload.keys())},
    ))
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="tool.call",
        event_type="planned",
        producer=skill_name,
        payload={"tool": "skill_registry.invoke", "skill": skill_name},
    ))
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="skill.invoke",
        event_type="started",
        producer=skill_name,
        payload={"input": payload, "skill": skill_name},
    ))
    if board_tracker is not None:
        board_tracker.mark_stage_running(skill_name)

    result = registry.invoke(skill_name, payload)

    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="skill.invoke",
        event_type="completed",
        producer=skill_name,
        payload={"skill": skill_name, "output_keys": sorted(result.keys())},
    ))
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="agent.thought",
        event_type="summary",
        producer=skill_name,
        payload={"summary": f"{skill_name} 已完成", "output_keys": sorted(result.keys())},
    ))
    logger.emit(EventEnvelope(
        trace_id=trace_id,
        topic="tool.call",
        event_type="completed",
        producer=skill_name,
        payload={"tool": "skill_registry.invoke", "skill": skill_name},
    ))
    if board_tracker is not None:
        board_tracker.mark_stage_completed(skill_name, result)
    return result
