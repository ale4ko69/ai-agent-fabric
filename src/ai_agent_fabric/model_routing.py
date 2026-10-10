from __future__ import annotations

import json
from typing import Any

from pathlib import Path

from .project_state import state_path


TIERS = {"economy", "standard", "deep"}
PRICE_POLICIES = {"minimize", "balanced", "quality-first"}
CANONICAL_ROLES = {"orchestrator", "explore", "plan", "opponent", "dev", "review", "validation"}


def default_routing() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "role_tiers": {
            "orchestrator": {"capability_floor": "standard", "cost_policy": "balanced", "allowed": ["standard", "deep"]},
            "explore": {"capability_floor": "standard", "cost_policy": "minimize", "allowed": ["standard", "deep"]},
            "plan": {"capability_floor": "deep", "cost_policy": "quality-first", "allowed": ["deep"]},
            "opponent": {"capability_floor": "standard", "cost_policy": "minimize", "allowed": ["standard", "deep"]},
            "dev": {"capability_floor": "standard", "cost_policy": "balanced", "allowed": ["standard", "deep"]},
            "review": {"capability_floor": "standard", "cost_policy": "minimize", "allowed": ["standard", "deep"]},
            "validation": {"capability_floor": "standard", "cost_policy": "minimize", "allowed": ["standard", "deep"]}
        }
    }


def validate_routing(routing: dict[str, Any]) -> None:
    if not isinstance(routing, dict):
        raise ValueError("routing must be an object")
    if set(routing) != {"schema_version", "role_tiers"}:
        raise ValueError("routing contains undeclared fields")
    if type(routing.get("schema_version")) is not int or routing["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    roles = routing.get("role_tiers")
    if not isinstance(roles, dict):
        raise ValueError("role_tiers must be an object")
    unknown = set(roles) - CANONICAL_ROLES
    missing = CANONICAL_ROLES - set(roles)
    if unknown or missing:
        details = []
        if unknown:
            details.append("unknown roles: " + ", ".join(sorted(unknown)))
        if missing:
            details.append("missing roles: " + ", ".join(sorted(missing)))
        raise ValueError("routing must define exactly the canonical roles (" + "; ".join(details) + ")")
    for role, policy in roles.items():
        if not isinstance(policy, dict):
            raise ValueError(f"role policy must be an object: {role}")
        if set(policy) != {"capability_floor", "cost_policy", "allowed"}:
            raise ValueError(f"role policy contains undeclared fields: {role}")
        floor = policy.get("capability_floor")
        cost_policy = policy.get("cost_policy")
        allowed = policy.get("allowed")
        if floor not in TIERS or cost_policy not in PRICE_POLICIES or not isinstance(allowed, list) or len(allowed) != len(set(allowed)) or floor not in allowed or any(tier not in TIERS for tier in allowed):
            raise ValueError(f"invalid tier policy: {role}")


def load_routing(project_root: Path) -> dict[str, Any]:
    path = state_path(project_root, "config/model-routing.json")
    routing = json.loads(path.read_text(encoding="utf-8"))
    validate_routing(routing)
    return routing
