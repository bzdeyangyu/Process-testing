from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
WIKI_DIR = BASE_DIR / "wiki"
DESIGN_LIB_DIR = BASE_DIR / "design_library"
OUTPUT_DIR = BASE_DIR / "output"
HOOKS_ENABLED = True
SIGNAL_DIR = BASE_DIR / ".runtime" / "signals"
MVP_MODE = False
SKILL_REGISTRY_AUTO_LOAD = True

LLM_MODE = os.getenv("LLM_MODE", "real")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4")

# 生图专用 API Key（CogView 复用 GLM 同账号 key）；优先读环境变量
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", API_KEY)
