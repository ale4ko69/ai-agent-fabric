from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CANONICAL_GATES = {
    "intake": "task-accepted",
    "discovery": "research-complete",
    "plan-freshness": "implementation-ready",
    "scope": "implementation-continues",
    "review": "review-complete",
    "validation": "task-close-ready",
    "close-out": "archived",
    "resume": "resumed",
}


def default_gates() -> dict[str, object]:
    """Portable gate semantics. Project commands and thresholds remain profile data."""
    return {
        "schema_version": 1,
        "gates": [
            _gate("intake", "task-accepted", ["task-classification", "task-state"]),
            _gate("discovery", "research-complete", ["source-evidence"]),
            _gate("plan-freshness", "implementation-ready", ["approved-plan", "current-evidence", "opponent-verdict"]),
            _gate("scope", "implementation-continues", ["approved-spec", "scope-check"]),
            _gate("review", "review-complete", ["changed-artifacts", "review-result"]),
            _gate("validation", "task-close-ready", ["validation-evidence"]),
            _gate("close-out", "archived", ["close-out-evidence", "archive-record"]),
            _gate("resume", "resumed", ["task-state", "memory-restore"]),
        ],
    }


def _gate(gate_id: str, transition: str, evidence: list[str]) -> dict[str, object]:
    return {"id": gate_id, "transition": transition, "evidence": evidence}


def validate_gates(registry: dict[str, Any]) -> None:
    """Validate the complete immutable gate contract of one Fabric release."""
    if not isinstance(registry, dict) or set(registry) != {"schema_version", "gates"}:
        raise ValueError("gate registry must use the declared object shape")
    if type(registry.get("schema_version")) is not int or registry["schema_version"] != 1 or not isinstance(registry.get("gates"), list):
        raise ValueError("gate registry must declare schema_version 1 and gates")
    gates = registry["gates"]
    by_id: dict[str, dict[str, Any]] = {}
    for gate in gates:
        if not isinstance(gate, dict) or set(gate) != {"id", "transition", "evidence"}:
            raise ValueError("each gate must declare id, transition, and evidence")
        gate_id = gate["id"]
        evidence = gate["evidence"]
        if not isinstance(gate_id, str) or gate_id in by_id:
            raise ValueError("gate identifiers must be unique strings")
        if gate.get("transition") != CANONICAL_GATES.get(gate_id):
            raise ValueError(f"gate has an invalid transition: {gate_id}")
        if not isinstance(evidence, list) or not evidence or len(evidence) != len(set(evidence)) or any(not isinstance(item, str) or not item.strip() for item in evidence):
            raise ValueError(f"gate has invalid evidence requirements: {gate_id}")
        by_id[gate_id] = gate
    if set(by_id) != set(CANONICAL_GATES):
        raise ValueError("gate registry must define exactly the canonical Fabric gates")


def load_gates(path: Path) -> dict[str, Any]:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to load gate registry: {path}") from error
    if not isinstance(registry, dict):
        raise ValueError("gate registry must be a JSON object")
    validate_gates(registry)
    return registry


def validate_checkpoint(registry: dict[str, Any], gate_id: str, evidence: list[str]) -> dict[str, Any]:
    """Return a deterministic gate checkpoint or reject incomplete evidence."""
    validate_gates(registry)
    if not isinstance(gate_id, str) or not gate_id:
        raise ValueError("gate id must be a non-empty string")
    if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
        raise ValueError("checkpoint evidence must be a list of non-empty names")
    if len(evidence) != len(set(evidence)):
        raise ValueError("checkpoint evidence names must be unique")
    gate = next((item for item in registry["gates"] if item["id"] == gate_id), None)
    if gate is None:
        raise ValueError(f"unknown Fabric gate: {gate_id}")
    required = set(gate["evidence"])
    supplied = set(evidence)
    missing = sorted(required - supplied)
    if missing:
        raise ValueError(f"gate {gate_id} is missing evidence: {', '.join(missing)}")
    unexpected = sorted(supplied - required)
    if unexpected:
        raise ValueError(f"gate {gate_id} has unexpected evidence: {', '.join(unexpected)}")
    return {
        "gate": gate_id,
        "transition": gate["transition"],
        "required_evidence": sorted(required),
        "supplied_evidence": sorted(supplied),
    }
