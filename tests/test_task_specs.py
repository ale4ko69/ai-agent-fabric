from pathlib import Path
import json
import tempfile
import unittest

from ai_agent_fabric.task_specs import approve_planned_task, approval_preview, create_task, implementation_readiness, slugify, validate_task
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

    def test_runtime_research_append_preserves_an_approved_planning_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = bound_project(Path(directory))
            package = create_task(project, "Add account export", "planned")
            kepler_path = package / "kepler.json"
            kepler = json.loads(kepler_path.read_text(encoding="utf-8"))
            kepler["verdict"] = "advice"
            kepler_path.write_text(json.dumps(kepler, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            preview = approval_preview(project, "add-account-export")
            digest = str(preview["kepler_verdict_sha256"])
            approve_planned_task(project, "add-account-export", f"approve add-account-export {digest}", digest)
            baseline = json.loads((package / "approval.json").read_text(encoding="utf-8"))["artifact_digests"]["research.md"]

            with (package / "research.md").open("a", encoding="utf-8") as handle:
                handle.write("\n## Runtime observation\n\n- Endpoint returned an unknown state.\n")

            self.assertTrue(implementation_readiness(project, "add-account-export")["ready"])
            self.assertEqual(approval_preview(project, "add-account-export")["artifact_digests"]["research.md"], baseline)

            research_path = package / "research.md"
            research_path.write_text(research_path.read_text(encoding="utf-8").replace("## Evidence", "## Changed evidence", 1), encoding="utf-8")
            reasons = implementation_readiness(project, "add-account-export")["reasons"]
            self.assertIn("Kepler verdict does not match the current spec, research, and plan content", reasons)
