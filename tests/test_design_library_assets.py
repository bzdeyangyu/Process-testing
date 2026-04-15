from pathlib import Path


def test_each_design_md_has_nine_sections_and_three_prompts() -> None:
    root = Path(r"C:\Users\39859\Documents\codex\cc\design_library")
    style_dirs = [path for path in root.iterdir() if path.is_dir()]

    assert len(style_dirs) == 6
    for style_dir in style_dirs:
        text = (style_dir / "DESIGN.md").read_text(encoding="utf-8")
        sections = [line for line in text.splitlines() if line.startswith("## ")]
        prompts = [line for line in text.splitlines() if line.startswith("PROMPT: ")]
        assert len(sections) == 9
        assert len(prompts) >= 3
