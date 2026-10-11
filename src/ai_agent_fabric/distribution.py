from __future__ import annotations

import base64
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
import platform
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any

from .clients import SUPPORTED_CLIENTS
from .agent_profiles import default_capabilities, default_profiles
from .capabilities import load_capabilities
from .gates import default_gates, validate_gates
from .installer import default_project_profile, validate_project_profile
from .memory import MEMORY_SCHEMA_VERSION, initialize, schema_version
from .model_routing import default_routing, load_routing
from .work_tracking import default_config, load_config
from .environment import detect_environment
from .project_state import state_directory, state_path


INSTALLATION_FILE = "installation.json"
RELEASE_MANIFEST_FILE = "release-manifest.json"
PROJECT_BINDING_FILE = "fabric-binding.json"
PROJECT_UPDATE_FILE = "pending-update.json"
CLIENT_RECORD_DIRECTORY = "clients"
CODEX_SKILL_NAMES = ("work", "start", "restore", "harness", "guards")
VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]*$")
SECRET_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]{0,127}$")
MANAGED_BLOCK_BEGIN = "<!-- AI-Agent-Fabric: begin -->"
MANAGED_BLOCK_END = "<!-- AI-Agent-Fabric: end -->"
MANAGED_BLOCK_PATTERN = re.compile(
    rf"(?ms)^{re.escape(MANAGED_BLOCK_BEGIN)}\r?\n.*?^{re.escape(MANAGED_BLOCK_END)}\r?\n?"
)
RELEASE_ASSETS = (
    ".codex-plugin",
    "hooks",
    "README.md",
    "pyproject.toml",
    "src",
    "core",
    "schemas",
    "scripts",
    "skills",
    "docs/agents",
    "docs/architecture.md",
    "docs/agent-clients.md",
    "docs/client-adapter-evidence.md",
    "docs/delegation.md",
    "docs/execution-policy.md",
    "docs/gates.md",
    "docs/global-distribution.md",
    "docs/guards.md",
    "docs/harness.md",
    "docs/using-fabric.md",
    "docs/manifests.md",
    "docs/memory.md",
    "docs/model-routing.md",
    "docs/planning-policy.md",
    "docs/project-profile.md",
    "docs/project-onboarding.md",
    "docs/security",
    "docs/task-artifacts.md",
    "docs/task-specs.md",
    "docs/validation-matrix.md",
    "docs/workflow.md",
    "docs/integrations",
)


def default_fabric_home(environment: dict[str, str] | None = None) -> Path:
    """Return the per-user installation root without creating it."""
    override = os.environ.get("AI_AGENT_FABRIC_HOME")
    if override:
        return Path(override).expanduser()
    system = (environment or {}).get("system", platform.system().lower()).lower()
    if system == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "AI-Agent-Fabric"
        return Path.home() / "AppData" / "Local" / "AI-Agent-Fabric"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    return Path(xdg_data_home) / "ai-agent-fabric" if xdg_data_home else Path.home() / ".local" / "share" / "ai-agent-fabric"


def adapter_manifest(client: str) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: {client}")
    manifests: dict[str, dict[str, Any]] = {
        "codex": {
            "schema_version": 3,
            "client": "codex",
            "surface": "codex local runtime",
            "loading": {
                "mode": "ordered",
                "sequence": ["global-bootstrap", "project-overlay", "task-package"],
            },
            "entry_points": [
                {"scope": "user", "path": "~/.codex/AGENTS.md", "purpose": "global-bootstrap"},
            ],
            "project_overlay": {"path": ".agent-fabric/project-overlay.md", "loader": "global-bootstrap"},
            "delivery": {"default": "managed-block", "supported": ["symlink", "wrapper", "managed-block"]},
            "lifecycle": {"preview": True, "backup": True, "rollback": True, "uninstall": True},
            "hooks": {
                "mode": "adapter",
                "events": ["session-start"],
                "implementation": {
                    "client_version": "Codex plugin hooks",
                    "hook_point": "SessionStart",
                    "handler": "hooks/codex_session_start.py",
                    "delivery": "plugin",
                    "ownership_record": "client-record",
                    "rollback": True,
                    "uninstall": True,
                },
            },
        },
        "copilot": {
            "schema_version": 3,
            "client": "copilot",
            "surface": "copilot CLI",
            "loading": {
                "mode": "combined",
                "sequence": ["global-bootstrap", "project-overlay", "task-package"],
            },
            "entry_points": [
                {"scope": "user", "path": "~/.copilot/copilot-instructions.md", "purpose": "global-bootstrap"},
            ],
            "project_overlay": {"path": ".agent-fabric/project-overlay.md", "loader": "global-bootstrap"},
            "delivery": {"default": "managed-block", "supported": ["symlink", "wrapper", "managed-block"]},
            "lifecycle": {"preview": True, "backup": True, "rollback": True, "uninstall": True},
            "hooks": {"mode": "unsupported", "events": []},
        },
        "claude": {
            "schema_version": 3,
            "client": "claude",
            "surface": "claude code local runtime",
            "loading": {
                "mode": "additive",
                "sequence": ["global-bootstrap", "project-overlay", "task-package"],
            },
            "entry_points": [
                {"scope": "user", "path": "~/.claude/CLAUDE.md", "purpose": "global-bootstrap"},
            ],
            "project_overlay": {"path": ".agent-fabric/project-overlay.md", "loader": "global-bootstrap"},
            "delivery": {"default": "import", "supported": ["import", "wrapper"]},
            "lifecycle": {"preview": True, "backup": True, "rollback": True, "uninstall": True},
            "hooks": {"mode": "unsupported", "events": []},
        },
    }
    manifest = manifests[client]
    validate_adapter_manifest(manifest)
    return manifest


def validate_adapter_manifest(manifest: dict[str, Any]) -> None:
    expected_fields = {"schema_version", "client", "surface", "loading", "entry_points", "project_overlay", "delivery", "lifecycle", "hooks"}
    if not isinstance(manifest, dict) or set(manifest) != expected_fields:
        raise ValueError("client adapter manifest must use the declared object shape")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 3 or manifest.get("client") not in SUPPORTED_CLIENTS:
        raise ValueError("invalid client adapter manifest identity")
    if not isinstance(manifest.get("surface"), str) or not manifest["surface"].strip():
        raise ValueError("client adapter manifest must name a surface")
    loading = manifest.get("loading")
    if not isinstance(loading, dict) or set(loading) != {"mode", "sequence"} or loading.get("mode") not in {"ordered", "combined", "additive"}:
        raise ValueError("client adapter manifest must define a loading mode")
    sequence = loading.get("sequence")
    valid_layers = {"managed", "user", "global-bootstrap", "project-overlay", "task-package"}
    if not isinstance(sequence, list) or len(sequence) < 2 or len(set(sequence)) != len(sequence) or any(layer not in valid_layers for layer in sequence):
        raise ValueError("client adapter manifest must define valid loading layers")
    entry_points = manifest.get("entry_points")
    if not isinstance(entry_points, list) or len(entry_points) != 1:
        raise ValueError("client adapter manifest must declare exactly one entry point")
    purposes = set()
    for entry_point in entry_points:
        if not isinstance(entry_point, dict) or set(entry_point) != {"scope", "path", "purpose"} or entry_point.get("scope") != "user":
            raise ValueError("client adapter manifest has invalid entry point scope")
        if not isinstance(entry_point.get("path"), str) or not entry_point["path"].strip():
            raise ValueError("client adapter manifest has invalid entry point path")
        purpose = entry_point.get("purpose")
        if purpose != "global-bootstrap":
            raise ValueError("client adapter manifest has invalid entry point purpose")
        purposes.add(purpose)
    if purposes != {"global-bootstrap"}:
        raise ValueError("client adapter manifest must declare exactly one global bootstrap entry point")
    project_overlay = manifest.get("project_overlay")
    if (
        not isinstance(project_overlay, dict)
        or set(project_overlay) != {"path", "loader"}
        or project_overlay.get("path") != ".agent-fabric/project-overlay.md"
        or project_overlay.get("loader") != "global-bootstrap"
    ):
        raise ValueError("client adapter manifest must declare the managed project overlay loader")
    delivery = manifest.get("delivery")
    if not isinstance(delivery, dict) or set(delivery) != {"default", "supported"} or delivery.get("default") not in {"symlink", "import", "wrapper", "managed-block", "unsupported"}:
        raise ValueError("client adapter manifest has invalid delivery")
    supported = delivery.get("supported")
    if not isinstance(supported, list) or len(supported) != len(set(supported)) or any(value not in {"symlink", "import", "wrapper", "managed-block"} for value in supported):
        raise ValueError("client adapter manifest has invalid supported delivery methods")
    if delivery["default"] != "unsupported" and delivery["default"] not in supported:
        raise ValueError("default delivery must be supported")
    lifecycle = manifest.get("lifecycle")
    if not isinstance(lifecycle, dict) or set(lifecycle) != {"preview", "backup", "rollback", "uninstall"} or lifecycle.get("preview") is not True or not all(isinstance(lifecycle.get(field), bool) for field in ("backup", "rollback", "uninstall")):
        raise ValueError("client adapter manifest must require preview")
    hooks = manifest.get("hooks")
    hook_events = {"session-start", "pre-tool-use", "post-tool-use", "checkpoint"}
    if not isinstance(hooks, dict) or hooks.get("mode") not in {"unsupported", "adapter"}:
        raise ValueError("client adapter manifest must explicitly declare hook support")
    events = hooks.get("events")
    if not isinstance(events, list) or len(events) != len(set(events)) or any(event not in hook_events for event in events):
        raise ValueError("client adapter manifest has invalid hook events")
    implementation = hooks.get("implementation")
    if hooks["mode"] == "unsupported" and (set(hooks) != {"mode", "events"} or events or implementation is not None):
        raise ValueError("unsupported hooks must not declare events or an implementation")
    if hooks["mode"] == "adapter":
        if not events:
            raise ValueError("adapter hooks must declare at least one event")
        if (
            not isinstance(implementation, dict)
            or set(hooks) != {"mode", "events", "implementation"}
            or set(implementation) != {"client_version", "hook_point", "handler", "delivery", "ownership_record", "rollback", "uninstall"}
            or not all(isinstance(implementation.get(field), str) and implementation[field] for field in ("client_version", "hook_point", "handler"))
            or implementation.get("delivery") not in {"symlink", "wrapper", "import", "plugin"}
            or implementation.get("ownership_record") != "client-record"
            or implementation.get("rollback") is not True
            or implementation.get("uninstall") is not True
        ):
            raise ValueError("adapter hooks require a concrete reversible implementation contract")


def installation_path(fabric_home: Path) -> Path:
    return fabric_home / INSTALLATION_FILE


def release_path(fabric_home: Path, version: str) -> Path:
    _validate_version(version)
    return fabric_home / "releases" / version


def load_installation(fabric_home: Path) -> dict[str, Any]:
    path = installation_path(fabric_home)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise FileNotFoundError(f"Fabric installation manifest does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Fabric installation manifest is invalid JSON: {path}") from error
    validate_installation_manifest(manifest)
    return manifest


def validate_installation_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "fabric_home", "current_release", "releases"}:
        raise ValueError("installation manifest must use the declared object shape")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("installation manifest schema_version must be 1")
    if not isinstance(manifest.get("fabric_home"), str) or not manifest["fabric_home"]:
        raise ValueError("installation manifest must declare fabric_home")
    releases = manifest.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ValueError("installation manifest must declare releases")
    versions = {entry.get("version") for entry in releases if isinstance(entry, dict)}
    if len(versions) != len(releases) or manifest.get("current_release") not in versions:
        raise ValueError("installation manifest has invalid release identities")
    for entry in releases:
        if not isinstance(entry, dict) or set(entry) != {"version", "path", "manifest_sha256"} or not isinstance(entry.get("version"), str) or not entry["version"] or not isinstance(entry.get("path"), str) or not entry["path"] or not re.fullmatch(r"[a-f0-9]{64}", str(entry.get("manifest_sha256", ""))):
            raise ValueError("installation manifest has invalid release metadata")
        _validate_version(entry["version"])
        if entry["path"] != f"releases/{entry['version']}":
            raise ValueError("installation manifest release path does not match its version")


def install_release(source_root: Path, fabric_home: Path | None = None, version: str | None = None) -> Path:
    """Create an immutable user-level release without replacing an existing release."""
    source = source_root.resolve()
    selected_version = version or _source_version(source)
    _validate_version(selected_version)
    _validate_source(source)
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    destination = release_path(home, selected_version)
    if destination.exists():
        raise FileExistsError(f"Fabric release already exists and will not be replaced: {destination}")
    destination.mkdir(parents=True)
    for relative in RELEASE_ASSETS:
        _copy_asset(source, destination, relative)
    _write_release_core(destination)
    _write_release_adapters(destination)
    _write_release_launcher(destination)
    release_manifest = _release_manifest(destination, selected_version)
    manifest_path = destination / RELEASE_MANIFEST_FILE
    _write_json(manifest_path, release_manifest)
    _update_installation(home, selected_version, manifest_path)
    _write_global_launcher(home)
    _write_global_adapters(home, destination)
    _write_global_skills(home, destination)
    _write_global_codex_marketplace(home, selected_version)
    return destination


def bind_project(project_root: Path, release: str, client: str, fabric_home: Path | None = None) -> Path:
    """Pin a project to one installed Fabric release and create its local overlay."""
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: {client}")
    _validate_version(release)
    project = project_root.resolve()
    if not project.is_dir():
        raise ValueError(f"Target project does not exist: {project}")
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    _validate_bindable_release(home, release)
    fabric_dir = state_directory(project, create=True)
    binding_path = state_path(project, PROJECT_BINDING_FILE, create_parents=True)
    if binding_path.exists():
        raise FileExistsError(f"Project binding already exists and will not be replaced: {binding_path}")
    fabric_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = state_path(project, "project-overlay.md", create_parents=True)
    if overlay_path.exists():
        raise FileExistsError(f"Project overlay already exists and will not be replaced: {overlay_path}")
    _ensure_project_configuration(project)
    binding = {
        "schema_version": 1,
        "fabric_release": release,
        "client": client,
        "profile": ".agent-fabric/profile.json",
        "project_overlay": ".agent-fabric/project-overlay.md",
        "enabled_packs": [],
    }
    validate_project_binding(binding)
    overlay_path.write_text(
        "# Project overlay\n\n"
        "Add project-specific rules here. These rules refine only the configuration points "
        "declared by the selected Fabric release.\n",
        encoding="utf-8",
    )
    _write_json(binding_path, binding)
    return binding_path


def release_preview(source_root: Path, fabric_home: Path | None = None, version: str | None = None) -> list[Path]:
    """List all paths a release installation would create or replace."""
    source = source_root.resolve()
    selected_version = version or _source_version(source)
    _validate_version(selected_version)
    _validate_source(source)
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    destination = release_path(home, selected_version)
    if destination.exists():
        raise FileExistsError(f"Fabric release already exists and will not be replaced: {destination}")
    paths = [destination / asset for asset in RELEASE_ASSETS]
    paths.extend(_release_generated_paths(destination))
    paths.extend([destination / RELEASE_MANIFEST_FILE, installation_path(home), home / "bin" / "ai-agent-fabric", home / "bin" / "ai-agent-fabric.py"])
    paths.extend(home / "adapters" / client / "bootstrap.md" for client in SUPPORTED_CLIENTS)
    paths.extend([
        home / "marketplace" / "plugins" / "agent-fabric",
        home / "marketplace" / ".agents" / "plugins" / "marketplace.json",
    ])
    if installation_path(home).exists():
        paths.append(home / "backups" / "installation-<timestamp>.json")
    return paths


def binding_preview(project_root: Path, release: str, client: str, fabric_home: Path | None = None) -> list[Path]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: {client}")
    _validate_version(release)
    project = project_root.resolve()
    if not project.is_dir():
        raise ValueError(f"Target project does not exist: {project}")
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    _validate_bindable_release(home, release)
    fabric_dir = state_directory(project)
    return [
        state_path(project, PROJECT_BINDING_FILE),
        state_path(project, "project-overlay.md"),
        state_path(project, "profile.json"),
        state_path(project, "config/capabilities.json"),
        state_path(project, "config/work-tracking.json"),
        state_path(project, "config/model-routing.json"),
        state_path(project, "memory.db"),
    ]


def project_onboarding_preview(project_root: Path, client: str, fabric_home: Path | None = None, release: str | None = None) -> list[Path]:
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    selected_release = release or load_installation(home)["current_release"]
    return binding_preview(project_root, selected_release, client, home)


def onboard_project(project_root: Path, client: str, fabric_home: Path | None = None, release: str | None = None) -> Path:
    """Create a project-owned overlay for the selected installed Fabric release."""
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    selected_release = release or load_installation(home)["current_release"]
    return bind_project(project_root, selected_release, client, home)


def project_status(project_root: Path, fabric_home: Path | None = None) -> dict[str, Any]:
    """Inspect project Fabric state without creating files or selecting a client."""
    project = project_root.resolve()
    if not project.is_dir():
        raise ValueError(f"Target project does not exist: {project}")
    raw_fabric_dir = project / ".agent-fabric"
    report: dict[str, Any] = {
        "project_root": str(project),
        "fabric_directory": raw_fabric_dir.is_dir() and not raw_fabric_dir.is_symlink(),
        "binding": False,
        "profile": False,
        "project_overlay": False,
        "pending_update": False,
    }
    try:
        fabric_dir = state_directory(project)
        binding_path = state_path(project, PROJECT_BINDING_FILE)
        pending_path = _pending_project_update_path(project)
        report.update({"binding": binding_path.is_file(), "pending_update": pending_path.is_file()})
    except ValueError as error:
        report.update({"status": "invalid", "error": str(error)})
        return report
    if not binding_path.is_file():
        report["status"] = "unbound" if not fabric_dir.exists() else "partial"
        return report
    try:
        binding = _load_project_binding(binding_path)
        profile_path = _project_relative_path(project, binding["profile"])
        overlay_path = _project_relative_path(project, binding["project_overlay"])
        report.update({"profile": profile_path.is_file(), "project_overlay": overlay_path.is_file()})
        home = (fabric_home or default_fabric_home()).expanduser().resolve()
        installation = load_installation(home)
        report.update(
            {
                "current_release": installation["current_release"],
                "update_available": binding["fabric_release"] != installation["current_release"],
            }
        )
        _validate_installed_release(home, binding["fabric_release"])
        if not profile_path.is_file() or not overlay_path.is_file():
            report.update({"status": "partial", "client": binding["client"], "release": binding["fabric_release"]})
            return report
        _load_project_profile(profile_path)
        load_capabilities(project)
        load_routing(project)
        load_config(project)
    except (ValueError, FileNotFoundError) as error:
        report.update({"status": "invalid", "error": str(error)})
        return report
    if report["pending_update"]:
        report.update({"status": "update-pending", "client": binding["client"], "release": binding["fabric_release"]})
        return report
    report.update({"status": "bound", "client": binding["client"], "release": binding["fabric_release"]})
    return report


def require_bound_project(
    project_root: Path,
    fabric_home: Path | None = None,
    *,
    allow_pending_update: bool = False,
) -> dict[str, Any]:
    """Refuse write workflows until the project has an intact Fabric binding."""
    report = project_status(project_root, fabric_home)
    allowed_statuses = {"bound"}
    if allow_pending_update:
        allowed_statuses.add("update-pending")
    if report["status"] not in allowed_statuses:
        raise ValueError(
            "Project is not ready for Fabric-managed writes: "
            f"status is {report['status']}. Run `project status`, then explicitly initialize or repair the binding."
        )
    return report


def project_context(project_root: Path, fabric_home: Path | None = None) -> dict[str, Any]:
    """Return only the read-only contracts a selected client needs for a bound project."""
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    report = require_bound_project(project, home)
    binding = _load_project_binding(state_path(project, PROJECT_BINDING_FILE))
    release = release_path(home, binding["fabric_release"])
    # A context is consumed by an external client.  Resolve every local contract
    # now, so a binding or config symlink cannot make that client read outside
    # the selected project.
    profile = _project_contract_file(project, binding["profile"], "profile")
    overlay = _project_contract_file(project, binding["project_overlay"], "project overlay")
    capabilities = _project_contract_file(project, ".agent-fabric/config/capabilities.json", "capabilities config")
    model_routing = _project_contract_file(project, ".agent-fabric/config/model-routing.json", "model routing config")
    work_tracking = _project_contract_file(project, ".agent-fabric/config/work-tracking.json", "work tracking config")
    return {
        "project_root": str(project),
        "client": binding["client"],
        "release": binding["fabric_release"],
        "current_release": report["current_release"],
        "update_available": report["update_available"],
        "release_root": str(release),
        "shared_contracts": {
            "agent_profiles": str(release / "core" / "agent-profiles.json"),
            "gates": str(release / "core" / "gates.json"),
            "adapter_manifest": str(release / "adapters" / binding["client"] / "adapter-manifest.json"),
        },
        "project_contracts": {
            "profile": str(profile),
            "overlay": str(overlay),
            "capabilities": str(capabilities),
            "model_routing": str(model_routing),
            "work_tracking": str(work_tracking),
        },
        "memory": "not exposed by client context",
        "status": report["status"],
    }


def secret_entry_preview(
    project_root: Path,
    destination: str,
    label: str,
    fabric_home: Path | None = None,
) -> dict[str, str]:
    """Resolve a safe, project-local hidden-prompt secret entry without writing it."""
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    report = require_bound_project(project, home)
    if not _safe_project_relative_path(destination):
        raise ValueError("Secret destination must be a safe project-relative path")
    if not isinstance(label, str) or not SECRET_LABEL_PATTERN.fullmatch(label):
        raise ValueError("Secret label must be a concise non-secret identifier")
    binding = _load_project_binding(state_path(project, PROJECT_BINDING_FILE))
    profile_path = _project_relative_path(project, binding["profile"])
    profile = _load_project_profile(profile_path)
    allowed_root = _project_relative_path(project, profile["secrets"]["allowed_root"])
    requested_destination = _project_relative_path(project, destination)
    if requested_destination == allowed_root:
        raise ValueError("Secret destination must name a file below the profile-declared secret root")
    try:
        requested_destination.relative_to(allowed_root)
    except ValueError:
        raise ValueError("Secret destination must stay under the profile-declared secret root") from None
    release = release_path(home, report["release"])
    script = release / "scripts" / "secret-entry.sh"
    if not script.is_file() or script.is_symlink():
        raise ValueError("Selected Fabric release has no trusted Bash secret-entry helper")
    environment = detect_environment()
    if not environment.bash_path:
        raise ValueError("Hidden secret entry requires detected Bash; use `bootstrap bash` first")
    return {
        "project_root": str(project),
        "release": report["release"],
        "bash": environment.bash_path,
        "helper": str(script),
        "destination": destination,
        "label": label,
        "prompt": "The next command opens a hidden terminal prompt. The secret is never passed as an argument or printed.",
    }


def enter_secret(
    project_root: Path,
    destination: str,
    label: str,
    fabric_home: Path | None = None,
) -> None:
    """Open the selected release's Bash helper; secret bytes never enter CLI arguments or state."""
    preview = secret_entry_preview(project_root, destination, label, fabric_home)
    subprocess.run(
        [preview["bash"], preview["helper"], preview["project_root"], preview["destination"], preview["label"]],
        cwd=preview["project_root"],
        check=True,
    )


def project_update_preview(project_root: Path, release: str, fabric_home: Path | None = None) -> dict[str, Any]:
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    if _pending_project_update_path(project).is_file():
        raise ValueError("Project has an interrupted Fabric update; run `distribution repair-project-update` first")
    try:
        require_bound_project(project, home)
    except ValueError as error:
        # A damaged *current* immutable release must not trap a project on it.
        # The update still validates the binding and the selected target release,
        # then journals/backups the binding through the normal update path.
        if project_status(project, home).get("error") != "Fabric release file set does not match its manifest":
            raise
    binding_path = state_path(project, PROJECT_BINDING_FILE)
    binding = _load_project_binding(binding_path)
    target_manifest = _validate_bindable_release(home, release)
    if binding["fabric_release"] == release:
        raise ValueError(f"Project already uses Fabric release {release}")
    current_memory_version = schema_version(project)
    target_memory = target_manifest["memory"]
    if current_memory_version < target_memory["minimum_compatible"]:
        raise ValueError("Project memory is older than the selected release's supported migration floor")
    if current_memory_version > target_memory["schema_version"]:
        raise ValueError("Project memory is newer than the selected release and cannot be downgraded")
    return {
        "binding": str(binding_path),
        "from_release": binding["fabric_release"],
        "to_release": release,
        "backup": str(state_path(project, "backups/fabric-binding-<timestamp>.json")),
        "memory_migration": {
            "database": str(state_path(project, "memory.db")),
            "from_schema": current_memory_version,
            "to_schema": target_memory["schema_version"],
            "required": current_memory_version < target_memory["schema_version"],
        },
    }


def update_project(project_root: Path, release: str, fabric_home: Path | None = None) -> Path:
    """Move one project to an installed release after preserving its prior binding."""
    preview = project_update_preview(project_root, release, fabric_home)
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    binding_path = Path(preview["binding"])
    binding = _load_project_binding(binding_path)
    backup_path = _backup_project_binding(binding_path)
    pending_path = state_path(project, f"updates/{PROJECT_UPDATE_FILE}", create_parents=True)
    _write_json(
        pending_path,
        {
            "schema_version": 1,
            "from_release": binding["fabric_release"],
            "to_release": release,
            "binding": str(binding_path),
            "backup": str(backup_path),
            "stage": "prepared",
        },
    )
    # Apply the target release's forward-only local-memory migration before switching
    # the pinned release. A durable pending record makes an interruption repairable.
    _migrate_project_memory(project, home, release)
    pending = _load_pending_project_update(pending_path)
    pending["stage"] = "memory-migrated"
    _write_json(pending_path, pending)
    binding["fabric_release"] = release
    _write_json(binding_path, binding)
    pending_path.unlink()
    return backup_path


def repair_project_update(project_root: Path, fabric_home: Path | None = None) -> Path:
    """Explicitly finish a durable interrupted update; never silently roll memory back."""
    preview = repair_project_update_preview(project_root, fabric_home)
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    pending_path = _pending_project_update_path(project)
    pending = _load_pending_project_update(pending_path)
    binding_path = Path(pending["binding"])
    binding = _load_project_binding(Path(preview["binding_source"]))
    if preview["restores_binding_backup"]:
        _write_json(binding_path, binding)
    _migrate_project_memory(project, home, pending["to_release"])
    binding["fabric_release"] = pending["to_release"]
    _write_json(binding_path, binding)
    pending_path.unlink()
    return binding_path


def repair_project_update_preview(project_root: Path, fabric_home: Path | None = None) -> dict[str, Any]:
    """Describe the explicit recovery without changing a binding, journal, or database."""
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    pending_path = _pending_project_update_path(project)
    pending = _load_pending_project_update(pending_path)
    binding_path = Path(pending["binding"])
    expected_binding_path = state_path(project, PROJECT_BINDING_FILE).resolve()
    if binding_path.resolve() != expected_binding_path:
        raise ValueError("Interrupted update references an unexpected binding path")
    binding_source = binding_path
    restores_binding_backup = False
    try:
        binding = _load_project_binding(binding_path)
    except ValueError:
        backup_path = Path(pending["backup"])
        backup_directory = state_path(project, "backups").resolve()
        if not backup_path.is_file() or backup_path.resolve().parent != backup_directory:
            raise ValueError("Interrupted update cannot restore a trusted binding backup") from None
        binding = _load_project_binding(backup_path)
        binding_source = backup_path
        restores_binding_backup = True
    if binding["fabric_release"] not in {pending["from_release"], pending["to_release"]}:
        raise ValueError("Project binding no longer matches the interrupted update")
    target_manifest = _validate_installed_release(home, pending["to_release"])
    current_memory_version = schema_version(project)
    target_memory = target_manifest["memory"]
    if current_memory_version < target_memory["minimum_compatible"]:
        raise ValueError("Project memory is older than the recovery release's supported migration floor")
    if current_memory_version > target_memory["schema_version"]:
        raise ValueError("Project memory is newer than the recovery release and cannot be downgraded")
    return {
        "journal": str(pending_path),
        "stage": pending["stage"],
        "binding": str(binding_path),
        "binding_source": str(binding_source),
        "restores_binding_backup": restores_binding_backup,
        "from_release": pending["from_release"],
        "to_release": pending["to_release"],
        "memory_migration": {
            "database": str(state_path(project, "memory.db")),
            "from_schema": current_memory_version,
            "to_schema": target_memory["schema_version"],
            "required": current_memory_version < target_memory["schema_version"],
        },
    }


def rollback_project(project_root: Path, fabric_home: Path | None = None) -> Path:
    project_rollback_preview(project_root, fabric_home)
    project = project_root.resolve()
    binding_path = state_path(project, PROJECT_BINDING_FILE)
    backups = sorted(state_path(project, "backups").glob("fabric-binding-*.json"))
    backup = backups[-1]
    restored = _load_project_binding(backup)
    _backup_project_binding(binding_path)
    _write_json(binding_path, restored)
    return binding_path


def project_rollback_preview(project_root: Path, fabric_home: Path | None = None) -> dict[str, Any]:
    project = project_root.resolve()
    home = (fabric_home or default_fabric_home()).expanduser().resolve()
    if _pending_project_update_path(project).is_file():
        raise ValueError("Project has an interrupted Fabric update; repair it before rollback")
    binding_path = state_path(project, PROJECT_BINDING_FILE)
    binding = _load_project_binding(binding_path)
    profile_path = _project_relative_path(project, binding["profile"])
    overlay_path = _project_relative_path(project, binding["project_overlay"])
    if not profile_path.is_file() or not overlay_path.is_file():
        raise ValueError("Project binding is incomplete and cannot be rolled back safely")
    _load_project_profile(profile_path)
    backups = sorted(state_path(project, "backups").glob("fabric-binding-*.json"))
    if not backups:
        raise ValueError(f"No project binding backup is available: {binding_path}")
    backup = backups[-1]
    restored = _load_project_binding(backup)
    restored_manifest = _validate_installed_release(home, restored["fabric_release"])
    current_memory_version = schema_version(project)
    if current_memory_version < restored_manifest["memory"]["minimum_compatible"]:
        raise ValueError("Project memory is older than the rollback release's supported compatibility floor")
    if current_memory_version > restored_manifest["memory"]["schema_version"]:
        raise ValueError("Project memory is newer than the rollback release and cannot be downgraded")
    return {
        "binding": str(binding_path),
        "from_release": binding["fabric_release"],
        "to_release": restored["fabric_release"],
        "restore_from": str(backup),
        "backup_current": str(state_path(project, "backups/fabric-binding-<timestamp>.json")),
        "memory_schema": current_memory_version,
    }


def client_entry_point(client: str) -> Path:
    manifest = adapter_manifest(client)
    entry = next(item for item in manifest["entry_points"] if item["purpose"] == "global-bootstrap")
    return Path(entry["path"]).expanduser()


def client_record_path(fabric_home: Path, client: str) -> Path:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"Unsupported client: {client}")
    return fabric_home / CLIENT_RECORD_DIRECTORY / f"{client}.json"


def codex_skill_record_path(fabric_home: Path) -> Path:
    return fabric_home / CLIENT_RECORD_DIRECTORY / "codex-skills.json"


def codex_skill_root() -> Path:
    return Path.home() / ".codex" / "skills"


def codex_skill_enable_preview(fabric_home: Path) -> dict[str, Any]:
    """Describe the four user-scoped Codex skill links without writing them."""
    home = fabric_home.expanduser().resolve()
    installation = load_installation(home)
    release = installation["current_release"]
    _validate_installed_release(home, release)
    source_root = home / "skills"
    record_path = codex_skill_record_path(home)
    record = _load_codex_skill_record(record_path, home) if record_path.is_file() else None
    actions: list[dict[str, str]] = []
    blocked: list[str] = []
    for name in CODEX_SKILL_NAMES:
        source = source_root / name
        destination = codex_skill_root() / name
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"Global Fabric skill is missing: {source}")
        owned = (record is not None and name in record["skills"] and _owned_codex_skill_link(destination, source))
        recoverable = record is None and _owned_codex_skill_link(destination, source)
        if destination.exists() or destination.is_symlink():
            action = "already-installed" if owned else "adopt-interrupted-fabric-link" if recoverable else "blocked-user-owned-target"
            if not owned and not recoverable:
                blocked.append(str(destination))
        else:
            action = "create-symlink"
        actions.append({"name": name, "source": str(source), "destination": str(destination), "action": action})
    preview: dict[str, Any] = {
        "client": "codex",
        "release": release,
        "method": "user-scope-symlink-skills",
        "ownership_record": str(record_path),
        "skills": actions,
    }
    if blocked:
        preview["blocked"] = blocked
    if os.name == "nt":
        preview["windows_elevation_notice"] = {
            "may_be_required": True,
            "title": "Windows permission for Fabric skill links",
            "what_will_change": f"Create up to {len(CODEX_SKILL_NAMES)} symbolic-link folders under {codex_skill_root()}.",
            "why": "Codex discovers user-scoped skills from this standard directory. Each link points only to Fabric-managed files under the user-level Fabric home.",
            "scope": "No project files or unrelated user skills are changed. If Windows asks for UAC approval, elevation is only for these declared links.",
            "cancel": "Cancelling leaves the skill folders unchanged.",
        }
    return preview


def enable_codex_skills(fabric_home: Path, *, allow_windows_elevation: bool = False) -> Path:
    """Install only Fabric-owned user-scoped Codex skill links."""
    preview = codex_skill_enable_preview(fabric_home)
    if preview.get("blocked"):
        raise FileExistsError("Refusing to replace user-owned Codex skill directories: " + ", ".join(preview["blocked"]))
    home = fabric_home.expanduser().resolve()
    created: list[Path] = []
    try:
        pending = [item for item in preview["skills"] if item["action"] == "create-symlink"]
        for index, item in enumerate(pending):
            if item["action"] == "already-installed":
                continue
            source = Path(item["source"])
            destination = Path(item["destination"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                destination.symlink_to(source, target_is_directory=True)
            except OSError as error:
                if not _requires_windows_symlink_elevation(error) or not allow_windows_elevation:
                    raise PermissionError(
                        "Windows requires permission for these native symbolic links. Review "
                        "`distribution enable-codex-skills --preview`, then repeat with --elevate."
                    ) from error
                elevated_links = [(Path(candidate["source"]), Path(candidate["destination"])) for candidate in pending[index:]]
                _create_elevated_windows_symlinks(elevated_links)
                created.extend(target for _, target in elevated_links)
                break
            created.append(destination)
        record = {
            "schema_version": 1,
            "client": "codex",
            "release": preview["release"],
            "skills": {item["name"]: {"source": item["source"], "destination": item["destination"]} for item in preview["skills"]},
        }
        _write_json(codex_skill_record_path(home), record)
    except BaseException:
        for destination in reversed(created):
            _remove_client_artifact(destination)
        raise
    return codex_skill_record_path(home)


def disable_codex_skills(fabric_home: Path) -> None:
    """Remove only legacy direct links which the Fabric record still owns."""
    home = fabric_home.expanduser().resolve()
    record_path = codex_skill_record_path(home)
    _load_codex_skill_record(record_path, home)
    for name in CODEX_SKILL_NAMES:
        (codex_skill_root() / name).unlink()
    record_path.unlink()


def client_enable_preview(fabric_home: Path, client: str, method: str | None = None) -> dict[str, Any]:
    home = fabric_home.expanduser().resolve()
    installation = load_installation(home)
    release = installation["current_release"]
    _validate_installed_release(home, release)
    adapter = adapter_manifest(client)
    selected_method = method or adapter["delivery"]["default"]
    if selected_method not in adapter["delivery"]["supported"]:
        raise ValueError(f"Unsupported delivery method for {client}: {selected_method}")
    preflight = client_preflight(client)
    bootstrap = home / "adapters" / client / "bootstrap.md"
    if not bootstrap.is_file():
        raise ValueError(f"Fabric home does not contain the managed {client} adapter: {bootstrap}")
    destination = client_entry_point(client)
    record = client_record_path(home, client)
    exists = destination.exists() or destination.is_symlink()
    owned = _load_client_record(record, client, destination) if record.is_file() else None
    if selected_method == "managed-block":
        action = "update-managed-block" if owned is not None else "append-managed-block"
    elif exists and owned is None:
        action = "blocked-user-owned-target"
    elif exists:
        action = "replace-owned-target-with-backup"
    else:
        action = "create"
    preview = {
        "client": client,
        "release": release,
        "method": selected_method,
        "source": str(bootstrap),
        "destination": str(destination),
        "ownership_record": str(record),
        "action": action,
        "preflight": preflight,
    }
    if selected_method == "managed-block":
        preview["managed_block"] = _managed_block(client, bootstrap)
    if selected_method == "symlink" and os.name == "nt":
        preview["windows_elevation_notice"] = _windows_elevation_notice(destination, bootstrap)
    return preview


def _windows_elevation_notice(destination: Path, source: Path) -> dict[str, Any]:
    return {
        "may_be_required": True,
        "title": "Windows permission for a symbolic link",
        "what_will_change": f"Create one symbolic link at {destination} that points to the Fabric bootstrap at {source}.",
        "why": "Windows may require permission to create a native NTFS symbolic link. This is unrelated to the project, its files, or its secrets.",
        "scope": "If Windows asks for UAC approval, elevated rights are used only for creating this one declared adapter link. The installer still refuses user-owned targets and records the link for rollback or uninstall.",
        "cancel": "Cancelling the UAC prompt leaves the client configuration unchanged. Choose the wrapper method instead if a symbolic link is not desired.",
    }


def enable_client(
    fabric_home: Path,
    client: str,
    method: str | None = None,
    *,
    allow_windows_elevation: bool = False,
    elevation_notice_acknowledged: bool = False,
) -> Path:
    """Connect one declared user-level client entry point to the active Fabric release."""
    preview = client_enable_preview(fabric_home, client, method)
    if not preview["preflight"]["ready"]:
        raise ValueError(f"Client surface is not verified for installation: {preview['preflight']['reason']}")
    if preview["action"] == "blocked-user-owned-target":
        raise FileExistsError(f"Refusing to replace user-owned client artifact: {preview['destination']}")
    if allow_windows_elevation and preview.get("windows_elevation_notice") and not elevation_notice_acknowledged:
        raise PermissionError(
            "The Windows symbolic-link permission notice must be shown and acknowledged "
            "before Fabric may request UAC elevation."
        )
    home = fabric_home.expanduser().resolve()
    destination = Path(preview["destination"])
    record_path = Path(preview["ownership_record"])
    previous = _load_client_record(record_path, client, destination) if record_path.is_file() else None
    backups: list[dict[str, Any]] = list(previous.get("backups", [])) if previous else []
    if preview["method"] == "managed-block":
        if previous is not None:
            backups.append(_backup_managed_block(home, client, destination, previous))
    elif preview["action"] == "replace-owned-target-with-backup":
        backups.append(_backup_owned_client_artifact(home, client, destination, previous))
        _remove_client_artifact(destination)
    source = Path(preview["source"])
    managed_original = destination.read_text(encoding="utf-8") if preview["method"] == "managed-block" and destination.exists() else None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if preview["method"] == "managed-block":
            _upsert_managed_block(destination, str(preview["managed_block"]))
        elif preview["method"] == "symlink":
            try:
                destination.symlink_to(source)
            except OSError as error:
                if not _requires_windows_symlink_elevation(error):
                    raise
                if not allow_windows_elevation:
                    raise PermissionError(
                        "Windows requires UAC permission for this native symbolic link. "
                        "Review `distribution enable-client --preview`, then repeat with --elevate "
                        "or explicitly choose --method wrapper."
                    ) from error
                _create_elevated_windows_symlink(source, destination)
        else:
            destination.write_text(_client_wrapper(client, source, preview["method"]), encoding="utf-8")
        record = {
            "schema_version": 1,
            "client": client,
            "release": preview["release"],
            "method": preview["method"],
            "destination": str(destination),
            "source": str(source),
            "fingerprint": _managed_block_fingerprint(str(preview["managed_block"])) if preview["method"] == "managed-block" else _artifact_fingerprint(destination),
            "preflight": preview["preflight"],
            "backups": backups,
        }
        _write_json(record_path, record)
    except BaseException:
        if preview["method"] == "managed-block":
            if managed_original is None:
                if destination.exists():
                    destination.unlink()
            else:
                destination.write_text(managed_original, encoding="utf-8")
        else:
            _remove_client_artifact(destination)
        if previous is not None and backups:
            _restore_client_artifact(home, destination, backups[-1])
        raise
    return record_path


def _requires_windows_symlink_elevation(error: OSError) -> bool:
    return os.name == "nt" and getattr(error, "winerror", None) == 1314


def _create_elevated_windows_symlink(source: Path, destination: Path) -> None:
    """Create one declared NTFS link through the Windows UAC boundary."""
    if os.name != "nt":
        raise OSError("Windows elevation is unavailable on this host")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Refusing to elevate over an existing artifact: {destination}")

    def powershell_literal(path: Path) -> str:
        return str(path).replace("'", "''")

    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"New-Item -ItemType SymbolicLink -Path '{powershell_literal(destination)}' "
        f"-Target '{powershell_literal(source)}' | Out-Null"
    )
    parameters = "-NoProfile -NonInteractive -EncodedCommand " + base64.b64encode(script.encode("utf-16le")).decode("ascii")
    _shell_execute_elevated(_trusted_windows_powershell(), parameters)
    if not destination.is_symlink() or _resolved_symlink_target(destination) != source.resolve(strict=True):
        raise OSError("Windows elevation completed without creating the requested symbolic link")


def _create_elevated_windows_symlinks(links: list[tuple[Path, Path]]) -> None:
    """Create a declared batch of directory links through one UAC prompt."""
    if os.name != "nt":
        raise OSError("Windows elevation is unavailable on this host")
    if not links:
        return
    for source, destination in links:
        if not source.is_dir() or destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Refusing to elevate over an invalid skill-link target: {destination}")

    def literal(path: Path) -> str:
        return str(path).replace("'", "''")

    commands = ["$ErrorActionPreference = 'Stop'", *(
        f"New-Item -ItemType SymbolicLink -Path '{literal(destination)}' -Target '{literal(source)}' | Out-Null"
        for source, destination in links
    )]
    parameters = "-NoProfile -NonInteractive -EncodedCommand " + base64.b64encode("; ".join(commands).encode("utf-16le")).decode("ascii")
    _shell_execute_elevated(_trusted_windows_powershell(), parameters)
    for source, destination in links:
        if not destination.is_symlink() or _resolved_symlink_target(destination) != source.resolve(strict=True):
            raise OSError("Windows elevation completed without creating every requested skill link")


def _trusted_windows_powershell() -> str:
    """Return the System32 PowerShell path without trusting PATH or the working directory."""
    if os.name != "nt":
        raise OSError("Windows elevation is unavailable on this host")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = ctypes.create_unicode_buffer(32768)
    length = kernel32.GetSystemDirectoryW(buffer, len(buffer))
    if not length or length >= len(buffer):
        raise OSError(ctypes.get_last_error(), "Windows system directory could not be resolved")
    executable = Path(buffer.value) / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"System PowerShell executable is unavailable: {executable}")
    return str(executable)


def _shell_execute_elevated(executable: str, parameters: str) -> None:
    """Run a narrow command after UAC and propagate cancellation or child failure."""
    if os.name != "nt":
        raise OSError("Windows elevation is unavailable on this host")

    class ShellExecuteInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong), ("fMask", ctypes.c_ulong), ("hwnd", ctypes.c_void_p),
            ("lpVerb", ctypes.c_wchar_p), ("lpFile", ctypes.c_wchar_p), ("lpParameters", ctypes.c_wchar_p),
            ("lpDirectory", ctypes.c_wchar_p), ("nShow", ctypes.c_int), ("hInstApp", ctypes.c_void_p),
            ("lpIDList", ctypes.c_void_p), ("lpClass", ctypes.c_wchar_p), ("hkeyClass", ctypes.c_void_p),
            ("dwHotKey", ctypes.c_ulong), ("hIcon", ctypes.c_void_p), ("hProcess", ctypes.c_void_p),
        ]

    info = ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(ShellExecuteInfo)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = executable
    info.lpParameters = parameters
    info.nShow = 1
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        error = ctypes.get_last_error()
        if error == 1223:
            raise PermissionError("Windows UAC confirmation was cancelled; client configuration was not changed")
        raise OSError(error, "Windows could not start the elevated symbolic-link operation")
    try:
        kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
            raise OSError(ctypes.get_last_error(), "Windows could not read the elevated operation result")
        if exit_code.value != 0:
            raise OSError(f"Elevated symbolic-link operation failed with exit code {exit_code.value}")
    finally:
        kernel32.CloseHandle(info.hProcess)


def client_preflight(client: str) -> dict[str, Any]:
    """Verify a concrete supported CLI surface without creating files."""
    adapter = adapter_manifest(client)
    executable = shutil.which(client)
    if not executable:
        return {"ready": False, "client": client, "surface": adapter["surface"], "reason": f"{client} executable was not found"}
    try:
        result = subprocess.run([executable, "--version"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"ready": False, "client": client, "surface": adapter["surface"], "reason": f"could not inspect client version: {error}"}
    if result.returncode != 0:
        return {"ready": False, "client": client, "surface": adapter["surface"], "reason": "client version command failed"}
    return {
        "ready": True,
        "client": client,
        "surface": adapter["surface"],
        "executable": executable,
        "version": result.stdout.strip(),
        "entry_point": str(client_entry_point(client)),
    }


def client_rollback_preview(fabric_home: Path, client: str) -> dict[str, Any]:
    home = fabric_home.expanduser().resolve()
    destination = client_entry_point(client)
    record = _load_client_record(client_record_path(home, client), client, destination)
    backups = record.get("backups", [])
    if not backups:
        raise ValueError(f"No rollback artifact is available for {client}")
    backup = backups[-1]
    preview = {"client": client, "action": "restore-owned-artifact", "destination": str(destination), "from_release": record["release"], "to_release": backup["release"], "backup_kind": backup["kind"]}
    if os.name == "nt" and (record["method"] == "symlink" or backup["kind"] == "symlink"):
        source = Path(backup["target"]) if backup["kind"] == "symlink" else Path(record["source"])
        preview["windows_elevation_notice"] = _windows_elevation_notice(destination, source)
    return preview


def client_uninstall_preview(fabric_home: Path, client: str) -> dict[str, Any]:
    home = fabric_home.expanduser().resolve()
    destination = client_entry_point(client)
    record = _load_client_record(client_record_path(home, client), client, destination)
    return {"client": client, "action": "remove-owned-artifact", "destination": str(destination), "release": record["release"], "method": record["method"]}


def rollback_client(
    fabric_home: Path,
    client: str,
    *,
    allow_windows_elevation: bool = False,
    elevation_notice_acknowledged: bool = False,
) -> Path:
    home = fabric_home.expanduser().resolve()
    destination = client_entry_point(client)
    record_path = client_record_path(home, client)
    record = _load_client_record(record_path, client, destination)
    preview = client_rollback_preview(home, client)
    if allow_windows_elevation and preview.get("windows_elevation_notice") and not elevation_notice_acknowledged:
        raise PermissionError("The Windows symbolic-link permission notice must be shown and acknowledged before Fabric may request UAC elevation.")
    backups = list(record["backups"])
    target = backups[-1]
    current_backup = _backup_managed_block(home, client, destination, record) if record["method"] == "managed-block" else _backup_owned_client_artifact(home, client, destination, record)
    try:
        if record["method"] == "managed-block":
            if target["kind"] != "managed-block":
                raise ValueError("Managed-block rollback requires a managed-block backup")
            _upsert_managed_block(destination, (home / target["path"]).read_text(encoding="utf-8"))
        else:
            _remove_client_artifact(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            _restore_client_artifact(home, destination, target, allow_windows_elevation=allow_windows_elevation)
        record.update(
            {
                "release": target["release"],
                "method": target["method"],
                "source": target["source"],
                "fingerprint": _managed_block_fingerprint((home / target["path"]).read_text(encoding="utf-8")) if record["method"] == "managed-block" else _artifact_fingerprint(destination),
                "backups": backups[:-1] + [current_backup],
            }
        )
        _write_json(record_path, record)
    except BaseException:
        if record["method"] == "managed-block":
            _upsert_managed_block(destination, (home / current_backup["path"]).read_text(encoding="utf-8"))
        else:
            _remove_client_artifact(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            _restore_client_artifact(home, destination, current_backup, allow_windows_elevation=allow_windows_elevation)
        raise
    return record_path


def uninstall_client(fabric_home: Path, client: str) -> None:
    home = fabric_home.expanduser().resolve()
    destination = client_entry_point(client)
    record_path = client_record_path(home, client)
    preview = client_uninstall_preview(home, client)
    record = _load_client_record(record_path, client, destination)
    if preview["method"] == "managed-block":
        _remove_managed_block(destination, record["fingerprint"])
    else:
        _remove_client_artifact(destination)
    record_path.unlink()


def _client_wrapper(client: str, source: Path, method: str) -> str:
    source_text = source.as_posix()
    if method == "import":
        # Claude Code accepts absolute @ imports, but spaces must be escaped and
        # quoting would make the import literal rather than load it.
        escaped_source = source_text.replace(" ", r"\ ")
        return f"# Managed by AI Agent Fabric.\n@{escaped_source}\n"
    return (
        "# Managed by AI Agent Fabric.\n\n"
        f"Read `{source_text}` before working in a repository. "
        "Do not edit this managed wrapper; use the Fabric installer to update or remove it.\n"
    )


def _managed_block(client: str, source: Path) -> str:
    return (
        f"{MANAGED_BLOCK_BEGIN}\n"
        "# AI Agent Fabric\n\n"
        f"Read `{source.as_posix()}` before repository work. If the repository contains "
        "`.agent-fabric/fabric-binding.json`, follow the bound Fabric release and its "
        "project-local overlay. Do not initialize Fabric in an unbound repository unless "
        "the user asks.\n"
        f"{MANAGED_BLOCK_END}\n"
    )


def _managed_block_fingerprint(block: str) -> str:
    return "managed-block:" + hashlib.sha256(block.encode("utf-8")).hexdigest()


def _single_managed_block(text: str) -> str:
    matches = list(MANAGED_BLOCK_PATTERN.finditer(text))
    if len(matches) != 1:
        raise ValueError("Expected exactly one AI Agent Fabric managed block")
    return matches[0].group(0)


def _upsert_managed_block(destination: Path, block: str) -> None:
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    matches = list(MANAGED_BLOCK_PATTERN.finditer(existing))
    if len(matches) > 1:
        raise ValueError(f"Refusing to modify multiple managed blocks: {destination}")
    if matches:
        updated = existing[:matches[0].start()] + block + existing[matches[0].end():]
    elif existing:
        updated = existing.rstrip() + "\n\n" + block
    else:
        updated = block
    destination.write_text(updated, encoding="utf-8")


def _remove_managed_block(destination: Path, expected_fingerprint: str) -> None:
    text = destination.read_text(encoding="utf-8")
    block = _single_managed_block(text)
    if _managed_block_fingerprint(block) != expected_fingerprint:
        raise ValueError(f"Managed Fabric block changed outside installer ownership: {destination}")
    updated = MANAGED_BLOCK_PATTERN.sub("", text, count=1).strip()
    if updated:
        destination.write_text(updated + "\n", encoding="utf-8")
    else:
        destination.unlink()


def _load_client_record(path: Path, client: str, destination: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid client ownership record: {path}") from error
    required = {"schema_version", "client", "release", "method", "destination", "source", "fingerprint", "preflight", "backups"}
    if not isinstance(record, dict) or set(record) != required or type(record.get("schema_version")) is not int or record["schema_version"] != 1 or record.get("client") != client or record.get("destination") != str(destination):
        raise ValueError(f"Client ownership record does not own the selected entry point: {path}")
    if record.get("method") not in {"symlink", "import", "wrapper", "managed-block"} or not isinstance(record.get("backups"), list) or not isinstance(record.get("fingerprint"), str):
        raise ValueError(f"Client ownership record is malformed: {path}")
    if record["method"] == "managed-block":
        if not destination.is_file() or _managed_block_fingerprint(_single_managed_block(destination.read_text(encoding="utf-8"))) != record["fingerprint"]:
            raise ValueError(f"Managed Fabric block changed outside installer ownership: {destination}")
    elif (destination.exists() or destination.is_symlink()) and record["fingerprint"] != _artifact_fingerprint(destination):
        raise ValueError(f"Client artifact changed outside Fabric ownership and will not be replaced: {destination}")
    return record


def _backup_owned_client_artifact(home: Path, client: str, destination: Path, record: dict[str, Any]) -> dict[str, Any]:
    if destination.is_symlink():
        return {"kind": "symlink", "target": _symlink_target(destination), "release": record["release"], "method": record["method"], "source": record["source"]}
    if not destination.is_file():
        raise ValueError(f"Installer-owned client artifact is not a file or symlink: {destination}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = home / "backups" / "clients" / client / f"{timestamp}.md"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(destination, backup)
    return {"kind": "file", "path": str(backup.relative_to(home)), "release": record["release"], "method": record["method"], "source": record["source"]}


def _backup_managed_block(home: Path, client: str, destination: Path, record: dict[str, Any]) -> dict[str, Any]:
    block = _single_managed_block(destination.read_text(encoding="utf-8"))
    if _managed_block_fingerprint(block) != record["fingerprint"]:
        raise ValueError(f"Managed Fabric block changed outside installer ownership: {destination}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = home / "backups" / "clients" / client / f"{timestamp}.managed-block.md"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(block, encoding="utf-8")
    return {"kind": "managed-block", "path": str(backup.relative_to(home)), "release": record["release"], "method": record["method"], "source": record["source"]}


def _restore_client_artifact(
    home: Path,
    destination: Path,
    backup: dict[str, Any],
    *,
    allow_windows_elevation: bool = False,
) -> None:
    if backup["kind"] == "symlink":
        try:
            destination.symlink_to(backup["target"])
        except OSError as error:
            if not _requires_windows_symlink_elevation(error):
                raise
            if not allow_windows_elevation:
                raise PermissionError(
                    "Windows requires UAC permission to restore this native symbolic link. "
                    "Review `distribution rollback-client --preview`, then repeat with --elevate."
                ) from error
            target = Path(backup["target"])
            if not target.is_absolute():
                target = destination.parent / target
            _create_elevated_windows_symlink(target, destination)
    elif backup["kind"] == "file":
        shutil.copy2(home / backup["path"], destination)
    else:
        raise ValueError("Unknown client artifact backup kind")


def _remove_client_artifact(destination: Path) -> None:
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
        return
    if destination.exists():
        raise ValueError(f"Refusing to remove non-file client artifact: {destination}")


def _artifact_fingerprint(path: Path) -> str:
    if path.is_symlink():
        return "symlink:" + _symlink_target(path)
    return "file:" + _sha256(path)


def _symlink_target(path: Path) -> str:
    """Read a link target, including an elevated Windows link visible to a normal process."""
    try:
        return os.readlink(path)
    except OSError as error:
        if os.name != "nt" or getattr(error, "winerror", None) != 5:
            raise
        # An administrator-created NTFS link can be traversed by the original user
        # while Windows denies direct reparse-data reads. Resolve the existing link
        # instead; a broken or retargeted link fails closed here.
        return str(path.resolve(strict=True))


def _resolved_symlink_target(path: Path) -> Path:
    target = Path(_symlink_target(path))
    if not target.is_absolute():
        target = path.parent / target
    return target.resolve(strict=True)


def validate_project_binding(binding: dict[str, Any]) -> None:
    required = {"schema_version", "fabric_release", "client", "profile", "project_overlay", "enabled_packs"}
    if not isinstance(binding, dict) or set(binding) != required:
        raise ValueError("project binding must use the declared object shape")
    if type(binding.get("schema_version")) is not int or binding["schema_version"] != 1 or binding.get("client") not in SUPPORTED_CLIENTS:
        raise ValueError("invalid project binding identity")
    _validate_version(str(binding.get("fabric_release", "")))
    for field in ("profile", "project_overlay"):
        value = binding.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"project binding {field} must be a safe project-relative path")
        if not _safe_project_relative_path(value):
            raise ValueError(f"project binding {field} must be a safe project-relative path")
    packs = binding.get("enabled_packs")
    if not isinstance(packs, list) or len(set(packs)) != len(packs) or any(not isinstance(pack, str) or not pack for pack in packs):
        raise ValueError("project binding enabled_packs must be a unique string list")


def _safe_project_relative_path(value: str) -> bool:
    candidate = Path(value)
    windows_candidate = PureWindowsPath(value)
    return not candidate.is_absolute() and not windows_candidate.is_absolute() and not windows_candidate.root and ".." not in candidate.parts and ".." not in windows_candidate.parts


def _project_relative_path(project: Path, value: str) -> Path:
    if not _safe_project_relative_path(value):
        raise ValueError(f"Unsafe project-relative path: {value}")
    root = project.resolve()
    candidate = (root / value).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Project binding path escapes the project root: {value}")
    return candidate


def _project_contract_file(project: Path, value: str, label: str) -> Path:
    """Resolve an existing project contract and keep its real target in-project."""
    candidate = _project_relative_path(project, value)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"Project {label} is missing or cannot be resolved: {value}") from error
    root = project.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Project {label} escapes the project root: {value}")
    if not resolved.is_file():
        raise ValueError(f"Project {label} must be a file: {value}")
    return resolved


def _load_project_binding(path: Path) -> dict[str, Any]:
    try:
        binding = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid project binding: {path}") from error
    validate_project_binding(binding)
    return binding


def _validate_installed_release(fabric_home: Path, release: str) -> dict[str, Any]:
    _validate_version(release)
    home = fabric_home.expanduser().resolve()
    installation = load_installation(home)
    entry = next((candidate for candidate in installation["releases"] if candidate["version"] == release), None)
    if entry is None:
        raise ValueError(f"Fabric release is not installed: {release}")
    releases_root = home / "releases"
    release_directory = release_path(home, release)
    if releases_root.is_symlink() or release_directory.is_symlink():
        raise ValueError("Fabric release storage must not use symbolic links")
    resolved_releases_root = releases_root.resolve()
    resolved_release_directory = release_directory.resolve()
    if resolved_release_directory.parent != resolved_releases_root:
        raise ValueError("Fabric release directory escapes managed release storage")
    manifest = release_directory / RELEASE_MANIFEST_FILE
    if not manifest.is_file():
        raise ValueError(f"Fabric release manifest is missing: {manifest}")
    if _sha256(manifest) != entry["manifest_sha256"]:
        raise ValueError(f"Fabric release manifest integrity check failed: {manifest}")
    try:
        release_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Fabric release manifest is invalid JSON: {manifest}") from error
    if not isinstance(release_manifest, dict):
        raise ValueError(f"Fabric release manifest must be a JSON object: {manifest}")
    if type(release_manifest.get("schema_version")) is int and release_manifest.get("schema_version") == 1:
        # Pre-contract releases had no declared database version. Treat them as
        # schema 0 only for validation of an existing old binding; they cannot be
        # selected for a downgrade once a project has migrated forward.
        if release_manifest.get("version") != release or not isinstance(release_manifest.get("files"), dict):
            raise ValueError(f"Fabric release manifest has invalid structure: {manifest}")
        release_manifest = {
            **release_manifest,
            "memory": {"schema_version": 0, "minimum_compatible": 0},
        }
    elif set(release_manifest) != {"schema_version", "version", "created_at", "memory", "files"}:
        raise ValueError(f"Fabric release manifest has invalid structure: {manifest}")
    memory = release_manifest.get("memory")
    if (
        type(release_manifest.get("schema_version")) is not int
        or (
            release_manifest.get("schema_version") != 2
            and release_manifest.get("schema_version") != 1
        )
    ) or (
        release_manifest.get("version") != release
        or (
            release_manifest.get("schema_version") == 2
            and (
                not isinstance(release_manifest.get("created_at"), str)
                or not release_manifest["created_at"]
            )
        )
        or not isinstance(release_manifest.get("files"), dict)
        or not isinstance(memory, dict)
        or set(memory) != {"schema_version", "minimum_compatible"}
        or not all(type(memory.get(field)) is int and memory[field] >= 0 for field in ("schema_version", "minimum_compatible"))
        or memory["minimum_compatible"] > memory["schema_version"]
    ):
        raise ValueError(f"Fabric release manifest has invalid structure: {manifest}")
    release_root = manifest.parent.resolve()
    actual_files: set[str] = set()
    for path in release_root.rglob("*"):
        if path == manifest:
            continue
        if path.is_symlink():
            raise ValueError(f"Fabric release contains an undeclared symbolic link: {path.relative_to(release_root)}")
        if path.is_file():
            actual_files.add(path.relative_to(release_root).as_posix())
    declared_files = set(release_manifest["files"])
    if actual_files != declared_files:
        raise ValueError("Fabric release file set does not match its manifest")
    for relative, expected_hash in release_manifest["files"].items():
        if not isinstance(relative, str) or not re.fullmatch(r"[a-f0-9]{64}", str(expected_hash)):
            raise ValueError(f"Fabric release manifest has invalid file metadata: {manifest}")
        candidate = (release_root / relative).resolve()
        if not candidate.is_relative_to(release_root) or not candidate.is_file() or _sha256(candidate) != expected_hash:
            raise ValueError(f"Fabric release file integrity check failed: {relative}")
    return release_manifest


def _validate_bindable_release(fabric_home: Path, release: str) -> dict[str, Any]:
    """Allow a new binding only when this runtime can initialize matching memory."""
    manifest = _validate_installed_release(fabric_home, release)
    if manifest["memory"]["schema_version"] != MEMORY_SCHEMA_VERSION:
        raise ValueError(
            "Fabric release cannot initialize a new project with this runtime memory schema; "
            "legacy releases remain readable only for existing bindings"
        )
    return manifest


def _backup_project_binding(binding_path: Path) -> Path:
    backup_dir = binding_path.parent / "backups"
    if backup_dir.is_symlink():
        raise ValueError("Project binding backups must not use a symbolic link")
    if backup_dir.exists() and not backup_dir.is_dir():
        raise ValueError("Project binding backup path must be a directory")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = backup_dir / f"fabric-binding-{timestamp}.json"
    shutil.copy2(binding_path, backup)
    return backup


def _pending_project_update_path(project: Path) -> Path:
    return state_path(project, f"updates/{PROJECT_UPDATE_FILE}")


def _load_pending_project_update(path: Path) -> dict[str, Any]:
    try:
        pending = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid pending project update record: {path}") from error
    required = {"schema_version", "from_release", "to_release", "binding", "backup", "stage"}
    if (
        not isinstance(pending, dict)
        or set(pending) != required
        or type(pending.get("schema_version")) is not int
        or pending["schema_version"] != 1
        or pending.get("stage") not in {"prepared", "memory-migrated"}
        or not all(isinstance(pending.get(field), str) and pending[field] for field in ("from_release", "to_release", "binding", "backup"))
    ):
        raise ValueError(f"Invalid pending project update record: {path}")
    _validate_version(pending["from_release"])
    _validate_version(pending["to_release"])
    return pending


def _ensure_project_configuration(project: Path) -> None:
    """Create only target-owned state; no shared role or gate data is copied here."""
    state_directory(project, create=True)
    profile_path = state_path(project, "profile.json", create_parents=True)
    if not profile_path.exists():
        _write_json(profile_path, default_project_profile(project.name))
    capabilities_path = state_path(project, "config/capabilities.json", create_parents=True)
    if not capabilities_path.exists():
        _write_json(capabilities_path, default_capabilities())
    work_tracking_path = state_path(project, "config/work-tracking.json", create_parents=True)
    if not work_tracking_path.exists():
        _write_json(work_tracking_path, default_config())
    routing_path = state_path(project, "config/model-routing.json", create_parents=True)
    if not routing_path.exists():
        _write_json(routing_path, default_routing())
    initialize(project)


def _load_project_profile(path: Path) -> dict[str, Any]:
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid project profile: {path}") from error
    if not isinstance(profile, dict):
        raise ValueError(f"Invalid project profile: {path}")
    validate_project_profile(profile)
    return profile


def _validate_source(source: Path) -> None:
    required = (source / "pyproject.toml", source / "src" / "ai_agent_fabric", source / "schemas")
    if not source.is_dir() or any(not item.exists() for item in required):
        raise ValueError(f"Source is not an AI Agent Fabric repository: {source}")


def _source_version(source: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', (source / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError("Could not determine Fabric version from pyproject.toml")
    return match.group(1)


def _validate_version(version: str) -> None:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("Fabric version must be a safe release identifier")


def _copy_asset(source: Path, destination: Path, relative: str) -> None:
    origin = source / relative
    target = destination / relative
    if not origin.exists():
        raise ValueError(f"Release source asset is missing: {origin}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if origin.is_dir():
        shutil.copytree(origin, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(origin, target)


def _write_release_adapters(release: Path) -> None:
    # The globally installed launcher resolves the active immutable release.
    # Client bootstrap must not pin users to this release's private launcher.
    launcher = _global_launcher_command(release.parents[1])
    for client in SUPPORTED_CLIENTS:
        adapter_dir = release / "adapters" / client
        adapter_dir.mkdir(parents=True, exist_ok=True)
        _write_json(adapter_dir / "adapter-manifest.json", adapter_manifest(client))
        bootstrap = (
            "# AI Agent Fabric global bootstrap\n\n"
            "This managed user-level instruction provides the shared Fabric only. "
            "It never supplies project commands, tracker settings, secrets, task content, or memory.\n\n"
            "Do not assume the current global release applies to a repository.\n\n"
            "When the current repository contains `.agent-fabric/fabric-binding.json`, read that "
            "binding, then run the read-only command "
            f"`{launcher} project context <project-root> --json`. Use only its returned shared "
            "contract paths and project-contract paths before selecting work. The returned context "
            "does not expose project memory, task contents, or secrets.\n\n"
            "When no binding exists, report that Fabric is available but this project is not bound. "
            f"First run `{launcher} project status <project-root>` as a read-only discovery step. "
            "Do not create files merely because the repository was opened. After the user explicitly "
            f"asks to initialize this project, first run `{launcher} project init <project-root> "
            f"--client {client} --preview`; create the binding only after the preview is accepted.\n\n"
            "The installed skills-only package **Agent Fabric** owns the portable workflow Skills "
            "for work routing, task start/restore, and Harness review. When the user asks for one "
            "of those workflows, use the matching Agent Fabric skill. The bound release supplies "
            "only shared contracts and project rules.\n\n"
            + ("For Codex: after successful `start --apply` or `restore`, read `socrates_chat_request`. Root must create or reopen the named separate Socrates chat, pass it the task id and created chat thread id, then stop task work. Only that chat may run the returned Socrates activation command and own planning, delegation, implementation decisions, durable state, and task-user communication. Root must not present itself as Socrates. If start, restore, chat creation, or activation-packet delivery fails, Root may only report the failure and use the explicit Fabric recovery path.\n\n" if client == "codex" else "")
            + f"The canonical global Fabric launcher is `{launcher}`. Use it for every Fabric command; "
            "it selects the active installed release. A project path only selects that project's local "
            "context and never supplies a project-local executable.\n\n"
            "When the user corrects agent behaviour in a bound project, record only a minimal "
            "project-local Harness signal with the launcher. Never copy the conversation, commands, "
            "or secrets into that signal. Do not claim automatic capture unless this adapter manifest "
            "declares an installed hook implementation.\n"
        )
        (adapter_dir / "bootstrap.md").write_text(bootstrap, encoding="utf-8")


def _write_release_core(release: Path) -> None:
    """Materialize shared authority once per immutable Fabric release."""
    core = release / "core"
    core.mkdir(parents=True, exist_ok=True)
    _write_json(core / "agent-profiles.json", default_profiles())
    gates = default_gates()
    validate_gates(gates)
    _write_json(core / "gates.json", gates)


def _write_release_launcher(release: Path) -> None:
    """Write the portable Bash launcher used by a release bootstrap."""
    launcher = release / "bin" / "ai-agent-fabric"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "fabric_release_dir=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")/..\" && pwd)\"\n"
        "fabric_home_dir=\"$(cd -- \"${fabric_release_dir}/../..\" && pwd)\"\n"
        "export AI_AGENT_FABRIC_HOME=\"${fabric_home_dir}\"\n"
        "export PYTHONPATH=\"${fabric_release_dir}/src${PYTHONPATH:+:${PYTHONPATH}}\"\n"
        "export PYTHONDONTWRITEBYTECODE=1\n"
        "fabric_python=\"\"\n"
        "for candidate_python in python3 python; do\n"
        "  if command -v \"${candidate_python}\" >/dev/null 2>&1 && \"${candidate_python}\" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then\n"
        "    fabric_python=\"${candidate_python}\"\n"
        "    break\n"
        "  fi\n"
        "done\n"
        "if [[ -z \"${fabric_python}\" ]]; then\n"
        "  printf '%s\\n' 'AI Agent Fabric requires Python 3.10 or newer. Install it, then retry.' >&2\n"
        "  exit 127\n"
        "fi\n"
        "exec \"${fabric_python}\" -m ai_agent_fabric \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)


def _write_global_launcher(fabric_home: Path) -> None:
    """Write the one user-level launcher that routes to the active release."""
    launcher = fabric_home / "bin" / "ai-agent-fabric"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "fabric_home_dir=\"$(cd -- \"$(dirname -- \"${BASH_SOURCE[0]}\")/..\" && pwd)\"\n"
        "fabric_python=\"\"\n"
        "for candidate_python in python3 python; do\n"
        "  if command -v \"${candidate_python}\" >/dev/null 2>&1; then\n"
        "    fabric_python=\"${candidate_python}\"\n"
        "    break\n"
        "  fi\n"
        "done\n"
        "if [[ -z \"${fabric_python}\" ]]; then\n"
        "  printf '%s\\n' 'AI Agent Fabric requires Python to select its active release.' >&2\n"
        "  exit 127\n"
        "fi\n"
        "current_release=\"$(\"${fabric_python}\" - \"${fabric_home_dir}/installation.json\" <<'PY'\n"
        "import json\n"
        "import pathlib\n"
        "import sys\n"
        "with pathlib.Path(sys.argv[1]).open(encoding='utf-8') as file:\n"
        "    print(json.load(file)['current_release'])\n"
        "PY\n"
        ")\"\n"
        "exec bash \"${fabric_home_dir}/releases/${current_release}/bin/ai-agent-fabric\" \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    python_launcher = fabric_home / "bin" / "ai-agent-fabric.py"
    python_launcher.write_text(
        "from __future__ import annotations\n\n"
        "import json\n"
        "from pathlib import Path\n"
        "import sys\n\n"
        "sys.dont_write_bytecode = True\n"
        "for stream in (sys.stdout, sys.stderr):\n"
        "    if hasattr(stream, 'reconfigure'):\n"
        "        stream.reconfigure(encoding='utf-8', errors='strict')\n"
        "home = Path(__file__).resolve().parent.parent\n"
        "with (home / 'installation.json').open(encoding='utf-8') as file:\n"
        "    release = json.load(file)['current_release']\n"
        "sys.path.insert(0, str(home / 'releases' / release / 'src'))\n"
        "from ai_agent_fabric.__main__ import main\n\n"
        "main()\n",
        encoding="utf-8",
    )


def _global_launcher_command(fabric_home: Path) -> str:
    """Return a runtime-safe global CLI command for generated client bootstraps."""
    if os.name == "nt":
        return f'"{sys.executable}" "{fabric_home / "bin" / "ai-agent-fabric.py"}"'
    return _bash_launcher_command(fabric_home / "bin" / "ai-agent-fabric")


def _bash_launcher_command(script: Path) -> str:
    """Return a host-correct command for the global Bash launcher.

    Windows can expose a WSL shim named ``bash`` ahead of Git Bash on PATH. Fabric
    therefore names a verified Git Bash executable when one is present instead of
    relying on the ambiguous command name.
    """
    if os.name == "nt":
        candidates = (
            Path(os.environ.get("AI_AGENT_FABRIC_BASH", "")) if os.environ.get("AI_AGENT_FABRIC_BASH") else None,
            Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "Git" / "bin" / "bash.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")) / "Git" / "bin" / "bash.exe",
        )
        for candidate in candidates:
            if candidate is not None and candidate.is_file():
                return f'"{candidate}" "{script}"'
    return f"bash {shlex.quote(str(script))}"


def _write_global_adapters(fabric_home: Path, release: Path) -> None:
    """Refresh stable client bootstrap paths after the active release changes."""
    for client in SUPPORTED_CLIENTS:
        source = release / "adapters" / client / "bootstrap.md"
        if not source.is_file():
            raise ValueError(f"Release is missing the {client} bootstrap: {source}")
        destination = fabric_home / "adapters" / client / "bootstrap.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    _refresh_stable_client_record_releases(fabric_home, release.name)


def _refresh_stable_client_record_releases(fabric_home: Path, release: str) -> None:
    """Advance records which point at stable adapter paths after a release switch.

    The user-owned entry point remains unchanged for a managed block, so only an
    ownership record which still matches that block may be advanced.  Records
    for copied, imported, or externally edited artifacts remain untouched.
    """
    for client in SUPPORTED_CLIENTS:
        record_path = client_record_path(fabric_home, client)
        if not record_path.is_file():
            continue
        destination = client_entry_point(client)
        try:
            record = _load_client_record(record_path, client, destination)
            stable_source = fabric_home / "adapters" / client / "bootstrap.md"
            if record["method"] != "managed-block" or Path(record["source"]) != stable_source:
                continue
            current_block = _single_managed_block(destination.read_text(encoding="utf-8"))
            if _managed_block_fingerprint(current_block) != record["fingerprint"]:
                continue
        except (OSError, ValueError):
            continue
        if record["release"] != release:
            record["release"] = release
            _write_json(record_path, record)


def _write_global_skills(fabric_home: Path, release: Path) -> None:
    """Refresh the Fabric-owned stable skill sources used by client links."""
    source_root = release / "skills"
    destination_root = fabric_home / "skills"
    for name in CODEX_SKILL_NAMES:
        source = source_root / name
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"Release is missing required Fabric skill: {source}")
        destination = destination_root / name
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink():
                destination.unlink()
            else:
                shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
    _refresh_codex_skill_record_release(fabric_home, release.name)


def _write_global_codex_marketplace(fabric_home: Path, release: str) -> None:
    """Materialize the Fabric-owned Codex plugin marketplace source."""
    root = fabric_home / "marketplace"
    plugin = root / "plugins" / "agent-fabric"
    skills = plugin / "skills"
    if plugin.exists() or plugin.is_symlink():
        if plugin.is_symlink():
            plugin.unlink()
        else:
            shutil.rmtree(plugin)
    skills.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fabric_home / "skills", skills)
    release_hooks = fabric_home / "releases" / release / "hooks"
    if not (release_hooks / "hooks.json").is_file():
        raise ValueError(f"Release is missing the Codex hook configuration: {release_hooks}")
    shutil.copytree(release_hooks, plugin / "hooks")
    manifest = {
        "name": "agent-fabric",
        "version": release,
        "description": "Portable project-scoped agent workflow, memory, task routing, and Harness retrospective skills.",
        "skills": "./skills/",
        "hooks": "./hooks/hooks.json",
        "interface": {
            "displayName": "Agent Fabric",
            "shortDescription": "Project-local agent workflow and memory",
            "longDescription": "Reusable Agent Fabric skills for routing work, starting and restoring task packages, and reviewing project-local Harness lessons.",
            "category": "Productivity",
            "capabilities": [],
        },
    }
    manifest_path = plugin / ".codex-plugin" / "plugin.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(manifest_path, manifest)
    marketplace = {
        "name": "agent-fabric-local",
        "interface": {"displayName": "Agent Fabric"},
        "plugins": [
            {
                "name": "agent-fabric",
                "source": {"source": "local", "path": "./plugins/agent-fabric"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(marketplace_path, marketplace)


def _refresh_codex_skill_record_release(fabric_home: Path, release: str) -> None:
    record_path = codex_skill_record_path(fabric_home)
    if not record_path.is_file():
        return
    try:
        record = _load_codex_skill_record(record_path, fabric_home)
    except ValueError:
        return
    if record["release"] != release:
        record["release"] = release
        _write_json(record_path, record)


def _owned_codex_skill_link(destination: Path, source: Path) -> bool:
    return destination.is_symlink() and destination.resolve(strict=True) == source.resolve(strict=True)


def _load_codex_skill_record(path: Path, fabric_home: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid Codex skill ownership record: {path}") from error
    expected = {"schema_version", "client", "release", "skills"}
    if not isinstance(record, dict) or set(record) != expected or record.get("schema_version") != 1 or record.get("client") != "codex" or not isinstance(record.get("skills"), dict) or set(record["skills"]) != set(CODEX_SKILL_NAMES):
        raise ValueError(f"Invalid Codex skill ownership record: {path}")
    for name in CODEX_SKILL_NAMES:
        entry = record["skills"].get(name)
        source = fabric_home / "skills" / name
        destination = codex_skill_root() / name
        if not isinstance(entry, dict) or entry.get("source") != str(source) or entry.get("destination") != str(destination) or not _owned_codex_skill_link(destination, source):
            raise ValueError(f"Fabric does not own the Codex skill link: {destination}")
    return record


def _release_generated_paths(release: Path) -> list[Path]:
    paths = [
        release / "core" / "agent-profiles.json",
        release / "core" / "gates.json",
        release / "bin" / "ai-agent-fabric",
    ]
    for client in SUPPORTED_CLIENTS:
        paths.extend([
            release / "adapters" / client / "adapter-manifest.json",
            release / "adapters" / client / "bootstrap.md",
        ])
    return paths


def _release_manifest(release: Path, version: str) -> dict[str, Any]:
    hashes = {
        path.relative_to(release).as_posix(): _sha256(path)
        for path in sorted(release.rglob("*"))
        if path.is_file() and path.name != RELEASE_MANIFEST_FILE
    }
    return {
        "schema_version": 2,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "memory": {
            "schema_version": MEMORY_SCHEMA_VERSION,
            "minimum_compatible": 0,
        },
        "files": hashes,
    }


def _migrate_project_memory(project: Path, fabric_home: Path, release: str) -> None:
    """Run the selected release's explicit migration before moving a binding."""
    target_manifest = _validate_installed_release(fabric_home, release)
    target_version = target_manifest["memory"]["schema_version"]
    current_version = schema_version(project)
    if current_version < target_manifest["memory"]["minimum_compatible"]:
        raise ValueError("Project memory is older than the selected release's supported migration floor")
    if current_version > target_version:
        raise ValueError("Project memory is newer than the selected release and cannot be downgraded")
    if current_version == target_version:
        return
    launcher = release_path(fabric_home, release) / "bin" / "ai-agent-fabric"
    if not launcher.is_file():
        raise ValueError(f"Selected release has no launcher: {launcher}")
    environment = os.environ.copy()
    environment["AI_AGENT_FABRIC_HOME"] = str(fabric_home)
    release_source = str(release_path(fabric_home, release) / "src")
    environment["PYTHONPATH"] = release_source + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    subprocess.run(
        [sys.executable, "-B", "-m", "ai_agent_fabric", "memory", "init", str(project), "--home", str(fabric_home)],
        check=True,
        env=environment,
        stdout=subprocess.DEVNULL,
    )
    if schema_version(project) != target_version:
        raise ValueError("Selected release did not produce its declared memory schema version")


def _update_installation(home: Path, version: str, release_manifest_path: Path) -> None:
    path = installation_path(home)
    if path.exists():
        previous = load_installation(home)
        backups = home / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(path, backups / f"installation-{timestamp}.json")
        releases = [entry for entry in previous["releases"] if entry["version"] != version]
    else:
        releases = []
    releases.append(
        {
            "version": version,
            "path": f"releases/{version}",
            "manifest_sha256": _sha256(release_manifest_path),
        }
    )
    manifest = {"schema_version": 1, "fabric_home": str(home), "current_release": version, "releases": releases}
    validate_installation_manifest(manifest)
    _write_json(path, manifest)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(path)
