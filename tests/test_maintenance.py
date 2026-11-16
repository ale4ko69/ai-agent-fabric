import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_agent_fabric.maintenance import apply_candidate, candidate_digest, inspect_operation, load_maintenance_policy, parse_candidate, preview_candidate
from ai_agent_fabric.entrypoints import start_task
from ai_agent_fabric.memory import claim_socrates_chat, advance_task_step
from ai_agent_fabric.task_specs import approval_preview, attest_chat_approval


class MaintenancePreviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / ".agent-fabric" / "config"
        self.config.mkdir(parents=True)
        (self.config / "capabilities.json").write_text(json.dumps({
            "schema_version": 1,
            "requirements": {"bash": "optional", "python": "required", "git": "required"},
            "enabled_packs": ["maintenance"],
        }), encoding="utf-8")
        (self.root / "evidence.md").write_text("evidence", encoding="utf-8")
        self.policy = {"schema_version": 1, "enabled": True, "paths": ["docs/guide.md"], "commands": [["python", "check.py"]], "delivery": []}
        self.candidate = {"task_id": "test-task", "paths": ["docs/guide.md"], "commands": [["python", "check.py"]], "delivery": [], "evidence": ["evidence.md"]}

    def write_policy(self):
        (self.config / "maintenance-policy.json").write_text(json.dumps(self.policy), encoding="utf-8")

    def test_absent_policy_is_disabled(self):
        self.assertFalse(load_maintenance_policy(self.root)["enabled"])
        with self.assertRaises(PermissionError):
            preview_candidate(self.root, "test-task", self.candidate)

    def test_preview_is_read_only_and_requires_approval(self):
        self.write_policy()
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": False}):
            with self.assertRaises(PermissionError):
                preview_candidate(self.root, "test-task", self.candidate)
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}):
            result = preview_candidate(self.root, "test-task", self.candidate)
        self.assertEqual(result["status"], "preview-only")
        self.assertEqual(len(result["candidate_sha256"]), 64)
        self.assertFalse((self.root / "docs" / "guide.md").exists())

    def test_forbidden_paths_commands_and_delivery_are_denied(self):
        self.write_policy()
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}):
            for name, value in (("paths", ["../escape"]), ("paths", [".git/config"]), ("paths", ["c:escape"]), ("paths", ["docs/file:stream"]), ("commands", [["other"]]), ("delivery", ["push"])):
                candidate = dict(self.candidate, **{name: value})
                with self.subTest(name=name, value=value), self.assertRaises((PermissionError, ValueError)):
                    preview_candidate(self.root, "test-task", candidate)

    def test_duplicate_keys_and_linked_targets_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_candidate('{"task_id":"first","task_id":"second"}')
        (self.root / "actual").mkdir()
        try:
            (self.root / "docs").symlink_to(self.root / "actual", target_is_directory=True)
        except OSError:
            self.skipTest("symbolic links are unavailable")
        self.write_policy()
        with self.assertRaises(ValueError):
            load_maintenance_policy(self.root)

    def test_capability_and_project_policy_do_not_leak(self):
        self.write_policy()
        (self.config / "capabilities.json").write_text(json.dumps({
            "schema_version": 1,
            "requirements": {"bash": "optional", "python": "required", "git": "required"},
            "enabled_packs": [],
        }), encoding="utf-8")
        with self.assertRaises(PermissionError):
            preview_candidate(self.root, "test-task", self.candidate)
        other = self.root / "other"
        (other / ".agent-fabric" / "config").mkdir(parents=True)
        self.assertFalse(load_maintenance_policy(other)["enabled"])

    def test_invalid_policy_types_and_duplicates_fail_closed(self):
        path = self.config / "maintenance-policy.json"
        path.write_text('{"schema_version":1,"enabled":true,"enabled":false,"paths":[],"commands":[],"delivery":[]}', encoding="utf-8")
        with self.assertRaises(ValueError):
            load_maintenance_policy(self.root)

    def test_apply_respects_reviewed_preimage_and_preserves_a_concurrent_edit(self):
        target = self.config / "harness" / "retrospective.json"
        target.parent.mkdir()
        original = '{"schema_version":1,"minimum_signal_count":1,"summary_style":"brief"}'
        updated = '{"schema_version":1,"minimum_signal_count":2,"summary_style":"detailed"}'
        target.write_text(original, encoding="utf-8")
        self.policy["paths"] = [".agent-fabric/config/harness/retrospective.json"]
        self.policy["commands"] = []
        self.write_policy()
        candidate = dict(self.candidate, paths=self.policy["paths"], commands=[], edit={
            "path": self.policy["paths"][0],
            "before_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "content": updated,
        }, evaluations=["json-object"])
        package = self.root / "package"
        package.mkdir()
        lifecycle = {"lifecycle": {"status": "active", "next_action": "implementation"}, "socrates_chat": {"status": "claimed"}}
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}), patch("ai_agent_fabric.maintenance.restore", return_value=lifecycle), patch("ai_agent_fabric.maintenance.package_path", return_value=package):
            digest = preview_candidate(self.root, "test-task", candidate)["candidate_sha256"]
            (package / "spec.md").write_text("maintenance-candidate-sha256: " + digest + "\n", encoding="utf-8")
            target.write_text("other agent edit", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(target.read_text(encoding="utf-8"), "other agent edit")
            target.write_text(original, encoding="utf-8")
            result = apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(result["status"], "applied")
            self.assertEqual(target.read_text(encoding="utf-8"), updated)
            backup = self.root / ".agent-fabric" / "backups" / "maintenance" / "preimages" / (hashlib.sha256(original.encode()).hexdigest() + ".json")
            self.assertEqual(backup.read_text(encoding="utf-8"), original)
            self.assertEqual(inspect_operation(self.root, result["candidate_sha256"])["status"], "candidate-present")
            target.write_text(original, encoding="utf-8")
            self.assertEqual(inspect_operation(self.root, result["candidate_sha256"])["status"], "unchanged")
            with self.assertRaises(FileExistsError):
                apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            target.write_text("other agent edit", encoding="utf-8")
            self.assertEqual(inspect_operation(self.root, result["candidate_sha256"])["status"], "conflict")
            self.assertEqual(target.read_text(encoding="utf-8"), "other agent edit")

    def test_apply_rejects_candidate_not_bound_to_spec(self):
        self.write_policy()
        package = self.root / "package"
        package.mkdir()
        (package / "spec.md").write_text("No approved candidate", encoding="utf-8")
        lifecycle = {"lifecycle": {"status": "active", "next_action": "implementation"}, "socrates_chat": {"status": "claimed"}}
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}), patch("ai_agent_fabric.maintenance.restore", return_value=lifecycle), patch("ai_agent_fabric.maintenance.package_path", return_value=package):
            with self.assertRaises(PermissionError):
                apply_candidate(self.root, "test-task", self.candidate)

    def test_late_edit_during_authority_check_is_preserved(self):
        import ai_agent_fabric.maintenance as maintenance
        target = self.config / "harness" / "retrospective.json"
        target.parent.mkdir()
        old = '{"schema_version":1,"minimum_signal_count":1,"summary_style":"brief"}'
        new = '{"schema_version":1,"minimum_signal_count":2,"summary_style":"brief"}'
        target.write_text(old, encoding="utf-8")
        self.policy["paths"] = [".agent-fabric/config/harness/retrospective.json"]
        self.policy["commands"] = []
        self.write_policy()
        candidate = dict(self.candidate, paths=self.policy["paths"], commands=[], edit={"path": self.policy["paths"][0], "before_sha256": hashlib.sha256(old.encode()).hexdigest(), "content": new}, evaluations=["json-object"])
        package = self.root / "package"
        package.mkdir()
        lifecycle = {"lifecycle": {"status": "active", "next_action": "implementation"}, "socrates_chat": {"status": "claimed"}}
        real_preview = maintenance.preview_candidate
        count = 0
        def preview_and_edit(*args, **kwargs):
            nonlocal count
            count += 1
            result = real_preview(*args, **kwargs)
            if count == 2:
                target.write_text("another agent wrote this", encoding="utf-8")
            return result
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}), patch("ai_agent_fabric.maintenance.restore", return_value=lifecycle), patch("ai_agent_fabric.maintenance.package_path", return_value=package):
            digest = real_preview(self.root, "test-task", candidate)["candidate_sha256"]
            (package / "spec.md").write_text("maintenance-candidate-sha256: " + digest + "\n", encoding="utf-8")
            with patch("ai_agent_fabric.maintenance.preview_candidate", side_effect=preview_and_edit):
                with self.assertRaises(FileExistsError):
                    apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(target.read_text(encoding="utf-8"), "another agent wrote this")

    def test_policy_change_during_preparation_fails_closed(self):
        import ai_agent_fabric.maintenance as maintenance
        target = self.config / "harness" / "retrospective.json"
        target.parent.mkdir()
        old = '{"schema_version":1,"minimum_signal_count":1,"summary_style":"brief"}'
        new = '{"schema_version":1,"minimum_signal_count":2,"summary_style":"brief"}'
        target.write_text(old, encoding="utf-8")
        self.policy["paths"] = [".agent-fabric/config/harness/retrospective.json"]
        self.policy["commands"] = []
        self.write_policy()
        candidate = dict(self.candidate, paths=self.policy["paths"], commands=[], edit={"path": self.policy["paths"][0], "before_sha256": hashlib.sha256(old.encode()).hexdigest(), "content": new}, evaluations=["json-object"])
        package = self.root / "package"
        package.mkdir()
        lifecycle = {"lifecycle": {"status": "active", "next_action": "implementation"}, "socrates_chat": {"status": "claimed"}}
        real_preview = maintenance.preview_candidate
        count = 0
        def preview_and_revoke(*args, **kwargs):
            nonlocal count
            count += 1
            result = real_preview(*args, **kwargs)
            if count == 2:
                self.policy["enabled"] = False
                self.write_policy()
            return result
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}), patch("ai_agent_fabric.maintenance.restore", return_value=lifecycle), patch("ai_agent_fabric.maintenance.package_path", return_value=package):
            digest = real_preview(self.root, "test-task", candidate)["candidate_sha256"]
            (package / "spec.md").write_text("maintenance-candidate-sha256: " + digest + "\n", encoding="utf-8")
            with patch("ai_agent_fabric.maintenance.preview_candidate", side_effect=preview_and_revoke):
                with self.assertRaises(PermissionError):
                    apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(target.read_text(encoding="utf-8"), old)

    def test_prepared_unchanged_operation_does_not_retry_automatically(self):
        target = self.config / "harness" / "retrospective.json"
        target.parent.mkdir()
        old = '{"schema_version":1,"minimum_signal_count":1,"summary_style":"brief"}'
        new = '{"schema_version":1,"minimum_signal_count":2,"summary_style":"brief"}'
        target.write_text(old, encoding="utf-8")
        self.policy["paths"] = [".agent-fabric/config/harness/retrospective.json"]
        self.policy["commands"] = []
        self.write_policy()
        candidate = dict(self.candidate, paths=self.policy["paths"], commands=[], edit={"path": self.policy["paths"][0], "before_sha256": hashlib.sha256(old.encode()).hexdigest(), "content": new}, evaluations=["json-object"])
        package = self.root / "package"
        package.mkdir()
        lifecycle = {"lifecycle": {"status": "active", "next_action": "implementation"}, "socrates_chat": {"status": "claimed"}}
        with patch("ai_agent_fabric.maintenance.implementation_readiness", return_value={"ready": True}), patch("ai_agent_fabric.maintenance.restore", return_value=lifecycle), patch("ai_agent_fabric.maintenance.package_path", return_value=package):
            digest = preview_candidate(self.root, "test-task", candidate)["candidate_sha256"]
            (package / "spec.md").write_text("maintenance-candidate-sha256: " + digest + "\n", encoding="utf-8")
            with patch("ai_agent_fabric.maintenance.os.replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(inspect_operation(self.root, digest)["status"], "unchanged")
            with self.assertRaises(FileExistsError):
                apply_candidate(self.root, "test-task", candidate)
            self.assertEqual(target.read_text(encoding="utf-8"), old)

    def test_typed_config_rejects_privilege_fields(self):
        from ai_agent_fabric.maintenance import _retrospective_config
        with self.assertRaises(ValueError):
            _retrospective_config('{"schema_version":1,"minimum_signal_count":1,"summary_style":"brief","guards":"off"}')

    def test_harness_review_reads_typed_candidate_context(self):
        from ai_agent_fabric.harness import retrospective_input
        path = self.config / "harness" / "retrospective.json"
        path.parent.mkdir()
        path.write_text('{"schema_version":1,"minimum_signal_count":2,"summary_style":"detailed"}', encoding="utf-8")
        report = retrospective_input(self.root)
        context = report["maintenance_context"]
        self.assertFalse(context["threshold_met"])
        self.assertEqual(context["summary_style"], "detailed")
        self.assertEqual(context["candidate_input"]["snapshot_sha256"], report["snapshot"]["sha256"])
        self.assertEqual(context["candidate_input"]["status"], "needs-evidence-and-scoped-proposal")
        (self.config / "capabilities.json").write_text(json.dumps({
            "schema_version": 1,
            "requirements": {"bash": "optional", "python": "required", "git": "required"},
            "enabled_packs": [],
        }), encoding="utf-8")
        self.assertNotIn("maintenance_context", retrospective_input(self.root))

    def test_actual_approved_task_lifecycle_and_stale_scope(self):
        target = self.config / "harness" / "retrospective.json"
        target.parent.mkdir()
        old = '{"schema_version":1,"minimum_signal_count":1,"summary_style":"brief"}'
        new = '{"schema_version":1,"minimum_signal_count":2,"summary_style":"brief"}'
        target.write_text(old, encoding="utf-8")
        self.policy["paths"] = [".agent-fabric/config/harness/retrospective.json"]
        self.policy["commands"] = []
        self.write_policy()
        candidate = dict(self.candidate, paths=self.policy["paths"], commands=[], edit={
            "path": self.policy["paths"][0], "before_sha256": hashlib.sha256(old.encode()).hexdigest(), "content": new,
        }, evaluations=["json-object"])
        start_task(self.root, "Test task", "planned", "test-task")
        claim_socrates_chat(self.root, "test-task", "test-chat")
        package = self.root / "docs/specs/active/test-task"
        digest = candidate_digest(candidate)["candidate_sha256"]
        (package / "spec.md").write_text("maintenance-candidate-sha256: " + digest + "\n", encoding="utf-8")
        kepler_path = package / "kepler.json"
        kepler = json.loads(kepler_path.read_text(encoding="utf-8"))
        kepler["verdict"] = "advice"
        kepler["artifact_digests"] = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in ("spec.md", "research.md", "plan.md")}
        kepler_path.write_text(json.dumps(kepler), encoding="utf-8")
        reviewed = approval_preview(self.root, "test-task")["kepler_verdict_sha256"]
        attest_chat_approval(self.root, "test-task", reviewed, "test-owner-chat")
        evidence = "docs/specs/active/test-task/evidence/test-evidence.md"
        (self.root / evidence).write_text("test evidence", encoding="utf-8")
        for step in ("intake", "discovery", "plan", "kepler", "human-approval"):
            advance_task_step(self.root, "test-task", step, "done", evidence, "test-evidence")
        target.write_text("other edit", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            apply_candidate(self.root, "test-task", candidate)
        self.assertEqual(target.read_text(encoding="utf-8"), "other edit")
        target.write_text(old, encoding="utf-8")
        (package / "spec.md").write_text((package / "spec.md").read_text(encoding="utf-8") + "scope changed\n", encoding="utf-8")
        with self.assertRaises(PermissionError):
            apply_candidate(self.root, "test-task", candidate)
        self.assertEqual(target.read_text(encoding="utf-8"), old)
        (package / "spec.md").write_text("maintenance-candidate-sha256: " + digest + "\n", encoding="utf-8")
        result = apply_candidate(self.root, "test-task", candidate)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(target.read_text(encoding="utf-8"), new)
        self.assertEqual((self.root / result["backup"]).read_text(encoding="utf-8"), old)
        self.policy["delivery"] = [{}]
        self.write_policy()
        with self.assertRaises(ValueError):
            load_maintenance_policy(self.root)


if __name__ == "__main__":
    unittest.main()
