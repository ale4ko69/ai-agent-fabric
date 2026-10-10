from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .harness import flush_guard_traces, resume_snapshot
from .memory import activate_task_lifecycle, database_path, initialize, record, require_current_schema
from .task_specs import create_task, package_path, slugify, task_root, workflow_steps


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
        "action": "create-project-local-task-package-and-start-socrates",
    }


def start_task(project_root: Path, title: str, work_class: str, task_id: str | None = None) -> dict[str, Any]:
    """Create a task package and activate its project-local Socrates session."""
    start_preview(project_root, title, work_class, task_id)
    root = project_root.resolve()
    stable_id = slugify(task_id or title)
    _ensure_memory(root)
    package = create_task(root, title, work_class, stable_id)
    lifecycle = activate_task_lifecycle(root, stable_id, title, str(package.relative_to(root)).replace("\\", "/"), workflow_steps(work_class), "start")
    record(
        root,
        stable_id,
        "task-started",
        "orchestrator",
        "task-lifecycle-started",
        {"task_package": str(package.relative_to(root)).replace("\\", "/")},
    )
    flush_guard_traces(root)
    return {"package": str(package), "task_id": stable_id, "socrates": {"lifecycle": "started", **lifecycle}}


def restore_task(project_root: Path, task_id: str) -> dict[str, Any]:
    """Resume one task's project-local Socrates session and return its context."""
    root = project_root.resolve()
    package = package_path(root, task_id)
    metadata = json.loads((package / "task.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or not isinstance(metadata.get("id"), str) or not isinstance(metadata.get("title"), str):
        raise ValueError(f"Task metadata is invalid: {package / 'task.json'}")
    # Restore must never manufacture a blank lifecycle for an existing package:
    # absence is a recovery problem, not a new-task signal.
    if not database_path(root).is_file():
        raise FileNotFoundError("Task memory is missing; restore requires the original project-local memory.db")
    require_current_schema(root)
    lifecycle = activate_task_lifecycle(root, metadata["id"], metadata["title"], str(package.relative_to(root)).replace("\\", "/"), workflow_steps(metadata.get("work_class", "")), "restore")
    record(
        root,
        metadata["id"],
        "task-restored",
        "orchestrator",
        "task-lifecycle-restored",
        {"task_package": str(package.relative_to(root)).replace("\\", "/")},
    )
    flush_guard_traces(root)
    snapshot = resume_snapshot(root, metadata["id"])
    snapshot["socrates"] = {"lifecycle": "resumed", **lifecycle}
    return snapshot


def restore_picker(project_root: Path, selection: str | None = None) -> dict[str, Any]:
    """Resolve a human-friendly task selection before any restore mutation occurs."""
    tasks = _active_tasks(project_root.resolve())
    choices = [{"number": index, **task} for index, task in enumerate(tasks, start=1)]
    if selection is None:
        return {
            "route": "select-task" if choices else "start",
            "tasks": choices,
            "selection_help": "Choose a number, exact title, or task id; restore has not run yet.",
        }
    selected = next((task for task in tasks if task["id"] == selection), None)
    if selected is None and selection.isdecimal():
        position = int(selection)
        if 1 <= position <= len(tasks):
            selected = tasks[position - 1]
    if selected is None:
        selected = next((task for task in tasks if task["title"].casefold() == selection.casefold()), None)
    if selected is None:
        raise ValueError("Task selection does not match an active task; run restore without a selection to view the list")
    return {"route": "restore", "task_id": selected["id"], "selected": selected}


def _ensure_memory(project_root: Path) -> None:
    """Initialize only absent task memory; existing schemas require explicit migration."""
    if database_path(project_root).is_file():
        require_current_schema(project_root)
    else:
        initialize(project_root)


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
