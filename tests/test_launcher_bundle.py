from pathlib import Path


def test_launcher_bundle_files_exist_and_cover_bootstrap_flow() -> None:
    root = Path(__file__).resolve().parents[1]

    batch_launcher = root / "launch_process_testing.bat"
    python_launcher = root / "process_testing_launcher.py"
    package_script = root / "package_process_testing.py"
    quickstart = root / "docs" / "launcher_quickstart.md"
    architecture_page = root / "dashboard" / "architecture.html"

    assert batch_launcher.exists()
    assert python_launcher.exists()
    assert package_script.exists()
    assert quickstart.exists()
    assert architecture_page.exists()

    batch_text = batch_launcher.read_text(encoding="utf-8")
    python_text = python_launcher.read_text(encoding="utf-8")
    package_text = package_script.read_text(encoding="utf-8")
    quickstart_text = quickstart.read_text(encoding="utf-8")
    architecture_text = architecture_page.read_text(encoding="utf-8")

    assert "process_testing_launcher.py" in batch_text

    assert "python -m venv" in python_text
    assert "pip install -r requirements.txt" in python_text
    assert "demo/run_mvp.py --no-llm --image-provider mock" in python_text
    assert "server.py" in python_text
    assert "http://localhost:8765/" in python_text
    assert "webbrowser.open" in python_text
    assert "architecture.html" not in python_text

    assert "zipfile" in package_text
    assert "Process-testing-launcher.zip" in package_text

    assert "launch_process_testing.bat" in quickstart_text
    assert "Python 3.13" in quickstart_text or "Python 3" in quickstart_text
    assert "dashboard" in quickstart_text.lower()
    assert "architecture" in quickstart_text.lower()
    assert "<title>" in architecture_text
