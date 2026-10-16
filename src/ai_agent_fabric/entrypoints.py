from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .harness import flush_guard_traces, resume_snapshot
from .memory import activate_task_lifecycle, archive_completed_lifecycle, archive_preflight, database_path, initialize, prepare_socrates_chat, record, require_current_schema
from .identifiers import require_task_id, slugify
from .task_specs import archive_task as archive_task_package, archived_package_path, create_task, package_path, task_root, workflow_steps


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
    stable_id = require_task_id(task_id) if task_id is not None else slugify(title)
    package = package_path(project_root, stable_id)
    if package.exists():
        raise FileExistsError(f"Task package already exists: {package}")
    return {
        "task_id": stable_id,
        "work_class": work_class,
        "package": str(package),
        "action": "create-project-local-task-package-and-request-separate-socrates-chat",
    }


def start_task(project_root: Path, title: str, work_class: str, task_id: str | None = None) -> dict[str, Any]:
    """Create a task package and wait for a separate Socrates chat to claim it."""
    start_preview(project_root, title, work_class, task_id)
    root = project_root.resolve()
    stable_id = require_task_id(task_id) if task_id is not None else slugify(title)
    _ensure_memory(root)
    package = create_task(root, title, work_class, stable_id)
    try:
        lifecycle = activate_task_lifecycle(
            root, stable_id, title, str(package.relative_to(root)).replace("\\", "/"), workflow_steps(work_class), "start",
            {"task_package": str(package.relative_to(root)).replace("\\", "/")},
        )
        prepare_socrates_chat(root, stable_id)
    except BaseException:
        # Package publication is compensated on lifecycle failure; never strand a new orphan.
        shutil.rmtree(package, ignore_errors=True)
        raise
    flush_guard_traces(root)
    return {"package": str(package), "task_id": stable_id, "socrates_chat_request": _socrates_chat_request(stable_id, title)}


def recover_unicode_package(project_root: Path, source_name: str, task_id: str | None = None, *, apply: bool = False) -> dict[str, str]:
    """Preview or migrate one legacy Unicode active package without direct SQLite edits."""
    root = project_root.resolve()
    source = task_root(root) / "active" / source_name
    if not source.is_dir() or source.name != source_name:
        raise ValueError("recovery source must name one existing active package directory")
    metadata_path = source / "task.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or not isinstance(metadata.get("title"), str) or not isinstance(metadata.get("work_class"), str):
        raise ValueError("legacy package task.json is invalid")
    stable_id = require_task_id(task_id) if task_id is not None else slugify(metadata["title"])
    destination = package_path(root, stable_id)
    if destination.exists() and destination != source:
        raise FileExistsError(f"Task package already exists: {destination}")
    result = {"source": str(source), "task_id": stable_id, "package": str(destination), "action": "rename-package-update-task-json-and-start-socrates"}
    if not apply:
        return result
    if database_path(root).is_file():
        require_current_schema(root)
    else:
        initialize(root)
    metadata["id"] = stable_id
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(metadata_path)
    source.replace(destination)
    try:
        activate_task_lifecycle(root, stable_id, metadata["title"], str(destination.relative_to(root)).replace("\\", "/"), workflow_steps(metadata["work_class"]), "start")
        prepare_socrates_chat(root, stable_id)
        record(root, stable_id, "task-recovered", "orchestrator", "unicode-package-recovered", {"task_package": str(destination.relative_to(root)).replace("\\", "/")})
    except BaseException:
        destination.replace(source)
        raise
    return result


def restore_task(project_root: Path, task_id: str) -> dict[str, Any]:
    """Return task context without letting Root resume or impersonate Socrates."""
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
    snapshot = resume_snapshot(root, metadata["id"])
    snapshot["socrates_chat_request"] = _socrates_chat_request(metadata["id"], metadata["title"])
    return snapshot


def archive_completed_task(project_root: Path, task_id: str, reason: str) -> dict[str, str]:
    """Move a completed package to the recoverable archive and record that transition."""
    root = project_root.resolve()
    archive_preflight(root, task_id)
    active_package = package_path(root, task_id)
    archived_package = archived_package_path(root, task_id)
    if active_package.is_dir():
        destination = archive_task_package(root, task_id, reason)
    elif archived_package.is_dir():
        destination = archived_package
    else:
        raise FileNotFoundError(f"Task package does not exist: {active_package}")
    recorded = archive_completed_lifecycle(root, task_id, reason)
    return {"package": str(destination), **recorded}


def _socrates_chat_request(task_id: str, title: str) -> dict[str, str]:
    """Adapter-facing request to create the task's separate Socrates chat."""
    return {
        "owner": "root",
        "task_id": task_id,
        "title": title,
        "action": "create-separate-socrates-chat",
        "chat_title": f"Socrates — {title}",
        "root_limit": "Root must create or reopen the separate Socrates chat and then must not plan, delegate, implement, or mutate this task.",
        "socrates_activation": f"socrates claim <project-root> --session {task_id} --thread-id <created-chat-thread-id> --json",
    }


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
