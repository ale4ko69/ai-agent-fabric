from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess

from .environment import Environment, detect_environment


@dataclass(frozen=True)
class BootstrapPlan:
    available: bool
    command: tuple[str, ...] | None
    manual_message: str | None


def bash_install_plan(environment: Environment | None = None) -> BootstrapPlan:
    current = environment or detect_environment()
    if current.bash_path:
        return BootstrapPlan(True, None, None)
    if current.kind == "windows" and shutil.which("winget"):
        return BootstrapPlan(False, ("winget", "install", "--id", "Git.Git", "--exact"), None)
    if current.kind in ("linux", "wsl"):
        for manager, command in (
            ("apt-get", ("sudo", "apt-get", "install", "-y", "bash")),
            ("dnf", ("sudo", "dnf", "install", "-y", "bash")),
            ("pacman", ("sudo", "pacman", "-S", "--needed", "bash")),
        ):
            if shutil.which(manager):
                return BootstrapPlan(False, command, None)
    return BootstrapPlan(False, None, "Install a Bash distribution supported by this host, then run detect again.")


def install_bash(environment: Environment | None = None) -> None:
    plan = bash_install_plan(environment)
    if plan.available:
        return
    if plan.command is None:
        raise RuntimeError(plan.manual_message or "No supported Bash installation plan")
    subprocess.run(plan.command, check=True)
    if not detect_environment().bash_path:
        raise RuntimeError("Installation command completed but Bash was not detected. Restart the terminal and run detect again.")
