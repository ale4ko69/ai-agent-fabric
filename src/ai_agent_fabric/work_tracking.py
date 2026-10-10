from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .project_state import state_path


PROVIDERS = {"none", "project-adapter"}
ADAPTER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
ACTIONS = {"read", "comment", "transition", "create"}


def default_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": "none",
        "enabled": False,
        "write_policy": {"require_user_approval": True, "allowed_actions": ["read"]},
    }


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise ValueError("work-tracking configuration must be an object")
    allowed_fields = {"schema_version", "provider", "adapter", "enabled", "write_policy", "content", "workflow"}
    if set(config) - allowed_fields:
        raise ValueError("work-tracking configuration contains undeclared fields")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    if config.get("provider") not in PROVIDERS:
        raise ValueError("provider must be one of: none, project-adapter")
    adapter = config.get("adapter")
    if config["provider"] == "project-adapter":
        if not isinstance(adapter, dict) or set(adapter) != {"id"} or not isinstance(adapter.get("id"), str) or not ADAPTER_ID_PATTERN.fullmatch(adapter["id"]):
            raise ValueError("project-adapter requires a safe project-owned adapter id")
    elif adapter is not None:
        raise ValueError("adapter is allowed only for provider project-adapter")
    if not isinstance(config.get("enabled"), bool):
        raise ValueError("enabled must be boolean")
    policy = config.get("write_policy")
    if not isinstance(policy, dict) or set(policy) != {"require_user_approval", "allowed_actions"} or not isinstance(policy.get("require_user_approval"), bool):
        raise ValueError("write_policy.require_user_approval must be boolean")
    actions = policy.get("allowed_actions")
    if not isinstance(actions, list) or len(actions) != len(set(actions)) or any(action not in ACTIONS for action in actions):
        raise ValueError("write_policy.allowed_actions contains an unsupported action")
    for optional_object in ("content", "workflow"):
        if optional_object in config and not isinstance(config[optional_object], dict):
            raise ValueError(f"{optional_object} must be an object")
    serialized = json.dumps(config).lower()
    if any(marker in serialized for marker in ("token", "password", "secret", "api_key")):
        raise ValueError("work-tracking configuration must not contain secrets")


def load_config(project_root: Path) -> dict[str, Any]:
    path = state_path(project_root, "config/work-tracking.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config
