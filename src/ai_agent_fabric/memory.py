from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .project_state import state_path


SECRET_FIELD_MARKERS = {"token", "password", "secret", "apikey", "authorization", "credential", "privatekey"}
CANONICAL_AGENTS = {"orchestrator", "explore", "plan", "opponent", "dev", "review", "validation"}
MEMORY_SCHEMA_VERSION = 8
SAFE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
SAFE_PATH_REFERENCE = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*$")
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?:^|[^a-z0-9])(sk-[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|xox[baprs]-[a-z0-9-]{10,}|akia[0-9a-z]{16})(?:$|[^a-z0-9])", re.IGNORECASE),
    re.compile(r"eyj[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bbearer\s+[a-z0-9._~+/-]{12,}", re.IGNORECASE),
)

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  actor TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS records_session_kind ON records(session_id, kind);
CREATE TABLE IF NOT EXISTS delegation_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idempotency_key TEXT NOT NULL UNIQUE,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  agent TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'dispatched')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dispatched_at TEXT
);
CREATE INDEX IF NOT EXISTS delegation_requests_session_status ON delegation_requests(session_id, status);
CREATE TABLE IF NOT EXISTS result_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idempotency_key TEXT NOT NULL UNIQUE,
  request_id TEXT NOT NULL UNIQUE REFERENCES delegation_requests(idempotency_key),
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  agent TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'acknowledged')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  acknowledged_at TEXT
);
CREATE INDEX IF NOT EXISTS result_outbox_session_status ON result_outbox(session_id, status);
CREATE TABLE IF NOT EXISTS guard_failures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idempotency_key TEXT NOT NULL UNIQUE,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  incident_id TEXT NOT NULL,
  taxonomy TEXT NOT NULL,
  guard TEXT NOT NULL,
  evidence_artifact TEXT NOT NULL,
  policy TEXT NOT NULL CHECK(policy IN ('block', 'retry-then-escalate')),
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'retrying', 'blocked', 'escalated')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS guard_failures_session_guard ON guard_failures(session_id, guard, taxonomy, incident_id, id);
CREATE TABLE IF NOT EXISTS guard_incidents (
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  guard TEXT NOT NULL,
  incident_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('retrying', 'blocked', 'escalated')),
  PRIMARY KEY(session_id, guard, incident_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS guard_incidents_active ON guard_incidents(session_id, guard) WHERE status='retrying';
CREATE TABLE IF NOT EXISTS guard_outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idempotency_key TEXT NOT NULL UNIQUE,
  failure_key TEXT NOT NULL UNIQUE REFERENCES guard_failures(idempotency_key) ON DELETE CASCADE,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  guard TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK(outcome IN ('retry', 'block', 'escalate')),
  attempt INTEGER NOT NULL CHECK(attempt >= 1),
  evidence_artifact TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS guard_outcomes_session_guard ON guard_outcomes(session_id, guard, id);
CREATE TABLE IF NOT EXISTS task_lifecycles (
  session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
  task_package TEXT NOT NULL,
  next_action TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('active', 'blocked', 'escalated')),
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resumed_at TEXT
);
CREATE TABLE IF NOT EXISTS task_steps (
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  step_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending', 'in-progress', 'done', 'skipped')),
  closure_artifact TEXT,
  closure_reason TEXT,
  PRIMARY KEY(session_id, step_id)
);
CREATE TABLE IF NOT EXISTS guard_trace_outbox (
  failure_key TEXT PRIMARY KEY REFERENCES guard_failures(idempotency_key) ON DELETE CASCADE,
  event_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'delivered')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  delivered_at TEXT
);
"""


def database_path(project_root: Path) -> Path:
    return state_path(project_root, "memory.db")


def connect(project_root: Path, *, create: bool = True) -> sqlite3.Connection:
    path = state_path(project_root, "memory.db", create_parents=create)
    if not create and not path.is_file():
        raise FileNotFoundError(f"Project memory database does not exist: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(project_root: Path) -> Path:
    connection = connect(project_root)
    try:
        connection.executescript(SCHEMA)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(result_outbox)")}
        if "request_id" not in columns:
            connection.execute("ALTER TABLE result_outbox ADD COLUMN request_id TEXT")
        guard_columns = {row["name"] for row in connection.execute("PRAGMA table_info(guard_failures)")}
        if "incident_id" not in guard_columns:
            connection.execute("ALTER TABLE guard_failures ADD COLUMN incident_id TEXT NOT NULL DEFAULT 'legacy-incident'")
        step_columns = {row["name"] for row in connection.execute("PRAGMA table_info(task_steps)")}
        if "closure_artifact" not in step_columns:
            connection.execute("ALTER TABLE task_steps ADD COLUMN closure_artifact TEXT")
        if "closure_reason" not in step_columns:
            connection.execute("ALTER TABLE task_steps ADD COLUMN closure_reason TEXT")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS legacy_result_outbox ("
            "original_id INTEGER PRIMARY KEY, idempotency_key TEXT NOT NULL, session_id TEXT NOT NULL, "
            "agent TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, "
            "acknowledged_at TEXT, quarantined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO legacy_result_outbox(original_id, idempotency_key, session_id, agent, payload_json, status, created_at, acknowledged_at) "
            "SELECT id, idempotency_key, session_id, agent, payload_json, status, created_at, acknowledged_at "
            "FROM result_outbox WHERE request_id IS NULL"
        )
        connection.execute("DELETE FROM result_outbox WHERE request_id IS NULL")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS result_outbox_request_id ON result_outbox(request_id) WHERE request_id IS NOT NULL")
        connection.execute(f"PRAGMA user_version={MEMORY_SCHEMA_VERSION}")
        connection.commit()
    finally:
        connection.close()
    return database_path(project_root)


def require_current_schema(project_root: Path) -> None:
    """Read-only guard: lifecycle operations never silently migrate a project's memory."""
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
    finally:
        connection.close()


def schema_version(project_root: Path) -> int:
    """Return the declared local schema version without creating or migrating state."""
    connection = connect(project_root, create=False)
    try:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])
    finally:
        connection.close()


def quarantined_results(project_root: Path) -> list[dict[str, Any]]:
    """Read retained legacy specialist results that require human relinking."""
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='legacy_result_outbox'"
        ).fetchone()
        if exists is None:
            return []
        rows = connection.execute(
            "SELECT original_id, idempotency_key, session_id, agent, status, created_at, acknowledged_at, quarantined_at "
            "FROM legacy_result_outbox ORDER BY original_id"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _require_current_schema_connection(connection: sqlite3.Connection) -> None:
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required_tables = {"sessions", "records", "delegation_requests", "result_outbox", "guard_failures", "guard_incidents", "guard_outcomes", "task_lifecycles", "task_steps", "guard_trace_outbox"}
    if not required_tables.issubset(tables):
        raise ValueError("Project memory schema requires migration; run `memory init <project> --home <fabric-home>` explicitly")
    result_columns = {row["name"] for row in connection.execute("PRAGMA table_info(result_outbox)")}
    if "request_id" not in result_columns:
        raise ValueError("Project memory schema requires migration; run `memory init <project> --home <fabric-home>` explicitly")
    step_columns = {row["name"] for row in connection.execute("PRAGMA table_info(task_steps)")}
    if not {"closure_artifact", "closure_reason"}.issubset(step_columns):
        raise ValueError("Project memory schema requires migration; run `memory init <project> --home <fabric-home>` explicitly")


def start_session(project_root: Path, session_id: str, title: str, actor: str = "orchestrator") -> None:
    if actor != "orchestrator" or not _safe_identifier(session_id) or not isinstance(title, str) or not title.strip():
        raise ValueError("only the orchestrator may start a session with a safe identifier and title")
    _reject_secret_fields({"title": title})
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        connection.execute(
            "INSERT INTO sessions(id, title) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET title=excluded.title, status='active', updated_at=CURRENT_TIMESTAMP",
            (session_id, title),
        )
        connection.commit()
    finally:
        connection.close()


def activate_task_lifecycle(
    project_root: Path,
    session_id: str,
    title: str,
    task_package: str,
    step_ids: list[str],
    mode: str,
) -> dict[str, Any]:
    """Create or resume the durable task-local Socrates execution context."""
    if mode not in {"start", "restore"} or not _safe_identifier(session_id) or not _safe_path_reference(task_package):
        raise ValueError("task lifecycle requires a safe session and task package")
    if not step_ids or len(step_ids) != len(set(step_ids)) or not all(_safe_identifier(step) for step in step_ids):
        raise ValueError("task lifecycle requires unique safe workflow steps")
    start_session(project_root, session_id, title)
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            lifecycle = connection.execute("SELECT task_package FROM task_lifecycles WHERE session_id=?", (session_id,)).fetchone()
            if lifecycle is None:
                connection.execute(
                    "INSERT INTO task_lifecycles(session_id, task_package, next_action, status) VALUES (?, ?, ?, 'active')",
                    (session_id, task_package, step_ids[0]),
                )
                connection.executemany(
                    "INSERT INTO task_steps(session_id, step_id, status) VALUES (?, ?, 'pending')",
                    [(session_id, step) for step in step_ids],
                )
            elif lifecycle["task_package"] != task_package:
                raise ValueError("task lifecycle package does not match its existing session")
            if mode == "restore":
                connection.execute("UPDATE task_lifecycles SET resumed_at=CURRENT_TIMESTAMP WHERE session_id=?", (session_id,))
            active = _next_task_action(connection, session_id)
            connection.execute(
                "UPDATE task_lifecycles SET next_action=?, status=? WHERE session_id=?",
                (active["next_action"], active["status"], session_id),
            )
        return active
    finally:
        connection.close()


def _next_task_action(connection: sqlite3.Connection, session_id: str) -> dict[str, str]:
    escalated = connection.execute(
        "SELECT 1 FROM guard_failures WHERE session_id=? AND status='escalated' LIMIT 1", (session_id,)
    ).fetchone()
    if escalated is not None:
        return {"next_action": "user-escalation", "status": "escalated"}
    blocked = connection.execute(
        "SELECT 1 FROM guard_failures WHERE session_id=? AND status='blocked' LIMIT 1", (session_id,)
    ).fetchone()
    if blocked is not None:
        return {"next_action": "guard-blocked", "status": "blocked"}
    step = connection.execute(
        "SELECT step_id FROM task_steps WHERE session_id=? AND status IN ('in-progress', 'pending') "
        "ORDER BY CASE status WHEN 'in-progress' THEN 0 ELSE 1 END, rowid LIMIT 1", (session_id,)
    ).fetchone()
    return {"next_action": step["step_id"] if step is not None else "archive", "status": "active"}


def advance_task_step(
    project_root: Path, session_id: str, step_id: str, status: str,
    closure_artifact: str | None = None, closure_reason: str | None = None,
) -> dict[str, Any]:
    """Socrates-only durable checklist transition; steps may only move forward."""
    if not _safe_identifier(session_id) or not _safe_identifier(step_id) or status not in {"in-progress", "done", "skipped"}:
        raise ValueError("task step transition is invalid")
    closing = status in {"done", "skipped"}
    if closing:
        if not _safe_path_reference(closure_artifact or "") or not isinstance(closure_reason, str) or not closure_reason.strip():
            raise ValueError("closing a task step requires an evidence artifact and reason")
        _reject_secret_fields({"closure_reason": closure_reason})
        artifact_path = (project_root.resolve() / closure_artifact).resolve()
        if not artifact_path.is_file() or project_root.resolve() not in artifact_path.parents:
            raise ValueError("task step closure evidence artifact must exist below the project root")
    elif closure_artifact is not None or closure_reason is not None:
        raise ValueError("only a completed or skipped task step may declare closure evidence")
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            row = connection.execute(
                "SELECT rowid, status FROM task_steps WHERE session_id=? AND step_id=?", (session_id, step_id)
            ).fetchone()
            if row is None:
                raise KeyError(step_id)
            if row["status"] in {"done", "skipped"}:
                if row["status"] != status:
                    raise ValueError("completed task steps are immutable")
            else:
                earlier_open = connection.execute(
                    "SELECT 1 FROM task_steps WHERE session_id=? AND rowid<? AND status NOT IN ('done', 'skipped') LIMIT 1",
                    (session_id, row["rowid"]),
                ).fetchone()
                if earlier_open is not None:
                    raise ValueError("task steps must advance in workflow order")
                connection.execute(
                    "UPDATE task_steps SET status=?, closure_artifact=?, closure_reason=? WHERE session_id=? AND step_id=?",
                    (status, closure_artifact, closure_reason, session_id, step_id),
                )
            active = _next_task_action(connection, session_id)
            connection.execute(
                "UPDATE task_lifecycles SET next_action=?, status=? WHERE session_id=?",
                (active["next_action"], active["status"], session_id),
            )
        return {"step_id": step_id, "step_status": status, "closure_artifact": closure_artifact, **active}
    finally:
        connection.close()


def record(project_root: Path, session_id: str, kind: str, actor: str, summary: str, evidence: dict[str, Any]) -> None:
    if actor != "orchestrator" or not all(_safe_identifier(value) for value in (session_id, kind)) or not isinstance(summary, str) or not summary.strip() or not isinstance(evidence, dict):
        raise ValueError("only the orchestrator may persist records with safe identifiers, summary, and object evidence")
    _reject_secret_fields({"summary": summary, "evidence": evidence})
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        connection.execute(
            "INSERT INTO records(session_id, kind, actor, summary, evidence_json) VALUES (?, ?, ?, ?, ?)",
            (session_id, kind, actor, summary, json.dumps(evidence, ensure_ascii=False, sort_keys=True)),
        )
        connection.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        connection.commit()
    finally:
        connection.close()


def submit_request(project_root: Path, request: dict[str, Any], actor: str = "orchestrator") -> bool:
    """Queue one bounded, project-local delegation request; duplicate retries are harmless."""
    if actor != "orchestrator" or not _valid_request(request):
        raise ValueError("only the orchestrator may submit a valid delegation request")
    _reject_secret_fields(request)
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        cursor = connection.execute(
            "INSERT INTO delegation_requests(idempotency_key, session_id, agent, payload_json) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(idempotency_key) DO NOTHING",
            (request["idempotency_key"], request["session_id"], request["agent"], json.dumps(request, ensure_ascii=False, sort_keys=True)),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def pending_requests(project_root: Path, session_id: str) -> list[dict[str, Any]]:
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        rows = connection.execute(
            "SELECT request.idempotency_key, request.agent, request.payload_json, request.status, request.created_at "
            "FROM delegation_requests AS request WHERE request.session_id=? "
            "AND request.status IN ('pending', 'dispatched') "
            "AND NOT EXISTS (SELECT 1 FROM result_outbox AS result WHERE result.request_id=request.idempotency_key) "
            "ORDER BY request.id", (session_id,)
        ).fetchall()
    finally:
        connection.close()
    return [{"idempotency_key": row["idempotency_key"], "agent": row["agent"], "status": row["status"], "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]} for row in rows]


def mark_request_dispatched(project_root: Path, idempotency_key: str, actor: str = "orchestrator") -> bool:
    """Record one hand-off without changing the request's immutable scope payload."""
    if actor != "orchestrator" or not _safe_identifier(idempotency_key):
        raise ValueError("only the orchestrator may dispatch a safe request identifier")
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            row = connection.execute(
                "SELECT status FROM delegation_requests WHERE idempotency_key=?", (idempotency_key,)
            ).fetchone()
            if row is None:
                raise KeyError(idempotency_key)
            if row["status"] == "dispatched":
                return False
            connection.execute(
                "UPDATE delegation_requests SET status='dispatched', dispatched_at=CURRENT_TIMESTAMP WHERE idempotency_key=?",
                (idempotency_key,),
            )
        return True
    finally:
        connection.close()


def submit_result(project_root: Path, result: dict[str, Any]) -> bool:
    """Durably enqueue a specialist result. Duplicate retries are harmless."""
    required = {"idempotency_key", "request_id", "session_id", "agent", "summary", "artifacts", "findings", "decisions"}
    if not isinstance(result, dict) or set(result) != required:
        raise ValueError("result does not satisfy the delegation-result contract")
    if not all(_safe_identifier(result[field]) for field in ("idempotency_key", "request_id", "session_id")) or not isinstance(result["summary"], str) or not result["summary"].strip():
        raise ValueError("result does not satisfy the delegation-result contract")
    if result["agent"] not in CANONICAL_AGENTS - {"orchestrator"} or not _valid_result_items(result):
        raise ValueError("result does not satisfy the delegation-result contract")
    _reject_secret_fields(result)
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            request = connection.execute(
                "SELECT session_id, agent, status FROM delegation_requests WHERE idempotency_key=?", (result["request_id"],)
            ).fetchone()
            if request is None or request["status"] != "dispatched":
                raise ValueError("result requires a matching dispatched delegation request")
            if request["session_id"] != result["session_id"] or request["agent"] != result["agent"]:
                raise ValueError("result does not match the delegated session or agent")
            cursor = connection.execute(
                "INSERT INTO result_outbox(idempotency_key, request_id, session_id, agent, payload_json) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(idempotency_key) DO NOTHING",
                (result["idempotency_key"], result["request_id"], result["session_id"], result["agent"], json.dumps(result, ensure_ascii=False, sort_keys=True)),
            )
        return cursor.rowcount == 1
    finally:
        connection.close()


def acknowledge_result(project_root: Path, idempotency_key: str, actor: str = "orchestrator") -> bool:
    """Atomically persist a queued result and mark it acknowledged by the orchestrator."""
    if actor != "orchestrator" or not _safe_identifier(idempotency_key):
        raise ValueError("only the orchestrator may acknowledge a safe result identifier")
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            row = connection.execute(
                "SELECT session_id, agent, payload_json, status FROM result_outbox WHERE idempotency_key=?", (idempotency_key,)
            ).fetchone()
            if row is None:
                raise KeyError(idempotency_key)
            if row["status"] == "acknowledged":
                return False
            payload = json.loads(row["payload_json"])
            connection.execute(
                "INSERT INTO records(session_id, kind, actor, summary, evidence_json) VALUES (?, ?, ?, ?, ?)",
                (row["session_id"], "agent-result", actor, payload["summary"], row["payload_json"]),
            )
            connection.execute(
                "UPDATE result_outbox SET status='acknowledged', acknowledged_at=CURRENT_TIMESTAMP WHERE idempotency_key=?",
                (idempotency_key,),
            )
            connection.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (row["session_id"],))
        return True
    finally:
        connection.close()


def pending_results(project_root: Path, session_id: str) -> list[dict[str, Any]]:
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        rows = connection.execute(
            "SELECT idempotency_key, agent, payload_json, created_at FROM result_outbox "
            "WHERE session_id=? AND status='pending' ORDER BY id", (session_id,)
        ).fetchall()
    finally:
        connection.close()
    return [{"idempotency_key": row["idempotency_key"], "agent": row["agent"], "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]} for row in rows]


def restore(project_root: Path, session_id: str) -> dict[str, Any]:
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        session = connection.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if session is None:
            raise KeyError(session_id)
        rows = connection.execute(
            "SELECT kind, actor, summary, evidence_json, created_at FROM records WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        failures = connection.execute(
            "SELECT idempotency_key, incident_id, taxonomy, guard, evidence_artifact, policy, status, created_at "
            "FROM guard_failures WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        outcomes = connection.execute(
            "SELECT idempotency_key, failure_key, guard, outcome, attempt, evidence_artifact, created_at "
            "FROM guard_outcomes WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        lifecycle = connection.execute(
            "SELECT task_package, next_action, status, started_at, resumed_at FROM task_lifecycles WHERE session_id=?", (session_id,)
        ).fetchone()
        steps = connection.execute(
            "SELECT step_id, status, closure_artifact, closure_reason FROM task_steps WHERE session_id=? ORDER BY rowid", (session_id,)
        ).fetchall()
    finally:
        connection.close()
    return {
        "session": dict(session),
        "records": [{**dict(row), "evidence": json.loads(row["evidence_json"])} for row in rows],
        "guard_failures": [dict(row) for row in failures],
        "guard_outcomes": [dict(row) for row in outcomes],
        "lifecycle": dict(lifecycle) if lifecycle is not None else None,
        "steps": [dict(row) for row in steps],
    }


def _persist_guard_failure(
    project_root: Path,
    session_id: str,
    idempotency_key: str,
    incident_id: str,
    taxonomy: str,
    guard: str,
    evidence_artifact: str,
    policy: str,
) -> dict[str, Any]:
    """Private Socrates persistence primitive; public callers use socrates.py."""
    if (
        not all(_safe_identifier(value) for value in (session_id, idempotency_key, incident_id, taxonomy, guard))
        or not _safe_path_reference(evidence_artifact)
        or policy not in {"block", "retry-then-escalate"}
    ):
        raise ValueError("Guard failure is invalid")
    root = project_root.resolve()
    artifact_path = (root / evidence_artifact).resolve()
    if not artifact_path.is_file() or root not in artifact_path.parents:
        raise ValueError("Guard failure evidence artifact must exist below the project root")
    connection = connect(root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            existing = connection.execute(
                "SELECT failure.idempotency_key, failure.session_id, failure.incident_id, failure.taxonomy, failure.guard, failure.evidence_artifact, "
                "failure.policy, failure.status, outcome.idempotency_key AS outcome_key, outcome.outcome, outcome.attempt "
                "FROM guard_failures AS failure LEFT JOIN guard_outcomes AS outcome ON outcome.failure_key=failure.idempotency_key "
                "WHERE failure.idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                return {"created": False, "failure": _guard_failure_payload(existing)}
            session = connection.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone()
            if session is None:
                raise KeyError(session_id)
            active_incident = connection.execute(
                "SELECT incident_id FROM guard_incidents WHERE session_id=? AND guard=? AND status='retrying'",
                (session_id, guard),
            ).fetchone()
            if active_incident is not None and active_incident["incident_id"] != incident_id:
                raise ValueError("a retry must retain the active Guard incident id")
            prior_failures = connection.execute(
                "SELECT COUNT(*) FROM guard_failures WHERE session_id=? AND incident_id=? AND taxonomy=? AND guard=?",
                (session_id, incident_id, taxonomy, guard),
            ).fetchone()[0]
            attempt = int(prior_failures) + 1
            outcome = "block" if policy == "block" else ("retry" if attempt < 3 else "escalate")
            status = {"retry": "retrying", "block": "blocked", "escalate": "escalated"}[outcome]
            connection.execute(
                "INSERT INTO guard_failures(idempotency_key, session_id, incident_id, taxonomy, guard, evidence_artifact, policy, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (idempotency_key, session_id, incident_id, taxonomy, guard, evidence_artifact, policy, status),
            )
            outcome_key = f"{idempotency_key}.outcome"
            connection.execute(
                "INSERT INTO guard_outcomes(idempotency_key, failure_key, session_id, guard, outcome, attempt, evidence_artifact) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (outcome_key, idempotency_key, session_id, guard, outcome, attempt, evidence_artifact),
            )
            connection.execute(
                "INSERT INTO guard_incidents(session_id, guard, incident_id, status) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(session_id, guard, incident_id) DO UPDATE SET status=excluded.status",
                (session_id, guard, incident_id, status),
            )
            connection.execute(
                "INSERT INTO guard_trace_outbox(failure_key, event_json) VALUES (?, ?)",
                (
                    idempotency_key,
                    json.dumps(
                        {"idempotency_key": idempotency_key, "kind": "guard-failure", "gate": guard,
                         "task_id": session_id, "status": status, "artifacts": [evidence_artifact]},
                        ensure_ascii=False, sort_keys=True,
                    ),
                ),
            )
            connection.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            row = connection.execute(
                "SELECT failure.idempotency_key, failure.session_id, failure.incident_id, failure.taxonomy, failure.guard, failure.evidence_artifact, "
                "failure.policy, failure.status, outcome.idempotency_key AS outcome_key, outcome.outcome, outcome.attempt "
                "FROM guard_failures AS failure JOIN guard_outcomes AS outcome ON outcome.failure_key=failure.idempotency_key "
                "WHERE failure.idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
        return {"created": True, "failure": _guard_failure_payload(row)}
    finally:
        connection.close()


def _guard_failure_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "idempotency_key": row["idempotency_key"],
        "session_id": row["session_id"],
        "incident_id": row["incident_id"],
        "taxonomy": row["taxonomy"],
        "guard": row["guard"],
        "evidence_artifact": row["evidence_artifact"],
        "policy": row["policy"],
        "status": row["status"],
        "outcome": row["outcome"],
        "attempt": row["attempt"],
        "outcome_idempotency_key": row["outcome_key"],
    }


def pending_guard_traces(project_root: Path) -> list[dict[str, Any]]:
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        rows = connection.execute(
            "SELECT failure_key, event_json FROM guard_trace_outbox WHERE status='pending' ORDER BY created_at"
        ).fetchall()
        return [{"failure_key": row["failure_key"], "event": json.loads(row["event_json"])} for row in rows]
    finally:
        connection.close()


def mark_guard_trace_delivered(project_root: Path, failure_key: str) -> bool:
    if not _safe_identifier(failure_key):
        raise ValueError("Guard trace failure key must be safe")
    connection = connect(project_root, create=False)
    try:
        _require_current_schema_connection(connection)
        with connection:
            cursor = connection.execute(
                "UPDATE guard_trace_outbox SET status='delivered', delivered_at=CURRENT_TIMESTAMP "
                "WHERE failure_key=? AND status='pending'",
                (failure_key,),
            )
        return cursor.rowcount == 1
    finally:
        connection.close()


def _reject_secret_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = "".join(character for character in str(key).lower() if character.isalnum())
            if any(marker in normalized for marker in SECRET_FIELD_MARKERS):
                raise ValueError("memory payload must not contain a secret-like field")
            _reject_secret_fields(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_secret_fields(item)
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
        raise ValueError("memory payload must not contain a secret-like value")


def _valid_result_items(result: dict[str, Any]) -> bool:
    artifacts = result["artifacts"]
    findings = result["findings"]
    decisions = result["decisions"]
    if not all(isinstance(items, list) for items in (artifacts, findings, decisions)):
        return False
    return (
        all(isinstance(item, dict) and set(item) == {"path"} and _safe_path_reference(item["path"]) for item in artifacts)
        and all(_valid_index_item(item) for item in findings)
        and all(_valid_index_item(item) for item in decisions)
    )


def _valid_request(request: Any) -> bool:
    required = {"idempotency_key", "session_id", "agent", "task_id", "scope_artifact", "input_artifacts", "required_outputs"}
    return (
        isinstance(request, dict)
        and set(request) == required
        and all(_safe_identifier(request[field]) for field in ("idempotency_key", "session_id", "task_id"))
        and _safe_path_reference(request["scope_artifact"])
        and request["agent"] in CANONICAL_AGENTS - {"orchestrator"}
        and all(isinstance(items, list) and len(items) == len(set(items)) and all(_safe_path_reference(item) for item in items) for items in (request["input_artifacts"], request["required_outputs"]))
    )


def _valid_index_item(item: Any) -> bool:
    return (
        isinstance(item, dict)
        and set(item) == {"id", "status", "references"}
        and _safe_identifier(item["id"])
        and _safe_identifier(item["status"])
        and isinstance(item["references"], list)
        and len(item["references"]) == len(set(item["references"]))
        and all(_safe_path_reference(reference) for reference in item["references"])
    )


def _safe_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(SAFE_IDENTIFIER.fullmatch(value)) and not any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)


def _safe_path_reference(value: Any) -> bool:
    return isinstance(value, str) and bool(SAFE_PATH_REFERENCE.fullmatch(value)) and not any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)
