from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
from typing import Any
from datetime import datetime, timezone

from .gates import load_gates, validate_checkpoint
from .memory import pending_requests, pending_results, require_current_schema, restore
from .task_specs import package_path
from .distribution import default_fabric_home, project_status, release_path
from .project_state import state_path


SECRET_FIELD_MARKERS = {"token", "password", "secret", "apikey", "authorization", "credential", "privatekey"}
TRACE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
TRACE_PATH_REFERENCE = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*$")
TRACE_STRING_FIELDS = {"kind", "gate", "transition", "task_id", "actor", "status"}
TRACE_LIST_FIELDS = {"required_evidence", "supplied_evidence", "artifacts"}
RETROSPECTIVE_SIGNAL_CATEGORIES = {
    "user-correction",
    "agent-drift",
    "missed-instruction",
    "scope-violation",
    "memory-gap",
    "repeated-failure",
    "security-concern",
    "friction",
}
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?:^|[^a-z0-9])(sk-[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|xox[baprs]-[a-z0-9-]{10,}|akia[0-9a-z]{16})(?:$|[^a-z0-9])", re.IGNORECASE),
    re.compile(r"eyj[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bbearer\s+[a-z0-9._~+/-]{12,}", re.IGNORECASE),
)


def trace_path(project_root: Path) -> Path:
    return state_path(project_root, "harness/trace.jsonl")


def signal_path(project_root: Path) -> Path:
    return state_path(project_root, "harness/signals.jsonl")


def retrospective_state_path(project_root: Path) -> Path:
    return state_path(project_root, "harness/retrospective-state.json")


def append_trace(project_root: Path, event: dict[str, Any]) -> Path:
    """Append a typed, non-secret audit event with no free-text payloads."""
    if not isinstance(event, dict):
        raise ValueError("trace event must be a JSON object")
    if _contains_secret_field(event):
        raise ValueError("trace event must not contain a secret-like field")
    _validate_trace_event(event)
    path = state_path(project_root, "harness/trace.jsonl", create_parents=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def record_checkpoint(project_root: Path, gate_id: str, evidence: list[str], fabric_home: Path | None = None) -> dict[str, Any]:
    """Validate a shared-release gate and append only evidence names to local trace."""
    root = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    status = project_status(root, home)
    if status.get("status") != "bound":
        raise ValueError("A Fabric checkpoint requires a bound project")
    binding_path = state_path(root, "fabric-binding.json")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    registry_path = release_path(home, binding["fabric_release"]) / "core" / "gates.json"
    checkpoint = validate_checkpoint(load_gates(registry_path), gate_id, evidence)
    append_trace(root, {"kind": "gate-checkpoint", **checkpoint})
    return checkpoint


def record_signal(
    project_root: Path,
    category: str,
    task_id: str | None = None,
    artifact: str | None = None,
) -> dict[str, str | None]:
    """Record a minimal project-local behavioural signal without chat text."""
    root = project_root.resolve()
    if category not in RETROSPECTIVE_SIGNAL_CATEGORIES:
        raise ValueError(f"Unknown retrospective signal category: {category}")
    if task_id is not None and not _is_safe_identifier(task_id):
        raise ValueError("signal task_id must be a safe identifier")
    if artifact is not None and not _is_safe_path_reference(artifact):
        raise ValueError("signal artifact must be a safe project-relative path")
    event: dict[str, str | None] = {
        "at": _utc_timestamp(),
        "category": category,
        "task_id": task_id,
        "artifact": artifact,
    }
    path = state_path(root, "harness/signals.jsonl", create_parents=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def retrospective_input(project_root: Path) -> dict[str, Any]:
    """Read the project-local window since the last approved Harness run."""
    root = project_root.resolve()
    state = _load_retrospective_state(root)
    after_offset = state.get("last_processed_offset", 0)
    signals, watermark = _read_signals_since(root, after_offset)
    snapshot_digest = _signal_window_digest(root, after_offset, watermark)
    return {
        "generated_at": _utc_timestamp(),
        "since_offset": after_offset,
        "snapshot": {"start_offset": after_offset, "end_offset": watermark, "sha256": snapshot_digest},
        "signals": signals,
        "instructions": {
            "evidence": "Use the active task artifacts and current-session context to substantiate signals; a signal is not proof by itself.",
            "output": "Create a project-local retrospective report with failure patterns, root causes, bounded proposals, and deferred out-of-scope findings.",
            "write_policy": "Do not edit instructions, profiles, workflow, or global Fabric from this input. Kepler and a human must review proposals first.",
        },
    }


def close_retrospective(
    project_root: Path,
    report_artifact: str,
    kepler_verdict_artifact: str,
    human_decision_artifact: str,
    snapshot_start_offset: int,
    watermark: int,
    snapshot_digest: str,
    reviewer: str,
    human_approved: bool,
) -> dict[str, Any]:
    """Advance a project's Harness cursor only after an approved retrospective."""
    root = project_root.resolve()
    if reviewer != "opponent" or not human_approved:
        raise ValueError("A retrospective requires an opponent review and explicit human approval")
    if not isinstance(snapshot_start_offset, int) or not isinstance(watermark, int) or snapshot_start_offset < 0 or watermark < snapshot_start_offset:
        raise ValueError("retrospective snapshot offsets must be ordered non-negative byte offsets")
    if not re.fullmatch(r"[a-f0-9]{64}", snapshot_digest):
        raise ValueError("retrospective snapshot digest must be a SHA-256 value")
    for label, artifact in (
        ("report", report_artifact),
        ("Kepler verdict", kepler_verdict_artifact),
        ("human decision", human_decision_artifact),
    ):
        if not _is_safe_path_reference(artifact):
            raise ValueError(f"{label} artifact must be a safe project-relative path")
        artifact_path = (root / artifact).resolve()
        if not artifact_path.is_file() or root not in artifact_path.parents:
            raise ValueError(f"{label} artifact must exist below the project root")
    current_state = _load_retrospective_state(root)
    if snapshot_start_offset != current_state.get("last_processed_offset", 0):
        raise ValueError("retrospective snapshot does not start at the current project cursor")
    if snapshot_digest != _signal_window_digest(root, snapshot_start_offset, watermark):
        raise ValueError("retrospective snapshot no longer matches the signal log window")
    state = {
        "schema_version": 2,
        "last_processed_offset": watermark,
        "snapshot_sha256": snapshot_digest,
        "closed_at": _utc_timestamp(),
        "report_artifact": report_artifact,
        "kepler_verdict_artifact": kepler_verdict_artifact,
        "human_decision_artifact": human_decision_artifact,
    }
    path = state_path(root, "harness/retrospective-state.json", create_parents=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    append_trace(
        root,
        {
            "kind": "retrospective-closed",
            "actor": reviewer,
            "artifacts": [report_artifact, kepler_verdict_artifact, human_decision_artifact],
        },
    )
    return state


def _validate_trace_event(event: dict[str, Any]) -> None:
    if set(event) - (TRACE_STRING_FIELDS | TRACE_LIST_FIELDS):
        raise ValueError("trace event contains unsupported or free-text fields")
    if not isinstance(event.get("kind"), str) or not _is_safe_identifier(event["kind"]):
        raise ValueError("trace event kind must be a safe identifier")
    for field in TRACE_STRING_FIELDS - {"kind"}:
        if field in event and (not isinstance(event[field], str) or not _is_safe_identifier(event[field])):
            raise ValueError(f"trace event {field} must be a safe identifier")
    for field in TRACE_LIST_FIELDS:
        if field in event and (
            not isinstance(event[field], list)
            or any(not isinstance(value, str) or not _is_safe_trace_value(field, value) for value in event[field])
            or len(event[field]) != len(set(event[field]))
        ):
            raise ValueError(f"trace event {field} must be unique safe identifiers")


def _is_safe_identifier(value: str) -> bool:
    return bool(TRACE_IDENTIFIER.fullmatch(value)) and not any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)


def _is_safe_trace_value(field: str, value: str) -> bool:
    pattern = TRACE_PATH_REFERENCE if field == "artifacts" else TRACE_IDENTIFIER
    return bool(pattern.fullmatch(value)) and not any(secret.search(value) for secret in SECRET_VALUE_PATTERNS)


def _is_safe_path_reference(value: str) -> bool:
    return bool(TRACE_PATH_REFERENCE.fullmatch(value)) and not any(secret.search(value) for secret in SECRET_VALUE_PATTERNS)


def _read_signals_since(project_root: Path, offset: int) -> tuple[list[dict[str, str | None]], int]:
    path = signal_path(project_root)
    if not path.is_file():
        if offset:
            raise ValueError("retrospective signal log is missing before the recorded cursor")
        return [], 0
    if path.stat().st_size < offset:
        raise ValueError("retrospective signal log is shorter than the recorded cursor")
    signals: list[dict[str, str | None]] = []
    with path.open("rb") as handle:
        handle.seek(offset)
        line_number = 0
        while raw_line := handle.readline():
            line_number += 1
            try:
                signal = json.loads(raw_line.decode("utf-8"))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid retrospective signal at {path}:{line_number}") from error
            if not isinstance(signal, dict) or set(signal) != {"at", "category", "task_id", "artifact"}:
                raise ValueError(f"Invalid retrospective signal shape at {path}:{line_number}")
            if (
                not isinstance(signal["at"], str)
                or signal["category"] not in RETROSPECTIVE_SIGNAL_CATEGORIES
                or (signal["task_id"] is not None and not _is_safe_identifier(signal["task_id"]))
                or (signal["artifact"] is not None and not _is_safe_path_reference(signal["artifact"]))
            ):
                raise ValueError(f"Invalid retrospective signal values at {path}:{line_number}")
            signals.append(signal)
        return signals, handle.tell()


def _signal_window_digest(project_root: Path, start_offset: int, end_offset: int) -> str:
    path = signal_path(project_root)
    if start_offset < 0 or end_offset < start_offset:
        raise ValueError("retrospective snapshot offsets are invalid")
    if not path.is_file():
        if start_offset == end_offset == 0:
            return hashlib.sha256(b"").hexdigest()
        raise ValueError("retrospective signal log is missing before the requested snapshot")
    size = path.stat().st_size
    if end_offset > size:
        raise ValueError("retrospective watermark is beyond the current signal log")
    with path.open("rb") as handle:
        handle.seek(start_offset)
        window = handle.read(end_offset - start_offset)
    if window and not window.endswith(b"\n"):
        raise ValueError("retrospective watermark must end at a complete signal record")
    return hashlib.sha256(window).hexdigest()


def _load_retrospective_state(project_root: Path) -> dict[str, Any]:
    path = retrospective_state_path(project_root)
    if not path.is_file():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid retrospective state: {path}") from error
    if not isinstance(state, dict):
        raise ValueError(f"Invalid retrospective state: {path}")
    if state.get("schema_version") == 1:
        # V1 stored a timestamp cursor. Re-reading the log is conservative: it can
        # repeat a prior signal but never loses one at a timestamp race boundary.
        return {}
    if state.get("schema_version") == 2 and "snapshot_sha256" not in state:
        # Earlier v2 state had an offset but no window digest. Start conservatively
        # from zero rather than accepting an unverifiable cursor.
        return {}
    if (
        set(state) != {
            "schema_version", "last_processed_offset", "closed_at", "report_artifact",
            "kepler_verdict_artifact", "human_decision_artifact", "snapshot_sha256",
        }
        or state.get("schema_version") != 2
        or not isinstance(state.get("last_processed_offset"), int)
        or state["last_processed_offset"] < 0
        or not isinstance(state.get("closed_at"), str)
        or not isinstance(state.get("snapshot_sha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", state["snapshot_sha256"])
        or not all(_is_safe_path_reference(state.get(field, "")) for field in ("report_artifact", "kepler_verdict_artifact", "human_decision_artifact"))
    ):
        raise ValueError(f"Invalid retrospective state: {path}")
    return state


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = "".join(character for character in str(key).lower() if character.isalnum())
            if any(marker in normalized for marker in SECRET_FIELD_MARKERS):
                return True
            if _contains_secret_field(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)
    return False


def resume_snapshot(project_root: Path, task_id: str) -> dict[str, Any]:
    """Return local durable context only; this does not execute project commands."""
    package = package_path(project_root, task_id)
    if not package.is_dir():
        raise FileNotFoundError(package)
    task = json.loads((package / "task.json").read_text(encoding="utf-8"))
    snapshot: dict[str, Any] = {"task": task, "package": str(package), "artifacts": []}
    for relative in ("spec.md", "research.md", "plan.md", "kepler.md", "tasks.md", "session-state.md"):
        if (package / relative).is_file():
            snapshot["artifacts"].append(relative)
    try:
        snapshot["memory"] = restore(project_root, task["id"])
        snapshot["pending_requests"] = pending_requests(project_root, task["id"])
        snapshot["pending_results"] = pending_results(project_root, task["id"])
    except KeyError:
        snapshot["memory"] = None
        snapshot["pending_requests"] = []
        snapshot["pending_results"] = []
    return snapshot


def health_report(project_root: Path, fabric_home: Path | None = None) -> dict[str, Any]:
    root = project_root.resolve()
    expected = {
        "binding": state_path(root, "fabric-binding.json"),
        "profile": state_path(root, "profile.json"),
        "capabilities": state_path(root, "config/capabilities.json"),
        "model_routing": state_path(root, "config/model-routing.json"),
        "work_tracking": state_path(root, "config/work-tracking.json"),
        "memory": state_path(root, "memory.db"),
    }
    report: dict[str, Any] = {
        "project_root": str(root),
        "project": {name: path.is_file() for name, path in expected.items()},
        "fabric_status": project_status(root, fabric_home),
    }
    if expected["memory"].is_file():
        try:
            require_current_schema(root)
            report["memory_schema"] = "current"
        except (FileNotFoundError, ValueError):
            report["memory_schema"] = "migration-required"
    else:
        report["memory_schema"] = "missing"
    binding_path = expected["binding"]
    if binding_path.is_file():
        try:
            binding = json.loads(binding_path.read_text(encoding="utf-8"))
            home = (fabric_home or default_fabric_home()).expanduser().resolve()
            release = release_path(home, binding["fabric_release"])
            report["release"] = {
                "version": binding["fabric_release"],
                "present": release.is_dir(),
                "agent_profiles": (release / "core" / "agent-profiles.json").is_file(),
                "gates": (release / "core" / "gates.json").is_file(),
                "adapter": (release / "adapters" / binding["client"] / "adapter-manifest.json").is_file(),
            }
        except (KeyError, ValueError, json.JSONDecodeError):
            report["release"] = {"present": False, "error": "invalid project binding"}
    return report
