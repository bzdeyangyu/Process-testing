"""
AI 空间设计工作流 — 统一服务入口

启动方式：
    python server.py

功能：
    - GET  /boards/current   — 返回最新工程看板快照（供看板轮询）
    - GET  /boards           — 返回所有历史运行记录
    - GET  /renders/<file>   — 提供生成图片的静态访问
    - GET  /                 — 重定向到看板 index.html
    - POST /run              — 启动 MVP 工作流（异步，在后台线程运行）
    - GET  /status           — 当前是否有工作流在运行

端口：8765（与 dashboard/app.js 中 CURRENT_BOARD_URL 对应）
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
for candidate in (ROOT_DIR, SRC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from config import OUTPUT_DIR
from agent_runtime.board import ProjectBoardRepository

# 看板静态文件目录
DASHBOARD_DIR = ROOT_DIR / "dashboard"
RENDERS_DIR = OUTPUT_DIR / "renders"
BOARD_DIR = OUTPUT_DIR / "board"

# 全局状态
_running_lock = threading.Lock()
_running: bool = False
_last_result: dict | None = None


class Handler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/boards/current":
            self._handle_board_current()
        elif path == "/boards":
            self._handle_boards()
        elif path.startswith("/renders/"):
            # 支持子目录：/renders/scheme_A/render_1.png
            rel = path[len("/renders/"):]
            self._handle_static(RENDERS_DIR, rel)
        elif path == "/status":
            self._json(200, {"running": _running, "last_result_keys": list((_last_result or {}).keys())})
        elif path == "/" or path == "/index.html":
            self._handle_static(DASHBOARD_DIR, "index.html")
        elif path.startswith("/"):
            # 尝试从 dashboard 目录提供静态文件
            self._handle_static(DASHBOARD_DIR, path.lstrip("/"))
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        length = int(self.headers.get("Content-Length", "0"))
        body_raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            body = {}

        if path == "/run":
            self._handle_run(body)
        else:
            self._json(404, {"error": "not_found"})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ── 路由处理 ────────────────────────────────────────────────────────────

    def _handle_board_current(self) -> None:
        """返回最新看板快照（图片 local_path 转为 HTTP URL）"""
        current_file = BOARD_DIR / "project_board_current.json"
        if current_file.exists():
            try:
                data = json.loads(current_file.read_text(encoding="utf-8"))
                data = _patch_image_urls(data, RENDERS_DIR)
                self._json(200, data)
                return
            except (json.JSONDecodeError, OSError):
                pass
        # 尝试从 repository 读取
        try:
            repo = ProjectBoardRepository(BOARD_DIR)
            data = repo.get_current_project_card()
            data = _patch_image_urls(data, RENDERS_DIR)
            self._json(200, data)
        except Exception:
            self._json(404, {"error": "no_board_available", "hint": "请先运行 python demo/run_mvp.py"})

    def _handle_boards(self) -> None:
        """返回所有历史运行记录"""
        try:
            repo = ProjectBoardRepository(BOARD_DIR)
            data = repo.list_project_cards()
            self._json(200, data)
        except Exception:
            self._json(200, {"runs": []})

    def _handle_run(self, body: dict) -> None:
        """在后台线程启动 MVP 工作流"""
        global _running, _last_result
        with _running_lock:
            if _running:
                self._json(409, {"error": "already_running", "hint": "当前有工作流正在运行，请等待完成"})
                return
            _running = True

        brief = body.get("brief", "为某科技企业设计 800㎡ 展厅，风格偏科技感与未来感，要求沉浸式互动体验。")
        image_provider = body.get("image_provider", "cogview")
        image_api_key = body.get("image_api_key")

        def _run() -> None:
            global _running, _last_result
            try:
                # 动态导入避免循环依赖
                from demo.run_mvp import run_mvp
                result = run_mvp(
                    brief=brief,
                    use_real_llm=True,
                    image_provider=image_provider,
                    image_api_key=image_api_key,
                )
                _last_result = result
            except Exception as exc:
                _last_result = {"error": str(exc)}
            finally:
                _running = False

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        self._json(202, {"status": "started", "brief": brief, "image_provider": image_provider})

    def _handle_static(self, base_dir: Path, filename: str) -> None:
        """提供静态文件"""
        path = (base_dir / filename).resolve()
        # 安全检查：不允许路径穿越
        try:
            path.relative_to(base_dir.resolve())
        except ValueError:
            self._json(403, {"error": "forbidden"})
            return
        if not path.exists() or not path.is_file():
            self._json(404, {"error": "file_not_found", "path": filename})
            return
        content = path.read_bytes()
        content_type = _mime(path.suffix)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(content)

    # ── 工具方法 ────────────────────────────────────────────────────────────

    def _json(self, status: int, data: dict) -> None:
        encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(encoded)

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[server] {self.address_string()} - {fmt % args}")


def _mime(suffix: str) -> str:
    mapping = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }
    return mapping.get(suffix.lower(), "application/octet-stream")


def _patch_image_urls(data: dict, renders_dir: Path) -> dict:
    """将 board result 中图片的 local_path 转为 /renders/... HTTP URL"""
    import copy
    data = copy.deepcopy(data)
    result = data.get("result", {})
    if not result:
        return data

    renders_dir_resolved = renders_dir.resolve()

    def _fix_image(img: dict) -> dict:
        local = img.get("local_path")
        if local and not img.get("url"):
            try:
                rel = Path(local).resolve().relative_to(renders_dir_resolved)
                img["url"] = "/renders/" + rel.as_posix()
            except ValueError:
                # local_path 不在 renders_dir 内，尝试按文件名匹配
                fname = Path(local).name
                parent = Path(local).parent.name
                if parent.startswith("scheme_"):
                    img["url"] = f"/renders/{parent}/{fname}"
                else:
                    img["url"] = f"/renders/{fname}"
        elif local and img.get("url") and img["url"].startswith("http"):
            # 已有 CDN URL，同时补充本地备用
            try:
                rel = Path(local).relative_to(renders_dir)
                img["local_url"] = "/renders/" + rel.as_posix()
            except ValueError:
                pass
        return img

    # 处理 generated_schemes（三套方案）
    schemes = result.get("generated_schemes", [])
    for scheme in schemes:
        scheme["images"] = [_fix_image(img) for img in scheme.get("images", [])]

    # 处理旧版 generated_images（兼容）
    images = result.get("generated_images", [])
    result["generated_images"] = [_fix_image(img) for img in images]

    data["result"] = result
    return data


def main(host: str = "0.0.0.0", port: int = 8765) -> None:
    BOARD_DIR.mkdir(parents=True, exist_ok=True)
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"""
╔══════════════════════════════════════════════════════╗
║        AI 空间设计工作流 — 服务已启动                ║
╠══════════════════════════════════════════════════════╣
║  看板地址：  http://localhost:{port}/                    ║
║  API:        http://localhost:{port}/boards/current     ║
║  启动工作流: POST http://localhost:{port}/run            ║
╚══════════════════════════════════════════════════════╝

提示：
  先跑一次工作流：  python demo/run_mvp.py
  然后刷新看板查看结果
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] 已停止")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="0.0.0.0")
    args = p.parse_args()
    main(args.host, args.port)
