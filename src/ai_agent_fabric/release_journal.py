from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import string
import tempfile
from pathlib import Path
from typing import Any

from .agent_profiles import default_profiles
from .identifiers import require_task_id
from .project_state import state_path
from .task_specs import archived_package_path, package_path


FACTS_FILE = "close-out.json"
VERSION = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", re.ASCII | re.IGNORECASE)
ROLE_NAMES = {profile["id"]: profile["persona"] for profile in default_profiles()["profiles"]}


def _file_evidence(path: Path) -> tuple[str, list[int]]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        identity = os.fstat(stream.fileno())
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest(), [identity.st_dev, identity.st_ino]


def _contained_path(root: Path, reference: str) -> Path:
    from .memory import _safe_path_reference

    if not _safe_path_reference(reference):
        raise ValueError(f"Invalid artifact reference: {reference!r}")
    path = (root / reference).resolve()
    if root not in path.parents:
        raise ValueError(f"Artifact escapes its root: {reference}")
    return path


def _output_identity(root: Path, path: Path) -> dict[str, Any]:
    digest, identity = _file_evidence(path) if path.is_file() else (None, None)
    return {"resolved_path": path.relative_to(root).as_posix(), "sha256": digest, "identity": identity}


def output_baseline(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    try:
        inputs = {_contained_path(root, ref) for ref in [request["scope_artifact"], *request["input_artifacts"]]}
        present_inputs = [item for item in inputs if item.is_file()]
    except (OSError, RuntimeError, ValueError):
        return {}
    baseline = {}
    for ref in request["required_outputs"]:
        try:
            path = _contained_path(root, ref)
            if path in inputs or (path.is_file() and any(path.samefile(item) for item in present_inputs)):
                continue
            baseline[ref] = _output_identity(root, path)
        except (OSError, RuntimeError, ValueError):
            continue
    return baseline


def verify_outputs(root: Path, payload: dict[str, Any], request: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    current = output_baseline(root, request)
    verified = []
    seen = set()
    for artifact in payload["artifacts"]:
        ref, digest = artifact["path"], artifact.get("sha256")
        previous = baseline.get(ref)
        observed = current.get(ref)
        if (
            ref not in seen and digest is not None and previous is not None and observed is not None
            and previous["resolved_path"] == observed["resolved_path"]
            and previous["sha256"] != digest and observed["sha256"] == digest
        ):
            verified.append({"path": ref, "baseline_sha256": previous["sha256"], **observed})
            seen.add(ref)
    return verified


def _required_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected nonempty factual text")
    return value.strip()


def _facts(package: Path) -> dict[str, Any]:
    from .memory import _reject_secret_fields

    def evidence(refs: Any, required: bool) -> list[dict[str, str]]:
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            raise ValueError("Evidence must be a list of package-relative artifact paths")
        if required and not refs:
            raise ValueError("Change and executed-check facts require an evidence artifact")
        digests = []
        for ref in sorted(set(refs)):
            path = _contained_path(package, ref)
            if not path.is_file() or path.samefile(facts_path):
                raise ValueError(f"Evidence must reference another existing package file: {ref}")
            digests.append({"path": ref, "sha256": _file_evidence(path)[0]})
        return digests

    try:
        facts_path = _contained_path(package, FACTS_FILE)
        raw = json.loads(facts_path.read_text(encoding="utf-8"))
        _reject_secret_fields(raw)
        if (
            not isinstance(raw, dict) or set(raw) != {"schema_version", "changes", "checks"}
            or type(raw["schema_version"]) is not int or raw["schema_version"] != 1
            or not isinstance(raw["changes"], list) or not raw["changes"]
            or not isinstance(raw["checks"], list) or not raw["checks"]
        ):
            raise ValueError("Expected schema version 1 with at least one change and one check")
        changes = []
        for item in raw["changes"]:
            if not isinstance(item, dict) or set(item) != {"summary", "evidence"}:
                raise ValueError("Change requires summary and evidence")
            changes.append({"summary": _required_text(item["summary"]), "evidence": evidence(item["evidence"], True)})
        checks = []
        for item in raw["checks"]:
            if not isinstance(item, dict) or set(item) != {"name", "outcome", "reason", "evidence"}:
                raise ValueError("Check requires name, outcome, reason and evidence")
            outcome = item["outcome"]
            if outcome not in ("passed", "failed", "skipped", "unknown"):
                raise ValueError("Invalid check outcome")
            checks.append({
                "name": _required_text(item["name"]), "outcome": outcome,
                "reason": _required_text(item["reason"]),
                "evidence": evidence(item["evidence"], outcome in ("passed", "failed")),
            })
        return {"schema_version": 1, "changes": changes, "checks": checks}
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError(f"Record valid close-out facts in {FACTS_FILE}: {error}") from error


def _participants(
    connection: sqlite3.Connection, root: Path, package: Path, original_package: Path, session_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT result.request_id, result.idempotency_key, result.agent, proof.evidence_json "
        "FROM result_outbox AS result JOIN delegation_requests AS request "
        "ON request.idempotency_key=result.request_id AND request.session_id=result.session_id AND request.agent=result.agent "
        "JOIN journal_contribution_proofs AS proof ON proof.result_id=result.idempotency_key "
        "WHERE result.session_id=? AND result.status='acknowledged' AND request.status='dispatched' "
        "ORDER BY result.agent, result.idempotency_key",
        (session_id,),
    ).fetchall()
    proofs = [(row, json.loads(row["evidence_json"])) for row in rows]
    claims: dict[tuple[object, str], set[str]] = {}
    for row, artifacts in proofs:
        for artifact in artifacts:
            for key in _claim_keys(artifact):
                claims.setdefault(key, set()).add(row["request_id"])
    participants = []
    for row, claimed_artifacts in proofs:
        artifacts = []
        for artifact in claimed_artifacts:
            if any(len(claims[key]) > 1 for key in _claim_keys(artifact)):
                continue
            try:
                path = _contained_path(root, artifact["path"])
                expected = root / artifact["resolved_path"]
                if original_package != package and expected.is_relative_to(original_package):
                    path = (package / expected.relative_to(original_package)).resolve()
                    expected = package / expected.relative_to(original_package)
                if path != expected or not path.is_relative_to(root) or not path.is_file():
                    continue
                digest, identity = _file_evidence(path)
                if digest != artifact["sha256"] or identity != artifact.get("identity"):
                    continue
            except (OSError, RuntimeError, ValueError):
                continue
            in_package = path.is_relative_to(package)
            artifacts.append({
                "path": path.relative_to(package if in_package else root).as_posix(),
                "relative_to": "package" if in_package else "project",
                "sha256": artifact["sha256"], "baseline_sha256": artifact["baseline_sha256"],
            })
        if artifacts:
            participants.append({
                "role": row["agent"], "name": ROLE_NAMES[row["agent"]], "request_id": row["request_id"],
                "result_id": row["idempotency_key"], "evidence": artifacts,
            })
    return participants


def _claim_keys(artifact: dict[str, Any]) -> list[tuple[object, str]]:
    digest = artifact["sha256"]
    keys: list[tuple[object, str]] = [(Path(artifact["resolved_path"]), digest)]
    if artifact.get("identity") and artifact["identity"][1]:
        keys.append((tuple(artifact["identity"]), digest))
    return keys


def capture_completion(connection: sqlite3.Connection, root: Path, session_id: str) -> None:
    lifecycle = connection.execute(
        "SELECT status FROM task_lifecycles WHERE session_id=? "
        "AND NOT EXISTS (SELECT 1 FROM project_journal WHERE session_id=?)",
        (session_id, session_id),
    ).fetchone()
    if lifecycle is None or lifecycle["status"] == "completed":
        return
    root = root.resolve()
    original_package = package_path(root, session_id)
    package = original_package
    if not package.is_dir():
        package = archived_package_path(root, session_id)
    snapshot = _facts(package)
    snapshot["participants"] = _participants(connection, root, package, original_package, session_id)
    connection.execute(
        "INSERT INTO project_journal(session_id, snapshot_json) VALUES (?, ?)",
        (session_id, json.dumps(snapshot, ensure_ascii=False, sort_keys=True)),
    )


def project_journal(root: Path, task_ids: list[str] | None = None) -> list[dict[str, Any]]:
    from .memory import _require_current_schema_connection, connect

    connection = connect(root, create=False)
    try:
        _require_current_schema_connection(connection)
        connection.execute("BEGIN")
        rows = connection.execute(
            "SELECT lifecycle.session_id, lifecycle.status, journal.completed_at, journal.snapshot_json "
            "FROM task_lifecycles AS lifecycle LEFT JOIN project_journal AS journal USING (session_id) "
            "ORDER BY lifecycle.session_id"
        ).fetchall()
        if task_ids is None:
            selected = [row for row in rows if row["snapshot_json"] is not None]
        else:
            if not task_ids or len(task_ids) != len(set(task_ids)):
                raise ValueError("Provide a nonempty list of distinct completed task IDs")
            indexed = {row["session_id"]: row for row in rows}
            selected = []
            for task_id in sorted(task_ids):
                row = indexed.get(require_task_id(task_id))
                if row is None:
                    raise ValueError(f"Unknown task: {task_id}")
                if row["status"] != "completed":
                    raise ValueError(f"Task has not completed: {task_id}")
                if row["snapshot_json"] is None:
                    raise ValueError(f"Completed task has no release-journal evidence: {task_id}")
                selected.append(row)
        return [
            {"task_id": row["session_id"], "completed_at": row["completed_at"], **json.loads(row["snapshot_json"])}
            for row in selected
        ]
    finally:
        connection.close()


def _markdown(value: str) -> str:
    return "".join("\\" + char if char in string.punctuation else char for char in " ".join(value.split()))


def _render(version: str, entries: list[dict[str, Any]]) -> bytes:
    lines = [f"# What's New in {version}", ""]
    for entry in entries:
        lines.extend([f"## `{entry['task_id']}`", ""])
        lines.extend(f"- {_markdown(change['summary'])}" for change in entry["changes"])
        names = sorted({item["name"] for item in entry["participants"]})
        if names:
            lines.extend(["", f"Participants: {', '.join(names)}"])
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def release_notes(root: Path, version: str, task_ids: list[str]) -> dict[str, Any]:
    if len(version) > 64 or not VERSION.fullmatch(version):
        raise ValueError("Version must be 1–64 ASCII letters or digits, with groups separated by dots or hyphens")
    version = version.lower()
    entries = project_journal(root, task_ids)
    relative = f"release-notes/whats-new-{version}.md"
    content = _render(version, entries)
    destination = state_path(root, relative)
    destination.parent.mkdir(exist_ok=True)
    destination = state_path(root, relative)
    stream = tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".notes-", delete=False)
    temporary = Path(stream.name)
    try:
        with stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        destination = state_path(root, relative)
        try:
            os.link(temporary, destination)
            replayed = False
        except FileExistsError:
            if not state_path(root, relative).is_file() or destination.read_bytes() != content:
                raise ValueError(f"Release notes already exist with different content for version {version}") from None
            replayed = True
    finally:
        temporary.unlink()
    return {"version": version, "path": str(destination), "task_ids": [entry["task_id"] for entry in entries], "replayed": replayed}
