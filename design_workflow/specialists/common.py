from __future__ import annotations

import asyncio

from design_workflow.llm_helpers import request_json


def normalize_style_preferences(structured_brief: dict) -> list[str]:
    style_preferences = structured_brief.get("style_preferences", [])
    if isinstance(style_preferences, dict):
        values: list[str] = []
        for key in ("primary", "secondary"):
            value = style_preferences.get(key)
            if isinstance(value, str) and value:
                values.append(value)
        keywords = style_preferences.get("keywords", [])
        if isinstance(keywords, list):
            values.extend(str(keyword) for keyword in keywords if keyword)
        return values
    if isinstance(style_preferences, list):
        return [str(item) for item in style_preferences if item]
    if isinstance(style_preferences, str):
        return [style_preferences]
    return []


def normalize_audience(structured_brief: dict) -> list[str]:
    audience = structured_brief.get("audience", [])
    if isinstance(audience, dict):
        values: list[str] = []
        for key in ("primary", "secondary", "tertiary", "quaternary"):
            value = audience.get(key)
            if isinstance(value, str) and value:
                values.append(value)
        characteristics = audience.get("characteristics", [])
        if isinstance(characteristics, list):
            values.extend(str(item) for item in characteristics if item)
        return values
    if isinstance(audience, list):
        return [str(item) for item in audience if item]
    if isinstance(audience, str):
        return [audience]
    return []


def summarize_brief(structured_brief: dict) -> str:
    project_type = structured_brief.get("project_type", "空间项目")
    area_sqm = structured_brief.get("area_sqm", 800)
    styles = ", ".join(normalize_style_preferences(structured_brief)[:3]) or "现代"
    return f"{project_type} / {area_sqm}㎡ / 风格偏好: {styles}"


def complete_with_llm(
    *,
    input_dict: dict,
    system_prompt: str,
    user_prompt: str,
    fallback: dict,
) -> dict:
    llm_client = input_dict.get("llm_client")
    if llm_client is None:
        return fallback
    return asyncio.run(
        request_json(
            llm_client=llm_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback=fallback,
        )
    )
