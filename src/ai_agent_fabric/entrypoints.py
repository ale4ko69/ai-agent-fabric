from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .harness import resume_snapshot
from .task_specs import create_task, package_path, slugify, task_root


def work_router(project_root: Path, selector: str | None = None) -> dict[str, Any]:
    """Choose one local Fabric path without creating state or executing project commands."""
    root = project_root.resolve()
    tasks = _active_tasks(root)
    if selector:
        selected_id = slugify(selector)
        if any(task["id"] == selected_id for task in tasks):
            return {"route": "restore", "task_id": selected_id, "next_command": "restore"}
        return {"route": "start", "requested_id": selected_id, "next_command": "start"}
    if len(tasks) == 1:
        return {"route": "restore", "task_id": tasks[0]["id"], "next_command": "restore"}
    if not tasks:
        return {"route": "start", "next_command": "start"}
    return {
        "route": "select-task",
        "tasks": tasks,
        "next_command": "restore <task-id>",
    }


def start_preview(project_root: Path, title: str, work_class: str, task_id: str | None = None) -> dict[str, str]:
    """Return the exact package that an explicit start operation would create."""
    stable_id = slugify(task_id or title)
    package = package_path(project_root, stable_id)
    if package.exists():
        raise FileExistsError(f"Task package already exists: {package}")
    return {
        "task_id": stable_id,
        "work_class": work_class,
        "package": str(package),
        "action": "create-project-local-task-package",
    }


def start_task(project_root: Path, title: str, work_class: str, task_id: str | None = None) -> Path:
    """Create exactly one explicitly named task package."""
    start_preview(project_root, title, work_class, task_id)
    return create_task(project_root, title, work_class, task_id)


def restore_task(project_root: Path, task_id: str) -> dict[str, Any]:
    """Return one task's durable context; restoration is strictly read-only."""
    return resume_snapshot(project_root, task_id)


def _active_tasks(project_root: Path) -> list[dict[str, str]]:
    root = task_root(project_root)
    active_root = root / "active"
    if not active_root.is_dir():
        return []
    tasks: list[dict[str, str]] = []
    for metadata_path in sorted(active_root.glob("*/task.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(metadata, dict)
            and metadata.get("status") == "active"
            and isinstance(metadata.get("id"), str)
            and isinstance(metadata.get("title"), str)
            and isinstance(metadata.get("work_class"), str)
        ):
            tasks.append(
                {
                    "id": metadata["id"],
                    "title": metadata["title"],
                    "work_class": metadata["work_class"],
                }
            )
    return tasks
