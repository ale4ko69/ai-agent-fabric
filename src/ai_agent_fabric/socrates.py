"""The single write boundary for one task-local Socrates lifecycle.

Specialists return artifacts to Socrates; they never select Guard policy, mutate a
checklist, or write durable Fabric state themselves.  Client adapters invoke these
operations only while executing the task's Socrates instruction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .guards import guard_definition
from .memory import _persist_guard_failure, advance_task_step


def record_guard_failure(
    project_root: Path,
    session_id: str,
    idempotency_key: str,
    incident_id: str,
    guard_id: str,
    evidence_artifact: str,
    fabric_home: Path | None = None,
) -> dict[str, Any]:
    """Apply the bound release's immutable Guard definition to a real failure."""
    definition = guard_definition(project_root, guard_id, fabric_home)
    return _persist_guard_failure(
        project_root,
        session_id,
        idempotency_key,
        incident_id,
        definition["taxonomy"],
        definition["id"],
        evidence_artifact,
        definition["policy"],
    )


def transition_step(
    project_root: Path, session_id: str, step_id: str, status: str,
    closure_artifact: str | None = None, closure_reason: str | None = None,
) -> dict[str, Any]:
    """Advance the Socrates-owned durable checklist in declared workflow order."""
    return advance_task_step(project_root, session_id, step_id, status, closure_artifact, closure_reason)


def record_harness_signal(
    project_root: Path, category: str, task_id: str | None = None, artifact: str | None = None
) -> dict[str, str | None]:
    """Socrates-only entry point for behavioural retrospective signals."""
    from .harness import _record_signal

    return _record_signal(project_root, category, task_id, artifact)
