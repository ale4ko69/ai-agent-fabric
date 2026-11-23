from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from .clients import detect_client
from .codex_project import PENDING, RECEIPT, adapter_git_paths, codex_project_status
from .environment import detect_environment
from .project_git import apply_project_git_plan, project_git_plan
from .project_install import (
    DIGEST_PATTERN, RUNTIME_DIRECTORY, _check_case_alias, _digest, checked_directory,
    load_project_installation, observe_runtime_git_ownership,
)


def _observe_installation(project: Path, version: str) -> tuple[list[str], dict[str, str]]:
    paths, ownership = observe_runtime_git_ownership(project)
    adapter = codex_project_status(project)
    adapter_paths = adapter_git_paths(version)
    if adapter["file_installation"] == "installed":
        for relative in adapter_paths:
            _check_case_alias(project / relative)
        paths.extend(adapter_paths)
        ownership[RECEIPT] = hashlib.sha256((project / RECEIPT).read_bytes()).hexdigest()
    elif any(os.path.lexists(project / path) for path in adapter_paths) or adapter["file_installation"] not in {"absent", "unmanaged"}:
        raise ValueError(f"Unverified Codex adapter state requires owner review: {adapter.get('error', PENDING)}")
    return paths, ownership


def project_git_cleanup_preview(target: str | Path) -> dict[str, Any]:
    """Inspect complete legacy ownership before proposing any Git exclusion."""
    project = checked_directory(target, owned=True)
    environment = detect_environment()
    detected = detect_client(project)
    runtime = load_project_installation(project)
    version = runtime["fabric_release"]
    paths, ownership = _observe_installation(project, version)
    git = project_git_plan(project, environment, paths, reserved=(RUNTIME_DIRECTORY,))
    plan = {
        "schema_version": 1,
        "mode": "project-git-cleanup",
        "project_root": str(project),
        "fabric_release": version,
        "client": runtime["client"],
        "environment": environment.kind,
        "detected_clients": list(detected.candidates),
        "ownership_sha256": ownership,
        "git": git,
    }
    plan["preview_sha256"] = _digest(plan)
    return plan


def apply_project_git_cleanup(target: str | Path, *, expected_preview_sha256: str) -> dict[str, Any]:
    plan = project_git_cleanup_preview(target)
    if (
        not isinstance(expected_preview_sha256, str)
        or not DIGEST_PATTERN.fullmatch(expected_preview_sha256)
        or expected_preview_sha256 != plan["preview_sha256"]
    ):
        raise ValueError("Git cleanup preview digest is stale or invalid; review a fresh preview")
    project = Path(plan["project_root"])

    def verify_ownership() -> None:
        if _observe_installation(project, plan["fabric_release"]) != (plan["git"]["paths"], plan["ownership_sha256"]):
            raise ValueError("Project installation ownership changed during Git publication")

    unchanged = plan["git"]["status"] != "append"
    apply_project_git_plan(project, detect_environment(), plan["git"], verify_ownership=verify_ownership)
    return {**plan, "status": "unchanged" if unchanged else "updated"}
