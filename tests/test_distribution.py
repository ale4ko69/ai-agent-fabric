from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock
import os
import hashlib
import subprocess
import sys
import shutil
import py_compile

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
    def test_new_product_init_rechecks_an_existing_empty_folder_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            install_release(SOURCE_ROOT, home, "test-new-product")

            preview = distribution.project_onboarding_preview(project, "codex", home, require_empty=True)

            self.assertTrue(all(path.is_relative_to(project / ".agent-fabric") for path in preview))
            self.assertEqual(list(project.iterdir()), [])
            hidden = project / ".owner-file"
            hidden.write_text("preserve", encoding="utf-8")
            for operation in (distribution.project_onboarding_preview, distribution.onboard_project):
                with self.assertRaisesRegex(ValueError, "empty local folder"):
                    operation(project, "codex", home, require_empty=True)
            self.assertEqual(hidden.read_text(encoding="utf-8"), "preserve")
            self.assertFalse((project / ".agent-fabric").exists())

            hidden.unlink()
            distribution.onboard_project(project, "codex", home, require_empty=True)

            self.assertEqual({path.name for path in project.iterdir()}, {".agent-fabric"})
            self.assertTrue((project / ".agent-fabric/memory.db").is_file())
            self.assertEqual(project_status(project, home)["status"], "bound")

    def test_new_product_init_does_not_create_a_missing_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "missing"
            home = root / "home"
            for operation in (distribution.project_onboarding_preview, distribution.onboard_project):
                with self.assertRaisesRegex(ValueError, "does not exist"):
                    operation(project, "codex", home, require_empty=True)
            self.assertEqual(list(root.iterdir()), [])

    def test_new_product_plugin_registry_preserves_legacy_skill_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            links = root / "codex-skills"
            owner_skill = links / "new-product"
            owner_skill.mkdir(parents=True)
            (owner_skill / "SKILL.md").write_text("Owner skill", encoding="utf-8")
            release = install_release(SOURCE_ROOT, home, "test-skills")
            plugin = home / "marketplace/plugins/agent-fabric"
            source_names = {path.name for path in (SOURCE_ROOT / "skills").iterdir() if (path / "SKILL.md").is_file()}

            self.assertEqual(set(distribution.FABRIC_SKILL_NAMES), source_names)
            self.assertEqual(distribution.CODEX_SKILL_NAMES, ("work", "start", "restore", "harness", "guards"))
            self.assertEqual({path.name for path in (plugin / "skills").iterdir()}, source_names)
            self.assertEqual(
                (plugin / "skills/new-product/SKILL.md").read_bytes(),
                (release / "skills/new-product/SKILL.md").read_bytes(),
            )
            declaration = json.loads((SOURCE_ROOT / "release-source.json").read_text(encoding="utf-8"))
            self.assertEqual(declaration["home_outputs"], list(distribution.RELEASE_HOME_OUTPUTS))
            self.assertFalse((home / "skills/new-product").exists())

            with mock.patch.object(distribution, "codex_skill_root", return_value=links):
                try:
                    distribution.enable_codex_skills(home)
                except PermissionError as error:
                    self.skipTest(f"host does not permit test symlink creation: {error}")
                record_path = distribution.codex_skill_record_path(home)
                record = json.loads(record_path.read_text(encoding="utf-8"))
                self.assertEqual(set(record["skills"]), set(distribution.CODEX_SKILL_NAMES))
                self.assertEqual(
                    {item["action"] for item in distribution.codex_skill_enable_preview(home)["skills"]},
                    {"already-installed"},
                )
                install_release(SOURCE_ROOT, home, "test-skills-updated")
                self.assertEqual(json.loads(record_path.read_text(encoding="utf-8"))["release"], "test-skills-updated")
                distribution.disable_codex_skills(home)
                self.assertFalse(record_path.exists())
            self.assertEqual({path.name for path in links.iterdir()}, {"new-product"})
            self.assertEqual((owner_skill / "SKILL.md").read_text(encoding="utf-8"), "Owner skill")

    def test_release_preview_includes_client_records_and_preserves_managed_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, entry = root / "home", root / "AGENTS.md"
            entry.write_text("Owner instructions\n", encoding="utf-8")
            with mock.patch.object(distribution, "client_entry_point", return_value=entry):
                install_release(SOURCE_ROOT, home, "test-old")
                distribution.enable_client(home, "codex", "managed-block")
                original_entry = entry.read_bytes()
                preview = distribution.release_preview(SOURCE_ROOT, home, "test-new")
                for client in ("codex", "copilot", "claude"):
                    self.assertIn(home / "clients" / f"{client}.json", preview)
                install_release(SOURCE_ROOT, home, "test-new")
                self.assertEqual(entry.read_bytes(), original_entry)
                record = json.loads((home / "clients/codex.json").read_text(encoding="utf-8"))
                self.assertEqual(record["release"], "test-new")

    def test_installed_launcher_uses_selected_source_installer_for_preview_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project, target_source = root / "home", root / "project", root / "target-source"
            project.mkdir()
            install_release(SOURCE_ROOT, home, "test-old")
            bind_project(project, "test-old", "codex", home)
            overlay = project / ".agent-fabric/project-overlay.md"
            overlay.write_text("owner overlay", encoding="utf-8")
            shutil.copytree(SOURCE_ROOT, target_source, ignore=shutil.ignore_patterns(".git", ".worktrees", ".agent-fabric", ".codex", ".agents", "specs", "__pycache__", "*.pyc"))
            target_distribution = target_source / "src/ai_agent_fabric/distribution.py"
            source_text = target_distribution.read_text(encoding="utf-8")
            target_distribution.write_text(source_text.replace('    "docs/cli.md",', '    "docs/target-only.md",\n    "docs/cli.md",', 1), encoding="utf-8")
            (target_source / "docs/target-only.md").write_text("target-only", encoding="utf-8")
            declaration_path = target_source / "release-source.json"
            declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
            declaration["assets"].insert(declaration["assets"].index("docs/cli.md"), "docs/target-only.md")
            declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
            target_profiles = target_source / "src/ai_agent_fabric/agent_profiles.py"
            target_profiles.write_text(target_profiles.read_text(encoding="utf-8").replace('"maintenance", "Metis"', '"maintenance", "TargetMetis"', 1), encoding="utf-8")
            # A valid timestamp-based poisoned cache must never execute. Staging
            # copies source without __pycache__ and launches isolated Python.
            original = target_profiles.read_bytes()
            original_stat = target_profiles.stat()
            payload = b"\nopen(__import__('os').environ['F_M'],'w').close()\n"
            needle = b"Validates declared contracts and assertions when the project enables it."
            self.assertGreater(len(needle), len(payload))
            poisoned = original.replace(needle, needle[len(payload):], 1) + payload
            self.assertEqual(len(poisoned), len(original))
            target_profiles.write_bytes(poisoned)
            os.utime(target_profiles, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            py_compile.compile(str(target_profiles), doraise=True, invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
            target_profiles.write_bytes(original)
            os.utime(target_profiles, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            marker = root / "poisoned-bytecode-executed"
            environment = os.environ.copy()
            environment["F_M"] = str(marker)
            base = [sys.executable, str(home / "bin/ai-agent-fabric.py"), "distribution", "install-release", str(target_source), "--home", str(home), "--version", "test-new", "--json"]
            preview = json.loads(subprocess.run(base + ["--preview"], capture_output=True, text=True, check=True, env=environment).stdout)
            self.assertIn(str(home / "releases/test-new/docs/target-only.md"), preview["paths"])
            self.assertFalse((home / "releases/test-new").exists())
            (target_source / "docs/target-only.md").write_text("changed after preview", encoding="utf-8")
            stale = subprocess.run(base + ["--expected-source-sha256", preview["source_sha256"]], capture_output=True, text=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertFalse((home / "releases/test-new").exists())
            (target_source / "docs/target-only.md").write_text("target-only", encoding="utf-8")
            installed = json.loads(subprocess.run(base + ["--expected-source-sha256", preview["source_sha256"]], capture_output=True, text=True, check=True, env=environment).stdout)
            self.assertEqual(installed["paths"], [str(home / "releases/test-new")])
            profiles = json.loads((home / "releases/test-new/core/agent-profiles.json").read_text(encoding="utf-8"))["profiles"]
            self.assertEqual(next(p["persona"] for p in profiles if p["id"] == "maintenance"), "TargetMetis")
            self.assertTrue((home / "releases/test-new/docs/target-only.md").is_file())
            self.assertFalse(marker.exists())
            self.assertEqual(project_status(project, home)["release"], "test-old")
            self.assertEqual(overlay.read_text(encoding="utf-8"), "owner overlay")

    def test_source_installer_missing_or_missing_asset_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            shutil.copytree(SOURCE_ROOT, source, ignore=shutil.ignore_patterns(".git", ".worktrees", ".agent-fabric", ".codex", ".agents", "specs", "__pycache__", "*.pyc"))
            (source / "scripts/run-fabric.py").unlink()
            with self.assertRaisesRegex(ValueError, "safe versioned installer"):
                distribution.release_preview(source, root / "home", "test-missing")
            self.assertFalse((root / "home").exists())
            shutil.copy2(SOURCE_ROOT / "scripts/run-fabric.py", source / "scripts/run-fabric.py")
            (source / "docs/cli.md").unlink()
            with self.assertRaisesRegex(ValueError, "Release source asset is missing"):
                distribution.install_release(source, root / "home", "test-missing")
            self.assertFalse((root / "home/releases/test-missing").exists())

    def test_foreign_source_preview_never_executes_its_installer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            marker = root / "unexpected-side-effect"
            shutil.copytree(SOURCE_ROOT, source, ignore=shutil.ignore_patterns(".git", ".worktrees", ".agent-fabric", ".codex", ".agents", "specs", "__pycache__", "*.pyc"))
            (source / "scripts/run-fabric.py").write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('unexpected')\n", encoding="utf-8")
            preview = distribution.release_preview(source, root / "home", "test-preview")
            self.assertTrue(preview)
            self.assertFalse(marker.exists())
            self.assertFalse((root / "home").exists())

    def test_foreign_source_preview_rejects_linked_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, external = root / "source", root / "external-docs"
            shutil.copytree(SOURCE_ROOT, source, ignore=shutil.ignore_patterns(".git", ".worktrees", ".agent-fabric", ".codex", ".agents", "specs", "__pycache__", "*.pyc"))
            (source / "docs").rename(external)
            try:
                (source / "docs").symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("symbolic links are unavailable")
            with self.assertRaisesRegex(ValueError, "link or junction"):
                distribution.release_preview(source, root / "home", "test-linked-parent")
            self.assertFalse((root / "home").exists())
    def test_installed_candidate_digest_requires_no_prior_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project = root / "home", root / "project"
            project.mkdir()
            install_release(SOURCE_ROOT, home, "test-digest")
            bind_project(project, "test-digest", "codex", home)
            candidate = {"task_id": "future-task", "paths": ["docs/example.md"], "commands": [], "delivery": [], "evidence": ["evidence.md"]}
            (project / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")
            result = subprocess.run([sys.executable, str(home / "bin/ai-agent-fabric.py"), "harness", "maintenance-digest", str(project), "--candidate", "candidate.json", "--home", str(home), "--json"], capture_output=True, text=True, check=True)
            output = json.loads(result.stdout)
            expected = hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            self.assertEqual(output["candidate_sha256"], expected)
            self.assertEqual(output["status"], "digest-only-not-authorized")
    def test_windows_cp1252_python_launcher_emits_russian_json_as_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fabric-home"
            project = root / "project"
            project.mkdir()
            install_release(SOURCE_ROOT, home, "test-utf8")
            bind_project(project, "test-utf8", "codex", home)
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "cp1252"
            environment["AI_AGENT_FABRIC_HOME"] = str(home)
            result = subprocess.run(
                [sys.executable, str(home / "bin/ai-agent-fabric.py"), "start", str(project), "--title", "Проверить и упорядочить каталог компонентов", "--type", "small-bug", "--apply", "--json"],
                capture_output=True, env=environment, check=True,
            )
            payload = json.loads(result.stdout.decode("utf-8"))
            self.assertEqual(payload["task_id"], "review-and-organize-component-catalog")
            self.assertEqual(payload["created"]["task_id"], "review-and-organize-component-catalog")
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
            self.assertEqual(update_preview["maintenance_policy"]["action"], "default-deny-without-file")
            policy = project / ".agent-fabric/config/maintenance-policy.json"
            policy.write_text('{"owner":"preserve"}', encoding="utf-8")
            overlay = project / ".agent-fabric/project-overlay.md"
            overlay_before = overlay.read_bytes()
            self.assertEqual(project_update_preview(project, "test-b", home)["maintenance_policy"]["action"], "preserve")
            update_project(project, "test-b", home)
            self.assertEqual(policy.read_text(encoding="utf-8"), '{"owner":"preserve"}')
            self.assertEqual(overlay.read_bytes(), overlay_before)
            current = project_status(project, home)
            self.assertFalse(current["update_available"])
            rollback_preview = project_rollback_preview(project, home)
            self.assertEqual(rollback_preview["from_release"], "test-b")
            self.assertEqual(rollback_preview["to_release"], "test-a")
            rollback_project(project, home)
            self.assertEqual(project_status(project, home)["release"], "test-a")

    def test_update_repairs_a_project_pinned_to_a_damaged_current_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "fabric-home"
            project = root / "project"
            project.mkdir()
            release_a = install_release(SOURCE_ROOT, home, "test-a")
            bind_project(project, "test-a", "codex", home)
            install_release(SOURCE_ROOT, home, "test-b")

            (release_a / "unexpected.pyc").write_text("damaged", encoding="utf-8")
            self.assertEqual(project_status(project, home)["error"], "Fabric release file set does not match its manifest")

            update_project(project, "test-b", home)

            current = project_status(project, home)
            self.assertEqual(current["status"], "bound")
            self.assertEqual(current["release"], "test-b")

    def test_interrupted_update_preserves_policy_and_overlay_until_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project = root / "fabric-home", root / "project"
            project.mkdir()
            install_release(SOURCE_ROOT, home, "test-a")
            bind_project(project, "test-a", "codex", home)
            install_release(SOURCE_ROOT, home, "test-b")
            overlay = project / ".agent-fabric/project-overlay.md"
            policy = project / ".agent-fabric/config/maintenance-policy.json"
            overlay.write_text("owner overlay", encoding="utf-8")
            policy.write_text('{"owner":"existing"}', encoding="utf-8")
            with mock.patch.object(distribution, "_migrate_project_memory", side_effect=RuntimeError("simulated interruption")):
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    update_project(project, "test-b", home)
            self.assertEqual(project_status(project, home)["status"], "update-pending")
            self.assertEqual(distribution.repair_project_update_preview(project, home)["stage"], "prepared")
            distribution.repair_project_update(project, home)
            self.assertEqual(project_status(project, home)["release"], "test-b")
            self.assertEqual(overlay.read_text(encoding="utf-8"), "owner overlay")
            self.assertEqual(policy.read_text(encoding="utf-8"), '{"owner":"existing"}')

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

    def test_generated_codex_bootstrap_requires_a_separate_socrates_chat_and_recovery_only_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "fabric-home"

            release = install_release(SOURCE_ROOT, home, "test-codex-handoff")
            bootstrap = (release / "adapters" / "codex" / "bootstrap.md").read_text(encoding="utf-8")

            self.assertIn("socrates_chat_request", bootstrap)
            self.assertIn("create or reopen the named separate Socrates chat", bootstrap)
            self.assertIn("Root must not present itself as Socrates", bootstrap)
            self.assertIn("chat creation, or activation-packet delivery fails", bootstrap)
            self.assertIn("autonomous delivery", bootstrap)
            self.assertIn("durable `rollout` step", bootstrap)
            stable_bootstrap = (home / "adapters" / "codex" / "bootstrap.md").read_text(encoding="utf-8")
            self.assertEqual(stable_bootstrap, bootstrap)

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
