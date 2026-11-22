import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import jsonschema
except ImportError:
    jsonschema = None

from ai_agent_fabric import codex_project, distribution, project_install
from ai_agent_fabric.entrypoints import restore_task, start_task
from ai_agent_fabric.socrates import transition_step


SOURCE = Path(__file__).resolve().parents[1]


class CodexProjectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        preview = project_install.project_install_preview(self.project, SOURCE, "codex")
        installed = project_install.install_project(self.project, SOURCE, "codex", expected_preview_sha256=preview["preview_sha256"])
        self.release = Path(installed["fabric_home"]) / "releases" / installed["fabric_release"]

    def apply_adapter(self) -> dict:
        """Применять только digest отдельного adapter preview в temp fixture."""
        preview = codex_project.codex_project_preview(self.project)
        return codex_project.install_codex_project(self.project, expected_preview_sha256=preview["preview_sha256"])

    def launcher(self, *arguments: str) -> subprocess.CompletedProcess:
        """Тестировать только scoped runtime CLI, не Codex/App executable."""
        return subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(self.project / project_install.LAUNCHER), *arguments],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def test_preview_is_separate_stable_and_writes_nothing(self) -> None:
        before = {path.relative_to(self.project).as_posix(): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        with (
            mock.patch.object(codex_project.os, "symlink", side_effect=AssertionError("preview link")),
            mock.patch.object(Path, "mkdir", side_effect=AssertionError("preview mkdir")),
            mock.patch.object(distribution, "client_preflight", side_effect=AssertionError("Codex executable")),
        ):
            first = codex_project.codex_project_preview(self.project)
            second = codex_project.codex_project_preview(self.project)
        self.assertEqual(first, second)
        self.assertEqual(first["files"], [codex_project.RECEIPT])
        self.assertEqual(first["transient_paths"], [codex_project.PENDING])
        self.assertEqual(len(first["links"]), 2)
        self.assertEqual(first["desktop_discovery"], "unverified")
        self.assertEqual(first["claim_restore"], "unverified")
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".agents").exists())
        after = {path.relative_to(self.project).as_posix(): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_profiles_are_rendered_once_from_pinned_canonical_data(self) -> None:
        profiles = json.loads((self.release / "core/agent-profiles.json").read_bytes())
        documents = {name: (self.release / "docs/agents" / f"{name}.md").read_bytes() for name in codex_project.PERSONAS.values()}
        expected = codex_project.render_project_agents(profiles, documents)
        self.assertEqual(set(expected), set(codex_project.PERSONAS.values()))
        for profile in profiles["profiles"]:
            name = profile["persona"].lower()
            data = (self.release / codex_project.AGENT_DIRECTORY / f"{name}.toml").read_bytes()
            self.assertEqual(data, expected[name])
        changed = copy.deepcopy(profiles)
        changed["profiles"][4]["purpose"] = "Source-owned updated purpose"
        self.assertIn(b"Source-owned updated purpose", codex_project.render_project_agents(changed, documents)["heracles"])
        with self.assertRaises(ValueError):
            codex_project.render_project_agents([], documents)
        skill = (self.release / codex_project.SKILL_DIRECTORY / "SKILL.md").read_text(encoding="utf-8")
        for text in ("real Desktop thread ID", "stop", "Root does not execute this claim", "unverified"):
            self.assertIn(text, skill)

    @unittest.skipIf(tomllib is None, "TOML parsing requires Python 3.11+ or the optional tomli test dependency")
    def test_all_generated_personas_parse_as_standalone_agent_toml(self) -> None:
        profiles = json.loads((self.release / "core/agent-profiles.json").read_bytes())
        for profile in profiles["profiles"]:
            name = profile["persona"].lower()
            with self.subTest(persona=name):
                parsed = tomllib.loads((self.release / codex_project.AGENT_DIRECTORY / f"{name}.toml").read_text(encoding="utf-8"))
                self.assertEqual(set(parsed), {"name", "description", "developer_instructions"})
                self.assertEqual(parsed["name"], name)
                self.assertEqual(parsed["description"], profile["purpose"])
                self.assertIn(json.dumps(profile, ensure_ascii=False, sort_keys=True), parsed["developer_instructions"])
                self.assertIn((self.release / "docs/agents" / f"{name}.md").read_text(encoding="utf-8"), parsed["developer_instructions"])
                self.assertIn("Native subagents are not Socrates chats", parsed["developer_instructions"])

    def test_apply_installs_only_relative_native_links_and_owned_receipt(self) -> None:
        global_root = self.root / "user"
        global_root.mkdir()
        sentinel = global_root / "owner-config"
        sentinel.write_bytes(b"untouched")
        native = self.project / "AGENTS.md"
        native.write_bytes(b"owner project instructions")
        runtime_receipt = (self.project / ".agent-fabric/project-installation.json").read_bytes()
        database = (self.project / ".agent-fabric/memory.db").read_bytes()
        manifest_before = (self.release / "release-manifest.json").read_bytes()
        with (
            mock.patch.dict(os.environ, {"HOME": str(global_root), "AI_AGENT_FABRIC_HOME": str(global_root)}),
            mock.patch.object(distribution, "enable_client", side_effect=AssertionError("global client")),
            mock.patch.object(codex_project, "render_project_agents", side_effect=AssertionError("late renderer")),
        ):
            result = self.apply_adapter()
        self.assertEqual(result["file_installation"], "installed")
        self.assertEqual(result["links_observed"], 2)
        for name in codex_project.PERSONAS.values():
            profile = self.project / ".codex/agents" / f"{name}.toml"
            self.assertFalse(profile.is_symlink())
            self.assertEqual(
                profile.read_bytes(),
                (self.release / codex_project.AGENT_DIRECTORY / profile.name).read_bytes(),
            )
        self.assertEqual(result["desktop_discovery"], "unverified")
        self.assertEqual(result["claim_restore"], "unverified")
        for link in result["links"]:
            destination = self.project / link["path"]
            self.assertTrue(destination.is_symlink())
            self.assertEqual(os.readlink(destination).replace("\\", "/"), link["target"])
            self.assertFalse(Path(link["target"]).is_absolute())
            self.assertTrue(destination.resolve().is_relative_to(self.release))
        record = json.loads((self.project / codex_project.RECEIPT).read_bytes())
        codex_project.validate_codex_project_installation(record)
        self.assertFalse((self.project / codex_project.PENDING).exists())
        self.assertEqual((self.project / ".agent-fabric/project-installation.json").read_bytes(), runtime_receipt)
        self.assertEqual((self.project / ".agent-fabric/memory.db").read_bytes(), database)
        self.assertEqual((self.release / "release-manifest.json").read_bytes(), manifest_before)
        self.assertEqual(native.read_bytes(), b"owner project instructions")
        self.assertEqual(list(global_root.iterdir()), [sentinel])
        self.assertFalse((self.project / ".codex/config.toml").exists())
        self.assertFalse((self.project / ".codex/AGENTS.md").exists())
        report = distribution.project_context(self.project)
        self.assertEqual(report["client_activation"], "none")
        self.assertEqual(report["project_adapter"]["file_installation"], "installed")
        self.assertEqual(report["project_adapter"]["desktop_discovery"], "unverified")
        with self.assertRaises(FileExistsError):
            codex_project.codex_project_preview(self.project)

    def test_existing_codex_state_is_never_overwritten_or_merged(self) -> None:
        codex = self.project / ".codex"
        codex.mkdir()
        for name in ("config.toml", "AGENTS.md", "instructions.md"):
            (codex / name).write_bytes(b"owner")
        (codex / "agents").mkdir()
        with self.assertRaises(FileExistsError):
            codex_project.codex_project_preview(self.project)
        self.assertEqual((codex / "config.toml").read_bytes(), b"owner")
        self.assertFalse((self.project / codex_project.PENDING).exists())

    def test_existing_other_skills_are_preserved_but_entry_collision_blocks(self) -> None:
        skills = self.project / ".agents/skills"
        skills.mkdir(parents=True)
        other = skills / "owner-skill"
        other.mkdir()
        (other / "SKILL.md").write_bytes(b"owner skill")
        preview = codex_project.codex_project_preview(self.project)
        self.assertNotIn(".agents", preview["directories"])
        entry = skills / "agent-fabric-project"
        entry.mkdir()
        with self.assertRaises(FileExistsError):
            codex_project.install_codex_project(self.project, expected_preview_sha256=preview["preview_sha256"])
        self.assertEqual((other / "SKILL.md").read_bytes(), b"owner skill")
        entry.rmdir()
        self.apply_adapter()
        self.assertEqual((other / "SKILL.md").read_bytes(), b"owner skill")

    def test_stale_digest_and_case_alias_fail_before_any_write(self) -> None:
        preview = codex_project.codex_project_preview(self.project)
        with self.assertRaisesRegex(ValueError, "digest"):
            codex_project.install_codex_project(self.project, expected_preview_sha256="0" * 64)
        self.assertFalse((self.project / codex_project.PENDING).exists())
        (self.project / ".agents").mkdir()
        with self.assertRaisesRegex(ValueError, "digest"):
            codex_project.install_codex_project(self.project, expected_preview_sha256=preview["preview_sha256"])
        (self.project / ".Codex").mkdir()
        with self.assertRaises((ValueError, FileExistsError)):
            codex_project.codex_project_preview(self.project)
        self.assertFalse((self.project / codex_project.PENDING).exists())

    def test_linked_parents_and_traversal_are_rejected(self) -> None:
        external = self.root / "external"
        external.mkdir()
        (self.project / ".agents").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Links"):
            codex_project.codex_project_preview(self.project)
        self.assertEqual(list(external.iterdir()), [])
        with self.assertRaises(ValueError):
            codex_project.codex_project_preview(str(self.project / ".." / self.project.name))

    def test_native_link_denial_is_precise_and_leaves_pending_ownership(self) -> None:
        preview = codex_project.codex_project_preview(self.project)
        with mock.patch.object(codex_project.os, "symlink", side_effect=PermissionError("native links unavailable")):
            with self.assertRaisesRegex(OSError, "No copy, junction or elevation fallback"):
                codex_project.install_codex_project(self.project, expected_preview_sha256=preview["preview_sha256"])
        self.assertTrue((self.project / codex_project.PENDING).is_file())
        self.assertFalse((self.project / codex_project.RECEIPT).exists())
        self.assertFalse(os.path.lexists(self.project / ".codex/agents"))
        self.assertEqual(codex_project.codex_project_status(self.project)["file_installation"], "incomplete")
        with self.assertRaises(FileExistsError):
            codex_project.codex_project_preview(self.project)

    def test_unobservable_or_replaced_links_never_claim_app_discovery(self) -> None:
        self.apply_adapter()
        link = self.project / ".codex/agents"
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()
        link.mkdir()
        status = codex_project.codex_project_status(self.project)
        self.assertEqual(status["file_installation"], "invalid")
        self.assertIn("not a copy or junction", status["error"])
        self.assertEqual(status["desktop_discovery"], "unverified")
        self.assertEqual(status["claim_restore"], "unverified")
        self.assertEqual(distribution.project_status(self.project)["status"], "bound")

    def test_unmanaged_config_after_install_is_reported_without_replacement(self) -> None:
        self.apply_adapter()
        config = self.project / ".codex/config.toml"
        config.write_bytes(b"owner changes")
        status = codex_project.codex_project_status(self.project)
        self.assertEqual(status["file_installation"], "invalid")
        self.assertIn("Unmanaged config", status["error"])
        self.assertEqual(config.read_bytes(), b"owner changes")

    def test_failed_link_observation_during_apply_reports_incomplete(self) -> None:
        preview = codex_project.codex_project_preview(self.project)
        with mock.patch.object(codex_project.os, "readlink", return_value="../../outside"):
            with self.assertRaisesRegex(OSError, "incomplete at .codex/agents"):
                codex_project.install_codex_project(self.project, expected_preview_sha256=preview["preview_sha256"])
        self.assertEqual(codex_project.codex_project_status(self.project)["file_installation"], "incomplete")

    def test_installation_does_not_claim_or_restore_a_socrates_chat(self) -> None:
        started = start_task(self.project, "Transfer boundary", "small-bug", "transfer-boundary")
        before = restore_task(self.project, started["task_id"])
        self.apply_adapter()
        after = restore_task(self.project, started["task_id"])
        self.assertEqual(before, after)
        self.assertEqual(after["memory"]["socrates_chat"]["status"], "awaiting-claim")
        with self.assertRaisesRegex(PermissionError, "claimed separate Socrates chat"):
            transition_step(self.project, started["task_id"], "intake", "in-progress")

    def test_receipt_rejects_foreign_paths_and_fictitious_verified_claims(self) -> None:
        self.apply_adapter()
        record = json.loads((self.project / codex_project.RECEIPT).read_bytes())
        for field, value in (
            ("desktop_discovery", "verified"), ("claim_restore", "verified"),
            ("directories", ["../../outside"]), ("links", []), ("schema_version", True),
            ("unknown", True), ("fabric_release", ".."),
        ):
            candidate = {**record, field: value}
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    codex_project.validate_codex_project_installation(candidate)

    @unittest.skipIf(jsonschema is None, "JSON Schema checks require the optional jsonschema test dependency")
    def test_ownership_schema_accepts_receipt_and_rejects_unsafe_shapes(self) -> None:
        schema = json.loads((SOURCE / "schemas/codex-project-installation.schema.json").read_bytes())
        validator_type = getattr(jsonschema, "Draft202012Validator", None)
        if validator_type is None:
            # В jsonschema 3.x доступны только общие с Draft 7 keywords этой схемы.
            # Меняем dialect лишь в тестовой копии: это не проверка meta-schema 2020-12.
            validator_type = jsonschema.Draft7Validator
            schema = {**schema, "$schema": validator_type.META_SCHEMA["$id"]}
        validator_type.check_schema(schema)
        validator = validator_type(schema)
        self.apply_adapter()
        record = json.loads((self.project / codex_project.RECEIPT).read_bytes())
        validator.validate(record)
        for field, value in (("desktop_discovery", "verified"), ("claim_restore", "verified"), ("directories", ["../../outside"]), ("unknown", True)):
            with self.subTest(field=field):
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate({**record, field: value})
        bad = copy.deepcopy(record)
        bad["links"][0]["target"] = "/outside"
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(bad)
        for version in (".", "..", "CON", "con.1", "1.2.", "1.2\n", "a/b", "a\\b"):
            with self.subTest(version=version):
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate({**record, "fabric_release": version})
                with self.assertRaises(ValueError):
                    codex_project.validate_codex_project_installation({**record, "fabric_release": version})
                bad = copy.deepcopy(record)
                bad["links"] = codex_project._links(version)
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(bad)

    def test_scoped_cli_preview_apply_status_and_wrong_project_restriction(self) -> None:
        target = str(self.project)
        preview = self.launcher("project", "codex-install", target, "--preview", "--json")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        digest = json.loads(preview.stdout)["preview_sha256"]
        missing_digest = self.launcher("project", "codex-install", target, "--apply")
        self.assertNotEqual(missing_digest.returncode, 0)
        applied = self.launcher("project", "codex-install", target, "--apply", "--expected-preview-sha256", digest, "--json")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        status = self.launcher("project", "codex-status", target, "--json")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["file_installation"], "installed")
        other = self.root / "other"
        other.mkdir()
        refused = self.launcher("project", "codex-install", str(other), "--preview")
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(list(other.iterdir()), [])
