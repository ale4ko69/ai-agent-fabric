from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ai_agent_fabric import codex_project, project_git, project_git_cleanup, project_install
from ai_agent_fabric.environment import detect_environment


SOURCE = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("git"), "Git worktree fixtures require Git")
class ProjectGitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.git("init", "-q", "--template=")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.excludesFile", str(self.base / "no-global-exclusions"))
        self.exclude = self.project / ".git/info/exclude"
        self.exclude.parent.mkdir(exist_ok=True)
        self.exclude.write_bytes(b"# owner rules\n/owner-private\n")

    def git(self, *args: str, cwd: Path | None = None) -> bytes:
        completed = subprocess.run(
            ["git", "-C", str(cwd or self.project), *args],
            capture_output=True, check=True,
        )
        return completed.stdout

    def status(self) -> bytes:
        return self.git("status", "--porcelain=v1", "--untracked-files=all")

    def install(self) -> dict:
        preview = project_install.project_install_preview(self.project, SOURCE, "codex")
        return project_install.install_project(
            self.project, SOURCE, "codex", expected_preview_sha256=preview["preview_sha256"],
        )

    def cleanup(self) -> dict:
        preview = project_git_cleanup.project_git_cleanup_preview(self.project)
        return project_git_cleanup.apply_project_git_cleanup(
            self.project, expected_preview_sha256=preview["preview_sha256"],
        )

    def commit(self) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def test_fresh_install_excludes_generated_files_but_leaves_editable_paths_visible(self) -> None:
        own = self.project / "owner-private"
        own.write_bytes(b"owner")
        self.install()
        sibling = self.project / ".agent-fabric/owner-config"
        sibling.write_bytes(b"owner")
        status = self.status()
        self.assertIn(b".agent-fabric/profile.json", status)
        self.assertIn(b".agent-fabric/owner-config", status)
        self.assertNotIn(b"owner-private", status)
        self.assertNotIn(b".agent-fabric/runtime", status)
        self.assertNotIn(b".agent-fabric/project-installation.json", status)
        self.assertNotIn(b".agent-fabric/memory.db", status)
        self.assertTrue(self.exclude.read_bytes().startswith(b"# owner rules\n/owner-private\n"))

    def test_complete_tracked_contracts_preserve_bytes_index_and_existing_changes(self) -> None:
        _, prepared = project_install._plan(self.project, SOURCE, "codex")
        for relative in project_install.PROJECT_CONTRACTS:
            destination = self.project / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(prepared[relative].replace(b"\n", b"\r\n"))
        self.commit()
        profile = self.project / ".agent-fabric/profile.json"
        profile.write_bytes(profile.read_bytes() + b"\r\n")
        self.git("add", ".agent-fabric/profile.json")
        overlay = self.project / ".agent-fabric/project-overlay.md"
        overlay.write_bytes(overlay.read_bytes() + b"Owner note.\r\n")
        before = self.status()
        index = (self.project / ".git/index").read_bytes()
        files = {path: (self.project / path).read_bytes() for path in project_install.PROJECT_CONTRACTS}
        self.install()
        self.assertEqual((self.project / ".git/index").read_bytes(), index)
        self.assertEqual(self.status(), before)
        self.assertEqual({path: (self.project / path).read_bytes() for path in files}, files)

    def test_staged_deletion_of_generated_or_contract_path_is_reported(self) -> None:
        for relative in (".agent-fabric/runtime/local", ".agent-fabric/profile.json"):
            with self.subTest(relative=relative):
                path = self.project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"owner")
                self.commit()
                self.git("rm", "--", relative)
                before = self.status()
                with self.assertRaisesRegex(ValueError, "Tracked or staged"):
                    project_install.project_install_preview(self.project, SOURCE, "codex")
                self.assertEqual(self.status(), before)
                self.git("commit", "-qm", "remove fixture path")

    def test_negated_path_and_mutated_exclude_block_without_overwrite(self) -> None:
        preview = project_install.project_install_preview(self.project, SOURCE, "codex")
        self.exclude.write_bytes(b"# owner edit between preview and apply\n")
        with self.assertRaisesRegex(ValueError, "stale"):
            project_install.install_project(
                self.project, SOURCE, "codex", expected_preview_sha256=preview["preview_sha256"],
            )
        self.assertFalse((self.project / ".agent-fabric").exists())
        (self.project / ".gitignore").write_bytes(b"!/.agent-fabric/project-installation.json\n")
        with self.assertRaisesRegex(ValueError, "keeps a generated path visible"):
            project_install.project_install_preview(self.project, SOURCE, "codex")
        self.assertEqual(self.exclude.read_bytes(), b"# owner edit between preview and apply\n")

    def test_legacy_cleanup_preserves_task_memory_receipts_and_retries(self) -> None:
        installed = self.install()
        owner_rule = b"# owner ignored file without terminating newline"
        self.exclude.write_bytes(owner_rule)
        package = self.project / "docs/specs/active/local-task"
        package.mkdir(parents=True)
        task = package / "spec.md"
        task.write_bytes(b"owner task")
        paths = [project_install.PROJECT_RECEIPT, project_git.MEMORY_PATH, *installed["preserved_files"]]
        paths += [".agent-fabric/fabric-binding.json", "docs/specs/active/local-task/spec.md"]
        before = {path: (self.project / path).read_bytes() for path in paths}
        self.assertIn(b".agent-fabric/runtime", self.status())
        self.assertEqual(self.cleanup()["status"], "updated")
        self.assertNotIn(b".agent-fabric/runtime", self.status())
        self.assertIn(b"docs/specs/active/local-task/spec.md", self.status())
        exclude = self.exclude.read_bytes()
        self.assertTrue(exclude.startswith(owner_rule + b"\n"))
        self.assertEqual(self.cleanup()["status"], "unchanged")
        self.assertEqual(self.exclude.read_bytes(), exclude)
        self.assertEqual({path: (self.project / path).read_bytes() for path in paths}, before)

    def test_legacy_unknown_content_and_tracked_generated_files_stay_visible(self) -> None:
        self.install()
        self.exclude.write_bytes(b"# owner rules only\n")
        extra = self.project / ".agent-fabric/runtime/local"
        extra.write_bytes(b"owner")
        with self.assertRaisesRegex(ValueError, "Unexpected content"):
            project_git_cleanup.project_git_cleanup_preview(self.project)
        self.assertIn(b"runtime/local", self.status())
        extra.unlink()
        self.git("add", "-f", project_install.PROJECT_RECEIPT)
        with self.assertRaisesRegex(ValueError, "Tracked or staged generated"):
            project_git_cleanup.project_git_cleanup_preview(self.project)
        self.assertIn(project_install.PROJECT_RECEIPT.encode(), self.status())

    def test_legacy_edited_launcher_stays_visible(self) -> None:
        self.install()
        self.exclude.write_bytes(b"# owner rules only\n")
        launcher = self.project / project_install.LAUNCHER
        with launcher.open("ab") as stream:
            stream.write(b"\n# owner edit\n")
        with self.assertRaisesRegex(ValueError, "differs from the supported Fabric template"):
            project_git_cleanup.project_git_cleanup_preview(self.project)
        self.assertIn(project_install.LAUNCHER.encode(), self.status())
        self.assertEqual(self.exclude.read_bytes(), b"# owner rules only\n")

    def test_exact_rule_escapes_glob_characters_and_leaves_runtime_siblings_visible(self) -> None:
        runtime = self.project / project_install.RUNTIME_DIRECTORY
        runtime.mkdir(parents=True)
        filename = "asset [one].txt"
        (runtime / filename).write_bytes(b"generated")
        (runtime / "asset o.txt").write_bytes(b"owner")
        generated = (runtime / filename).relative_to(self.project).as_posix()
        environment = detect_environment()
        plan = project_git.project_git_plan(self.project, environment, [generated], reserved=(project_install.RUNTIME_DIRECTORY,))
        project_git.apply_project_git_plan(self.project, environment, plan)
        status = self.status()
        self.assertIn(b"asset o.txt", status)
        self.assertNotIn(filename.encode(), status)

    def test_exclusion_publication_failure_keeps_complete_runtime_recoverable(self) -> None:
        (self.project / "fixture").write_bytes(b"original")
        self.commit()
        (self.project / "fixture").write_bytes(b"owner edit")
        before = self.status()
        index = (self.project / ".git/index").read_bytes()
        rules = self.exclude.read_bytes()
        with mock.patch.object(project_install, "apply_project_git_plan", side_effect=OSError("interrupted")):
            with self.assertRaisesRegex(ValueError, "ownership receipt was published"):
                self.install()
        project_install.load_project_installation(self.project)
        self.assertEqual(self.exclude.read_bytes(), rules)
        self.assertIn(project_install.PROJECT_RECEIPT.encode(), self.status())
        self.assertEqual((self.project / ".git/index").read_bytes(), index)
        self.assertEqual(self.cleanup()["status"], "updated")
        self.assertIn(before, self.status())
        self.assertEqual((self.project / ".git/index").read_bytes(), index)
        self.assertTrue(self.exclude.read_bytes().startswith(rules))

    def test_ownership_change_after_exclude_publication_restores_owner_rules(self) -> None:
        environment = detect_environment()
        paths = project_install.RUNTIME_GIT_PATHS
        owner = self.exclude.read_bytes()
        plan = project_git.project_git_plan(self.project, environment, paths)

        def verify_ownership() -> None:
            if self.exclude.read_bytes() != owner:
                raise ValueError("ownership changed")

        with self.assertRaisesRegex(ValueError, "original exclusions restored"):
            project_git.apply_project_git_plan(
                self.project, environment, plan, verify_ownership=verify_ownership,
            )
        self.assertEqual(self.exclude.read_bytes(), owner)
        self.assertFalse(self.exclude.with_name("exclude.lock").exists())
        project_git.apply_project_git_plan(self.project, environment, plan)
        self.assertEqual(project_git.project_git_plan(self.project, environment, paths)["status"], "already-covered")

    def test_linked_worktree_only_accepts_already_effective_rules(self) -> None:
        (self.project / "fixture").write_bytes(b"worktree")
        self.commit()
        linked = self.base / "linked"
        self.git("worktree", "add", "--detach", str(linked), "HEAD")
        env = detect_environment()
        paths = project_install.RUNTIME_GIT_PATHS
        for worktree in (self.project, linked):
            with self.assertRaisesRegex(ValueError, "shared by linked worktrees"):
                project_git.project_git_plan(worktree, env, paths)
        self.exclude.write_text("\n".join("/" + path for path in paths) + "\n", encoding="ascii")
        self.assertEqual(project_git.project_git_plan(linked, env, paths)["status"], "already-covered")

    def test_submodule_uses_its_own_git_metadata(self) -> None:
        (self.project / "fixture").write_bytes(b"submodule")
        self.commit()
        superproject = self.base / "superproject"
        superproject.mkdir()
        self.git("init", "-q", cwd=superproject)
        self.git("-c", "protocol.file.allow=always", "submodule", "add", str(self.project), "component", cwd=superproject)
        child = superproject / "component"
        plan = project_git.project_git_plan(child, detect_environment(), project_install.RUNTIME_GIT_PATHS)
        self.assertEqual(Path(plan["exclude"]), superproject / ".git/modules/component/info/exclude")
        self.assertEqual(plan["status"], "append")

    def test_adapter_hides_only_verified_generated_links_and_receipt(self) -> None:
        source = self.base / "symlink source"
        source.mkdir()
        link = self.base / "symlink probe"
        try:
            os.symlink(source, link, target_is_directory=True)
        except OSError:
            self.skipTest("Native directory symlinks are unavailable for this test process")
        self.install()
        sibling = self.project / ".agents/skills/owner/SKILL.md"
        sibling.parent.mkdir(parents=True)
        sibling.write_bytes(b"owner")
        preview = codex_project.codex_project_preview(self.project)
        codex_project.install_codex_project(self.project, expected_preview_sha256=preview["preview_sha256"])
        self.assertIn(b".agents/skills/owner/SKILL.md", self.status())
        for path in codex_project.adapter_git_paths(preview["fabric_release"]):
            self.assertNotIn(path.encode(), self.status())

    def test_git_metadata_failure_leaves_owner_bytes_and_allows_new_preview(self) -> None:
        env = detect_environment()
        paths = project_install.RUNTIME_GIT_PATHS
        plan = project_git.project_git_plan(self.project, env, paths)
        owner = self.exclude.read_bytes()
        with mock.patch.object(project_git.os, "replace", side_effect=OSError("metadata write failed")):
            with self.assertRaisesRegex(OSError, "metadata write failed"):
                project_git.apply_project_git_plan(self.project, env, plan)
        self.assertEqual(self.exclude.read_bytes(), owner)
        self.assertFalse(self.exclude.with_name("exclude.lock").exists())
        project_git.apply_project_git_plan(self.project, env, plan)
        self.assertEqual(project_git.project_git_plan(self.project, env, paths)["status"], "already-covered")

    def test_source_cleanup_help_is_available_without_project_runtime(self) -> None:
        command = [
            sys.executable, "-I", "-S", "-B", str(SOURCE / "scripts/run-fabric.py"),
            "project", "git-cleanup", "--help",
        ]
        result = subprocess.run(command, capture_output=True, check=True)
        self.assertIn(b"--expected-preview-sha256", result.stdout)
