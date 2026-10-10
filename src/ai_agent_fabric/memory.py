from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .project_state import state_path


SECRET_FIELD_MARKERS = {"token", "password", "secret", "apikey", "authorization", "credential", "privatekey"}
CANONICAL_AGENTS = {"orchestrator", "explore", "plan", "opponent", "dev", "review", "validation"}
MEMORY_SCHEMA_VERSION = 2
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
    required_tables = {"sessions", "records", "delegation_requests", "result_outbox"}
    if not required_tables.issubset(tables):
        raise ValueError("Project memory schema requires migration; run `memory init <project> --home <fabric-home>` explicitly")
    result_columns = {row["name"] for row in connection.execute("PRAGMA table_info(result_outbox)")}
    if "request_id" not in result_columns:
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
    finally:
        connection.close()
    return {"session": dict(session), "records": [{**dict(row), "evidence": json.loads(row["evidence_json"])} for row in rows]}


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
