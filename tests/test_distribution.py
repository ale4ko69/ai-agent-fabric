from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from ai_agent_fabric import distribution
from ai_agent_fabric.distribution import (
    bind_project,
    binding_preview,
    install_release,
    project_context,
    project_rollback_preview,
    project_status,
    rollback_project,
    update_project,
    project_update_preview,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class DistributionLifecycleTest(unittest.TestCase):
    def test_windows_elevation_requires_acknowledged_notice_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fabric-home"
            destination = root / "client" / "AGENTS.md"
            install_release(SOURCE_ROOT, home, "test-a")
            ready = {"ready": True, "client": "codex", "surface": "test", "executable": "test", "version": "test", "entry_point": str(destination)}
            with (
                mock.patch.object(distribution.os, "name", "nt"),
                mock.patch.object(distribution, "client_entry_point", return_value=destination),
                mock.patch.object(distribution, "client_preflight", return_value=ready),
            ):
                preview = distribution.client_enable_preview(home, "codex", "symlink")
                self.assertIn("windows_elevation_notice", preview)
                with self.assertRaises(PermissionError):
                    distribution.enable_client(home, "codex", "symlink", allow_windows_elevation=True)
            self.assertFalse(destination.exists() or destination.is_symlink())

    def test_release_binding_context_and_update_preview_remain_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fabric-home"
            project = root / "project"
            project.mkdir()

            release = install_release(SOURCE_ROOT, home, "test-a")
            self.assertTrue((release / "docs" / "validation-matrix.md").is_file())
            self.assertEqual(project_status(project, home)["status"], "unbound")
            self.assertFalse((project / ".agent-fabric").exists())

            preview = binding_preview(project, "test-a", "codex", home)
            self.assertTrue(all(path.is_relative_to(project) for path in preview))
            bind_project(project, "test-a", "codex", home)
            self.assertEqual(project_status(project, home)["status"], "bound")

            context = project_context(project, home)
            self.assertEqual(context["client"], "codex")
            self.assertEqual(context["status"], "bound")
            self.assertEqual(context["memory"], "not exposed by client context")
            self.assertNotIn("tasks", context["project_contracts"])
            self.assertFalse((project / ".codex").exists())

            install_release(SOURCE_ROOT, home, "test-b")
            stale = project_status(project, home)
            self.assertEqual(stale["release"], "test-a")
            self.assertEqual(stale["current_release"], "test-b")
            self.assertTrue(stale["update_available"])
            update_preview = project_update_preview(project, "test-b", home)
            self.assertEqual(update_preview["from_release"], "test-a")
            self.assertEqual(update_preview["to_release"], "test-b")
            update_project(project, "test-b", home)
            current = project_status(project, home)
            self.assertFalse(current["update_available"])
            rollback_preview = project_rollback_preview(project, home)
            self.assertEqual(rollback_preview["from_release"], "test-b")
            self.assertEqual(rollback_preview["to_release"], "test-a")
            rollback_project(project, home)
            self.assertEqual(project_status(project, home)["release"], "test-a")

    def test_codex_plugin_marketplace_includes_the_trusted_session_start_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fabric-home"

            install_release(SOURCE_ROOT, home, "test-hook")

            plugin = home / "marketplace" / "plugins" / "agent-fabric"
            manifest = json.loads((plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
            hooks = json.loads((plugin / "hooks" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["hooks"], "./hooks/hooks.json")
            self.assertIn("SessionStart", hooks["hooks"])
            self.assertTrue((plugin / "hooks" / "codex_session_start.py").is_file())

    def test_linked_state_directory_is_rejected_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            outside = root / "outside"
            project.mkdir()
            outside.mkdir()
            state = project / ".agent-fabric"
            try:
                state.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"host does not permit test symlink creation: {error}")
            report = project_status(project, root / "fabric-home")
            self.assertEqual(report["status"], "invalid")
            self.assertFalse(any(outside.iterdir()))
