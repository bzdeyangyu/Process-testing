from __future__ import annotations

from pathlib import Path

from config import DESIGN_LIB_DIR, WIKI_DIR


def parse_brief(brief: str) -> dict:
    project_type = "科技展厅" if "科技" in brief else "展览空间"
    audience = "企业客户与公众访客"
    area_sqm = 800 if "800" in brief else 500
    return {
        "project_type": project_type,
        "audience": audience,
        "area_sqm": area_sqm,
    }


def extract_constraints(brief: str) -> dict:
    style_preferences: list[str] = []
    if "科技" in brief:
        style_preferences.append("科技感")
    if "未来" in brief:
        style_preferences.append("未来感")
    if not style_preferences:
        style_preferences.append("现代简洁")
    return {
        "style_preferences": style_preferences,
        "special_requirements": ["沉浸式互动", "品牌展示"],
    }


def validate_requirements(payload: dict) -> None:
    if "area_sqm" not in payload:
        raise ValueError("area_sqm is required")


def get_design_spec(style_key: str) -> dict:
    path = DESIGN_LIB_DIR / style_key / "DESIGN.md"
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    colors = [line.split(": ", 1)[1] for line in lines if line.startswith("HEX: ")]
    prompts = [line.split(": ", 1)[1] for line in lines if line.startswith("PROMPT: ")]
    materials = [line.split(": ", 1)[1] for line in lines if line.startswith("MATERIAL: ")]
    return {
        "style_key": style_key,
        "raw": text,
        "colors": colors,
        "materials": materials,
        "agent_prompt_guide": prompts,
    }


def color_palette(design_spec: dict) -> list[dict]:
    semantic_names = ["primary", "accent", "support"]
    return [
        {"name": semantic_names[index] if index < len(semantic_names) else f"color-{index+1}", "hex": color}
        for index, color in enumerate(design_spec["colors"][:3])
    ]


def material_spec(design_spec: dict, palette: list[dict], structured_brief: dict) -> dict:
    return {
        "style_key": design_spec["style_key"],
        "project_type": structured_brief["project_type"],
        "palette": palette,
        "materials": design_spec["materials"][:3],
        "direction": "未来科技与品牌沉浸体验",
    }


def style_inject(*, prompt_template: str, structured_brief: dict, material_spec: dict) -> str:
    palette = ", ".join(item["hex"] for item in material_spec["palette"])
    materials = ", ".join(material_spec["materials"])
    return (
        f"{prompt_template}\n"
        f"项目类型: {structured_brief['project_type']}\n"
        f"面积: {structured_brief['area_sqm']}㎡\n"
        f"色彩: {palette}\n"
        f"材料: {materials}\n"
        f"# [TODO: REAL API]"
    )


def wiki_update(page_name: str, content: str, source_agent: str) -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    pages = WIKI_DIR / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    path = pages / f"{page_name}.md"
    prefix = f"- {source_agent}: "
    with path.open("a", encoding="utf-8") as handle:
        handle.write(prefix + content + "\n")


def wiki_query(keywords: list[str]) -> str | None:
    pages = WIKI_DIR / "pages"
    if not pages.exists():
        return None
    lowered = [keyword.lower() for keyword in keywords]
    for path in sorted(pages.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        name = path.stem.replace("-", " ")
        if all(keyword in (content + "\n" + name).lower() for keyword in lowered):
            return content
    return None


def wiki_lint() -> dict:
    pages = WIKI_DIR / "pages"
    orphan_pages: list[str] = []
    if pages.exists():
        for path in sorted(pages.glob("*.md")):
            if path.stat().st_size == 0:
                orphan_pages.append(path.name)
    return {
        "orphan_pages": orphan_pages,
        "conflicts": [],
        "outdated_pages": [],
    }
