from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath

from .project_state import state_path
from .identifiers import require_task_id, slugify


WORK_CLASSES = {"small-bug", "planned"}
WORKFLOW_STEPS = {
    "small-bug": ("intake", "evidence", "implementation", "review", "validation", "close-out", "rollout"),
    "planned": ("intake", "discovery", "plan", "kepler", "human-approval", "implementation", "review", "validation", "close-out", "rollout"),
}
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


def package_path(project_root: Path, task_id: str) -> Path:
    safe_id = require_task_id(task_id)
    return _contained_package_path(task_root(project_root), "active", safe_id)


def archived_package_path(project_root: Path, task_id: str) -> Path:
    return _contained_package_path(task_root(project_root), "archived", require_task_id(task_id))


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


def _artifact_digests(package: Path, research_baseline_sha256: str | None = None) -> dict[str, str]:
    """Hash immutable planning inputs, accepting only line-appended runtime research.

    A reviewed `research.md` remains part of the approval boundary.  Once it has
    been reviewed, later execution observations may be appended on complete-line
    boundaries, but cannot alter the reviewed prefix.
    """
    digests = {
        artifact: hashlib.sha256(_package_file(package, artifact).read_bytes()).hexdigest()
        for artifact in ("spec.md", "plan.md")
    }
    research_bytes = _package_file(package, "research.md").read_bytes()
    full_digest = hashlib.sha256(research_bytes).hexdigest()
    if research_baseline_sha256 is not None and full_digest != research_baseline_sha256:
        for boundary in _line_boundaries(research_bytes):
            if hashlib.sha256(research_bytes[:boundary]).hexdigest() == research_baseline_sha256:
                full_digest = research_baseline_sha256
                break
    return {"spec.md": digests["spec.md"], "research.md": full_digest, "plan.md": digests["plan.md"]}


def _line_boundaries(content: bytes) -> list[int]:
    """Return every safe append boundary, including the unchanged full artifact."""
    boundaries = [index + 1 for index, byte in enumerate(content) if byte == ord("\n")]
    if len(content) not in boundaries:
        boundaries.append(len(content))
    return boundaries


def _research_baseline_sha256(verdict: dict[str, object]) -> str | None:
    digests = verdict.get("artifact_digests")
    value = digests.get("research.md") if isinstance(digests, dict) else None
    return value if isinstance(value, str) and len(value) == 64 else None


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


def create_task(project_root: Path, title: str, work_class: str, task_id: str | None = None, *, new_product: bool = False) -> Path:
    """Создать обычный пакет; opt-in от start меняет только начальные артефакты discovery."""
    root = project_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Target repository does not exist: {root}")
    if work_class not in WORK_CLASSES:
        raise ValueError(f"Unsupported work class: {work_class}")
    if new_product and work_class != "planned":
        raise ValueError("New Product requires planned work")
    if new_product:
        require_new_product_client(root)
    stable_id = require_task_id(task_id) if task_id is not None else slugify(title)
    package = package_path(root, stable_id)
    if package.exists():
        raise FileExistsError(f"Task package already exists: {package}")
    evidence = package / "evidence"
    evidence.mkdir(parents=True)
    _write(package / "task.json", _task_metadata(stable_id, title, work_class))
    checklist = "\n".join(f"- [ ] `{step}`" for step in WORKFLOW_STEPS[work_class])
    _write(package / "tasks.md", f"# Tasks — {title}\n\n{checklist}\n")
    _write(evidence / "README.md", "# Evidence\n\nStore durable verification evidence here.\n")
    if work_class == "planned":
        _write(package / "spec.md", f"# {title}\n\n## User Value\n\n## Scope\n\n## Non-Goals\n\n## Acceptance Criteria\n\n## Constraints\n\n## Open Questions\n")
        _write(package / "research.md", f"# Research — {title}\n\n## Evidence\n\n## Options\n\n## Rejected approaches\n\n## Runtime observations\n\nAppend execution evidence below this heading; do not edit the reviewed planning sections.\n")
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
        session_state = "# Session state\n\nStatus: PENDING\n\n## Progress\n\n- [ ] Task not started\n"
        if new_product:
            _write_json_atomic(package / "mvp-scope.json", {
                "schema_version": 1,
                "scope": [],
                "exclusions": [],
                "acceptance_criteria": [],
                "constraints": [],
            })
            session_state = (
                "# Session state\n\nMode: new-product\n\nStatus: PENDING\n\n"
                "## Progress\n\n- [ ] Socrates chat not claimed; discovery not started\n\n"
                "## Next open question\n\nWho is the first user, and what problem should this product solve for them?\n\n"
                "## Discovery decisions\n\nRecord agreed facts, alternatives, assumptions, and deferred ideas here.\n\n"
                "## MVP owner decision\n\nPending. Before normal planning, present the exact MVP scope, non-goals, "
                "acceptance criteria, and constraints from mvp-scope.json; spec.md explains the proposal and risks. "
                "Use socrates approve-mvp --preview, then record the owner's explicit decision with "
                "--reviewed-scope-sha256, chat reference, and task-local evidence artifact. "
                "Reuse an existing explicit chat decision if it covers this exact contract; do not ask twice. "
                "Editorial spec edits do not revoke MVP approval. Summarize it here; "
                "this note alone does not unlock planning.\n"
            )
        _write(package / "session-state.md", session_state)
    return package


def new_product_context(project_root: Path, task_id: str) -> dict[str, str]:
    """Для start/restore прочитать opt-in и вопрос из пакета, не создавая новую память."""
    package = package_path(project_root, task_id)
    state = package / "session-state.md"
    if not state.exists() and not state.is_symlink():
        return {}
    content = _package_file(package, "session-state.md").read_text(encoding="utf-8")
    if "Mode: new-product" not in content.splitlines():
        return {}
    heading = "## Next open question\n"
    if content.count(heading) != 1:
        raise ValueError("New Product session-state.md requires one Next open question heading")
    question = content.split(heading, 1)[1].split("\n## ", 1)[0].strip()
    return {
        "mode": "new-product",
        "skill": "agent-fabric-new-product",
        "session_state": str(state.relative_to(project_root.resolve())).replace("\\", "/"),
        "next_open_question": question,
    }


def require_new_product_client(project_root: Path) -> None:
    """Ограничить opt-in из CLI и create_task привязкой Codex; установку plugin не выполнять."""
    binding = _load_json_object(state_path(project_root, "fabric-binding.json"), "project binding")
    if binding.get("client") != "codex":
        raise ValueError("New Product v1 requires a Codex-bound project")


def new_product_mvp_preview(project_root: Path, task_id: str) -> dict[str, object]:
    """Preview the MVP contract without granting approval; spec metadata is informational."""
    if not new_product_context(project_root, task_id):
        raise ValueError("MVP approval requires the saved New Product mode and session state")
    require_new_product_client(project_root)
    errors = validate_task(project_root, task_id)
    if errors:
        raise ValueError("Cannot approve invalid New Product package: " + "; ".join(errors))
    package = package_path(project_root, task_id)
    metadata = _load_json_object(_package_file(package, "task.json"), "task metadata")
    if metadata["id"] != task_id or metadata["work_class"] != "planned":
        raise ValueError("MVP approval requires the matching planned New Product task")
    try:
        scope_path = _package_file(package, "mvp-scope.json")
    except ValueError:
        raise ValueError(
            "New Product requires authoritative mvp-scope.json. Populate it from the agreed MVP contract, "
            "preview and attest it; legacy spec-only approvals cannot authorize it. Reuse the exact prior "
            "explicit owner decision only if its scope matches; do not ask a duplicate question."
        ) from None
    try:
        scope = json.loads(scope_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_mvp_fields)
    except (OSError, ValueError):
        raise ValueError("mvp-scope.json must be valid JSON without duplicate keys") from None
    fields = {"scope", "exclusions", "acceptance_criteria", "constraints"}
    if (
        not isinstance(scope, dict)
        or set(scope) != fields | {"schema_version"}
        or type(scope.get("schema_version")) is not int
        or scope["schema_version"] != 1
        or any(
            not isinstance(scope[field], list)
            or any(not isinstance(item, str) or not item.strip() for item in scope[field])
            for field in fields
        )
        or not scope["scope"]
        or not scope["acceptance_criteria"]
    ):
        raise ValueError(
            "mvp-scope.json requires exactly schema_version 1 and string arrays scope, exclusions, "
            "acceptance_criteria, constraints; scope and acceptance_criteria must not be empty"
        )
    canonical = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "task_id": task_id,
        "scope": scope,
        "scope_sha256": hashlib.sha256(canonical).hexdigest(),
        "scope_artifact": str((package / "mvp-scope.json").relative_to(project_root.resolve())).replace("\\", "/"),
        "spec_revision": metadata["workflow"]["spec_revision"],
        "spec_sha256": _sha256_file(_package_file(package, "spec.md")),
    }


def _unique_mvp_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate MVP contract key")
        value[key] = item
    return value


def workflow_steps(work_class: str) -> list[str]:
    if work_class not in WORKFLOW_STEPS:
        raise ValueError(f"Unsupported work class: {work_class}")
    return list(WORKFLOW_STEPS[work_class])


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
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1 or not isinstance(metadata.get("id"), str) or not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
        return ["task.json must declare schema_version 1 plus non-empty id and title"]
    try:
        require_task_id(metadata["id"])
    except ValueError:
        return ["task.json.id must be lowercase ASCII kebab-case"]
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
        return {"task_id": require_task_id(task_id), "ready": False, "reasons": errors}
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
    kepler_path = _package_file(package, "kepler.json")
    kepler = _load_json_object(kepler_path, "Kepler verdict", reasons)
    approval = _load_json_object(_package_file(package, "approval.json"), "approval", reasons)
    current_digests = _artifact_digests(package, _research_baseline_sha256(kepler))
    if kepler:
        _validate_kepler_verdict(kepler, spec_revision, plan_revision, current_digests, reasons)
    if approval:
        _validate_approval(approval, spec_revision, plan_revision, current_digests, _sha256_file(kepler_path), reasons, metadata["id"])
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


def _validate_approval(approval: dict[str, object], spec_revision: object, plan_revision: object, artifact_digests: dict[str, str], kepler_sha256: str, reasons: list[str], task_id: str) -> None:
    required = {"schema_version", "spec_revision", "plan_revision", "artifact_digests", "kepler_verdict_sha256", "approved", "approved_by", "approval_method", "approved_at"}
    method = approval.get("approval_method")
    if method == "agent-attested-chat":
        required |= {"task_id", "chat_reference", "expires_at"}
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
        or method not in {"interactive-terminal", "agent-attested-chat"}
        or not isinstance(approval.get("approved_at"), str)
    ):
        reasons.append("Planned work requires explicit human approval")
    if method == "agent-attested-chat":
        if approval.get("task_id") != task_id or not isinstance(approval.get("chat_reference"), str) or not approval["chat_reference"].strip():
            reasons.append("Chat approval must identify the current task and source chat")
        try:
            approved_at = datetime.fromisoformat(str(approval.get("approved_at")).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(approval.get("expires_at")).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if approved_at.tzinfo is None or expires_at.tzinfo is None or approved_at > now or expires_at <= now or expires_at <= approved_at or expires_at - approved_at > timedelta(hours=24):
                raise ValueError
        except (ValueError, OverflowError):
            reasons.append("Chat approval is expired or has invalid validity dates")


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
    kepler_path = _package_file(package, "kepler.json")
    reasons: list[str] = []
    kepler = _load_json_object(kepler_path, "Kepler verdict")
    digests = _artifact_digests(package, _research_baseline_sha256(kepler))
    _validate_kepler_verdict(
        kepler, spec_revision, plan_revision, digests, reasons
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
        "prompt": "Present this exact reviewed package for explicit owner approval; terminal and agent-attested chat methods are available.",
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


def attest_chat_approval(project_root: Path, task_id: str, reviewed_kepler_sha256: str, chat_reference: str) -> Path:
    """Record an agent assertion, not a verified or signed owner identity."""
    if not isinstance(chat_reference, str) or not chat_reference.strip() or len(chat_reference) > 256 or any(c in chat_reference for c in "\r\n"):
        raise ValueError("A short source chat reference is required")
    preview = approval_preview(project_root, task_id)
    if reviewed_kepler_sha256 != preview["kepler_verdict_sha256"]:
        raise ValueError("The reviewed package changed after preview; inspect and approve it again")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    approval = {
        "schema_version": 1, "task_id": preview["task_id"],
        "spec_revision": preview["spec_revision"], "plan_revision": preview["plan_revision"],
        "artifact_digests": preview["artifact_digests"], "kepler_verdict_sha256": preview["kepler_verdict_sha256"],
        "approved": True, "approved_by": "human", "approval_method": "agent-attested-chat",
        "chat_reference": chat_reference.strip(),
        "approved_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
    }
    path = Path(str(preview["approval_path"]))
    _write_json_atomic(path, approval)
    return path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
