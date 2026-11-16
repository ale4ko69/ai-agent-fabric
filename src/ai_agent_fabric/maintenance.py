"""Fail-closed maintenance inspection and one narrowly scoped configuration edit.

This module executes no external commands. A policy is authorization data, not a
process sandbox or proof that a change is safe.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .project_state import state_path
from .task_specs import implementation_readiness, package_path
from .capabilities import load_capabilities
from .memory import restore
from .identifiers import require_task_id


POLICY = "config/maintenance-policy.json"
SUPPORTED_TARGET = ".agent-fabric/config/harness/retrospective.json"
FORBIDDEN_COMPONENTS = {".git", ".codex", ".agents", ".aws", "secrets"}
FORBIDDEN_PREFIXES = (
    ".agent-fabric/fabric-binding.json", ".agent-fabric/memory.db",
    ".agent-fabric/config/maintenance-policy.json", ".agent-fabric/config/capabilities.json",
    ".agent-fabric/config/model-routing.json", ".agent-fabric/updates/",
)


def default_policy() -> dict[str, Any]:
    return {"schema_version": 1, "enabled": False, "paths": [], "commands": [], "delivery": []}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate maintenance JSON key")
        value[key] = item
    return value


def parse_candidate(content: str) -> dict[str, Any]:
    value = json.loads(content, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError("Candidate must be a JSON object")
    return value


def load_maintenance_policy(project: Path) -> dict[str, Any]:
    """Read a strictly shaped local policy; a missing policy denies everything."""
    _safe_path(project, ".agent-fabric/" + POLICY, allow_policy=True)
    path = state_path(project, POLICY)
    if not path.exists():
        return default_policy()
    try:
        policy = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Invalid maintenance policy") from error
    if not isinstance(policy, dict) or set(policy) != {"schema_version", "enabled", "paths", "commands", "delivery"}:
        raise ValueError("Maintenance policy must use the declared shape")
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1 or type(policy["enabled"]) is not bool:
        raise ValueError("Invalid maintenance policy version or enabled flag")
    if not isinstance(policy["paths"], list) or any(not isinstance(p, str) for p in policy["paths"]) or len(set(policy["paths"])) != len(policy["paths"]):
        raise ValueError("Maintenance paths must be a unique list")
    for target in policy["paths"]:
        _safe_path(project, target)
    commands = policy["commands"]
    if not isinstance(commands, list) or any(not isinstance(argv, list) or not argv or any(not isinstance(part, str) or not part or "\x00" in part for part in argv) for argv in commands):
        raise ValueError("Maintenance commands must be nonempty argument arrays")
    if not isinstance(policy["delivery"], list) or any(not isinstance(item, str) or item not in {"commit", "push", "release"} for item in policy["delivery"]) or len(set(policy["delivery"])) != len(policy["delivery"]):
        raise ValueError("Invalid maintenance delivery policy")
    return policy


def _safe_path(project: Path, target: object, *, allow_policy: bool = False) -> Path:
    if not isinstance(target, str) or not target or "\\" in target or ":" in target or "\x00" in target:
        raise ValueError("Maintenance target must be a normalized relative path")
    posix, windows = PurePosixPath(target), PureWindowsPath(target)
    if not posix.parts or posix.is_absolute() or windows.is_absolute() or windows.root or windows.drive or any(part in {".", ".."} for part in posix.parts) or str(posix) != target:
        raise ValueError("Maintenance target must stay within the project")
    protected = any(target.lower() == p or target.lower().startswith(p if p.endswith("/") else p + "/") for p in FORBIDDEN_PREFIXES)
    if any(part.lower() in FORBIDDEN_COMPONENTS for part in posix.parts) or (protected and not (allow_policy and target == ".agent-fabric/" + POLICY)):
        raise ValueError("Maintenance target is forbidden")
    root = project.resolve()
    current = root
    for part in posix.parts:
        current = current / part
        if current.is_symlink() or getattr(current, "is_junction", lambda: False)():
            raise ValueError("Maintenance target contains a link or junction")
        if current.exists() and getattr(current.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Maintenance target contains a reparse point")
    if not current.resolve().is_relative_to(root):
        raise ValueError("Maintenance target escapes the project")
    return current


def _retrospective_config(content: str) -> dict[str, Any]:
    """Permit only non-authority presentation and signal-threshold settings."""
    value = json.loads(content, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or set(value) != {"schema_version", "minimum_signal_count", "summary_style"}:
        raise ValueError("Harness retrospective config must use the declared shape")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("Unsupported Harness retrospective config version")
    if type(value["minimum_signal_count"]) is not int or not 1 <= value["minimum_signal_count"] <= 100:
        raise ValueError("Invalid Harness signal threshold")
    if not isinstance(value["summary_style"], str) or value["summary_style"] not in {"brief", "detailed"}:
        raise ValueError("Invalid Harness summary style")
    return value


def retrospective_config(project: Path) -> dict[str, Any]:
    _safe_path(project, ".agent-fabric/config/harness/retrospective.json")
    path = state_path(project, "config/harness/retrospective.json")
    if not path.exists():
        return {"schema_version": 1, "minimum_signal_count": 1, "summary_style": "brief"}
    return _retrospective_config(path.read_text(encoding="utf-8"))


def candidate_digest(candidate: dict[str, Any]) -> dict[str, str]:
    """Identify candidate bytes canonically without asserting approval or authority."""
    required = {"task_id", "paths", "commands", "delivery", "evidence"}
    if not isinstance(candidate, dict) or not required.issubset(candidate) or set(candidate) - required - {"edit", "evaluations"}:
        raise ValueError("Invalid maintenance candidate")
    task_id = require_task_id(candidate["task_id"])
    digest = hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return {"task_id": task_id, "candidate_sha256": digest, "status": "digest-only-not-authorized"}


def preview_candidate(project: Path, task_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate explicit targets against policy and the current task approval.

    This is a diagnostic only. Approval of the task and allowed paths are necessary,
    but do not prove that the candidate or a command is safe to execute.
    """
    identity = candidate_digest(candidate)
    if identity["task_id"] != task_id:
        raise ValueError("Invalid maintenance candidate")
    policy = load_maintenance_policy(project)
    if not policy["enabled"]:
        raise PermissionError("Maintenance policy is disabled or missing")
    if "maintenance" not in load_capabilities(project)["enabled_packs"]:
        raise PermissionError("Maintenance capability is not enabled for this project")
    if not implementation_readiness(project, task_id)["ready"]:
        raise PermissionError("Maintenance requires a current approved task")
    if not isinstance(candidate["paths"], list) or not candidate["paths"] or any(not isinstance(x, str) for x in candidate["paths"]) or len(set(candidate["paths"])) != len(candidate["paths"]):
        raise ValueError("Candidate must identify paths")
    for target in candidate["paths"]:
        _safe_path(project, target)
        if target not in policy["paths"]:
            raise PermissionError("Candidate path is not allowed")
    if not isinstance(candidate["commands"], list) or any(argv not in policy["commands"] for argv in candidate["commands"]):
        raise PermissionError("Candidate command is not allowed")
    if not isinstance(candidate["delivery"], list) or any(action not in policy["delivery"] for action in candidate["delivery"]):
        raise PermissionError("Candidate delivery is not allowed")
    if not isinstance(candidate["evidence"], list) or not candidate["evidence"] or any(not isinstance(x, str) for x in candidate["evidence"]) or len(set(candidate["evidence"])) != len(candidate["evidence"]):
        raise ValueError("Candidate requires evidence references")
    for artifact in candidate["evidence"]:
        if not _safe_path(project, artifact).is_file():
            raise ValueError("Candidate evidence must be an existing local file")
    return {"task_id": task_id, "candidate_sha256": identity["candidate_sha256"], "status": "preview-only", "paths": candidate["paths"], "commands": candidate["commands"], "delivery": candidate["delivery"]}


def apply_candidate(project: Path, task_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    """Apply one reviewed text edit with practical conflict detection.

    This does not isolate other processes or provide an atomic compare-and-swap.
    External commands and automatic delivery are not performed here.
    """
    root = project.resolve()
    preview = preview_candidate(root, task_id, candidate)
    task = restore(root, task_id)
    lifecycle = task.get("lifecycle") or {}
    chat = task.get("socrates_chat") or {}
    if lifecycle.get("status") != "active" or lifecycle.get("next_action") != "implementation" or chat.get("status") != "claimed":
        raise PermissionError("Maintenance requires the claimed active implementation step")
    marker = "maintenance-candidate-sha256: " + preview["candidate_sha256"]
    spec = (package_path(root, task_id) / "spec.md").read_text(encoding="utf-8")
    if marker not in spec.splitlines():
        raise PermissionError("Candidate digest is not bound to the approved task specification")
    if candidate["commands"] or candidate["delivery"]:
        raise PermissionError("Command execution and delivery are not supported by this apply action")
    edit = candidate.get("edit")
    if not isinstance(edit, dict) or set(edit) != {"path", "before_sha256", "content"}:
        raise ValueError("Candidate requires exactly one text edit with a preimage hash")
    path, before, content = edit["path"], edit["before_sha256"], edit["content"]
    if candidate["paths"] != [path] or not isinstance(path, str):
        raise ValueError("Edit must match the single allowed candidate path")
    if path != SUPPORTED_TARGET:
        raise PermissionError("Target is outside the supported maintenance surfaces")
    if not isinstance(before, str) or len(before) != 64 or any(c not in "0123456789abcdef" for c in before):
        raise ValueError("Edit preimage must be a lowercase SHA-256")
    if not isinstance(content, str) or "\x00" in content:
        raise ValueError("Edit content must be non-NUL text")
    _retrospective_config(content)
    payload = content.encode("utf-8")
    if hashlib.sha256(payload).hexdigest() == before:
        raise ValueError("Maintenance edit must change the target content")
    evals = candidate.get("evaluations")
    available = {"nonempty-utf8", "no-conflict-markers", "json-object"}
    if not isinstance(evals, list) or "json-object" not in evals or any(not isinstance(item, str) or item not in available for item in evals) or len(set(evals)) != len(evals) or len(payload) > 1024 * 1024:
        raise ValueError("Candidate requires valid built-in evaluations")
    if "nonempty-utf8" in evals and not payload:
        raise ValueError("nonempty-utf8 evaluation failed")
    if "no-conflict-markers" in evals and any(line.startswith(("<<<<<<< ", "=======", ">>>>>>> ")) for line in content.splitlines()):
        raise ValueError("no-conflict-markers evaluation failed")
    if "json-object" in evals:
        try:
            parsed = json.loads(content, object_pairs_hook=_unique_object)
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError("json-object evaluation failed") from error
        if not isinstance(parsed, dict):
            raise ValueError("json-object evaluation requires an object")
    target = _safe_path(root, path)
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise PermissionError("Maintenance only edits existing regular files without hard links")
    original = target.read_bytes()
    if hashlib.sha256(original).hexdigest() != before:
        raise FileExistsError("Maintenance conflict: target changed since review; preserve it and resolve the conflict")
    _retrospective_config(original.decode("utf-8"))
    policy_file = state_path(root, POLICY)
    policy_digest = hashlib.sha256(policy_file.read_bytes()).hexdigest()
    _safe_path(root, ".agent-fabric/backups/maintenance/preimages")
    backup_dir = state_path(root, "backups/maintenance/preimages", create_parents=True)
    backup_dir.mkdir(exist_ok=True)
    backup = _safe_path(root, ".agent-fabric/backups/maintenance/preimages/" + before + ".json")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(backup, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if backup.is_symlink() or backup.read_bytes() != original:
            raise FileExistsError("Maintenance backup conflict; preserve existing backup and resolve it")
    journal_relative = ".agent-fabric/backups/maintenance/operations/" + preview["candidate_sha256"] + ".json"
    _safe_path(root, journal_relative)
    journal_dir = state_path(root, "backups/maintenance/operations", create_parents=True)
    _safe_path(root, ".agent-fabric/backups/maintenance/operations")
    journal_dir.mkdir(exist_ok=True)
    journal = _safe_path(root, journal_relative)
    operation = {
        "schema_version": 1, "task_id": task_id, "candidate_sha256": preview["candidate_sha256"],
        "path": path, "before_sha256": before, "after_sha256": hashlib.sha256(payload).hexdigest(),
        "backup": str(backup.relative_to(root)).replace("\\", "/"), "status": "prepared",
    }
    try:
        descriptor = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError as error:
        raise FileExistsError("Maintenance journal already exists; inspect and agree on a resolution before any new candidate") from error
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(operation, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".fabric-maintenance-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        checked = _safe_path(root, path)
        current = checked.stat()
        if (current.st_dev, current.st_ino, current.st_nlink) != (info.st_dev, info.st_ino, info.st_nlink) or hashlib.sha256(checked.read_bytes()).hexdigest() != before:
            raise FileExistsError("Maintenance conflict: target changed during preparation; preserve it and resolve the conflict")
        latest = preview_candidate(root, task_id, candidate)
        latest_task = restore(root, task_id)
        latest_lifecycle = latest_task.get("lifecycle") or {}
        if latest["candidate_sha256"] != preview["candidate_sha256"] or hashlib.sha256(policy_file.read_bytes()).hexdigest() != policy_digest or latest_lifecycle.get("status") != "active" or latest_lifecycle.get("next_action") != "implementation" or (latest_task.get("socrates_chat") or {}).get("status") != "claimed" or marker not in (package_path(root, task_id) / "spec.md").read_text(encoding="utf-8").splitlines():
            raise PermissionError("Task or policy changed during preparation; inspect current state")
        checked = _safe_path(root, path)
        final_info = checked.stat()
        if (final_info.st_dev, final_info.st_ino, final_info.st_nlink) != (info.st_dev, info.st_ino, info.st_nlink) or hashlib.sha256(checked.read_bytes()).hexdigest() != before:
            raise FileExistsError("Maintenance conflict: target changed before replacement; preserve it and resolve the conflict")
        os.replace(temporary, checked)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"status": "applied", "path": path, "backup": str(backup.relative_to(root)), "journal": journal_relative, "candidate_sha256": preview["candidate_sha256"], "after_sha256": hashlib.sha256(payload).hexdigest(), "limitations": "Journal remains prepared for read-only recovery inspection. Practical conflict checks are not atomic compare-and-swap; file metadata may change; no command or delivery was executed."}


def inspect_operation(project: Path, candidate_sha256: str) -> dict[str, str]:
    """Inspect a one-file operation journal without mutating or restoring any file."""
    if not isinstance(candidate_sha256, str) or len(candidate_sha256) != 64 or any(c not in "0123456789abcdef" for c in candidate_sha256):
        raise ValueError("Candidate digest must be a lowercase SHA-256")
    root = project.resolve()
    journal = _safe_path(root, ".agent-fabric/backups/maintenance/operations/" + candidate_sha256 + ".json")
    record = parse_candidate(journal.read_text(encoding="utf-8"))
    expected = {"schema_version", "task_id", "candidate_sha256", "path", "before_sha256", "after_sha256", "backup", "status"}
    if set(record) != expected or type(record.get("schema_version")) is not int or record["schema_version"] != 1 or record["candidate_sha256"] != candidate_sha256 or record["status"] != "prepared" or record["path"] != SUPPORTED_TARGET:
        raise ValueError("Invalid maintenance journal")
    if any(not isinstance(record.get(key), str) or len(record[key]) != 64 or any(c not in "0123456789abcdef" for c in record[key]) for key in ("before_sha256", "after_sha256")):
        raise ValueError("Invalid maintenance journal digest")
    if record["backup"] != ".agent-fabric/backups/maintenance/preimages/" + record["before_sha256"] + ".json":
        raise ValueError("Invalid maintenance journal backup")
    target = _safe_path(root, record["path"])
    backup = _safe_path(root, record["backup"])
    if not backup.is_file() or hashlib.sha256(backup.read_bytes()).hexdigest() != record["before_sha256"]:
        raise ValueError("Maintenance preimage backup is missing or changed")
    current = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    state = "unchanged" if current == record["before_sha256"] else "candidate-present" if current == record["after_sha256"] else "conflict"
    return {"status": state, "path": record["path"], "backup": record["backup"], "recommended_action": "review-operation-evidence" if state != "conflict" else "preserve-file-and-resolve-conflict"}
