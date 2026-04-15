from pathlib import Path


def test_dashboard_assets_exist_and_reference_board_data() -> None:
    root = Path(__file__).resolve().parents[1]
    dashboard_dir = root / "dashboard"

    index_path = dashboard_dir / "index.html"
    app_path = dashboard_dir / "app.js"
    styles_path = dashboard_dir / "styles.css"

    assert index_path.exists()
    assert app_path.exists()
    assert styles_path.exists()

    script = app_path.read_text(encoding="utf-8")
    html = index_path.read_text(encoding="utf-8")
    assert "boards/current" in script or "project_board_current.json" in script
    assert "boards" in script or "project_board_index.json" in script
    assert "style_match" in script
    assert "architecture.html" in html
