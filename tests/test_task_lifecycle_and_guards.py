from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ai_agent_fabric.__main__ import main
from ai_agent_fabric.distribution import install_release, onboard_project
from ai_agent_fabric.entrypoints import recover_unicode_package, restore_picker, restore_task, start_task
from ai_agent_fabric.harness import flush_guard_traces, record_checkpoint
from ai_agent_fabric.memory import claim_socrates_chat, initialize
from ai_agent_fabric.socrates import record_guard_failure, record_harness_signal, transition_step


SOURCE_ROOT = Path(__file__).resolve().parents[1]


class TaskLifecycleAndGuardsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.project = root / "project"
        self.project.mkdir()
        self.home = root / "fabric-home"
        install_release(SOURCE_ROOT, self.home, "test")
        onboard_project(self.project, "codex", self.home, "test")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_start_requires_a_separate_socrates_chat_claim(self) -> None:
        result = start_task(self.project, "Example task", "small-bug", "example-task")

        request = result["socrates_chat_request"]
        self.assertEqual(request["owner"], "root")
        self.assertEqual(request["action"], "create-separate-socrates-chat")
        self.assertNotIn("socrates_handoff", result)
        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["socrates_chat_request"]["task_id"], "example-task")
        self.assertEqual(restored["memory"]["session"]["id"], "example-task")
        self.assertEqual(restored["memory"]["session"]["status"], "awaiting-socrates-chat")
        self.assertEqual(
            [record["kind"] for record in restored["memory"]["records"]],
            ["task-started"],
        )
        with self.assertRaisesRegex(PermissionError, "claimed separate Socrates chat"):
            transition_step(self.project, "example-task", "intake", "in-progress")
        claimed = claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        self.assertEqual(claimed["next_action"], "intake")
        self.assertEqual(claimed["thread_id"], "socrates-example-task")
        self.assertEqual(
            claim_socrates_chat(self.project, "example-task", "socrates-example-task"),
            claimed,
        )
        claimed_restore = restore_task(self.project, "example-task")
        self.assertEqual(claimed_restore["memory"]["session"]["status"], "active")
        self.assertEqual(claimed_restore["memory"]["socrates_chat"]["thread_id"], "socrates-example-task")

    def test_memory_migration_prepares_a_claim_for_an_existing_active_task(self) -> None:
        import sqlite3

        start_task(self.project, "Example task", "small-bug", "example-task")
        connection = sqlite3.connect(self.project / ".agent-fabric/memory.db")
        try:
            connection.execute("DELETE FROM socrates_chats WHERE session_id='example-task'")
            connection.execute("UPDATE sessions SET status='active' WHERE id='example-task'")
            connection.execute("PRAGMA user_version=9")
            connection.commit()
        finally:
            connection.close()

        initialize(self.project)

        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["session"]["status"], "awaiting-socrates-chat")
        self.assertEqual(restored["memory"]["socrates_chat"]["status"], "awaiting-claim")

    def test_russian_start_has_one_ascii_package_session_and_lifecycle(self) -> None:
        result = start_task(self.project, "Проверить и упорядочить каталог компонентов", "small-bug")
        task_id = "review-and-organize-component-catalog"
        self.assertEqual(result["task_id"], task_id)
        restored = restore_task(self.project, task_id)
        self.assertEqual(restored["memory"]["session"]["id"], task_id)
        self.assertEqual(len(restored["memory"]["steps"]), 6)

    def test_unicode_orphan_package_has_preview_and_safe_recovery(self) -> None:
        source = self.project / "docs/specs/active/Проверить-компоненты"
        source.mkdir(parents=True)
        (source / "evidence").mkdir()
        (source / "evidence/README.md").write_text("# Evidence\n", encoding="utf-8")
        (source / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
        (source / "task.json").write_text(json.dumps({"schema_version": 1, "id": "Проверить-компоненты", "title": "Проверить и упорядочить каталог компонентов", "work_class": "small-bug", "status": "active", "tracker": {"provider": "none", "reference": None, "url": None}, "workflow": {"schema_version": 1, "spec_revision": 1, "plan_revision": 1}}), encoding="utf-8")
        preview = recover_unicode_package(self.project, source.name)
        self.assertTrue(source.exists())
        self.assertEqual(preview["task_id"], "review-and-organize-component-catalog")
        result = recover_unicode_package(self.project, source.name, apply=True)
        self.assertFalse(source.exists())
        self.assertTrue(Path(result["package"]).is_dir())
        self.assertEqual(restore_task(self.project, result["task_id"])["memory"]["session"]["id"], result["task_id"])

    def test_failed_start_leaves_no_published_package_or_task_memory(self) -> None:
        with mock.patch("ai_agent_fabric.entrypoints.activate_task_lifecycle", side_effect=RuntimeError("lifecycle failed")):
            with self.assertRaisesRegex(RuntimeError, "lifecycle failed"):
                start_task(self.project, "Will fail", "small-bug")
        self.assertFalse((self.project / "docs/specs/active/will-fail").exists())
        import sqlite3
        connection = sqlite3.connect(self.project / ".agent-fabric/memory.db")
        try:
            self.assertEqual(connection.execute("SELECT count(*) FROM sessions").fetchone()[0], 0)
        finally:
            connection.close()

    def test_restore_picker_lists_tasks_and_resolves_number_title_or_id(self) -> None:
        start_task(self.project, "First task", "small-bug", "first-task")
        start_task(self.project, "Second task", "small-bug", "second-task")

        picker = restore_picker(self.project)

        self.assertEqual([item["number"] for item in picker["tasks"]], [1, 2])
        self.assertEqual(restore_picker(self.project, "2")["task_id"], "second-task")
        self.assertEqual(restore_picker(self.project, "First task")["task_id"], "first-task")
        self.assertEqual(restore_picker(self.project, "second-task")["task_id"], "second-task")
        self.assertNotIn("socrates_handoff", picker)

    def test_codex_session_start_hook_is_read_only_and_returns_active_task_data(self) -> None:
        start_task(self.project, "Hook task", "small-bug", "hook-task")
        hook = SOURCE_ROOT / "hooks" / "codex_session_start.py"
        environment = os.environ.copy()
        environment["AI_AGENT_FABRIC_HOME"] = str(self.home)

        result = subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps({"cwd": str(self.project)}),
            capture_output=True,
            text=True,
            check=True,
            env=environment,
        )

        payload = json.loads(result.stdout)
        context = payload["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("hook-task", context)
        self.assertIn("Hook task", context)
        restored = restore_task(self.project, "hook-task")
        self.assertEqual([record["kind"] for record in restored["memory"]["records"]], ["task-started"])

    def test_guard_failure_is_durable_idempotent_and_distinct_from_harness_signals(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        evidence = self.project / "docs/specs/active/example-task/evidence"
        for name in ("test-1.md", "test-2.md", "test-3.md"):
            (evidence / name).write_text("# Guard evidence\n", encoding="utf-8")

        first = record_guard_failure(
            self.project,
            "example-task",
            "guard-failure-1",
            "command-incident",
            "command",
            "docs/specs/active/example-task/evidence/test-1.md",
            self.home,
        )
        duplicate = record_guard_failure(
            self.project,
            "example-task",
            "guard-failure-1",
            "command-incident",
            "command",
            "docs/specs/active/example-task/evidence/test-1.md",
            self.home,
        )
        second = record_guard_failure(
            self.project,
            "example-task",
            "guard-failure-2",
            "command-incident",
            "command",
            "docs/specs/active/example-task/evidence/test-2.md",
            self.home,
        )
        third = record_guard_failure(
            self.project,
            "example-task",
            "guard-failure-3",
            "command-incident",
            "command",
            "docs/specs/active/example-task/evidence/test-3.md",
            self.home,
        )

        self.assertTrue(first["created"])
        self.assertEqual(first["failure"]["outcome"], "retry")
        self.assertFalse(duplicate["created"])
        self.assertEqual(duplicate["failure"]["attempt"], 1)
        self.assertEqual(second["failure"]["attempt"], 2)
        self.assertEqual(second["failure"]["outcome"], "retry")
        self.assertEqual(third["failure"]["attempt"], 3)
        self.assertEqual(third["failure"]["outcome"], "escalate")

        separate_incident = record_guard_failure(
            self.project, "example-task", "guard-failure-new-incident", "new-incident", "command",
            "docs/specs/active/example-task/evidence/test-3.md", self.home,
        )
        self.assertEqual(separate_incident["failure"]["attempt"], 1)
        self.assertEqual(separate_incident["failure"]["outcome"], "retry")

        restored = restore_task(self.project, "example-task")
        self.assertEqual(len(restored["memory"]["guard_failures"]), 4)
        self.assertEqual(len(restored["memory"]["guard_outcomes"]), 4)

    def test_harness_signal_does_not_create_a_guard_failure(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        record_harness_signal(self.project, "user-correction", "example-task")

        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["guard_failures"], [])
        signals = self.project / ".agent-fabric/harness/signals.jsonl"
        self.assertTrue(signals.is_file())

    def test_block_policy_stops_at_the_first_failure(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        evidence = self.project / "docs/specs/active/example-task/evidence/scope.md"
        evidence.write_text("# Guard evidence\n", encoding="utf-8")
        result = record_guard_failure(
            self.project,
            "example-task",
            "guard-failure-block",
            "checkpoint-incident",
            "checkpoint",
            "docs/specs/active/example-task/evidence/scope.md",
            self.home,
        )
        self.assertEqual(result["failure"]["status"], "blocked")
        self.assertEqual(result["failure"]["outcome"], "block")

    def test_guards_command_records_trace_after_durable_failure(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        artifact = self.project / "docs/specs/active/example-task/evidence/guard.md"
        artifact.write_text("# Guard evidence\n", encoding="utf-8")
        output = io.StringIO()
        original_argv = sys.argv
        try:
            sys.argv = [
                "ai-agent-fabric", "guards", "failure", str(self.project),
                "--session", "example-task",
                "--idempotency-key", "guard-cli-failure-1",
                "--incident-id", "guard-cli-incident",
                "--guard", "checkpoint",
                "--artifact", "docs/specs/active/example-task/evidence/guard.md",
                "--home", str(self.home),
                "--json",
            ]
            with redirect_stdout(output):
                main()
        finally:
            sys.argv = original_argv

        result = json.loads(output.getvalue())
        self.assertEqual(result["failure"]["outcome"], "block")
        trace = self.project / ".agent-fabric/harness/trace.jsonl"
        self.assertTrue(trace.is_file())
        self.assertEqual(json.loads(trace.read_text(encoding="utf-8").strip())["kind"], "guard-failure")

    def test_guard_rejects_missing_evidence_artifact(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        with self.assertRaisesRegex(ValueError, "evidence artifact"):
            record_guard_failure(
                self.project,
                "example-task",
                "missing-evidence",
                "missing-incident",
                "command",
                "docs/specs/active/example-task/evidence/missing.md",
                self.home,
            )

    def test_restore_recovers_a_pending_guard_trace_once(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        artifact = self.project / "docs/specs/active/example-task/evidence/trace.md"
        artifact.write_text("# Guard evidence\n", encoding="utf-8")
        record_guard_failure(
            self.project,
            "example-task",
            "pending-trace-1",
            "trace-incident",
            "checkpoint",
            "docs/specs/active/example-task/evidence/trace.md",
            self.home,
        )
        trace = self.project / ".agent-fabric/harness/trace.jsonl"
        self.assertFalse(trace.exists())

        restore_task(self.project, "example-task")
        self.assertFalse(trace.exists(), "Root restore must not run Socrates recovery work")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        flush_guard_traces(self.project)

        events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([event["idempotency_key"] for event in events], ["pending-trace-1"])

    def test_failed_checkpoint_records_the_declared_checkpoint_guard(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        artifact = self.project / "docs/specs/active/example-task/evidence/checkpoint.md"
        artifact.write_text("# Failed checkpoint evidence\n", encoding="utf-8")
        output = io.StringIO()
        original_argv = sys.argv
        try:
            sys.argv = [
                "ai-agent-fabric", "harness", "checkpoint", str(self.project),
                "--gate", "intake",
                "--evidence", "[]",
                "--session", "example-task",
                "--failure-id", "checkpoint-failure-1",
                "--failure-artifact", "docs/specs/active/example-task/evidence/checkpoint.md",
                "--home", str(self.home),
                "--json",
            ]
            with redirect_stdout(output):
                main()
        finally:
            sys.argv = original_argv

        result = json.loads(output.getvalue())
        self.assertEqual(result["checkpoint"]["status"], "failed")
        self.assertEqual(result["failure"]["guard"], "checkpoint")
        self.assertEqual(result["failure"]["outcome"], "block")

    def test_runtime_checkpoint_api_records_only_gate_validation_failures(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        artifact = self.project / "docs/specs/active/example-task/evidence/checkpoint-api.md"
        artifact.write_text("# Failed checkpoint evidence\n", encoding="utf-8")

        result = record_checkpoint(
            self.project, "intake", [], self.home,
            session_id="example-task", failure_id="checkpoint-api-failure", failure_artifact="docs/specs/active/example-task/evidence/checkpoint-api.md",
        )

        self.assertEqual(result["checkpoint"]["status"], "failed")
        self.assertEqual(result["failure"]["guard"], "checkpoint")

    def test_socrates_transition_restores_completed_checklist_without_restart(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        evidence = self.project / "docs/specs/active/example-task/evidence/intake.md"
        evidence.write_text("# Intake complete\n", encoding="utf-8")
        transition_step(self.project, "example-task", "intake", "in-progress")
        transition_step(
            self.project, "example-task", "intake", "done",
            "docs/specs/active/example-task/evidence/intake.md", "intake-evidence-complete",
        )

        restored = restore_task(self.project, "example-task")

        self.assertEqual(restored["memory"]["lifecycle"]["next_action"], "evidence")
        self.assertEqual(
            restored["memory"]["steps"][0],
            {"step_id": "intake", "status": "done", "closure_artifact": "docs/specs/active/example-task/evidence/intake.md", "closure_reason": "intake-evidence-complete"},
        )
        with self.assertRaisesRegex(ValueError, "immutable"):
            transition_step(self.project, "example-task", "intake", "in-progress")

    def test_socrates_rejects_closing_a_step_without_evidence_and_reason(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        with self.assertRaisesRegex(ValueError, "evidence artifact and reason"):
            transition_step(self.project, "example-task", "intake", "done")

    def test_restore_rejects_missing_memory_instead_of_recreating_steps(self) -> None:
        package = self.project / "docs/specs/active/example-task"
        package.mkdir(parents=True)
        (package / "task.json").write_text(
            json.dumps({"id": "example-task", "title": "Example task", "work_class": "small-bug"}), encoding="utf-8"
        )
        memory_db = self.project / ".agent-fabric/memory.db"
        memory_db.unlink()
        with self.assertRaisesRegex(FileNotFoundError, "memory is missing"):
            restore_task(self.project, "example-task")
