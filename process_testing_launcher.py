from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".launcher_venv"
STAMP_FILE = VENV_DIR / ".deps_installed"
REQUIREMENTS_FILE = ROOT / "requirements.txt"
BOARD_SNAPSHOT = ROOT / "output" / "board" / "project_board_current.json"
SERVER_URL = "http://localhost:8765/"


def print_step(message: str) -> None:
    print(f"[launcher] {message}", flush=True)


def resolve_python() -> list[str]:
    if sys.executable:
        return [sys.executable]
    return ["python"]


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run_command(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd or ROOT, check=True)


def ensure_venv() -> Path:
    python_cmd = resolve_python()
    target = venv_python()
    if not target.exists():
        print_step("创建虚拟环境...")
        # python -m venv .launcher_venv
        run_command([*python_cmd, "-m", "venv", str(VENV_DIR)])
    if not target.exists():
        raise RuntimeError("虚拟环境创建失败。")
    return target


def ensure_dependencies(python_path: Path) -> None:
    need_install = not STAMP_FILE.exists()
    if STAMP_FILE.exists() and REQUIREMENTS_FILE.stat().st_mtime > STAMP_FILE.stat().st_mtime:
        need_install = True
    if not need_install:
        return

    print_step("安装依赖...")
    # pip install -r requirements.txt
    run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"])
    STAMP_FILE.write_text(str(time.time()), encoding="utf-8")


def ensure_demo_data(python_path: Path) -> None:
    if BOARD_SNAPSHOT.exists():
        return
    print_step("生成首次演示数据（mock）...")
    # demo/run_mvp.py --no-llm --image-provider mock
    run_command([str(python_path), "demo/run_mvp.py", "--no-llm", "--image-provider", "mock"])


def is_server_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER_URL}status", timeout=3) as response:
            return response.status >= 200
    except Exception:
        return False


def start_server(python_path: Path) -> None:
    if is_server_alive():
        return
    print_step("启动本地服务...")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(
        [str(python_path), "server.py"],
        cwd=ROOT,
        creationflags=creationflags,
    )


def wait_for_server(timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_server_alive():
            return
        time.sleep(1)
    raise RuntimeError("服务启动超时，请检查是否有端口占用或 Python 报错。")


def open_url(url: str) -> bool:
    try:
        if webbrowser.open(url):
            return True
    except Exception:
        pass

    if os.name == "nt":
        for args in (
            ["cmd", "/c", "start", "", url],
            ["explorer.exe", url],
        ):
            try:
                subprocess.Popen(args, cwd=ROOT)
                return True
            except Exception:
                continue

    return False


def ensure_python_present() -> None:
    version = sys.version_info
    if version.major < 3:
        raise RuntimeError("未检测到 Python 3。请先安装 Python 3 后再运行启动器。")


def main() -> int:
    try:
        ensure_python_present()
        python_path = ensure_venv()
        ensure_dependencies(python_path)
        ensure_demo_data(python_path)
        start_server(python_path)
        wait_for_server()
        print_step("打开看板...")
        dashboard_opened = open_url(SERVER_URL)
        if dashboard_opened:
            print_step("已完成，浏览器将打开 Process testing 看板。")
        else:
            print_step(f"未能自动打开浏览器，请手动打开: {SERVER_URL}")
        return 0
    except Exception as exc:
        print_step(f"启动失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
