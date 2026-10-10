from pathlib import Path
import tempfile
import unittest

from ai_agent_fabric.distribution import binding_preview, install_release, onboard_project


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class InstallerTest(unittest.TestCase):
    def test_project_binding_writes_only_inside_target_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "project"
            target.mkdir()
            home = root / "fabric-home"
            install_release(SOURCE_ROOT, home, "test")
            preview = binding_preview(target, "test", "codex", home)
            self.assertTrue(all(path.is_relative_to(target) for path in preview))
            created = onboard_project(target, "codex", home, "test")
            self.assertEqual(created, target / ".agent-fabric" / "fabric-binding.json")
            self.assertTrue((target / ".agent-fabric" / "profile.json").is_file())
            self.assertTrue((target / ".agent-fabric" / "config" / "work-tracking.json").is_file())
            self.assertTrue((target / ".agent-fabric" / "config" / "model-routing.json").is_file())
            self.assertTrue((target / ".agent-fabric" / "memory.db").is_file())
