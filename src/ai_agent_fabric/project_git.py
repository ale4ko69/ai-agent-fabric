from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import Any, Callable

from .environment import Environment


MEMORY_PATH = ".agent-fabric/memory.db"
MEMORY_SIDECARS = tuple(MEMORY_PATH + suffix for suffix in ("-journal", "-wal", "-shm"))


def _git(
    project: Path, environment: Environment, *arguments: str,
    data: bytes | None = None, allowed: tuple[int, ...] = (0,),
) -> bytes:
    git = shutil.which("git")
    if git is None:
        raise ValueError("Git is required to inspect the target repository")
    command = [git, "-C", str(project), "-c", "core.quotePath=false", *arguments]
    if environment.bash_path:
        command = [environment.bash_path, "-c", 'exec "$@"', "fabric", *command]
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "MSYS2_ARG_CONV_EXCL": "*"})
    try:
        result = subprocess.run(
            command, input=data, env=env, capture_output=True, check=False, timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(f"Git timed out while inspecting the target ({arguments[0]})") from error
    if result.returncode not in allowed:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise ValueError(f"Git could not inspect the target ({arguments[0]}): {message}")
    return result.stdout


def _git_path(project: Path, environment: Environment, option: str) -> Path:
    args = option.split()
    value = _git(project, environment, "rev-parse", "--path-format=absolute", *args)
    path = Path(os.fsdecode(value.rstrip(b"\r\n")))
    if not path.is_absolute():
        raise ValueError(f"Git returned an ambiguous location for {option}")
    return path


def _ignore_matches(project: Path, environment: Environment, paths: list[str]) -> dict[str, tuple[str, str]]:
    if not paths:
        return {}
    data = b"".join(os.fsencode(path) + b"\0" for path in paths)
    output = _git(
        project, environment, "check-ignore", "--stdin", "-z", "-v",
        "--no-index", "--non-matching", data=data, allowed=(0, 1),
    )
    fields = output.split(b"\0")
    if len(fields) != len(paths) * 4 + 1 or fields[-1]:
        raise ValueError("Git returned an incomplete set of ignore observations")
    matches: dict[str, tuple[str, str]] = {}
    for offset, expected in enumerate(paths):
        source, _, pattern, path = map(os.fsdecode, fields[offset * 4:offset * 4 + 4])
        if path != expected:
            raise ValueError("Git returned an unexpected ignore path")
        matches[path] = (source, pattern)
    return matches


def _exclude_bytes(path: Path) -> bytes | None:
    # A submodule can place its metadata outside its worktree. Validate the
    # Git-reported location and never follow links within that metadata path.
    from .project_install import _check_path

    cursor = path.parent
    if not os.path.lexists(cursor):
        cursor = cursor.parent
    if not stat.S_ISDIR(_check_path(cursor, owned=True).st_mode):
        raise ValueError(f"Git exclusion parent must be an ordinary directory: {cursor}")
    if not os.path.lexists(path):
        return None
    info = _check_path(path, owned=True)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Git exclusion file must be an ordinary file: {path}")
    return path.read_bytes()


def _conflicts(index_paths: set[str], generated: list[str]) -> list[str]:
    roots = [path.rstrip("/").casefold() for path in generated]
    return sorted(
        path for path in index_paths if any(
            path.casefold() == root
            or path.casefold().startswith(root + "/")
            or root.startswith(path.casefold() + "/")
            for root in roots
        )
    )


def _anchored_rule(path: str) -> str:
    return "/" + "".join("\\" + char if char in "\\[]*? " else char for char in path)


def project_git_plan(
    project: Path, environment: Environment, paths: list[str], *,
    new_contracts: tuple[str, ...] = (), reserved: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Preview anchored worktree exclusions without writing Git metadata."""
    markers = (project / ".git", *(parent / ".git" for parent in project.parents))
    if not any(os.path.lexists(path) for path in markers):
        if shutil.which("git") and _git(
            project, environment, "rev-parse", "--is-bare-repository", allowed=(0, 128),
        ).strip() == b"true":
            raise ValueError("A Git worktree is required; target is a bare repository")
        return {
            "status": "not-a-git-worktree", "paths": paths, "new_contracts": new_contracts,
            "reserved": reserved,
        }
    if _git_path(project, environment, "--show-toplevel") != project:
        raise ValueError("Git installation target must be the repository worktree root")
    git_dir = _git_path(project, environment, "--git-dir")
    common = _git_path(project, environment, "--git-common-dir")
    exclude = _git_path(project, environment, "--git-path info/exclude")
    if exclude != common / "info" / "exclude":
        raise ValueError("Git returned an unexpected local exclusion path")
    content = _exclude_bytes(exclude)
    if content is not None and b"\0" in content:
        raise ValueError(f"Git exclusion file contains a NUL byte: {exclude}")
    index = _git(project, environment, "ls-files", "--cached", "--full-name", "-z")
    staged = _git(
        project, environment, "diff", "--cached", "--name-only", "--no-renames",
        "--no-ext-diff", "--no-relative", "-z",
    )
    indexed_paths = {os.fsdecode(part) for part in (index + staged).split(b"\0") if part}
    changed = _conflicts(indexed_paths, [*paths, *reserved])
    if changed:
        raise ValueError(f"Tracked or staged generated paths require owner review: {', '.join(changed)}")
    changed_contracts = _conflicts(indexed_paths, list(new_contracts))
    if changed_contracts:
        raise ValueError(f"Tracked or staged project contracts cannot be recreated: {', '.join(changed_contracts)}")
    matches = _ignore_matches(project, environment, paths)
    rules: list[str] = []
    for path, (source, pattern) in matches.items():
        if pattern and not pattern.startswith("!"):
            continue
        if pattern.startswith("!"):
            raise ValueError(f"A user rule in {source} keeps a generated path visible: {path}")
        rules.append(_anchored_rule(path))
    if rules:
        worktrees = _git(project, environment, "worktree", "list", "--porcelain", "-z")
        count = sum(field.startswith(b"worktree ") for field in worktrees.split(b"\0"))
        if git_dir != common or count != 1:
            raise ValueError(f"Cannot change exclusions shared by linked worktrees: {exclude}")
    return {
        "status": "append" if rules else "already-covered",
        "exclude": str(exclude),
        "exclude_sha256": hashlib.sha256(content).hexdigest() if content is not None else None,
        "paths": paths,
        "new_contracts": new_contracts,
        "reserved": reserved,
        "matches": matches,
        "rules": rules,
    }


def _replace_excludes(
    exclude: Path, previous: bytes | None, replacement: bytes | None,
    verify: Callable[[], None],
) -> None:
    lock = exclude.with_name("exclude.lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(lock, flags, 0o600), "wb") as stream:
        lock_stat = os.fstat(stream.fileno())
        published = False
        try:
            if replacement is not None:
                stream.write(replacement)
                stream.flush()
                os.fsync(stream.fileno())
                if previous is not None:
                    os.chmod(lock, stat.S_IMODE(exclude.stat().st_mode))
            verify()
            if _exclude_bytes(exclude) != previous:
                raise ValueError("Git exclusion file changed during apply")
            # Close before replacing on Windows.
            stream.close()
            if not os.path.samestat(lock_stat, lock.lstat()):
                raise ValueError("Git exclusion lock ownership changed")
            if replacement is None:
                exclude.unlink()
            else:
                os.replace(lock, exclude)
                published = True
        finally:
            if not published:
                stream.close()
                try:
                    if os.path.samestat(lock_stat, lock.lstat()):
                        lock.unlink()
                except FileNotFoundError:
                    pass


def apply_project_git_plan(
    project: Path, environment: Environment, plan: dict[str, Any], *,
    verify_ownership: Callable[[], None] = lambda: None,
) -> None:
    def current_plan() -> dict[str, Any]:
        return project_git_plan(
            project, environment, plan["paths"],
            new_contracts=plan["new_contracts"], reserved=plan["reserved"],
        )

    def verify_preview() -> None:
        if current_plan() != plan:
            raise ValueError("Git exclusion preview changed; review a fresh preview")
        verify_ownership()

    verify_preview()
    if plan["status"] != "append":
        return
    exclude = Path(plan["exclude"])
    exclude.parent.mkdir(exist_ok=True)
    content = _exclude_bytes(exclude)
    expected = plan["exclude_sha256"]
    if (hashlib.sha256(content).hexdigest() if content is not None else None) != expected:
        raise ValueError("Git exclusion file changed; review a fresh preview")
    base = content or b""
    newline = b"\r\n" if b"\r\n" in base else b"\n"
    if base and not base.endswith(b"\n"):
        base += newline
    block = ["# AI Agent Fabric project installation", *plan["rules"]]
    replacement = base + newline.join(os.fsencode(line) for line in block) + newline
    _replace_excludes(exclude, content, replacement, verify_preview)
    try:
        if current_plan()["status"] != "already-covered":
            raise ValueError("Git exclusions are not effective for all generated paths")
        verify_ownership()
    except (OSError, ValueError) as error:
        try:
            _replace_excludes(exclude, replacement, content, lambda: None)
        except (OSError, ValueError) as rollback_error:
            raise ValueError(
                f"Git exclusion verification failed ({error}); inspect {exclude} because its "
                f"original contents could not be restored safely: {rollback_error}"
            ) from rollback_error
        raise ValueError(f"Git exclusion verification failed; original exclusions restored: {error}") from error
