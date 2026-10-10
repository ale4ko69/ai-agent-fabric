from pathlib import Path
import tempfile
import unittest

from ai_agent_fabric.clients import detect_client
from ai_agent_fabric.distribution import bind_project, install_release
from ai_agent_fabric.installer import initialize_project


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class ClientTest(unittest.TestCase):
    def test_detects_one_local_client(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".codex").mkdir()
            result = detect_client(target)
        self.assertEqual(result.selected, "codex")
        self.assertFalse(result.ambiguous)

    def test_direct_legacy_initializer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "retired"):
                initialize_project(target, "Example")

    def test_explicit_client_binding_creates_only_fabric_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "project"
            target.mkdir()
            home = root / "fabric-home"
            install_release(SOURCE_ROOT, home, "test")
            binding = bind_project(target, "test", "claude", home)
            self.assertEqual(binding, target / ".agent-fabric" / "fabric-binding.json")
            self.assertTrue((target / ".agent-fabric" / "project-overlay.md").is_file())
            self.assertFalse((target / ".claude").exists())
