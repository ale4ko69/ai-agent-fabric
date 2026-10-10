from pathlib import Path
import tempfile
import unittest

from ai_agent_fabric.memory import initialize, record, restore, start_session
from ai_agent_fabric.distribution import install_release, onboard_project


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class MemoryTest(unittest.TestCase):
    def test_memory_round_trip_is_project_local(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            home = root / "fabric-home"
            install_release(SOURCE_ROOT, home, "test")
            onboard_project(project, "codex", home, "test")
            initialize(project)
            start_session(project, "task-1", "Example task")
            record(project, "task-1", "finding", "orchestrator", "Fact", {"source": "docs/a.md"})
            restored = restore(project, "task-1")
        self.assertEqual(restored["session"]["title"], "Example task")
        self.assertEqual(restored["records"][0]["evidence"]["source"], "docs/a.md")
