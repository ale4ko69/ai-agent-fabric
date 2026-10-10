from __future__ import annotations

import json
import hashlib
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

from .project_state import state_path


WORK_CLASSES = {"small-bug", "planned"}
OUT_OF_SCOPE_DISPOSITIONS = {"none", "backlog", "amendment-request"}
TASK_METADATA_FIELDS = {"schema_version", "id", "title", "work_class", "status", "tracker", "workflow"}


def task_root(project_root: Path) -> Path:
    root = project_root.resolve()
    profile_path = state_path(root, "profile.json")
    relative_root = "docs/specs"
    if profile_path.is_file():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            configured_root = profile.get("task_specs", {}).get("root", relative_root)
        except (json.JSONDecodeError, AttributeError):
            raise ValueError(f"Invalid project profile: {profile_path}") from None
        if not isinstance(configured_root, str) or not configured_root.strip():
            raise ValueError("profile.task_specs.root must be a non-empty relative path")
        relative_root = configured_root
    candidate = Path(relative_root)
    windows_candidate = PureWindowsPath(relative_root)
    if (
        candidate.is_absolute()
        or windows_candidate.is_absolute()
        or bool(windows_candidate.root)
        or ".." in candidate.parts
        or ".." in windows_candidate.parts
    ):
        raise ValueError("profile.task_specs.root must stay within the project root")
    resolved = (root / candidate).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("profile.task_specs.root must stay within the project root")
    return resolved


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).strip().lower()
    slug = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-_")
    if not slug:
        raise ValueError("title must contain letters or numbers")
    return slug


def package_path(project_root: Path, task_id: str) -> Path:
    safe_id = slugify(task_id)
    return _contained_package_path(task_root(project_root), "active", safe_id)


def archived_package_path(project_root: Path, task_id: str) -> Path:
    return _contained_package_path(task_root(project_root), "archived", slugify(task_id))


def _contained_package_path(root: Path, state: str, task_id: str) -> Path:
    candidate = root / state / task_id
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Task package path escapes the configured task root: {state}/{task_id}")
    return resolved


def _package_file(package: Path, relative: str) -> Path:
    candidate = package / relative
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"Task artifact is missing or cannot be resolved: {relative}") from error
    if not resolved.is_relative_to(package) or not resolved.is_file():
        raise ValueError(f"Task artifact escapes its package or is not a file: {relative}")
    return resolved


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json_atomic(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _artifact_digests(package: Path) -> dict[str, str]:
    return {
        artifact: hashlib.sha256(_package_file(package, artifact).read_bytes()).hexdigest()
        for artifact in ("spec.md", "research.md", "plan.md")
    }


def _task_metadata(task_id: str, title: str, work_class: str) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "id": task_id,
            "title": title,
            "work_class": work_class,
            "status": "active",
            "tracker": {"provider": "none", "reference": None, "url": None},
            "workflow": {"schema_version": 1, "spec_revision": 1, "plan_revision": 1},
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def create_task(project_root: Path, title: str, work_class: str, task_id: str | None = None) -> Path:
    root = project_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Target repository does not exist: {root}")
    if work_class not in WORK_CLASSES:
        raise ValueError(f"Unsupported work class: {work_class}")
    stable_id = slugify(task_id or title)
    package = package_path(root, stable_id)
    if package.exists():
        raise FileExistsError(f"Task package already exists: {package}")
    evidence = package / "evidence"
    evidence.mkdir(parents=True)
    _write(package / "task.json", _task_metadata(stable_id, title, work_class))
    _write(package / "tasks.md", f"# Tasks — {title}\n\n- [ ] Define the next verified action.\n")
    _write(evidence / "README.md", "# Evidence\n\nStore durable verification evidence here.\n")
    if work_class == "planned":
        _write(package / "spec.md", f"# {title}\n\n## User Value\n\n## Scope\n\n## Non-Goals\n\n## Acceptance Criteria\n\n## Constraints\n\n## Open Questions\n")
        _write(package / "research.md", f"# Research — {title}\n\n## Evidence\n\n## Options\n\n## Rejected approaches\n")
        _write(package / "plan.md", f"# Plan — {title}\n\n## Analysis\n\n## Architecture\n\n## Implementation\n\n## Validation\n")
        artifact_digests = _artifact_digests(package)
        _write(package / "kepler.md", "# KEPLER verdict\n\nStatus: pending\n\n## Evidence reviewed\n\n## Scope boundary\n\n## Verdict\n")
        _write(
            package / "kepler.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "spec_revision": 1,
                    "plan_revision": 1,
                    "verdict": "pending",
                    "reviewed_artifacts": ["spec.md", "research.md", "plan.md"],
                    "artifact_digests": artifact_digests,
                    "out_of_scope_disposition": "none",
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
        )
        _write(
            package / "approval.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "spec_revision": 1,
                    "plan_revision": 1,
                    "artifact_digests": artifact_digests,
                    "kepler_verdict_sha256": None,
                    "approved": False,
                    "approved_by": None,
                    "approval_method": None,
                    "approved_at": None,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
        )
        _write(package / "session-state.md", "# Session state\n\nStatus: PENDING\n\n## Progress\n\n- [ ] Task not started\n")
    return package


def archive_task(project_root: Path, task_id: str, reason: str) -> Path:
    """Move a validated task package to a recoverable archive without deletion."""
    package = package_path(project_root, task_id)
    errors = validate_task(project_root, task_id)
    if errors:
        raise ValueError("Cannot archive invalid task package: " + "; ".join(errors))
    if not reason.strip():
        raise ValueError("An archive reason is required")
    destination = archived_package_path(project_root, task_id)
    if destination.exists():
        raise FileExistsError(f"Archived task already exists: {destination}")
    metadata_path = _package_file(package, "task.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["status"] = "archived"
    _write(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    _write(package / "archive.json", json.dumps({"schema_version": 1, "reason": reason.strip()}, ensure_ascii=False, indent=2) + "\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(package), str(destination))
    return destination


def validate_task(project_root: Path, task_id: str) -> list[str]:
    try:
        package = package_path(project_root, task_id)
    except ValueError as error:
        return [str(error)]
    if not package.is_dir():
        return [f"Task package does not exist: {package}"]
    errors: list[str] = []
    try:
        metadata_path = _package_file(package, "task.json")
    except ValueError:
        return ["Missing task.json"]
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["task.json is not valid JSON"]
    if not isinstance(metadata, dict):
        return ["task.json must be a JSON object"]
    if set(metadata) != TASK_METADATA_FIELDS:
        return ["task.json must use the declared metadata shape"]
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1 or not isinstance(metadata.get("id"), str) or not metadata["id"].strip() or not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
        return ["task.json must declare schema_version 1 plus non-empty id and title"]
    if metadata.get("status") not in {"active", "archived"}:
        return ["task.json has an unsupported status"]
    tracker = metadata.get("tracker")
    if (
        not isinstance(tracker, dict)
        or set(tracker) != {"provider", "reference", "url"}
        or not isinstance(tracker.get("provider"), str)
        or not tracker["provider"].strip()
        or any(tracker.get(field) is not None and not isinstance(tracker[field], str) for field in ("reference", "url"))
    ):
        return ["task.json must declare a valid tracker reference"]
    workflow = metadata.get("workflow")
    if (
        not isinstance(workflow, dict)
        or set(workflow) != {"schema_version", "spec_revision", "plan_revision"}
        or type(workflow.get("schema_version")) is not int
        or workflow["schema_version"] != 1
        or not all(type(workflow.get(field)) is int and workflow[field] >= 1 for field in ("spec_revision", "plan_revision"))
    ):
        return ["task.json must declare valid workflow revisions"]
    work_class = metadata.get("work_class")
    if work_class not in WORK_CLASSES:
        errors.append("task.json has an unsupported work_class")
    required = ["tasks.md", "evidence/README.md"]
    if work_class == "planned":
        required.extend(["spec.md", "research.md", "plan.md", "kepler.md", "kepler.json", "approval.json", "session-state.md"])
    for relative in required:
        try:
            _package_file(package, relative)
        except ValueError:
            errors.append(f"Missing required artifact: {relative}")
    return errors


def implementation_readiness(project_root: Path, task_id: str) -> dict[str, object]:
    """Read whether the local package may enter implementation; never mutate it."""
    package = package_path(project_root, task_id)
    errors = validate_task(project_root, task_id)
    if errors:
        return {"task_id": slugify(task_id), "ready": False, "reasons": errors}
    metadata = _load_json_object(_package_file(package, "task.json"), "task metadata")
    work_class = metadata["work_class"]
    if work_class == "small-bug":
        return {
            "task_id": metadata["id"],
            "work_class": work_class,
            "ready": True,
            "reasons": [],
            "rule": "small-bug uses tasks and evidence without spec or plan",
        }
    reasons: list[str] = []
    workflow = metadata.get("workflow")
    if not isinstance(workflow, dict) or set(workflow) != {"schema_version", "spec_revision", "plan_revision"}:
        reasons.append("task.json must declare workflow revisions")
        workflow = {}
    plan_revision = workflow.get("plan_revision")
    spec_revision = workflow.get("spec_revision")
    if type(spec_revision) is not int or spec_revision < 1:
        reasons.append("task.json workflow.spec_revision must be a positive integer")
    if type(plan_revision) is not int or plan_revision < 1:
        reasons.append("task.json workflow.plan_revision must be a positive integer")
    current_digests = _artifact_digests(package)
    kepler_path = _package_file(package, "kepler.json")
    kepler = _load_json_object(kepler_path, "Kepler verdict", reasons)
    approval = _load_json_object(_package_file(package, "approval.json"), "approval", reasons)
    if kepler:
        _validate_kepler_verdict(kepler, spec_revision, plan_revision, current_digests, reasons)
    if approval:
        _validate_approval(approval, spec_revision, plan_revision, current_digests, _sha256_file(kepler_path), reasons)
    return {
        "task_id": metadata["id"],
        "work_class": work_class,
        "ready": not reasons,
        "reasons": reasons,
        "rule": "planned work requires a current Kepler advice verdict and explicit human approval",
    }


def _load_json_object(path: Path, label: str, errors: list[str] | None = None) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        if errors is not None:
            errors.append(f"{label} must be valid JSON")
            return {}
        raise ValueError(f"{label} must be valid JSON: {path}") from None
    if not isinstance(value, dict):
        if errors is not None:
            errors.append(f"{label} must be a JSON object")
            return {}
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _validate_kepler_verdict(verdict: dict[str, object], spec_revision: object, plan_revision: object, artifact_digests: dict[str, str], reasons: list[str]) -> None:
    required = {"schema_version", "spec_revision", "plan_revision", "verdict", "reviewed_artifacts", "artifact_digests", "out_of_scope_disposition"}
    if set(verdict) != required or type(verdict.get("schema_version")) is not int or verdict["schema_version"] != 1:
        reasons.append("kepler.json must use the declared Kepler verdict shape")
        return
    if type(verdict.get("spec_revision")) is not int or type(verdict.get("plan_revision")) is not int:
        reasons.append("Kepler verdict revisions must be integers")
        return
    if verdict.get("plan_revision") != plan_revision:
        reasons.append("Kepler verdict must review the current plan revision")
    if verdict.get("spec_revision") != spec_revision:
        reasons.append("Kepler verdict must review the current spec revision")
    if verdict.get("verdict") != "advice":
        reasons.append("Kepler must return advice before implementation")
    reviewed = verdict.get("reviewed_artifacts")
    if not isinstance(reviewed, list) or set(reviewed) != {"spec.md", "research.md", "plan.md"}:
        reasons.append("Kepler must review spec.md, research.md, and plan.md")
    if verdict.get("artifact_digests") != artifact_digests:
        reasons.append("Kepler verdict does not match the current spec, research, and plan content")
    disposition = verdict.get("out_of_scope_disposition")
    if disposition not in OUT_OF_SCOPE_DISPOSITIONS:
        reasons.append("Kepler out-of-scope disposition is invalid")
    elif disposition == "amendment-request":
        reasons.append("A requested spec amendment requires a revised plan and fresh Kepler verdict")


def _validate_approval(approval: dict[str, object], spec_revision: object, plan_revision: object, artifact_digests: dict[str, str], kepler_sha256: str, reasons: list[str]) -> None:
    required = {"schema_version", "spec_revision", "plan_revision", "artifact_digests", "kepler_verdict_sha256", "approved", "approved_by", "approval_method", "approved_at"}
    if set(approval) != required or type(approval.get("schema_version")) is not int or approval["schema_version"] != 1:
        reasons.append("approval.json must use the declared approval shape")
        return
    if type(approval.get("spec_revision")) is not int or type(approval.get("plan_revision")) is not int:
        reasons.append("Approval revisions must be integers")
        return
    if approval.get("plan_revision") != plan_revision:
        reasons.append("Approval must apply to the current plan revision")
    if approval.get("spec_revision") != spec_revision:
        reasons.append("Approval must apply to the current spec revision")
    if approval.get("artifact_digests") != artifact_digests or approval.get("kepler_verdict_sha256") != kepler_sha256:
        reasons.append("Approval does not match the current task artifacts and Kepler verdict")
    if (
        approval.get("approved") is not True
        or approval.get("approved_by") != "human"
        or approval.get("approval_method") != "interactive-terminal"
        or not isinstance(approval.get("approved_at"), str)
    ):
        reasons.append("Planned work requires explicit human approval")


def approval_preview(project_root: Path, task_id: str) -> dict[str, object]:
    """Show exactly what a human terminal approval would bind, without writing."""
    package = package_path(project_root, task_id)
    errors = validate_task(project_root, task_id)
    if errors:
        raise ValueError("Cannot approve invalid task package: " + "; ".join(errors))
    metadata = _load_json_object(_package_file(package, "task.json"), "task metadata")
    if metadata.get("work_class") != "planned":
        raise ValueError("Only planned work uses the Kepler and human approval gate")
    workflow = metadata.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("task.json must declare workflow revisions")
    spec_revision = workflow.get("spec_revision")
    plan_revision = workflow.get("plan_revision")
    digests = _artifact_digests(package)
    kepler_path = _package_file(package, "kepler.json")
    reasons: list[str] = []
    _validate_kepler_verdict(
        _load_json_object(kepler_path, "Kepler verdict"), spec_revision, plan_revision, digests, reasons
    )
    if reasons:
        raise ValueError("Cannot approve planned work: " + "; ".join(reasons))
    return {
        "task_id": metadata.get("id"),
        "spec_revision": spec_revision,
        "plan_revision": plan_revision,
        "artifact_digests": digests,
        "kepler_verdict_sha256": _sha256_file(kepler_path),
        "approval_path": str(_package_file(package, "approval.json")),
        "prompt": "A human must confirm this exact reviewed package in the terminal; no automated approval flag exists.",
    }


def approve_planned_task(project_root: Path, task_id: str, confirmation: str, reviewed_kepler_sha256: str) -> Path:
    """Persist one human terminal confirmation for the exact Kepler-reviewed package."""
    preview = approval_preview(project_root, task_id)
    current_sha256 = preview["kepler_verdict_sha256"]
    if reviewed_kepler_sha256 != current_sha256:
        raise ValueError("The reviewed package changed after preview; inspect the new preview and confirm it again")
    expected = f"approve {preview['task_id']} {current_sha256}"
    if confirmation.strip() != expected:
        raise ValueError(f"Approval was not confirmed. Type exactly: {expected}")
    approval: dict[str, object] = {
        "schema_version": 1,
        "spec_revision": preview["spec_revision"],
        "plan_revision": preview["plan_revision"],
        "artifact_digests": preview["artifact_digests"],
        "kepler_verdict_sha256": preview["kepler_verdict_sha256"],
        "approved": True,
        "approved_by": "human",
        "approval_method": "interactive-terminal",
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    path = Path(str(preview["approval_path"]))
    _write_json_atomic(path, approval)
    return path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
