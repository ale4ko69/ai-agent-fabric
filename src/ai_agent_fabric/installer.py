from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
import re

from .environment import Environment, command_is_allowed, detect_environment
from .project_state import state_path



PROFILE = {
    "schema_version": 3,
    "project_name": "",
    "commands": {},
    "integrations": {"work_tracking": ".agent-fabric/config/work-tracking.json"},
    "task_specs": {"root": "docs/specs"},
    "fabric": {"binding": ".agent-fabric/fabric-binding.json"},
    "memory": {"retention": "project-local"},
    "secrets": {"allowed_root": ".agent-fabric/secrets"},
}

SECRET_VALUE_PATTERNS = (
    re.compile(r"(?:^|[^a-z0-9])(sk-[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|xox[baprs]-[a-z0-9-]{10,}|akia[0-9a-z]{16})(?:$|[^a-z0-9])", re.IGNORECASE),
    re.compile(r"eyj[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bbearer\s+[a-z0-9._~+/-]{12,}", re.IGNORECASE),
)


def default_project_profile(name: str) -> dict[str, object]:
    """Return only project-owned configuration; shared roles remain in the Fabric release."""
    profile = json.loads(json.dumps(PROFILE))
    profile["project_name"] = name
    return profile


def validate_project_profile(profile: dict[str, object]) -> None:
    """Validate the portable, machine-readable project profile boundary."""
    if not isinstance(profile, dict):
        raise ValueError("project profile must be an object")
    expected_fields = {"schema_version", "project_name", "commands", "integrations", "task_specs", "fabric", "memory", "secrets"}
    if set(profile) != expected_fields:
        raise ValueError("project profile contains undeclared fields")
    if type(profile.get("schema_version")) is not int or profile["schema_version"] != 3 or not isinstance(profile.get("project_name"), str) or not profile["project_name"].strip():
        raise ValueError("project profile must declare schema_version 3 and project_name")
    _reject_secret_text(profile["project_name"], "project name")
    if not isinstance(profile.get("commands"), dict):
        raise ValueError("project profile commands must be an object")
    for command_name, declaration in profile["commands"].items():
        if not isinstance(command_name, str) or not isinstance(declaration, dict) or set(declaration) != {"family", "command"}:
            raise ValueError("each project command must declare family and command")
        if declaration["family"] not in {"python", "bash"} or not isinstance(declaration["command"], str) or not declaration["command"].strip():
            raise ValueError("project command family must be python or bash with a non-empty command")
        _reject_secret_text(command_name, "project command name")
        _reject_secret_text(declaration["command"], "project command")
    integrations = profile.get("integrations")
    if integrations != {"work_tracking": ".agent-fabric/config/work-tracking.json"}:
        raise ValueError("project profile must use the canonical work-tracking config path")
    _reject_secret_text(integrations["work_tracking"], "work-tracking path")
    task_specs = profile.get("task_specs")
    if not isinstance(task_specs, dict) or set(task_specs) != {"root"} or not _safe_relative_path(task_specs["root"]):
        raise ValueError("project profile task_specs must declare root")
    _reject_secret_text(task_specs["root"], "task-spec root")
    fabric = profile.get("fabric")
    if not isinstance(fabric, dict) or fabric != {"binding": ".agent-fabric/fabric-binding.json"}:
        raise ValueError("project profile must reference the standard Fabric binding")
    memory = profile.get("memory")
    if not isinstance(memory, dict) or memory != {"retention": "project-local"}:
        raise ValueError("project profile memory must remain project-local")
    secrets = profile.get("secrets")
    if not isinstance(secrets, dict) or set(secrets) != {"allowed_root"} or not _safe_relative_path(secrets["allowed_root"]):
        raise ValueError("project profile secrets must declare allowed_root")
    _reject_secret_text(secrets["allowed_root"], "secret root")


def _safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    windows_path = PureWindowsPath(value)
    return not path.is_absolute() and not windows_path.is_absolute() and not windows_path.root and ".." not in path.parts and ".." not in windows_path.parts


def _reject_secret_text(value: str, label: str) -> None:
    if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
        raise ValueError(f"project profile {label} must not contain a secret-like value")


def load_project_profile(project_root: Path) -> dict[str, object]:
    path = state_path(project_root, "profile.json")
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid project profile: {path}") from error
    if not isinstance(profile, dict):
        raise ValueError(f"Invalid project profile: {path}")
    validate_project_profile(profile)
    return profile


def resolve_project_command(profile: dict[str, object], command_name: str, environment: Environment | None = None) -> dict[str, str]:
    """Resolve one declared command only after its shell family is available."""
    validate_project_profile(profile)
    commands = profile["commands"]
    if not isinstance(command_name, str) or command_name not in commands:
        raise KeyError(f"Project command is not declared: {command_name}")
    declaration = commands[command_name]
    if not isinstance(declaration, dict):
        raise ValueError(f"Project command declaration is invalid: {command_name}")
    current = environment or detect_environment()
    family = declaration["family"]
    if not command_is_allowed(family, current):
        raise ValueError(f"Project command {command_name} requires unavailable {family} on {current.kind}")
    return {"name": command_name, "family": family, "command": declaration["command"], "host": current.kind}


def initialize_project(target: Path, name: str, client: str = "auto") -> list[Path]:
    raise RuntimeError(
        "Direct project initialization is retired because it bypasses the Fabric release binding. "
        "Use `ai-agent-fabric project init <target> --client <client> --preview` first."
    )


def preview_project(target: Path, client: str = "auto") -> list[Path]:
    raise RuntimeError(
        "Direct project initialization preview is retired. "
        "Use `ai-agent-fabric project init <target> --client <client> --preview`."
    )
