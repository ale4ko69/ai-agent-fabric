from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class Environment:
    kind: str
    system: str
    release: str
    python_available: bool
    bash_path: str | None

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    for candidate in (Path("/proc/sys/kernel/osrelease"), Path("/proc/version")):
        try:
            if "microsoft" in candidate.read_text(encoding="utf-8").lower():
                return True
        except OSError:
            continue
    return False


def _bash_path() -> str | None:
    system = platform.system().lower()
    candidates: list[Path] = []
    program_files = os.environ.get("ProgramFiles")
    if system == "windows" and program_files:
        candidates.append(Path(program_files) / "Git" / "bin" / "bash.exe")
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if system == "windows" and program_files_x86:
        candidates.append(Path(program_files_x86) / "Git" / "bin" / "bash.exe")
    git_path = shutil.which("git")
    if system == "windows" and git_path:
        candidates.append(Path(git_path).resolve().parent.parent / "bin" / "bash.exe")
    direct = shutil.which("bash")
    if direct:
        direct_path = Path(direct).resolve()
        # WindowsApps/bash.exe is a WSL launcher, not a usable Git Bash runtime.
        # Do not let an unprovisioned WSL installation shadow Git Bash.
        if system != "windows" or "windowsapps" not in {part.lower() for part in direct_path.parts}:
            candidates.append(direct_path)
    for candidate in candidates:
        if candidate.is_file() and _can_run_bash(candidate):
            return str(candidate)
    return None


def _can_run_bash(candidate: Path) -> bool:
    try:
        result = subprocess.run(
            [str(candidate), "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def detect_environment() -> Environment:
    system = platform.system().lower()
    release = platform.release()
    bash_path = _bash_path()
    if system == "windows":
        return Environment("windows", system, release, _python_available(), bash_path)
    if system == "linux" and _is_wsl():
        return Environment("wsl", system, release, _python_available(), bash_path)
    if system == "linux":
        return Environment("linux", system, release, _python_available(), bash_path)
    return Environment("unknown", system or "unknown", release, _python_available(), bash_path)


def _python_available() -> bool:
    return sys.version_info >= (3, 10)


def command_is_allowed(command_family: str, environment: Environment | None = None) -> bool:
    current = environment or detect_environment()
    if command_family == "python":
        return current.python_available
    if command_family == "bash":
        return current.bash_path is not None
    return False
