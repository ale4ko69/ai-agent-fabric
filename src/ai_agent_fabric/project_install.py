from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
from typing import Any

from . import distribution
from .agent_profiles import default_capabilities, default_profiles
from .clients import detect_client
from .environment import detect_environment
from .gates import default_gates
from .installer import default_project_profile, validate_project_profile
from .memory import MEMORY_SCHEMA_VERSION, initialize
from .model_routing import default_routing
from .work_tracking import default_config


PROJECT_INSTALLATION_FILE = "project-installation.json"
RUNTIME_DIRECTORY = ".agent-fabric/runtime"
LAUNCHER = f"{RUNTIME_DIRECTORY}/bin/ai-agent-fabric.py"
EXCLUDED_ASSETS = {".codex-plugin", "hooks", "release-source.json"}
DIGEST_PATTERN = re.compile(r"[a-f0-9]{64}")
RESERVED_COMPONENT = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.IGNORECASE)
PROJECT_RELEASE_EPOCH = "1970-01-01T00:00:00+00:00"


def _portable_component(value: str) -> bool:
    """Не допускать NTFS aliases/streams даже при подготовке runtime на POSIX."""
    return bool(value) and value not in {".", ".."} and not (
        any(character in value for character in "\\:<>\"|?*")
        or any(ord(character) < 32 for character in value)
        or value.endswith((" ", "."))
        or RESERVED_COMPONENT.match(value)
    )


def _check_path(path: Path, *, owned: bool = False) -> os.stat_result:
    """Проверить компоненты до resolve; installer и launcher не принимают перенаправления."""
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Links and reparse points are not allowed: {component}")
        if component != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"Path parent must be a directory: {component}")
    if owned and hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise ValueError(f"Path ownership conflict: {path}")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise ValueError(f"Hard-linked files are not allowed: {path}")
    return info


def checked_directory(value: str | Path, *, owned: bool = False) -> Path:
    """Сохранить лексическую проверку CLI-пути до нормализации, включая чужой формат ОС."""
    text = str(value)
    windows = PureWindowsPath(text)
    if (
        not text or "\x00" in text
        or (os.name != "nt" and ("\\" in text or windows.drive))
        or ".." in re.split(r"[/\\]", text)
        or any(not _portable_component(part) for part in Path(text).parts if part not in {".", Path(text).anchor})
        or text.startswith("//")
        or (os.name == "nt" and (
            text.startswith(("\\\\", "//"))
            or bool(windows.drive) != bool(windows.root)
        ))
    ):
        raise ValueError("Path must be unambiguous and must not contain traversal")
    path = Path(os.path.abspath(text))
    info = _check_path(path, owned=owned)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"Existing directory required: {path}")
    return path


def _json_bytes(value: dict[str, Any]) -> bytes:
    """Одинаковое представление контрактов для snapshot и публикации."""
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _digest(value: dict[str, Any]) -> str:
    """Связать preview со всеми входами и перечисленными выходами, без текущего времени."""
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _snapshot(source: Path, release_prefix: str) -> tuple[dict[str, bytes], set[str]]:
    """Считать доверенные исходники в память; после mkdir не исполнять и не копировать source."""
    distribution._validate_release_assets(source)
    files: dict[str, bytes] = {}
    directories: set[str] = set()
    for relative in distribution.RELEASE_ASSETS:
        if relative in EXCLUDED_ASSETS:
            continue
        # Из scripts нужен только runtime-helper, не installer и не клиентские entry points.
        if relative == "scripts":
            relative = "scripts/secret-entry.sh"
        elif relative == "skills":
            relative = "skills/project-entry"
        origin = source / relative
        for item in [origin, *sorted(origin.rglob("*"))] if origin.is_dir() else [origin]:
            if "__pycache__" in item.parts or item.suffix == ".pyc":
                continue
            info = _check_path(item)
            if any(not _portable_component(part) for part in item.relative_to(source).parts):
                raise ValueError(f"Ambiguous source asset name: {item}")
            destination = f"{release_prefix}/{item.relative_to(source).as_posix()}"
            if stat.S_ISDIR(info.st_mode):
                directories.add(destination)
            elif stat.S_ISREG(info.st_mode):
                files[destination] = item.read_bytes()
            else:
                raise ValueError(f"Source contains a non-regular asset: {item}")
    return files, directories


def _plan(target: str | Path, source_root: str | Path, client: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Подготовить все проверяемые байты, включая manifest/index/launcher, без записи.

    created_at — фиксированная эпоха воспроизводимой сборки, не время установки.
    file_sha256 покрывает только подготовленные файлы; SQLite создаётся initializer,
    а receipt содержит итоговый preview_sha256 и поэтому не хеширует сам себя.
    Эти два runtime_created_files и возможные SQLite sidecars перечисляются отдельно.
    """
    project = checked_directory(target, owned=True)
    source = checked_directory(source_root)
    if client != "codex":
        raise ValueError("Project runtime installation currently requires --client codex")
    environment = detect_environment()
    detected_client = detect_client(project)
    state = project / ".agent-fabric"
    if os.path.lexists(state):
        raise FileExistsError(f"Any existing .agent-fabric blocks installation: {state}")
    if not distribution._source_owns_installer(source):
        raise ValueError("Invoke scripts/run-fabric.py from the selected trusted source; cross-source dispatch is disabled")
    distribution._validate_release_assets(source)
    version = distribution._source_version(source)
    distribution._validate_version(version)
    if not _portable_component(version):
        raise ValueError("Unsafe release identity")
    source_digest = distribution.release_source_digest(source)
    prefix = f"{RUNTIME_DIRECTORY}/releases/{version}"
    files, directories = _snapshot(source, prefix)
    profile = default_project_profile(project.name)
    validate_project_profile(profile)
    contracts = {
        f"{prefix}/core/agent-profiles.json": default_profiles(),
        f"{prefix}/core/gates.json": default_gates(),
        ".agent-fabric/profile.json": profile,
        ".agent-fabric/config/capabilities.json": default_capabilities(),
        ".agent-fabric/config/work-tracking.json": default_config(),
        ".agent-fabric/config/model-routing.json": default_routing(),
        ".agent-fabric/fabric-binding.json": {
            "schema_version": 1, "fabric_release": version, "client": client,
            "profile": ".agent-fabric/profile.json",
            "project_overlay": ".agent-fabric/project-overlay.md", "enabled_packs": [],
        },
    }
    distribution.validate_project_binding(contracts[".agent-fabric/fabric-binding.json"])
    files.update({path: _json_bytes(value) for path, value in contracts.items()})
    # Dormant project adapter assets входят в immutable release; client links создаются отдельно.
    from .codex_project import AGENT_DIRECTORY, PERSONAS, render_project_agents
    rendered = render_project_agents(
        contracts[f"{prefix}/core/agent-profiles.json"],
        {persona: files[f"{prefix}/docs/agents/{persona}.md"] for persona in PERSONAS.values()},
    )
    files.update({f"{prefix}/{AGENT_DIRECTORY}/{persona}.toml": data for persona, data in rendered.items()})
    files[".agent-fabric/project-overlay.md"] = (
        "# Project overlay\n\n"
        "Project runtime only; client activation is none. Add project-specific rules here.\n"
    ).encode("utf-8")
    home = project / RUNTIME_DIRECTORY
    manifest = {
        "schema_version": 2, "version": version, "created_at": PROJECT_RELEASE_EPOCH,
        "memory": {"schema_version": MEMORY_SCHEMA_VERSION, "minimum_compatible": 0},
        "files": {
            path.removeprefix(f"{prefix}/"): hashlib.sha256(data).hexdigest()
            for path, data in sorted(files.items()) if path.startswith(f"{prefix}/")
        },
    }
    manifest_data = _json_bytes(manifest)
    manifest_hash = hashlib.sha256(manifest_data).hexdigest()
    files[f"{prefix}/release-manifest.json"] = manifest_data
    installation = {
        "schema_version": 1, "fabric_home": str(home), "current_release": version,
        "releases": [{
            "version": version, "path": f"releases/{version}",
            "manifest_sha256": manifest_hash,
        }],
    }
    distribution.validate_installation_manifest(installation)
    files[f"{RUNTIME_DIRECTORY}/installation.json"] = _json_bytes(installation)
    files[LAUNCHER] = _launcher(project, project / prefix, manifest_hash).encode("utf-8")
    runtime_created = {".agent-fabric/memory.db", f".agent-fabric/{PROJECT_INSTALLATION_FILE}"}
    for name in set(files) | runtime_created | directories.copy():
        directories.update(str(parent) for parent in PurePosixPath(name).parents if str(parent) != ".")
    all_paths = set(files) | runtime_created | directories
    if len({name.casefold() for name in all_paths}) != len(all_paths):
        raise ValueError("Source contains case-ambiguous output paths")
    if (set(files) | runtime_created) & directories:
        raise ValueError("Source contains conflicting file/directory output paths")
    file_hashes = {path: hashlib.sha256(data).hexdigest() for path, data in sorted(files.items())}
    target_stat = project.stat()
    plan = {
        "schema_version": 1, "mode": "project-runtime",
        "project_root": str(project), "source_root": str(source),
        "fabric_home": str(home), "fabric_release": version,
        "client": client, "client_activation": "none",
        "source_sha256": source_digest,
        "file_sha256": file_hashes,
        "snapshot_sha256": _digest(file_hashes),
        "target_identity": {
            "device": target_stat.st_dev, "inode": target_stat.st_ino,
            "mode": target_stat.st_mode, "owner": getattr(target_stat, "st_uid", 0),
        },
        "environment": environment.kind,
        "detected_clients": list(detected_client.candidates),
        "files": sorted(set(files) | runtime_created),
        "runtime_created_files": sorted(runtime_created),
        "directories": sorted(directories),
        "transient_paths": [".agent-fabric/memory.db" + suffix for suffix in ("-journal", "-wal", "-shm")],
    }
    if distribution.release_source_digest(source) != source_digest:
        raise ValueError("Source changed while preparing preview")
    plan["preview_sha256"] = _digest(plan)
    return plan, files


def project_install_preview(target: str | Path, source: str | Path, client: str) -> dict[str, Any]:
    """Показать хеши точных подготовленных байтов и отдельно БД/receipt без SQLite и записи."""
    return _plan(target, source, client)[0]


def _write_new(project: Path, relative: str, data: bytes) -> None:
    """Публиковать только новые обычные файлы в приватном дереве; конфликт не заменяется."""
    destination = project / relative
    _check_path(destination.parent, owned=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(destination, flags, 0o600), "wb") as stream:
        stream.write(data)


def install_project(
    target: str | Path, source: str | Path, client: str, *, expected_preview_sha256: str,
) -> dict[str, Any]:
    """Проверить заново построенный план до mkdir и записать его точные байты.

    Только SQLite и receipt создаются после публикации подготовленных файлов:
    их пути согласованы preview, но их байты не входят в file_sha256.
    """
    plan, files = _plan(target, source, client)
    if not isinstance(expected_preview_sha256, str) or not DIGEST_PATTERN.fullmatch(expected_preview_sha256) or expected_preview_sha256 != plan["preview_sha256"]:
        raise ValueError("Preview digest is stale or invalid; review a fresh preview")
    project = Path(plan["project_root"])
    checked_directory(project, owned=True)
    current = project.stat()
    if plan["target_identity"] != {
        "device": current.st_dev, "inode": current.st_ino,
        "mode": current.st_mode, "owner": getattr(current, "st_uid", 0),
    }:
        raise ValueError("Target changed since preview")
    state = project / ".agent-fabric"
    state.mkdir(mode=0o700)
    for relative in sorted(plan["directories"], key=lambda name: (len(PurePosixPath(name).parts), name)):
        if relative != ".agent-fabric":
            _check_path((project / relative).parent, owned=True)
            (project / relative).mkdir(mode=0o700)
    for relative, data in sorted(files.items()):
        _write_new(project, relative, data)
    # Проверить опубликованный release по подготовленным хешам, не пересоздавая manifest.
    distribution._validate_installed_release(Path(plan["fabric_home"]), plan["fabric_release"])
    # Только новая БД: canonical initializer создаёт текущую схему, существующую БД не трогаем.
    for relative in [".agent-fabric/memory.db", *plan["transient_paths"]]:
        if os.path.lexists(project / relative):
            raise FileExistsError(f"Memory ownership conflict: {relative}")
    _check_path(state, owned=True)
    _write_new(project, ".agent-fabric/memory.db", b"")
    initialize(project)
    record = {key: plan[key] for key in (
        "schema_version", "mode", "project_root", "fabric_home", "fabric_release",
        "client", "client_activation", "source_sha256", "preview_sha256",
        "files", "directories", "transient_paths",
    )}
    validate_project_installation(record)
    # Ownership публикуется последним; после сбоя дерево сохраняется для ручного осмотра.
    _write_new(project, f".agent-fabric/{PROJECT_INSTALLATION_FILE}", _json_bytes(record))
    load_project_installation(project)
    return {**plan, "status": "installed"}


def validate_project_installation(record: dict[str, Any]) -> None:
    """Строгий отдельный контракт ownership, без изменения схем binding/installation/SQLite."""
    fields = {
        "schema_version", "mode", "project_root", "fabric_home", "fabric_release",
        "client", "client_activation", "source_sha256", "preview_sha256",
        "files", "directories", "transient_paths",
    }
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError("Project installation must use the declared object shape")
    if type(record["schema_version"]) is not int or record["schema_version"] != 1 or record["mode"] != "project-runtime" or record["client"] != "codex" or record["client_activation"] != "none":
        raise ValueError("Invalid project runtime identity or activation")
    for field in ("source_sha256", "preview_sha256"):
        if not isinstance(record[field], str) or not DIGEST_PATTERN.fullmatch(record[field]):
            raise ValueError("Invalid project installation digest")
    for field in ("project_root", "fabric_home"):
        if not isinstance(record[field], str) or not Path(record[field]).is_absolute():
            raise ValueError("Project installation roots must be absolute")
    version = record["fabric_release"]
    if not isinstance(version, str) or not _portable_component(version):
        raise ValueError("Invalid project runtime release")
    distribution._validate_version(version)
    if Path(record["fabric_home"]) != Path(record["project_root"]) / RUNTIME_DIRECTORY:
        raise ValueError("Project runtime home must stay in the target state directory")
    for field in ("files", "directories", "transient_paths"):
        entries = record[field]
        if not isinstance(entries, list) or not entries or any(not isinstance(item, str) for item in entries):
            raise ValueError("Project ownership paths must be non-empty string lists")
        if len(set(entries)) != len(entries):
            raise ValueError("Duplicate project ownership paths")
        for item in entries:
            path = PurePosixPath(item)
            if path.parts[:1] != (".agent-fabric",) or any(not _portable_component(part) for part in path.parts) or str(path) != item:
                raise ValueError("Project ownership path escapes state")
    if set(record["files"]) & set(record["directories"]):
        raise ValueError("Project ownership file/directory conflict")
    required = {LAUNCHER, ".agent-fabric/fabric-binding.json", ".agent-fabric/memory.db", f".agent-fabric/{PROJECT_INSTALLATION_FILE}"}
    if not required.issubset(record["files"]) or ".agent-fabric" not in record["directories"]:
        raise ValueError("Project ownership record is incomplete")


def load_project_installation(project_root: Path) -> dict[str, Any]:
    """Проверять ownership перед локальной маршрутизацией; повреждение не включает global fallback."""
    project = checked_directory(project_root, owned=True)
    path = project / ".agent-fabric" / PROJECT_INSTALLATION_FILE
    _check_path(path, owned=True)
    record = json.loads(path.read_text(encoding="utf-8"))
    validate_project_installation(record)
    if record["project_root"] != str(project):
        raise ValueError("Project runtime cannot be relocated or used for another target")
    for field, predicate in (("files", stat.S_ISREG), ("directories", stat.S_ISDIR)):
        for relative in record[field]:
            if not predicate(_check_path(project / relative, owned=True).st_mode):
                raise ValueError(f"Project ownership type conflict: {relative}")
    for relative in record["transient_paths"]:
        if os.path.lexists(project / relative) and not stat.S_ISREG(_check_path(project / relative, owned=True).st_mode):
            raise ValueError(f"SQLite sidecar ownership conflict: {relative}")
    binding = distribution._load_project_binding(project / ".agent-fabric/fabric-binding.json")
    installation = distribution.load_installation(Path(record["fabric_home"]))
    if binding["fabric_release"] != record["fabric_release"] or binding["client"] != record["client"] or installation["current_release"] != record["fabric_release"] or installation["fabric_home"] != record["fabric_home"]:
        raise ValueError("Project runtime release, home or binding conflict")
    return record


def local_fabric_home(project: Path) -> Path | None:
    """Распознать и неполную установку, чтобы не подменить её глобальным runtime."""
    if os.path.lexists(project / ".agent-fabric" / PROJECT_INSTALLATION_FILE) or os.path.lexists(project / RUNTIME_DIRECTORY):
        return Path(load_project_installation(project)["fabric_home"])
    return None


def restrict_runtime_command(args: Any, project_root: Path) -> None:
    """После argparse и до dispatch закрепить target/home, запретив installer и global операции."""
    project = checked_directory(project_root, owned=True)
    record = load_project_installation(project)
    if Path(__file__).resolve().parents[2] != Path(record["fabric_home"]) / "releases" / record["fabric_release"]:
        raise ValueError("Project runtime launcher is pinned to one release")
    allowed = {
        "detect", "detect-client", "preflight", "work", "start", "restore",
        "recover-unicode-package", "memory", "guards", "socrates", "secret", "spec", "harness", "project",
    }
    if args.command not in allowed or (
        args.command == "project" and args.project_command not in {"status", "context", "command-preview", "codex-install", "codex-status"}
    ):
        raise ValueError("Project runtime launcher cannot dispatch installation or distribution commands")
    if hasattr(args, "target"):
        if checked_directory(args.target, owned=True) != project:
            raise ValueError("Project runtime launcher is pinned to one target")
        args.target = project
    if hasattr(args, "home"):
        if checked_directory(args.home, owned=True) != Path(record["fabric_home"]):
            raise ValueError("Project runtime launcher cannot select another Fabric home")
        args.home = Path(record["fabric_home"])


def _launcher(project: Path, release: Path, manifest_hash: str) -> str:
    """До импорта runtime проверить закреплённый release stdlib-кодом, включая чужой bytecode."""
    return f'''import sys

if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
    raise SystemExit("Project runtime requires python -I -S -B")

from pathlib import Path
import hashlib
import json
import os
import stat

project = Path({str(project)!r})
release = Path({str(release)!r})
home = project / ".agent-fabric/runtime"
launcher = project / {LAUNCHER!r}
if Path(os.path.abspath(__file__)) != launcher:
    raise SystemExit("Project runtime launcher cannot be relocated")
for path in [*reversed(launcher.parents), launcher, *reversed(release.parents), release, *release.rglob("*")]:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise SystemExit("Project runtime contains a link or reparse point")
    if hasattr(os, "geteuid") and path.is_relative_to(project) and info.st_uid != os.geteuid():
        raise SystemExit("Project runtime ownership conflict")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise SystemExit("Project runtime contains a hard-linked file")
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise SystemExit("Project runtime contains a non-regular path")
manifest_path = release / "release-manifest.json"
data = manifest_path.read_bytes()
if hashlib.sha256(data).hexdigest() != {manifest_hash!r}:
    raise SystemExit("Pinned release manifest changed")
manifest = json.loads(data)
actual = {{path.relative_to(release).as_posix() for path in release.rglob("*") if path.is_file() and path != manifest_path}}
if actual != set(manifest["files"]):
    raise SystemExit("Pinned release file set changed")
for relative, expected in manifest["files"].items():
    path = release / relative
    if not path.is_relative_to(release) or ".." in path.parts or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit("Pinned release integrity check failed")
os.environ["AI_AGENT_FABRIC_HOME"] = str(home)
for key in ("PYTHONPATH", "PYTHONHOME"):
    os.environ.pop(key, None)
sys.path.insert(0, str(release / "src"))
from ai_agent_fabric.__main__ import main
main(project_runtime=project)
'''
