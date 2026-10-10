from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from .environment import Environment, detect_environment
from .project_state import state_path


REQUIREMENT_VALUES = {"required", "optional", "forbidden"}
PACKS = {"documentation", "ui-ux", "ui-verification", "validation", "knowledge-publication"}


def validate_capabilities(config: dict[str, Any]) -> None:
    if not isinstance(config, dict) or set(config) != {"schema_version", "requirements", "enabled_packs"}:
        raise ValueError("capabilities must use the declared object shape")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    requirements = config.get("requirements")
    if not isinstance(requirements, dict) or set(requirements) != {"bash", "python", "git"}:
        raise ValueError("requirements must declare bash, python, and git")
    if any(value not in REQUIREMENT_VALUES for value in requirements.values()):
        raise ValueError("requirements contain an unsupported value")
    packs = config.get("enabled_packs")
    if not isinstance(packs, list) or any(pack not in PACKS for pack in packs) or len(set(packs)) != len(packs):
        raise ValueError("enabled_packs contain an unsupported or duplicate pack")


def load_capabilities(project_root: Path) -> dict[str, Any]:
    path = state_path(project_root, "config/capabilities.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_capabilities(config)
    return config


def available_capabilities(environment: Environment | None = None) -> dict[str, bool]:
    current = environment or detect_environment()
    return {
        "bash": current.bash_path is not None,
        "python": current.python_available,
        "git": shutil.which("git") is not None,
    }


def unmet_requirements(config: dict[str, Any], environment: Environment | None = None) -> list[str]:
    validate_capabilities(config)
    available = available_capabilities(environment)
    return [name for name, policy in config["requirements"].items() if policy == "required" and not available[name]]
