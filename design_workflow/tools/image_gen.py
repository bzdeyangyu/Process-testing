from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ImageProvider = Literal["cogview", "wanx", "mock"]

DEFAULT_ANGLE_NAMES = ["主入口视角", "中央展区视角", "细节特写视角"]
DEFAULT_MAX_WORKERS = 6


def _cogview_generate(
    prompt: str,
    api_key: str,
    model: str = "cogview-3-plus",
    size: str = "1344x768",
    max_retries: int = 3,
    retry_interval: int = 65,
) -> str:
    """Call the GLM CogView API and return an image URL.
    Automatically retries on 429 rate-limit with a wait interval."""
    endpoint = "https://open.bigmodel.cn/api/paas/v4/images/generations"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
    }).encode("utf-8")

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        req = Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["data"][0]["url"]
        except HTTPError as exc:
            if exc.code == 429 and attempt < max_retries - 1:
                # 限流：等待后重试
                time.sleep(retry_interval)
                last_exc = exc
                continue
            raise RuntimeError(f"CogView API 调用失败: {exc}") from exc
        except (URLError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"CogView API 调用失败: {exc}") from exc

    raise RuntimeError(f"CogView API 重试 {max_retries} 次后仍失败: {last_exc}")


def _wanx_generate(
    prompt: str,
    api_key: str,
    model: str = "wanx-v1",
    size: str = "1344*768",
) -> str:
    """Call DashScope Wanx asynchronously and return an image URL."""
    submit_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    payload = json.dumps({
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {
            "style": "<photography>",
            "size": size,
            "n": 1,
        },
    }).encode("utf-8")
    req = Request(
        submit_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        task_id = body["output"]["task_id"]
    except (HTTPError, URLError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Wanx 提交任务失败: {exc}") from exc

    poll_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    for _ in range(30):
        time.sleep(3)
        poll_req = Request(
            poll_url,
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        try:
            with urlopen(poll_req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            status = result["output"]["task_status"]
            if status == "SUCCEEDED":
                return result["output"]["results"][0]["url"]
            if status == "FAILED":
                raise RuntimeError(f"Wanx 任务失败: {result['output'].get('message', '')}")
        except (HTTPError, URLError, KeyError, json.JSONDecodeError):
            continue
    raise RuntimeError("Wanx 任务超时，90 秒内未完成")


_MOCK_PLACEHOLDER_URLS = [
    "https://picsum.photos/seed/showroom1/1344/768",
    "https://picsum.photos/seed/showroom2/1344/768",
    "https://picsum.photos/seed/showroom3/1344/768",
]


def _mock_generate(prompt: str, index: int = 0) -> str:
    del prompt
    return _MOCK_PLACEHOLDER_URLS[index % len(_MOCK_PLACEHOLDER_URLS)]


def generate_images(
    prompts: list[str],
    provider: ImageProvider = "cogview",
    api_key: str | None = None,
    output_dir: Path | None = None,
    save_locally: bool = False,
    angle_names: list[str] | None = None,
    max_workers: int | None = None,
) -> list[dict]:
    """Generate a batch of images concurrently while preserving result order."""
    jobs = []
    labels = angle_names or DEFAULT_ANGLE_NAMES
    for index, prompt in enumerate(prompts):
        jobs.append({
            "prompt": prompt,
            "angle": labels[index] if index < len(labels) else f"视角{index + 1}",
            "output_dir": output_dir,
            "filename": f"render_{index + 1}.png",
            "save_locally": save_locally,
        })
    return generate_image_jobs(
        jobs=jobs,
        provider=provider,
        api_key=api_key,
        max_workers=max_workers,
    )


# CogView 免费账号 QPS=1，必须串行；其他 provider 可以并发
_SERIAL_PROVIDERS: set[str] = {"cogview"}
# cogview 两张图之间的最小间隔（秒），避免连续请求触发 429
_COGVIEW_INTER_IMAGE_GAP = 5


def generate_image_jobs(
    *,
    jobs: list[dict],
    provider: ImageProvider = "cogview",
    api_key: str | None = None,
    max_workers: int | None = None,
) -> list[dict]:
    """Generate heterogeneous image jobs concurrently and keep per-job failures isolated."""
    if not jobs:
        return []

    # CogView 必须串行，避免并发全部 429
    if provider in _SERIAL_PROVIDERS:
        results: list[dict] = []
        for index, job in enumerate(jobs):
            result = _run_single_job(index, job, provider, api_key)
            results.append(result)
            # 成功后等一小段避免下一张立即 429
            if result.get("status") == "success" and index < len(jobs) - 1:
                time.sleep(_COGVIEW_INTER_IMAGE_GAP)
        return results

    worker_count = _resolve_worker_count(len(jobs), max_workers)
    ordered: list[dict | None] = [None] * len(jobs)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_run_single_job, index, job, provider, api_key): index
            for index, job in enumerate(jobs)
        }
        for future in as_completed(futures):
            index = futures[future]
            ordered[index] = future.result()

    return [item for item in ordered if item is not None]


def _resolve_worker_count(job_count: int, max_workers: int | None) -> int:
    requested = max_workers or DEFAULT_MAX_WORKERS
    return max(1, min(requested, job_count))


def _run_single_job(
    index: int,
    job: dict,
    provider: ImageProvider,
    api_key: str | None,
) -> dict:
    prompt = job["prompt"]
    angle = job.get("angle", f"视角{index + 1}")
    output_dir = job.get("output_dir")
    filename = job.get("filename", f"render_{index + 1}.png")
    save_locally = bool(job.get("save_locally"))

    try:
        url = _generate_single_url(index=index, prompt=prompt, provider=provider, api_key=api_key)
        local_path = None
        if save_locally and output_dir and url:
            local_path = _download_image(url, Path(output_dir), filename)
        return {
            "angle": angle,
            "prompt": prompt,
            "url": url,
            "local_path": str(local_path) if local_path else None,
            "status": "success",
        }
    except Exception as exc:
        return {
            "angle": angle,
            "prompt": prompt,
            "url": None,
            "local_path": None,
            "status": "error",
            "error": str(exc),
        }


def _generate_single_url(*, index: int, prompt: str, provider: ImageProvider, api_key: str | None) -> str:
    if provider == "mock":
        return _mock_generate(prompt, index=index)
    if provider == "cogview":
        if not api_key:
            raise ValueError("cogview 模式需要提供 api_key")
        return _cogview_generate(prompt, api_key=api_key)
    if provider == "wanx":
        if not api_key:
            raise ValueError("wanx 模式需要提供 api_key")
        return _wanx_generate(prompt, api_key=api_key)
    raise ValueError(f"不支持的 provider: {provider}")


def _download_image(url: str, output_dir: Path, filename: str) -> Path | None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            path.write_bytes(resp.read())
        return path
    except Exception:
        return None
