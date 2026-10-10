from __future__ import annotations

import json
from pathlib import Path

from .distribution import default_fabric_home, project_status, release_path


def guard_definition(project_root: Path, guard_id: str, fabric_home: Path | None = None) -> dict[str, str]:
    """Read one immutable Guard policy from the release pinned by a project."""
    root = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    status = project_status(root, home)
    if status.get("status") != "bound":
        raise ValueError("A Guard requires a bound project")
    binding_path = root / ".agent-fabric" / "fabric-binding.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    registry_path = release_path(home, binding["fabric_release"]) / "core" / "guards.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Guard registry is invalid: {registry_path}") from error
    if not isinstance(registry, dict) or registry.get("schema_version") != 1 or not isinstance(registry.get("guards"), list):
        raise ValueError("Guard registry must use schema version 1")
    for item in registry["guards"]:
        if (
            isinstance(item, dict)
            and set(item) == {"id", "taxonomy", "policy"}
            and item.get("id") == guard_id
            and isinstance(item.get("taxonomy"), str)
            and item.get("policy") in {"block", "retry-then-escalate"}
        ):
            return {"id": item["id"], "taxonomy": item["taxonomy"], "policy": item["policy"]}
    raise ValueError(f"Unknown immutable Guard: {guard_id}")
