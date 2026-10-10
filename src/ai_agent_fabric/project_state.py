from __future__ import annotations

from pathlib import Path, PureWindowsPath


STATE_DIRECTORY = ".agent-fabric"


def project_root(project_root: Path) -> Path:
    root = project_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Target project does not exist: {root}")
    return root


def state_directory(project_root: Path, *, create: bool = False) -> Path:
    """Return the project-owned state directory, rejecting a link at its boundary."""
    root = project_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Target project does not exist: {root}")
    directory = root / STATE_DIRECTORY
    if directory.is_symlink():
        raise ValueError(f"{STATE_DIRECTORY} must not be a symbolic link")
    if directory.exists() and not directory.is_dir():
        raise ValueError(f"{STATE_DIRECTORY} must be a directory")
    if create and not directory.exists():
        directory.mkdir()
    return directory


def state_path(project_root: Path, relative: str, *, create_parents: bool = False) -> Path:
    """Resolve a Fabric state path without permitting linked parent components."""
    relative_path = Path(relative)
    windows_path = PureWindowsPath(relative)
    if (
        not relative
        or relative_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.root
        or ".." in relative_path.parts
        or ".." in windows_path.parts
    ):
        raise ValueError("Fabric state path must be safely relative")
    directory = state_directory(project_root, create=create_parents)
    current = directory
    for component in relative_path.parts[:-1]:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"Fabric state directory must not be a symbolic link: {relative}")
        if current.exists():
            if not current.is_dir():
                raise ValueError(f"Fabric state path parent must be a directory: {relative}")
        elif create_parents:
            current.mkdir()
        else:
            break
    candidate = directory / relative_path
    if candidate.is_symlink():
        raise ValueError(f"Fabric state file must not be a symbolic link: {relative}")
    resolved_parent = candidate.parent.resolve()
    resolved_directory = directory.resolve()
    if not resolved_parent.is_relative_to(resolved_directory):
        raise ValueError(f"Fabric state path escapes the project: {relative}")
    return candidate
