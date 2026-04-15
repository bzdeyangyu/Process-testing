from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
ZIP_PATH = DIST_DIR / "Process-testing-launcher.zip"

INCLUDE_FILES = [
    ".env.example",
    ".gitignore",
    "config.py",
    "generate_pptx.py",
    "inspect_board.py",
    "launch_process_testing.bat",
    "package_process_testing.py",
    "process_testing_launcher.py",
    "pyproject.toml",
    "README.md",
    "requirements.txt",
    "server.py",
]

INCLUDE_DIRS = [
    "dashboard",
    "demo",
    "design_library",
    "design_workflow",
    "docs",
    "evaluation",
    "src",
    "wiki",
]
def build_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_name in INCLUDE_FILES:
            src = ROOT / file_name
            zf.write(src, arcname=file_name)

        for dir_name in INCLUDE_DIRS:
            base = ROOT / dir_name
            for path in base.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(ROOT))


def main() -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    build_zip()
    print(f"[package] 已生成: {ZIP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
