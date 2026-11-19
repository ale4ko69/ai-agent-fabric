from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import posixpath
import stat
from typing import Any

from . import distribution
from .clients import detect_client
from .environment import detect_environment
from .project_install import (
    DIGEST_PATTERN, _check_path, _digest, _json_bytes, _portable_component,
    _write_new, checked_directory, load_project_installation,
)


CODEX_REVISION = "d52a39b307b77e81cd272d08189341d944542b82"
AGENT_DIRECTORY = "adapters/codex-project/agents"
SKILL_DIRECTORY = "skills/project-entry"
RECEIPT = ".agent-fabric/codex-project-installation.json"
PENDING = ".agent-fabric/codex-project-pending.json"
PERSONAS = {
    "orchestrator": "socrates", "explore": "aristotle", "plan": "plato",
    "opponent": "kepler", "dev": "heracles", "review": "athena",
    "validation": "euclid", "maintenance": "metis",
}
COMMON_BOUNDARY = (
    "Use only the project's pinned local Fabric launcher: "
    "python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py. "
    "Run from the verified project root and inspect project context before task work. "
    "These persona instructions do not grant tools, sandbox permissions, model selection, "
    "task ownership or approval. Root is entry/recovery only, not Socrates. "
    "Only a separate, real task chat may become Socrates after claiming its durable task id "
    "with that chat's real Desktop thread ID. Native subagents are not Socrates chats. "
    "Never invent a thread ID, invoke an undocumented Desktop API, or substitute Root. "
    "Creation/reopening and transfer are explicit and manual. If identity or reopening is "
    "unavailable, stop and report that limitation. Installation of these files proves neither "
    "Desktop discovery nor claim/restore support.\n"
)


def render_project_agents(profiles: dict[str, Any], documents: dict[str, bytes]) -> dict[str, bytes]:
    """Рендерить общий registry и его readable companions один раз до хеширования release."""
    entries = profiles.get("profiles") if isinstance(profiles, dict) else None
    if not isinstance(profiles, dict) or profiles.get("schema_version") != 1 or not isinstance(entries, list) or len(entries) != len(PERSONAS):
        raise ValueError("Codex project rendering requires the canonical profile registry")
    rendered: dict[str, bytes] = {}
    seen: set[str] = set()
    for profile in entries:
        role = profile["id"]
        persona = PERSONAS.get(role)
        if persona is None or role in seen or profile["persona"].lower() != persona:
            raise ValueError("Codex project persona identities do not match the canonical registry")
        seen.add(role)
        document = documents[persona].decode("utf-8")
        boundary = (
            "If invoked as a native subagent, do not claim a task or write durable memory; "
            "return a needs-real-socrates-chat result to Root. In a real separate task chat, "
            "claim only after verifying its actual thread identity and owner-authorized transfer.\n"
            if role == "orchestrator" else
            "Accept bounded delegation only from the claimed Socrates chat. Return structured "
            "results and artifact references; do not claim tasks or write durable task memory.\n"
        )
        instructions = (
            COMMON_BOUNDARY + boundary + "\nCanonical machine profile:\n"
            + json.dumps(profile, ensure_ascii=False, sort_keys=True)
            + "\n\nCanonical readable companion:\n" + document
        )
        # JSON basic strings с экранированными переводами строк совместимы с TOML basic strings.
        description = json.dumps(profile["purpose"], ensure_ascii=False)
        rendered[persona] = (
            f"name = {json.dumps(persona)}\n"
            f"description = {description}\n"
            f"developer_instructions = {json.dumps(instructions, ensure_ascii=False)}\n"
        ).encode("utf-8")
    return rendered


def _links(version: str) -> list[dict[str, str]]:
    """Единственный список разрешённых относительных client links, без config/instruction writes."""
    prefix = f".agent-fabric/runtime/releases/{version}"
    links = []
    for persona in PERSONAS.values():
        path = f".codex/agents/{persona}.toml"
        target = f"{prefix}/{AGENT_DIRECTORY}/{persona}.toml"
        links.append({"path": path, "target": posixpath.relpath(target, posixpath.dirname(path)), "kind": "file"})
    path = ".agents/skills/agent-fabric-project"
    links.append({
        "path": path, "target": posixpath.relpath(f"{prefix}/{SKILL_DIRECTORY}", posixpath.dirname(path)),
        "kind": "directory",
    })
    return links


def _runtime(target: str | Path) -> tuple[Path, dict[str, Any], str]:
    """Только intact project-local runtime; global registry и исполняемый Codex не используются."""
    project = checked_directory(target, owned=True)
    runtime = load_project_installation(project)
    home = Path(runtime["fabric_home"])
    distribution._validate_installed_release(home, runtime["fabric_release"])
    manifest = home / "releases" / runtime["fabric_release"] / "release-manifest.json"
    return project, runtime, hashlib.sha256(manifest.read_bytes()).hexdigest()


def _case_conflict(parent: Path, name: str) -> None:
    """Не принимать case alias на POSIX, который станет конфликтом при переносе на Windows."""
    if parent.exists() and any(item.name.casefold() == name.casefold() and item.name != name for item in parent.iterdir()):
        raise FileExistsError(f"Case-ambiguous client path: {parent / name}")


def _observe_link(project: Path, link: dict[str, str]) -> None:
    """Проверить native symlink и его точную цель; это наблюдение filesystem, не Desktop."""
    destination = project / link["path"]
    _check_path(destination.parent, owned=True)
    info = destination.lstat()
    if not stat.S_ISLNK(info.st_mode) or getattr(destination, "is_junction", lambda: False)():
        raise ValueError(f"Expected a native symbolic link, not a copy or junction: {destination}")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise ValueError(f"Symbolic link ownership conflict: {destination}")
    observed = os.readlink(destination).replace("\\", "/")
    if Path(observed).is_absolute() or PureWindowsPath(observed).drive or observed != link["target"]:
        raise ValueError(f"Symbolic link target conflict: {destination}")
    expected = Path(os.path.abspath(destination.parent / link["target"]))
    if not expected.is_relative_to(project / ".agent-fabric/runtime/releases"):
        raise ValueError(f"Symbolic link escapes the pinned release: {destination}")
    target_info = _check_path(expected, owned=True)
    predicate = stat.S_ISDIR if link["kind"] == "directory" else stat.S_ISREG
    if not predicate(target_info.st_mode) or destination.resolve(strict=True) != expected:
        raise ValueError(f"Symbolic link is not observable at its pinned target: {destination}")


def _plan(target: str | Path) -> dict[str, Any]:
    """Read-only adapter preview не создаёт пробные links и не меняет immutable release."""
    project, runtime, manifest_hash = _runtime(target)
    distribution.require_bound_project(project, Path(runtime["fabric_home"]))
    environment = detect_environment()
    detected = detect_client(project)
    for relative in (RECEIPT, PENDING, ".codex"):
        candidate = project / relative
        _check_path(candidate.parent, owned=True)
        _case_conflict(candidate.parent, candidate.name)
        if os.path.lexists(candidate):
            raise FileExistsError(f"Existing client state will not be overwritten or merged: {candidate}")
    directories = [".codex", ".codex/agents"]
    existing: dict[str, Any] = {}
    for relative in (".", ".agents", ".agents/skills"):
        candidate = project / relative
        if relative != "." and candidate.parent.exists():
            _check_path(candidate.parent, owned=True)
            _case_conflict(candidate.parent, candidate.name)
        if os.path.lexists(candidate):
            info = _check_path(candidate, owned=True)
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"Client path parent must be an ordinary directory: {candidate}")
            existing[relative] = {
                "device": info.st_dev, "inode": info.st_ino, "mode": info.st_mode,
                "owner": getattr(info, "st_uid", 0),
            }
        elif relative != ".":
            directories.append(relative)
    links = _links(runtime["fabric_release"])
    for link in links:
        destination = project / link["path"]
        if destination.parent.exists():
            _case_conflict(destination.parent, destination.name)
        if os.path.lexists(destination):
            raise FileExistsError(f"Existing client link destination: {destination}")
        source = Path(os.path.abspath(destination.parent / link["target"]))
        try:
            _check_path(source, owned=True)
        except FileNotFoundError as error:
            raise ValueError("Pinned release lacks project adapter assets; use a fresh reviewed runtime release") from error
    plan = {
        "schema_version": 1, "mode": "codex-project", "client": "codex",
        "project_root": str(project), "fabric_release": runtime["fabric_release"],
        "release_manifest_sha256": manifest_hash, "format_revision": CODEX_REVISION,
        "existing_directories": existing, "environment": environment.kind,
        "detected_clients": list(detected.candidates),
        "directories": sorted(directories), "files": [RECEIPT], "links": links,
        "transient_paths": [PENDING],
        "desktop_discovery": "unverified", "claim_restore": "unverified",
    }
    plan["preview_sha256"] = _digest(plan)
    return plan


def codex_project_preview(target: str | Path) -> dict[str, Any]:
    """Отдельный preview показывает только client adapter writes, а не установку runtime."""
    return _plan(target)


def validate_codex_project_installation(record: dict[str, Any]) -> None:
    """Ownership допускает только известные native links и не может утверждать Desktop success."""
    fields = {
        "schema_version", "mode", "client", "project_root", "fabric_release",
        "release_manifest_sha256", "format_revision", "preview_sha256",
        "directories", "links", "desktop_discovery", "claim_restore",
    }
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError("Codex project ownership must use the declared object shape")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1 or record["mode"] != "codex-project" or record["client"] != "codex":
        raise ValueError("Invalid Codex project ownership identity")
    if record["desktop_discovery"] != "unverified" or record["claim_restore"] != "unverified" or record["format_revision"] != CODEX_REVISION:
        raise ValueError("Adapter files cannot attest Desktop discovery or claim/restore")
    for field in ("release_manifest_sha256", "preview_sha256"):
        if not isinstance(record[field], str) or not DIGEST_PATTERN.fullmatch(record[field]):
            raise ValueError("Invalid Codex project ownership digest")
    version = record["fabric_release"]
    if not isinstance(version, str) or not _portable_component(version):
        raise ValueError("Invalid Codex project release")
    distribution._validate_version(version)
    if not isinstance(record["project_root"], str) or not Path(record["project_root"]).is_absolute():
        raise ValueError("Codex project root must be absolute")
    directories = record["directories"]
    allowed = {".codex", ".codex/agents", ".agents", ".agents/skills"}
    if not isinstance(directories, list) or any(not isinstance(item, str) for item in directories):
        raise ValueError("Invalid Codex project directory inventory")
    if len(set(directories)) != len(directories) or not {".codex", ".codex/agents"}.issubset(directories) or not set(directories).issubset(allowed):
        raise ValueError("Codex project directory inventory escapes its scope")
    if record["links"] != _links(version):
        raise ValueError("Codex project link inventory must match the pinned persona and entry links")


def install_codex_project(target: str | Path, *, expected_preview_sha256: str) -> dict[str, Any]:
    """Заново проверить preview, затем создать native links; сбой сохраняет pending ownership."""
    plan = _plan(target)
    if not isinstance(expected_preview_sha256, str) or not DIGEST_PATTERN.fullmatch(expected_preview_sha256) or expected_preview_sha256 != plan["preview_sha256"]:
        raise ValueError("Codex project preview digest is stale or invalid; review a fresh preview")
    project = Path(plan["project_root"])
    record = {key: value for key, value in plan.items() if key not in {
        "existing_directories", "environment", "detected_clients", "files", "transient_paths",
    }}
    validate_codex_project_installation(record)
    pending_data = _json_bytes(record)
    _write_new(project, PENDING, pending_data)
    active = PENDING
    try:
        for relative in sorted(plan["directories"], key=lambda item: (len(Path(item).parts), item)):
            active = relative
            _check_path((project / relative).parent, owned=True)
            (project / relative).mkdir(mode=0o700)
        for link in plan["links"]:
            active = link["path"]
            _check_path((project / active).parent, owned=True)
            os.symlink(link["target"], project / active, target_is_directory=link["kind"] == "directory")
            _observe_link(project, link)
        active = RECEIPT
        _write_new(project, RECEIPT, _json_bytes(record))
        _check_path(project / PENDING, owned=True)
        if (project / PENDING).read_bytes() != pending_data:
            raise ValueError("Pending Codex ownership changed during apply")
        (project / PENDING).unlink()
    except (OSError, ValueError) as error:
        raise OSError(
            f"Codex project adapter incomplete at {active}: {error}. "
            f"Inspect {PENDING} and any created paths manually. No copy, junction or elevation fallback was attempted. "
            "Desktop discovery and claim/restore remain unverified."
        ) from error
    return {**plan, **codex_project_status(project)}


def codex_project_status(target: str | Path) -> dict[str, Any]:
    """Отделить observed filesystem от unverified Desktop; повреждение адаптера не подменять успехом."""
    report: dict[str, Any] = {
        "file_installation": "absent", "desktop_discovery": "unverified", "claim_restore": "unverified",
    }
    try:
        project, runtime, manifest_hash = _runtime(target)
        if os.path.lexists(project / PENDING):
            report.update({"file_installation": "incomplete", "pending_ownership": PENDING})
            return report
        if not os.path.lexists(project / RECEIPT):
            if os.path.lexists(project / ".codex"):
                report["file_installation"] = "unmanaged"
            return report
        _check_path(project / RECEIPT, owned=True)
        record = json.loads((project / RECEIPT).read_text(encoding="utf-8"))
        validate_codex_project_installation(record)
        if record["project_root"] != str(project) or record["fabric_release"] != runtime["fabric_release"] or record["release_manifest_sha256"] != manifest_hash:
            raise ValueError("Codex project ownership does not match the pinned local runtime")
        for relative in record["directories"]:
            if not stat.S_ISDIR(_check_path(project / relative, owned=True).st_mode):
                raise ValueError(f"Codex project directory ownership conflict: {relative}")
        if {path.name for path in (project / ".codex").iterdir()} != {"agents"} or (
            {path.name for path in (project / ".codex/agents").iterdir()}
            != {f"{persona}.toml" for persona in PERSONAS.values()}
        ):
            raise ValueError("Unmanaged config, instructions or agents appeared in owned .codex scope")
        for link in record["links"]:
            _observe_link(project, link)
        report.update({"file_installation": "installed", "ownership": RECEIPT, "links_observed": len(record["links"])})
    except (OSError, ValueError) as error:
        report.update({"file_installation": "invalid", "error": str(error)})
    return report
