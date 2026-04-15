from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from agent_runtime.schemas import utc_now

PROJECT_ID = "space-design-workflow"
PROJECT_NAME = "AI空间设计工作流"

FULL_STAGE_ORDER = [
    ("req_parser", "需求解析"),
    ("case_research", "案例研究"),
    ("concept", "概念提炼"),
    ("storyline", "故事线"),
    ("zoning", "空间分区"),
    ("material_style", "材料与风格"),
    ("visual_prompt", "视觉提示词"),
    ("image_gen", "效果图生成"),
    ("video_script", "视频脚本"),
    ("cost_estimate", "成本估算"),
    ("report", "汇报生成"),
    ("feedback", "反馈处理"),
    ("progress", "进度计划"),
]
MVP_STAGE_ORDER = [
    ("req_parser", "需求解析"),
    ("material_style", "材料与风格"),
    ("visual_prompt", "视觉提示词"),
    ("image_gen", "效果图生成"),
]
ARTIFACT_ORDER = [
    "structured_brief",
    "case_research",
    "concept",
    "storyline",
    "zoning",
    "material_style",
    "visual_prompt",
    "image_gen",
    "video_script",
    "cost_estimate",
    "report",
    "feedback",
    "progress",
]
ARTIFACT_LABELS = {
    "structured_brief": "结构化需求",
    "case_research": "案例研究",
    "concept": "概念提炼",
    "storyline": "故事线",
    "zoning": "空间分区",
    "material_style": "材料与风格",
    "visual_prompt": "视觉提示词",
    "image_gen": "效果图生成",
    "video_script": "视频脚本",
    "cost_estimate": "成本估算",
    "report": "汇报输出",
    "feedback": "反馈处理",
    "progress": "进度计划",
}


@dataclass(slots=True)
class _StageConfig:
    specialist: str
    phase: str


def _stage_configs(mode: str) -> list[_StageConfig]:
    selected = MVP_STAGE_ORDER if mode == "mvp" else FULL_STAGE_ORDER
    return [_StageConfig(specialist=name, phase=phase) for name, phase in selected]


class ProjectBoardTracker:
    def __init__(
        self,
        *,
        board_dir: Path,
        project_id: str,
        project_name: str,
        run_id: str,
        title: str,
        brief: str,
        mode: str,
    ) -> None:
        self._board_dir = Path(board_dir)
        self._board_dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._project_id = project_id
        self._project_name = project_name
        self._artifact_store: dict[str, dict] = {}
        now = utc_now()
        self._snapshot = {
            "project_id": project_id,
            "project_name": project_name,
            "run_id": run_id,
            "mode": mode,
            "title": title,
            "brief_summary": _shorten(brief, 120),
            "status": "pending",
            "overall_progress": 0,
            "current_phase": "待开始",
            "current_specialist": None,
            "started_at": now,
            "updated_at": now,
            "last_event": "project.created",
            "completion_summary": [],
            "current_situation": "任务已创建，等待开始。",
            "artifacts": _empty_artifacts(),
            "timeline": [],
            "stages": [
                {
                    "specialist": config.specialist,
                    "phase": config.phase,
                    "status": "pending",
                    "summary": "",
                    "started_at": None,
                    "updated_at": now,
                    "output_keys": [],
                    "output": None,
                }
                for config in _stage_configs(mode)
            ],
        }
        self._write()

    def start(self) -> None:
        self._snapshot["status"] = "running"
        self._snapshot["current_phase"] = "准备中"
        self._snapshot["current_situation"] = "项目已启动，等待首个阶段开始。"
        self._snapshot["last_event"] = "project.started"
        self._timeline("project.started", "项目已启动。")
        self._write()

    def mark_stage_running(self, specialist: str) -> None:
        stage = self._find_stage(specialist)
        now = utc_now()
        stage["status"] = "running"
        stage["started_at"] = stage["started_at"] or now
        stage["updated_at"] = now
        self._snapshot["status"] = "running"
        self._snapshot["current_phase"] = stage["phase"]
        self._snapshot["current_specialist"] = specialist
        self._snapshot["updated_at"] = now
        self._snapshot["last_event"] = f"{specialist}.started"
        self._snapshot["current_situation"] = f"当前正在执行 {stage['phase']}（{specialist}）。"
        self._timeline(f"{specialist}.started", self._snapshot["current_situation"])
        self._write()

    def mark_stage_completed(self, specialist: str, result: dict) -> None:
        stage = self._find_stage(specialist)
        now = utc_now()
        stage["status"] = "done"
        stage["updated_at"] = now
        stage["output_keys"] = sorted(result.keys())
        stage["summary"] = _summarize_stage(specialist, result)
        stage["output"] = _compact_stage_output(specialist, result)
        self._snapshot["updated_at"] = now
        self._snapshot["last_event"] = f"{specialist}.completed"
        self._snapshot["current_phase"] = stage["phase"]
        self._snapshot["current_specialist"] = specialist
        self._snapshot["current_situation"] = f"{stage['phase']}已完成，等待下一阶段。"
        self._snapshot["completion_summary"] = [
            current_stage["summary"]
            for current_stage in self._snapshot["stages"]
            if current_stage["status"] == "done" and current_stage["summary"]
        ]
        self._artifact_store.update(_artifact_entries_from_stage(specialist, result))
        self._snapshot["artifacts"] = _merge_artifacts(self._artifact_store)
        self._snapshot["overall_progress"] = _calculate_progress(self._snapshot["stages"])
        self._timeline(f"{specialist}.completed", stage["summary"] or f"{stage['phase']}已完成。")
        self._write()

    def mark_waiting(self, waiting_state: str, message: str) -> None:
        self._snapshot["status"] = waiting_state
        self._snapshot["updated_at"] = utc_now()
        self._snapshot["last_event"] = waiting_state
        self._snapshot["current_situation"] = message
        self._timeline(waiting_state, message)
        self._write()

    def fail(self, message: str) -> None:
        self._snapshot["status"] = "error"
        self._snapshot["updated_at"] = utc_now()
        self._snapshot["last_event"] = "project.error"
        self._snapshot["current_situation"] = message
        self._timeline("project.error", message)
        self._write()

    def cancel(self, message: str = "任务已取消。") -> None:
        self._snapshot["status"] = "cancelled"
        self._snapshot["updated_at"] = utc_now()
        self._snapshot["last_event"] = "project.cancelled"
        self._snapshot["current_situation"] = message
        self._timeline("project.cancelled", message)
        self._write()

    def finish(self, outputs: dict, result: dict | None = None) -> None:
        self._snapshot["status"] = "done"
        self._snapshot["overall_progress"] = 100
        self._snapshot["current_phase"] = "完成"
        self._snapshot["current_specialist"] = None
        self._snapshot["updated_at"] = utc_now()
        self._snapshot["last_event"] = "project.done"
        self._artifact_store.update(_artifact_entries_from_outputs(outputs))
        self._snapshot["artifacts"] = _merge_artifacts(self._artifact_store)
        self._snapshot["completion_summary"] = self._snapshot["completion_summary"] or _fallback_completion_summary(outputs)
        completed_count = sum(1 for stage in self._snapshot["stages"] if stage["status"] == "done")
        self._snapshot["current_situation"] = (
            f"本次项目已完成，共完成 {completed_count}/{len(self._snapshot['stages'])} 个阶段。"
        )
        self._snapshot["result"] = result or self._snapshot.get("result", {})
        self._timeline("project.done", self._snapshot["current_situation"])
        self._write()

    def snapshot(self) -> dict:
        return deepcopy(self._snapshot)

    def _find_stage(self, specialist: str) -> dict:
        for stage in self._snapshot["stages"]:
            if stage["specialist"] == specialist:
                return stage
        raise KeyError(f"Unknown specialist '{specialist}'")

    def _timeline(self, event: str, summary: str) -> None:
        self._snapshot["timeline"].append({"timestamp": utc_now(), "event": event, "summary": summary})

    def _write(self) -> None:
        run_path = self._board_dir / f"project_board_{self._run_id}.json"
        current_path = self._board_dir / "project_board_current.json"
        index_path = self._board_dir / "project_board_index.json"
        snapshot = deepcopy(self._snapshot)
        run_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        current_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        index = _load_json(index_path, {"project_id": self._project_id, "project_name": self._project_name, "runs": []})
        summary = {
            "run_id": snapshot["run_id"],
            "title": snapshot["title"],
            "mode": snapshot["mode"],
            "status": snapshot["status"],
            "overall_progress": snapshot["overall_progress"],
            "current_phase": snapshot["current_phase"],
            "updated_at": snapshot["updated_at"],
            "started_at": snapshot["started_at"],
            "brief_summary": snapshot["brief_summary"],
            "current_situation": snapshot["current_situation"],
            "completion_summary": snapshot["completion_summary"][:3],
        }
        runs = [item for item in index["runs"] if item["run_id"] != self._run_id]
        runs.append(summary)
        runs.sort(key=lambda item: item["updated_at"], reverse=True)
        index["runs"] = runs
        index["current_run_id"] = snapshot["run_id"]
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


class ProjectBoardRepository:
    def __init__(self, board_dir: Path) -> None:
        self._board_dir = Path(board_dir)

    def list_project_cards(self) -> dict:
        index_path = self._board_dir / "project_board_index.json"
        return _load_json(index_path, {"project_id": PROJECT_ID, "project_name": PROJECT_NAME, "runs": []})

    def get_project_card(self, run_id: str) -> dict:
        path = self._board_dir / f"project_board_{run_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown run '{run_id}'")
        return json.loads(path.read_text(encoding="utf-8"))

    def get_current_project_card(self) -> dict:
        path = self._board_dir / "project_board_current.json"
        if not path.exists():
            raise KeyError("No current board snapshot")
        return json.loads(path.read_text(encoding="utf-8"))


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def _shorten(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _calculate_progress(stages: list[dict]) -> int:
    if not stages:
        return 0
    done = sum(1 for stage in stages if stage["status"] == "done")
    return round(done / len(stages) * 100)


def _empty_artifacts() -> list[dict]:
    return [{"key": key, "label": ARTIFACT_LABELS[key], "ready": False, "summary": ""} for key in ARTIFACT_ORDER]


def _merge_artifacts(current: dict[str, dict]) -> list[dict]:
    return [current.get(key, {"key": key, "label": ARTIFACT_LABELS[key], "ready": False, "summary": ""}) for key in ARTIFACT_ORDER]


def _artifact_entries_from_stage(specialist: str, result: dict) -> dict[str, dict]:
    if specialist == "req_parser":
        return {"structured_brief": _artifact("structured_brief", _summarize_stage(specialist, result))}
    if specialist == "material_style":
        return {"material_style": _artifact("material_style", _summarize_stage(specialist, result))}
    if specialist == "visual_prompt":
        return {"visual_prompt": _artifact("visual_prompt", _summarize_stage(specialist, result))}
    if specialist == "image_gen":
        return {"image_gen": _artifact("image_gen", _summarize_stage(specialist, result))}
    if specialist in {"case_research", "concept", "storyline", "zoning", "video_script", "cost_estimate", "report", "feedback", "progress"}:
        return {specialist: _artifact(specialist, _summarize_stage(specialist, result))}
    return {}


def _artifact_entries_from_outputs(outputs: dict) -> dict[str, dict]:
    artifacts = {}
    if "structured_brief" in outputs:
        artifacts["structured_brief"] = _artifact("structured_brief", _summarize_stage("req_parser", outputs["structured_brief"]))
    if any(key in outputs for key in ("style_key", "palette", "material_spec")):
        artifacts["material_style"] = _artifact(
            "material_style",
            _summarize_stage(
                "material_style",
                {"style_key": outputs.get("style_key"), "palette": outputs.get("palette", []), "material_spec": outputs.get("material_spec", "")},
            ),
        )
    for key in ("case_research", "concept", "storyline", "zoning", "video_script", "cost_estimate", "report", "feedback", "progress"):
        if key in outputs:
            artifacts[key] = _artifact(key, _summarize_stage(key, outputs[key]))
    if "visual_prompt" in outputs:
        artifacts["visual_prompt"] = _artifact("visual_prompt", _summarize_stage("visual_prompt", outputs))
    if "generated_schemes" in outputs or "generated_images" in outputs:
        artifacts["image_gen"] = _artifact("image_gen", _summarize_stage("image_gen", outputs))
    return artifacts


def _artifact(key: str, summary: str) -> dict:
    return {"key": key, "label": ARTIFACT_LABELS[key], "ready": True, "summary": summary}


def _fallback_completion_summary(outputs: dict) -> list[str]:
    summary = []
    if "structured_brief" in outputs:
        summary.append(_summarize_stage("req_parser", outputs["structured_brief"]))
    if any(key in outputs for key in ("style_key", "material_spec")):
        summary.append(
            _summarize_stage(
                "material_style",
                {"style_key": outputs.get("style_key"), "palette": outputs.get("palette", []), "material_spec": outputs.get("material_spec", "")},
            )
        )
    if "visual_prompt" in outputs:
        summary.append(_summarize_stage("visual_prompt", outputs))
    if "generated_schemes" in outputs or "generated_images" in outputs:
        summary.append(_summarize_stage("image_gen", outputs))
    return [item for item in summary if item]


def _summarize_stage(specialist: str, result: dict) -> str:
    if specialist == "req_parser":
        return f"完成需求解析：{result.get('project_type', '项目')}，面积约 {result.get('area_sqm')}㎡。"
    if specialist == "case_research":
        return f"整理了 {len(result.get('case_cards', []))} 个对标案例。"
    if specialist == "concept":
        return f"产出 {len(result.get('concept_options', []))} 个概念方向。"
    if specialist == "storyline":
        return f"形成 {len(result.get('experience_sequence', []))} 段空间叙事。"
    if specialist == "zoning":
        return f"完成 {len(result.get('zones', []))} 个空间分区。"
    if specialist == "material_style":
        return f"确定风格 {result.get('style_key') or '未命名风格'}，输出 {len(result.get('palette', []))} 组主色。"
    if specialist == "visual_prompt":
        prompt = result.get("visual_prompt", "")
        schemes = result.get("schemes", [])
        if schemes:
            return f"生成 {len(schemes)} 套视觉方案提示词。"
        return f"生成视觉提示词，长度约 {len(prompt)} 字符。"
    if specialist == "image_gen":
        if "generated_schemes" in result:
            scheme_count = len(result.get("generated_schemes", []))
            image_count = sum(len(item.get("images", [])) for item in result.get("generated_schemes", []))
            return f"完成 {scheme_count} 套方案、共 {image_count} 张效果图生成。"
        return f"完成 {result.get('scheme_count', 0)} 套方案、共 {result.get('image_count', 0)} 张效果图生成。"
    if specialist == "video_script":
        return f"生成 {len(result.get('scene_sequence', []))} 段视频脚本。"
    if specialist == "cost_estimate":
        total = result.get("total_budget_wan")
        if isinstance(total, list) and len(total) == 2:
            return f"完成预算估算：{total[0]}-{total[1]} 万。"
        return "完成预算估算。"
    if specialist == "report":
        return f"整理 {len(result.get('slide_outline', []))} 页汇报提纲。"
    if specialist == "feedback":
        return f"生成 {len(result.get('patch_actions', []))} 项反馈修订动作。"
    if specialist == "progress":
        return f"排出 {len(result.get('milestones', []))} 个关键里程碑。"
    return "阶段已完成。"


def _compact_stage_output(specialist: str, result: dict) -> dict:
    max_str = 300

    def _clip(value):
        if isinstance(value, str):
            return value[:max_str] + ("…" if len(value) > max_str else "")
        if isinstance(value, list):
            return [_clip(item) for item in value[:6]]
        if isinstance(value, dict):
            return {key: _clip(inner) for key, inner in list(value.items())[:8]}
        return value

    if specialist == "req_parser":
        return {
            "project_type": result.get("project_type"),
            "area_sqm": result.get("area_sqm"),
            "target_audience": result.get("target_audience"),
            "style_preferences": result.get("style_preferences"),
            "special_requirements": _clip(result.get("special_requirements", "")),
        }
    if specialist == "material_style":
        return {
            "style_key": result.get("style_key"),
            "palette": result.get("palette", [])[:6],
            "material_spec": _clip(result.get("material_spec", "")),
            "lighting_concept": _clip(result.get("lighting_concept", "")),
            "style_match": _clip(result.get("style_match", {})),
        }
    if specialist == "visual_prompt":
        prompt_value = result.get("schemes") or result.get("visual_prompts") or result.get("visual_prompt")
        return {
            "visual_prompt": _clip(prompt_value),
            "direction": _clip(result.get("direction", "")),
            "summary": _clip(result.get("summary", "")),
        }
    if specialist == "image_gen":
        return {
            "generated_schemes": _clip(result.get("generated_schemes", [])),
            "image_count": result.get("image_count"),
            "scheme_count": result.get("scheme_count"),
        }
    if specialist == "case_research":
        return {"case_cards": _clip(result.get("case_cards", []))}
    if specialist == "concept":
        return {"concept_options": _clip(result.get("concept_options", []))}
    if specialist == "storyline":
        return {"experience_sequence": _clip(result.get("experience_sequence", []))}
    if specialist == "zoning":
        return {"zones": _clip(result.get("zones", []))}
    if specialist == "video_script":
        return {"scene_sequence": _clip(result.get("scene_sequence", []))}
    if specialist == "cost_estimate":
        return {
            "total_budget_wan": result.get("total_budget_wan"),
            "breakdown": _clip(result.get("breakdown", {})),
        }
    if specialist == "report":
        return {"slide_outline": _clip(result.get("slide_outline", []))}
    if specialist == "feedback":
        return {"patch_actions": _clip(result.get("patch_actions", []))}
    if specialist == "progress":
        return {"milestones": _clip(result.get("milestones", []))}
    return {key: _clip(value) for key, value in result.items()}
