from __future__ import annotations


def default_profiles() -> dict[str, object]:
    """Return the one machine-readable source for baseline agent semantics."""
    return {
        "schema_version": 1,
        "profiles": [
            _profile("orchestrator", "Socrates", "Coordinates task state and delegation.", "always", ["read", "bash", "memory-write"], "standard", "balanced"),
            _profile("explore", "Aristotle", "Builds evidence-backed usage and dependency maps.", "always", ["read", "search", "bash-read-only"], "standard", "balanced"),
            _profile("plan", "Plato", "Builds bounded implementation and validation plans.", "always", ["read", "search", "write-task-artifact"], "deep", "quality-first"),
            _profile("opponent", "Kepler", "Independently challenges evidence and plans without expanding scope.", "always", ["read", "search"], "standard", "minimize"),
            _profile("dev", "Heracles", "Implements approved scoped changes.", "always", ["read", "edit", "search", "bash"], "standard", "balanced"),
            _profile("review", "Athena", "Reviews changed work against evidence and acceptance criteria.", "always", ["read", "search", "bash-read-only"], "standard", "balanced"),
            _profile("validation", "Euclid", "Validates declared contracts and assertions when the project enables it.", "project-capability", ["read", "search", "bash-read-only"], "standard", "minimize"),
        ],
    }


def default_capabilities() -> dict[str, object]:
    """Return declarative target requirements, not a snapshot of the current host."""
    return {
        "schema_version": 1,
        "requirements": {"bash": "optional", "python": "required", "git": "required"},
        "enabled_packs": [],
    }


def _profile(
    role_id: str,
    persona: str,
    purpose: str,
    activation: str,
    capabilities: list[str],
    capability_floor: str,
    cost_policy: str,
) -> dict[str, object]:
    return {
        "id": role_id,
        "persona": persona,
        "purpose": purpose,
        "activation": activation,
        "capabilities": capabilities,
        "model_policy": {"capability_floor": capability_floor, "cost_policy": cost_policy},
    }
