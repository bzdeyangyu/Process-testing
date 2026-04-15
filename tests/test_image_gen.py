import threading
import time
from pathlib import Path

from design_workflow.tools import image_gen


def test_generate_images_runs_in_parallel_and_keeps_batch_alive(tmp_path: Path, monkeypatch) -> None:
    lock = threading.Lock()
    start_order: list[str] = []

    def fake_generate(prompt: str, api_key: str, model: str = "cogview-3-plus", size: str = "1344x768") -> str:
        with lock:
            start_order.append(prompt)
        time.sleep(0.15)
        if prompt == "broken":
            raise RuntimeError("boom")
        return f"https://example.com/{prompt}.png"

    def fake_download(url: str, output_dir: Path, filename: str) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        path.write_text(url, encoding="utf-8")
        return path

    monkeypatch.setattr(image_gen, "_cogview_generate", fake_generate)
    monkeypatch.setattr(image_gen, "_download_image", fake_download)

    started = time.perf_counter()
    results = image_gen.generate_images(
        prompts=["one", "two", "broken", "three"],
        provider="cogview",
        api_key="key",
        output_dir=tmp_path,
        save_locally=True,
        max_workers=4,
    )
    elapsed = time.perf_counter() - started

    assert [item["prompt"] for item in results] == ["one", "two", "broken", "three"]
    assert [item["status"] for item in results] == ["success", "success", "error", "success"]
    assert "boom" in results[2]["error"]
    assert results[0]["local_path"]
    assert elapsed < 0.45
    assert len(start_order) == 4
