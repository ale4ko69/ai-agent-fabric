import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ai_agent_fabric import distribution, project_install
from ai_agent_fabric.memory import MEMORY_SCHEMA_VERSION


SOURCE = Path(__file__).resolve().parents[1]


class ProjectInstallTest(unittest.TestCase):
    def install(self, target: Path) -> dict:
        """Тесты вызывают apply только с digest собственного read-only preview."""
        preview = project_install.project_install_preview(target, SOURCE, "codex")
        return project_install.install_project(target, SOURCE, "codex", expected_preview_sha256=preview["preview_sha256"])

    def run_launcher(self, target: Path, *arguments: str, environment: dict | None = None) -> subprocess.CompletedProcess:
        """Проверять установленный entry point отдельным isolated Python, без запуска клиента."""
        return subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(target / project_install.LAUNCHER), *arguments],
            capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
        )

    def test_fresh_install_exact_inventory_and_no_global_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "project"
            target.mkdir()
            global_home = root / "user"
            global_home.mkdir()
            sentinel = global_home / "owner-instructions"
            sentinel.write_bytes(b"untouched")
            native = target / "AGENTS.md"
            native.write_bytes(b"project instructions")
            with (
                mock.patch.dict(os.environ, {"HOME": str(global_home), "AI_AGENT_FABRIC_HOME": str(global_home)}),
                mock.patch.object(distribution, "install_release", side_effect=AssertionError("global install")),
                mock.patch.object(distribution, "_run_source_installer", side_effect=AssertionError("source dispatch")),
                mock.patch.object(distribution, "_write_global_launcher", side_effect=AssertionError("global launcher")),
                mock.patch.object(distribution, "enable_client", side_effect=AssertionError("client activation")),
                mock.patch.object(tempfile, "gettempdir", side_effect=AssertionError("system temp")),
            ):
                result = self.install(target)
            actual_files = {path.relative_to(target).as_posix() for path in (target / ".agent-fabric").rglob("*") if path.is_file()}
            actual_dirs = {".agent-fabric"} | {path.relative_to(target).as_posix() for path in (target / ".agent-fabric").rglob("*") if path.is_dir()}
            self.assertEqual(actual_files, set(result["files"]))
            self.assertEqual(actual_dirs, set(result["directories"]))
            self.assertEqual(result["client_activation"], "none")
            self.assertEqual(list(global_home.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_bytes(), b"untouched")
            self.assertEqual(native.read_bytes(), b"project instructions")
            self.assertFalse((target / ".codex").exists())
            home = Path(result["fabric_home"])
            for name in ("clients", "marketplace", "adapters", "skills"):
                self.assertFalse((home / name).exists())
            release = home / "releases" / result["fabric_release"]
            for name in (".codex-plugin", "hooks", "skills/work", "scripts/run-fabric.py", "adapters/codex", "bin"):
                self.assertFalse((release / name).exists())
            self.assertTrue((release / "scripts/secret-entry.sh").is_file())
            self.assertTrue((release / "skills/project-entry/SKILL.md").is_file())
            self.assertTrue((release / "skills/new-product/SKILL.md").is_file())
            self.assertTrue((release / "adapters/codex-project/agents/socrates.toml").is_file())
            with sqlite3.connect(target / ".agent-fabric/memory.db") as connection:
                self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], MEMORY_SCHEMA_VERSION)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)
            context = distribution.project_context(target, global_home)
            self.assertEqual(context["status"], "bound")
            self.assertEqual(context["client_activation"], "none")
            self.assertIsNone(context["shared_contracts"]["adapter_manifest"])
            self.assertTrue(Path(context["release_root"]).is_relative_to(target / ".agent-fabric"))

    def test_preview_is_read_only_repeatable_and_lists_sqlite_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            with (
                mock.patch.object(project_install, "initialize", side_effect=AssertionError("SQLite init")),
                mock.patch.object(sqlite3, "connect", side_effect=AssertionError("SQLite open")),
                mock.patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")),
            ):
                first = project_install.project_install_preview(target, SOURCE, "codex")
                second = project_install.project_install_preview(target, SOURCE, "codex")
            self.assertEqual(first, second)
            self.assertEqual(list(target.iterdir()), [])
            self.assertEqual(set(first["transient_paths"]), {".agent-fabric/memory.db" + suffix for suffix in ("-journal", "-wal", "-shm")})
            for relative in first["files"] + first["directories"] + first["transient_paths"]:
                self.assertTrue((target / relative).is_relative_to(target / ".agent-fabric"))
            self.assertFalse(any("__pycache__" in item or item.endswith(".pyc") for item in first["files"]))

    def test_plan_prepares_stable_manifest_index_and_launcher_without_wall_clock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            with mock.patch.object(distribution, "datetime") as clock:
                clock.now.side_effect = AssertionError("wall-clock metadata")
                first, prepared = project_install._plan(target, SOURCE, "codex")
                second, repeated = project_install._plan(target, SOURCE, "codex")
                clock.now.assert_not_called()
            self.assertEqual(first, second)
            self.assertEqual(prepared, repeated)
            self.assertEqual(list(target.iterdir()), [])
            prefix = f"{project_install.RUNTIME_DIRECTORY}/releases/{first['fabric_release']}"
            manifest_path = f"{prefix}/release-manifest.json"
            index_path = f"{project_install.RUNTIME_DIRECTORY}/installation.json"
            self.assertTrue({manifest_path, index_path, project_install.LAUNCHER}.issubset(prepared))
            expected_hashes = {path: hashlib.sha256(data).hexdigest() for path, data in prepared.items()}
            self.assertEqual(first["file_sha256"], expected_hashes)
            self.assertEqual(first["snapshot_sha256"], project_install._digest(expected_hashes))
            self.assertEqual(first["preview_sha256"], project_install._digest({key: value for key, value in first.items() if key != "preview_sha256"}))
            runtime_created = {".agent-fabric/memory.db", ".agent-fabric/project-installation.json"}
            self.assertEqual(set(first["runtime_created_files"]), runtime_created)
            self.assertEqual(set(first["files"]) - set(prepared), runtime_created)
            self.assertTrue(runtime_created.isdisjoint(expected_hashes))
            self.assertTrue(set(first["transient_paths"]).isdisjoint(expected_hashes))
            manifest = json.loads(prepared[manifest_path])
            self.assertEqual(manifest["created_at"], project_install.PROJECT_RELEASE_EPOCH)
            self.assertEqual(manifest["memory"]["schema_version"], MEMORY_SCHEMA_VERSION)
            self.assertEqual(manifest["files"], {
                path.removeprefix(f"{prefix}/"): digest
                for path, digest in expected_hashes.items()
                if path.startswith(f"{prefix}/") and path != manifest_path
            })
            index = json.loads(prepared[index_path])
            self.assertEqual(index["releases"][0]["manifest_sha256"], expected_hashes[manifest_path])
            self.assertIn(expected_hashes[manifest_path].encode("ascii"), prepared[project_install.LAUNCHER])

    def test_review_digest_covers_each_prepared_metadata_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            original = project_install.project_install_preview(target, SOURCE, "codex")
            serialize = project_install._json_bytes
            render = project_install._launcher
            prefix = f"{project_install.RUNTIME_DIRECTORY}/releases/{original['fabric_release']}"
            for selected in (f"{prefix}/release-manifest.json", f"{project_install.RUNTIME_DIRECTORY}/installation.json", project_install.LAUNCHER):
                def changed_json(value):
                    """Изменить только байты выбранного JSON-выхода, не исходники и не digest-код."""
                    data = serialize(value)
                    if (
                        selected == f"{prefix}/release-manifest.json"
                        and set(value) == {"schema_version", "version", "created_at", "memory", "files"}
                    ) or (
                        selected == f"{project_install.RUNTIME_DIRECTORY}/installation.json"
                        and set(value) == {"schema_version", "fabric_home", "current_release", "releases"}
                    ):
                        return data + b"\n"
                    return data

                def changed_launcher(*arguments):
                    """Отдельно проверить renderer: добавленный байт обязан менять review digest."""
                    return render(*arguments) + ("\n" if selected == project_install.LAUNCHER else "")

                with (
                    self.subTest(selected=selected),
                    mock.patch.object(project_install, "_json_bytes", side_effect=changed_json),
                    mock.patch.object(project_install, "_launcher", side_effect=changed_launcher),
                ):
                    changed = project_install.project_install_preview(target, SOURCE, "codex")
                    self.assertEqual(original["source_sha256"], changed["source_sha256"])
                    self.assertNotEqual(original["file_sha256"][selected], changed["file_sha256"][selected])
                    self.assertNotEqual(original["snapshot_sha256"], changed["snapshot_sha256"])
                    self.assertNotEqual(original["preview_sha256"], changed["preview_sha256"])
                    with self.assertRaisesRegex(ValueError, "digest"):
                        project_install.install_project(target, SOURCE, "codex", expected_preview_sha256=original["preview_sha256"])
            self.assertEqual(list(target.iterdir()), [])

    def test_apply_writes_exact_prepared_bytes_without_regenerating_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            plan, prepared = project_install._plan(target, SOURCE, "codex")
            with (
                mock.patch.object(project_install, "_plan", return_value=(plan, prepared)),
                mock.patch.object(distribution, "_release_manifest", side_effect=AssertionError("late manifest")),
                mock.patch.object(project_install, "_launcher", side_effect=AssertionError("late launcher")),
            ):
                result = project_install.install_project(target, SOURCE, "codex", expected_preview_sha256=plan["preview_sha256"])
            self.assertEqual(result["status"], "installed")
            for path, data in prepared.items():
                with self.subTest(path=path):
                    self.assertEqual((target / path).read_bytes(), data)
            receipt = json.loads((target / ".agent-fabric/project-installation.json").read_bytes())
            self.assertEqual(receipt["preview_sha256"], plan["preview_sha256"])
            manifest = distribution._validate_installed_release(Path(plan["fabric_home"]), plan["fabric_release"])
            self.assertEqual(manifest["created_at"], project_install.PROJECT_RELEASE_EPOCH)

    def test_schema_path_patterns_match_runtime_component_validation(self) -> None:
        schema = json.loads((SOURCE / "schemas/project-installation.schema.json").read_text(encoding="utf-8"))
        path_rule = schema["$defs"]["paths"]["items"]
        self.assertEqual(path_rule["type"], "string")
        for field in ("files", "directories", "transient_paths"):
            self.assertEqual(schema["properties"][field], {"$ref": "#/$defs/paths"})
        record = {
            "schema_version": 1, "mode": "project-runtime",
            "project_root": str(SOURCE), "fabric_home": str(SOURCE / project_install.RUNTIME_DIRECTORY),
            "fabric_release": "test-schema", "client": "codex", "client_activation": "none",
            "source_sha256": "0" * 64, "preview_sha256": "0" * 64,
            "files": [
                project_install.LAUNCHER, ".agent-fabric/fabric-binding.json",
                ".agent-fabric/memory.db", ".agent-fabric/project-installation.json",
            ],
            "directories": [".agent-fabric"], "transient_paths": [".agent-fabric/memory.db-journal"],
        }
        valid = (
            ".agent-fabric", ".agent-fabric/config/file.json", ".agent-fabric/.hidden",
            ".agent-fabric/a b/c..d", ".agent-fabric/COM0/COM10", ".agent-fabric/console/auxiliary",
            ".agent-fabric/Unicode-δ/ leading-space", ".agent-fabric/ConText",
        )
        invalid = (
            "", "/.agent-fabric/file", "./.agent-fabric/file", ".agent-fabric-other/file",
            ".agent-fabric/", ".agent-fabric//file", ".agent-fabric/.", ".agent-fabric/..",
            ".agent-fabric/a/./file", ".agent-fabric/a/../file", ".agent-fabric/a./file",
            ".agent-fabric/a /file", ".agent-fabric/file.", ".agent-fabric/file ", ".agent-fabric\n",
            ".agent-fabric/CON", ".agent-fabric/con.txt", ".agent-fabric/AUX/file",
            ".agent-fabric/NUL.log", ".agent-fabric/PRN", ".agent-fabric/CoM1.md",
            ".agent-fabric/com9", ".agent-fabric/lPt1/file", ".agent-fabric/LPT9.txt",
        )
        invalid += tuple(f".agent-fabric/a{character}b" for character in "\\:<>\"|?*")
        invalid += tuple(f".agent-fabric/a{chr(code)}b" for code in range(32))
        for accepted, paths in ((True, valid), (False, invalid)):
            for path in paths:
                with self.subTest(path=path):
                    self.assertEqual(re.search(path_rule["pattern"], path) is not None, accepted)
                    candidate = {**record, "transient_paths": [path]}
                    if accepted:
                        project_install.validate_project_installation(candidate)
                    else:
                        with self.assertRaises(ValueError):
                            project_install.validate_project_installation(candidate)
        release_rule = schema["properties"]["fabric_release"]
        for release, accepted in (
            ("1", True), ("0.1.30", True), ("1+local", True), ("ConText", True), ("COM0", True),
            (".", False), ("..", False), ("1.", False), ("1\n", False),
            ("CON", False), ("con.txt", False), ("LPT9", False), ("NUL.log", False),
        ):
            with self.subTest(release=release):
                self.assertEqual(re.search(release_rule["pattern"], release) is not None, accepted)
                candidate = {**record, "fabric_release": release}
                if accepted:
                    project_install.validate_project_installation(candidate)
                else:
                    with self.assertRaises(ValueError):
                        project_install.validate_project_installation(candidate)

    def test_bad_digest_and_changed_target_fail_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "project"
            target.mkdir()
            other = root / "other"
            other.mkdir()
            preview = project_install.project_install_preview(target, SOURCE, "codex")
            for candidate, digest in ((target, "0" * 64), (target, ""), (other, preview["preview_sha256"])):
                with self.subTest(candidate=candidate, digest=digest):
                    with self.assertRaisesRegex(ValueError, "digest"):
                        project_install.install_project(candidate, SOURCE, "codex", expected_preview_sha256=digest)
                    self.assertFalse((candidate / ".agent-fabric").exists())
            target.rename(root / "previous-target")
            target.mkdir()
            with self.assertRaisesRegex(ValueError, "digest"):
                project_install.install_project(target, SOURCE, "codex", expected_preview_sha256=preview["preview_sha256"])
            self.assertFalse((target / ".agent-fabric").exists())

    def test_changed_source_fails_before_writing_and_foreign_source_never_dispatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "project"
            target.mkdir()
            source = root / "source"
            source.mkdir()
            with mock.patch.object(distribution, "_run_source_installer", side_effect=AssertionError("foreign execution")):
                with self.assertRaisesRegex(ValueError, "selected trusted source"):
                    project_install.project_install_preview(target, source, "codex")
            for relative in distribution.RELEASE_ASSETS:
                origin = SOURCE / relative
                destination = source / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if origin.is_dir():
                    shutil.copytree(origin, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                else:
                    shutil.copy2(origin, destination)
            with mock.patch.object(distribution, "_source_owns_installer", return_value=True):
                preview = project_install.project_install_preview(target, source, "codex")
                with (source / "README.md").open("a", encoding="utf-8") as stream:
                    stream.write("\nChanged after review.\n")
                with self.assertRaisesRegex(ValueError, "digest"):
                    project_install.install_project(target, source, "codex", expected_preview_sha256=preview["preview_sha256"])
            self.assertFalse((target / ".agent-fabric").exists())

    def test_existing_state_file_directory_and_dangling_link_block_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for kind in ("file", "directory", "link"):
                target = root / kind
                target.mkdir()
                state = target / ".agent-fabric"
                if kind == "file":
                    state.write_bytes(b"owner")
                elif kind == "directory":
                    state.mkdir()
                else:
                    try:
                        state.symlink_to(root / "absent", target_is_directory=True)
                    except OSError:
                        continue
                with self.subTest(kind=kind):
                    with self.assertRaises(FileExistsError):
                        project_install.project_install_preview(target, SOURCE, "codex")

    def test_missing_traversal_foreign_paths_and_linked_ancestors_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "project"
            target.mkdir()
            paths = [str(root / "missing"), str(target / ".." / "project"), "C:project", "\\\\server\\share", str(root / "ambiguous. ")]
            if os.name != "nt":
                paths.append("C:\\project")
            for path in paths:
                with self.subTest(path=path):
                    with self.assertRaises((OSError, ValueError)):
                        project_install.project_install_preview(path, SOURCE, "codex")
            linked = root / "linked"
            try:
                linked.symlink_to(root, target_is_directory=True)
            except OSError:
                return
            with self.assertRaisesRegex(ValueError, "Links"):
                project_install.project_install_preview(linked / "project", SOURCE, "codex")
            with self.assertRaisesRegex(ValueError, "Links"):
                project_install.project_install_preview(target, linked, "codex")
            self.assertFalse((target / ".agent-fabric").exists())

    def test_reparse_and_foreign_owner_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            original = Path.lstat

            def reparse(path: Path):
                """Эмулировать Windows reparse на обычном каталоге без платформенных зависимостей."""
                info = original(path)
                return argparse.Namespace(st_mode=info.st_mode, st_file_attributes=0x400) if path == target else info

            with mock.patch.object(Path, "lstat", reparse):
                with self.assertRaisesRegex(ValueError, "reparse"):
                    project_install.project_install_preview(target, SOURCE, "codex")
            if hasattr(os, "geteuid"):
                owner = os.geteuid()
                with mock.patch.object(os, "geteuid", return_value=owner + 1):
                    with self.assertRaisesRegex(ValueError, "ownership"):
                        project_install.project_install_preview(target, SOURCE, "codex")

    def test_launcher_pins_home_project_release_and_rejects_global_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "project with spaces"
            target.mkdir()
            other = root / "other"
            other.mkdir()
            result = self.install(target)
            environment = dict(os.environ, AI_AGENT_FABRIC_HOME=str(other), PYTHONPATH=str(other), PYTHONHOME=str(other))
            status = self.run_launcher(target, "project", "status", str(target), "--json", environment=environment)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(json.loads(status.stdout)["release"], result["fabric_release"])
            forbidden = (
                ("distribution", "home"),
                ("distribution", "enable-client", "codex", "--home", str(other)),
                ("bootstrap", "bash", "--install"),
                ("project", "init", str(target), "--client", "codex"),
                ("project", "install", str(target), "--source", str(SOURCE), "--client", "codex", "--preview"),
                ("project", "status", str(other)),
                ("project", "status", str(target), "--home", str(other)),
                ("project", "status", str(target), "--ho", str(other)),
            )
            for command in forbidden:
                with self.subTest(command=command):
                    refused = self.run_launcher(target, *command)
                    self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(list(other.iterdir()), [])
            release = Path(result["fabric_home"]) / "releases" / result["fabric_release"]
            (release / "unexpected.pyc").write_bytes(b"untrusted")
            refused = self.run_launcher(target, "project", "status", str(target), "--json")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("file set changed", refused.stderr)

    def test_damaged_local_ownership_never_falls_back_to_global(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            self.install(target)
            (target / ".agent-fabric/project-installation.json").unlink()
            with mock.patch.object(distribution, "default_fabric_home", side_effect=AssertionError("global fallback")):
                self.assertEqual(distribution.project_status(target)["status"], "invalid")

    def test_ownership_contract_rejects_escape_unknown_fields_and_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            self.install(target)
            record = project_install.load_project_installation(target)
            for field, value in (
                ("files", ["/outside"]), ("directories", [".agent-fabric/../outside"]),
                ("transient_paths", [".agent-fabric/C:escape"]), ("client_activation", "desktop"),
                ("undeclared", True), ("fabric_home", str(target)),
                ("fabric_release", ".."), ("schema_version", True),
            ):
                bad = copy.deepcopy(record)
                bad[field] = value
                with self.subTest(field=field):
                    with self.assertRaises(ValueError):
                        project_install.validate_project_installation(bad)

    def test_cli_requires_explicit_mode_and_reviewed_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            base = [sys.executable, "-I", "-S", "-B", str(SOURCE / "scripts/run-fabric.py"), "project", "install", str(target), "--source", str(SOURCE), "--client", "codex", "--json"]
            for options in ([], ["--apply"], ["--preview", "--apply"], ["--preview", "--expected-preview-sha256", "0" * 64]):
                with self.subTest(options=options):
                    refused = subprocess.run([*base, *options], capture_output=True, text=True, check=False)
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertFalse((target / ".agent-fabric").exists())
            preview = subprocess.run([*base, "--preview"], capture_output=True, text=True, check=False)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            digest = json.loads(preview.stdout)["preview_sha256"]
            applied = subprocess.run([*base, "--apply", "--expected-preview-sha256", digest], capture_output=True, text=True, check=False)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(json.loads(applied.stdout)["client_activation"], "none")

    def test_interrupted_install_retains_partial_state_and_refuses_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            preview = project_install.project_install_preview(target, SOURCE, "codex")
            with mock.patch.object(project_install, "initialize", side_effect=OSError("interrupted")):
                with self.assertRaisesRegex(OSError, "interrupted"):
                    project_install.install_project(target, SOURCE, "codex", expected_preview_sha256=preview["preview_sha256"])
            self.assertTrue((target / ".agent-fabric").is_dir())
            self.assertFalse((target / ".agent-fabric/project-installation.json").exists())
            with self.assertRaises(FileExistsError):
                project_install.project_install_preview(target, SOURCE, "codex")

    def test_launcher_refuses_linked_release_root_and_ownership_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "project"
            target.mkdir()
            result = self.install(target)
            external = root / "external"
            external.write_bytes(b"untouched")
            sidecar = target / ".agent-fabric/memory.db-journal"
            try:
                sidecar.symlink_to(external)
            except OSError:
                return
            refused = self.run_launcher(target, "project", "status", str(target), "--json")
            self.assertNotEqual(refused.returncode, 0)
            self.assertEqual(external.read_bytes(), b"untouched")
            sidecar.unlink()
            release = Path(result["fabric_home"]) / "releases" / result["fabric_release"]
            moved = root / "moved-release"
            release.rename(moved)
            release.symlink_to(moved, target_is_directory=True)
            refused = self.run_launcher(target, "project", "status", str(target), "--json")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("link or reparse", refused.stderr)
