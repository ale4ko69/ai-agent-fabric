from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


SUPPORTED_CLIENTS = ("codex", "copilot", "claude")


@dataclass(frozen=True)
class ClientDetection:
    selected: str | None
    candidates: tuple[str, ...]

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_client(project_root: Path) -> ClientDetection:
    root = project_root.resolve()
    markers = {
        "codex": (root / ".codex").exists() or (root / "AGENTS.md").is_file(),
        "copilot": any(
            marker.exists()
            for marker in (
                root / ".github" / "copilot-instructions.md",
                root / ".github" / "instructions",
                root / ".github" / "agents",
            )
        ),
        "claude": (root / ".claude").exists() or (root / "CLAUDE.md").is_file(),
    }
    candidates = tuple(client for client in SUPPORTED_CLIENTS if markers[client])
    return ClientDetection(candidates[0] if len(candidates) == 1 else None, candidates)


def adapter_paths(project_root: Path, client: str) -> tuple[Path, ...]:
    root = project_root.resolve()
    if client == "codex":
        return root / ".codex" / "agents", root / ".codex" / "project-context"
    if client == "copilot":
        return root / ".github" / "agents", root / ".github"
    if client == "claude":
        return root / ".claude" / "agents", root
    raise ValueError(f"Unsupported client: {client}")
