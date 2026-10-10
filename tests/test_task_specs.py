from pathlib import Path
import tempfile
import unittest

from ai_agent_fabric.task_specs import create_task, slugify, validate_task
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
    def test_russian_title_uses_english_ascii_task_id_and_preserves_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = bound_project(Path(directory))
            title = "Проверить и упорядочить каталог компонентов"
            package = create_task(project, title, "small-bug")
            self.assertEqual(package.name, "review-and-organize-component-catalog")
            task = __import__("json").loads((package / "task.json").read_text(encoding="utf-8"))
            self.assertEqual(task["id"], "review-and-organize-component-catalog")
            self.assertEqual(task["title"], title)

    def test_english_title_has_predictable_kebab_slug(self) -> None:
        self.assertEqual(slugify("Fix save error"), "fix-save-error")

    def test_unicode_explicit_id_is_rejected_before_package_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = bound_project(Path(directory))
            with self.assertRaisesRegex(ValueError, "ASCII kebab-case"):
                create_task(project, "Русская задача", "small-bug", "русская-задача")
            self.assertFalse((project / "docs/specs/active").exists())
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
