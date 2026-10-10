from pathlib import Path
import tempfile
import unittest

from ai_agent_fabric.task_specs import create_task, validate_task
from ai_agent_fabric.distribution import install_release, onboard_project


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def bound_project(root: Path) -> Path:
    project = root / "project"
    project.mkdir()
    home = root / "fabric-home"
    install_release(SOURCE_ROOT, home, "test")
    onboard_project(project, "codex", home, "test")
    return project


class TaskSpecsTest(unittest.TestCase):
    def test_small_bug_has_only_lightweight_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = bound_project(Path(directory))
            package = create_task(project, "Fix save error", "small-bug")
            self.assertTrue((package / "tasks.md").is_file())
            self.assertFalse((package / "spec.md").exists())
            self.assertEqual(validate_task(project, "fix-save-error"), [])

    def test_planned_work_has_full_artifact_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = bound_project(Path(directory))
            package = create_task(project, "Add account export", "planned")
            for name in ("spec.md", "research.md", "plan.md", "kepler.md", "tasks.md", "session-state.md"):
                self.assertTrue((package / name).is_file())
            self.assertEqual(validate_task(project, "add-account-export"), [])

    def test_validator_detects_missing_planned_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = bound_project(Path(directory))
            package = create_task(project, "Add account export", "planned")
            (package / "kepler.md").unlink()
            self.assertIn("Missing required artifact: kepler.md", validate_task(project, "add-account-export"))
