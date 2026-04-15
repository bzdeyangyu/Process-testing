from __future__ import annotations

QUALITY_SUFFIX = "photorealistic, 8K resolution, architectural visualization, professional lighting, ultra detailed"
BANNED_PARAMS = ["--ar", "--q", "--v", "--style", "--chaos", "--seed", "midjourney"]
MIN_PROMPT_LENGTH = 320
MAX_PROMPT_LENGTH = 460

PROJECT_TYPE_MAP = {
    "企业展厅": "corporate exhibition hall",
    "科技展厅": "technology exhibition hall",
    "品牌展厅": "brand experience hall",
    "商业展示空间": "commercial exhibition space",
    "博物馆": "museum exhibition hall",
}
LOCATION_MAP = {
    "南京": "Nanjing",
    "上海": "Shanghai",
    "北京": "Beijing",
    "深圳": "Shenzhen",
    "广州": "Guangzhou",
}

VIEW_SLOTS = {
    "floor_plan": {
        "camera": "top-down conceptual floor-plan view",
        "function": "zoning logic and visitor circulation",
        "focal": "functional zones, paths, and hierarchy",
    },
    "mood_board": {
        "camera": "curated mood-board collage view",
        "function": "material and palette storytelling",
        "focal": "material swatches, media textures, and color rhythm",
    },
    "main_view_1": {
        "camera": "hero entrance wide-angle perspective",
        "function": "arrival impact and brand recognition",
        "focal": "the main arrival portal and iconic media gesture",
    },
    "main_view_2": {
        "camera": "central exhibition panoramic perspective",
        "function": "core display immersion",
        "focal": "the signature centerpiece and visitor engagement",
    },
    "node_view_1": {
        "camera": "close-up node perspective",
        "function": "interactive installation detail",
        "focal": "one tactile or digital highlight moment",
    },
    "node_view_2": {
        "camera": "secondary node intimate perspective",
        "function": "lounge or transition atmosphere",
        "focal": "one refined supporting zone with soft contrast",
    },
}


def compile_prompt(
    *,
    project_type: str,
    location: str | None,
    style_label: str,
    angle: str,
    scheme_label: str,
    scheme_description: str,
    material_phrase: str,
    palette_phrase: str,
    lighting_phrase: str,
    mood_phrase: str,
    audience_phrase: str,
    feature_phrase: str,
) -> tuple[str, dict]:
    view = VIEW_SLOTS[angle]
    project_label = PROJECT_TYPE_MAP.get(project_type, "exhibition interior")
    location_label = LOCATION_MAP.get(location or "", "project city") if location else "project city"

    prompt = (
        f"{view['camera']} of {scheme_label} {project_label} in {location_label}, "
        f"{style_label} interior, "
        f"materials featuring {material_phrase}, "
        f"lighting strategy {lighting_phrase}, "
        f"color palette {palette_phrase}, "
        f"mood set as {mood_phrase}, "
        f"focal point {feature_phrase}, "
        f"visitor experience for {audience_phrase}, "
        f"{QUALITY_SUFFIX}"
    )
    repaired = repair_prompt(prompt)
    return repaired, validate_prompt(repaired)


def validate_prompt(prompt: str) -> dict:
    lowered = prompt.lower()
    banned = [token for token in BANNED_PARAMS if token in lowered]
    required_slots_ok = all(
        phrase in lowered
        for phrase in [
            "materials featuring",
            "lighting strategy",
            "color palette",
            "mood set as",
            "focal point",
            "visitor experience",
            "photorealistic",
            "8k resolution",
            "architectural visualization",
        ]
    )
    length_ok = MIN_PROMPT_LENGTH <= len(prompt) <= MAX_PROMPT_LENGTH
    return {
        "passed": not banned and required_slots_ok and length_ok,
        "length": len(prompt),
        "length_ok": length_ok,
        "required_slots_ok": required_slots_ok,
        "banned_params_found": banned,
    }


def repair_prompt(prompt: str) -> str:
    sanitized = prompt
    for token in BANNED_PARAMS:
        sanitized = sanitized.replace(token, "")
        sanitized = sanitized.replace(token.title(), "")
    sanitized = " ".join(sanitized.replace(" ,", ",").split())
    if QUALITY_SUFFIX.lower() not in sanitized.lower():
        sanitized = sanitized.rstrip(", ") + f", {QUALITY_SUFFIX}"

    if len(sanitized) < MIN_PROMPT_LENGTH:
        extension = ", cinematic composition, precise detailing, layered spatial depth, premium interior finishing"
        sanitized = sanitized.rstrip(", ") + extension
    if len(sanitized) > MAX_PROMPT_LENGTH:
        if len(sanitized) > MAX_PROMPT_LENGTH:
            prefix_limit = MAX_PROMPT_LENGTH - len(QUALITY_SUFFIX) - 2
            sanitized = sanitized[:prefix_limit].rstrip(", ") + f", {QUALITY_SUFFIX}"

    return " ".join(sanitized.split())


def palette_phrase_from_palette(palette: list[dict]) -> str:
    colors = [item.get("hex", "") for item in palette[:2] if item.get("hex")]
    return ", ".join(colors) if colors else "#6C3EFF, #00C2FF, #0D0D0D"
