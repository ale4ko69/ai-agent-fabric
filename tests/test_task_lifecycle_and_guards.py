from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from ai_agent_fabric.__main__ import main
from ai_agent_fabric.distribution import install_release, onboard_project
from ai_agent_fabric.entrypoints import archive_completed_task, recover_unicode_package, restore_picker, restore_task, start_preview, start_task, work_router
from ai_agent_fabric.harness import flush_guard_traces, record_checkpoint
from ai_agent_fabric.memory import acknowledge_result, attest_new_product_mvp_approval, claim_socrates_chat, initialize, mark_request_dispatched, record, submit_request, submit_result
from ai_agent_fabric.socrates import record_guard_failure, record_harness_signal, resolve_guard, transition_step
from ai_agent_fabric.task_specs import create_task, implementation_readiness, new_product_mvp_preview, validate_task, workflow_steps


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

    def test_new_product_preview_is_read_only_and_rejects_small_bug(self) -> None:
        before = (self.project / ".agent-fabric/memory.db").read_bytes()
        preview = start_preview(self.project, "New product", "planned", new_product=True)

        self.assertEqual(preview["mode"], "new-product")
        self.assertEqual(preview["work_class"], "planned")
        self.assertEqual(Path(preview["package"]), self.project / "docs/specs/active/new-product")
        self.assertFalse(Path(preview["package"]).exists())
        for operation in (start_preview, start_task, create_task):
            with self.assertRaisesRegex(ValueError, "requires planned"):
                operation(self.project, "New product", "small-bug", new_product=True)
        self.assertEqual((self.project / ".agent-fabric/memory.db").read_bytes(), before)
        self.assertFalse((self.project / "docs").exists())

    def test_new_product_uses_ordinary_planned_package_lifecycle_and_claim(self) -> None:
        ordinary = start_task(self.project, "Ordinary feature", "planned")
        result = start_task(self.project, "New product", "planned", new_product=True)
        package = Path(result["package"])
        ordinary_package = Path(ordinary["package"])
        request = result["socrates_chat_request"]

        self.assertEqual(
            {path.relative_to(package) for path in package.rglob("*")},
            {path.relative_to(ordinary_package) for path in ordinary_package.rglob("*")},
        )
        self.assertEqual(validate_task(self.project, result["task_id"]), [])
        self.assertEqual(
            set(json.loads((package / "task.json").read_text(encoding="utf-8"))),
            set(json.loads((ordinary_package / "task.json").read_text(encoding="utf-8"))),
        )
        self.assertEqual(result["mode"], "new-product")
        self.assertEqual(request["skill"], "agent-fabric-new-product")
        self.assertEqual(request["session_state"], "docs/specs/active/new-product/session-state.md")
        self.assertIn("first user", request["next_open_question"])
        restored = restore_task(self.project, result["task_id"])
        self.assertEqual(restored["socrates_chat_request"], request)
        self.assertEqual(restored["memory"]["session"]["status"], "awaiting-socrates-chat")
        self.assertEqual([step["step_id"] for step in restored["memory"]["steps"]], workflow_steps("planned"))
        with self.assertRaisesRegex(PermissionError, "claimed separate Socrates chat"):
            transition_step(self.project, result["task_id"], "intake", "in-progress")
        claimed = claim_socrates_chat(self.project, result["task_id"], "socrates-new-product")
        self.assertEqual(claimed["next_action"], "intake")
        with self.assertRaisesRegex(ValueError, "different Socrates chat"):
            claim_socrates_chat(self.project, result["task_id"], "another-thread")
        self.assertFalse(implementation_readiness(self.project, result["task_id"])["ready"])

        ordinary_restore = restore_task(self.project, ordinary["task_id"])
        self.assertEqual(set(ordinary), {"package", "task_id", "socrates_chat_request"})
        self.assertNotIn("mode", ordinary_restore)
        self.assertEqual(
            set(ordinary_restore["socrates_chat_request"]),
            {"owner", "task_id", "title", "action", "chat_title", "root_limit", "socrates_activation"},
        )
        self.assertNotIn("mode", start_preview(self.project, "Another ordinary feature", "planned"))
        self.assertEqual(
            (ordinary_package / "session-state.md").read_text(encoding="utf-8"),
            "# Session state\n\nStatus: PENDING\n\n## Progress\n\n- [ ] Task not started\n",
        )

    def test_new_product_restore_preserves_question_decisions_and_completed_intake(self) -> None:
        result = start_task(self.project, "New product", "planned", new_product=True)
        package = Path(result["package"])
        task_id = result["task_id"]
        claim_socrates_chat(self.project, task_id, "socrates-new-product")
        evidence = package / "evidence/intake.md"
        evidence.write_text("# Intake complete\n", encoding="utf-8")
        transition_step(
            self.project, task_id, "intake", "done",
            "docs/specs/active/new-product/evidence/intake.md", "intake-complete",
        )
        research = {
            "idempotency_key": "product-research",
            "session_id": task_id,
            "task_id": task_id,
            "agent": "explore",
            "scope_artifact": "docs/specs/active/new-product/spec.md",
            "input_artifacts": ["docs/specs/active/new-product/research.md"],
            "required_outputs": ["docs/specs/active/new-product/research.md"],
        }
        submit_request(self.project, research)
        mark_request_dispatched(self.project, research["idempotency_key"])
        submit_result(self.project, {
            "idempotency_key": "product-research-result",
            "request_id": research["idempotency_key"],
            "session_id": task_id,
            "agent": "explore",
            "summary": "product-research-complete",
            "artifacts": [{"path": "docs/specs/active/new-product/research.md"}],
            "findings": [],
            "decisions": [],
        })
        state = package / "session-state.md"
        question = "Which offline workflow should the MVP support?\nWhat observable result counts as success?"
        state.write_text(
            "# Session state\n\nMode: new-product\n\n## Progress\n\nIntake complete; discovery in progress.\n\n"
            f"## Next open question\n\n{question}\n\n"
            "## Discovery decisions\n\nPaper walkthrough chosen; research deferred.\n\n"
            "## MVP owner decision\n\nPending owner scope-and-acceptance approval.\n",
            encoding="utf-8",
        )
        before_files = {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}

        restored = restore_task(self.project, task_id)
        again = restore_task(self.project, task_id)

        self.assertEqual(restored, again)
        self.assertEqual(restored["socrates_chat_request"]["next_open_question"], question)
        self.assertEqual(restored["memory"]["socrates_chat"]["thread_id"], "socrates-new-product")
        self.assertEqual(restored["memory"]["lifecycle"]["next_action"], "discovery")
        self.assertEqual(restored["memory"]["steps"][0]["status"], "done")
        self.assertEqual(restored["pending_requests"], [])
        self.assertEqual([item["idempotency_key"] for item in restored["pending_results"]], ["product-research-result"])
        self.assertEqual(
            {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob("*") if path.is_file()},
            before_files,
        )
        with self.assertRaisesRegex(ValueError, "only the orchestrator"):
            acknowledge_result(self.project, "product-research-result", actor="explore")
        self.assertTrue(acknowledge_result(self.project, "product-research-result"))
        self.assertFalse(acknowledge_result(self.project, "product-research-result"))
        self.assertEqual(restore_task(self.project, task_id)["pending_results"], [])
        self.assertFalse(implementation_readiness(self.project, task_id)["ready"])

    def test_new_product_restore_respects_custom_task_root_and_empty_question(self) -> None:
        profile_path = self.project / ".agent-fabric/profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["task_specs"]["root"] = "design/tasks"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        result = start_task(self.project, "New product", "planned", new_product=True)
        state = Path(result["package"]) / "session-state.md"
        state.write_text(
            "# Session state\n\nMode: new-product\n\n## Next open question\n\n"
            "## MVP owner decision\n\nApproved exact scope and acceptance; source: owner-chat-1.\n",
            encoding="utf-8",
        )

        restored = restore_task(self.project, result["task_id"])

        self.assertEqual(restored["socrates_chat_request"]["session_state"], "design/tasks/active/new-product/session-state.md")
        self.assertEqual(restored["socrates_chat_request"]["next_open_question"], "")
        self.assertFalse((self.project / "docs/specs").exists())
        self.assertFalse(implementation_readiness(self.project, result["task_id"])["ready"])

    def test_new_product_restore_rejects_ambiguous_saved_question_without_writes(self) -> None:
        result = start_task(self.project, "New product", "planned", new_product=True)
        state = Path(result["package"]) / "session-state.md"
        for content in (
            "# Session state\n\nMode: new-product\n",
            "# Session state\n\nMode: new-product\n\n## Next open question\n\nFirst?\n\n## Next open question\n\nSecond?\n",
        ):
            state.write_text(content, encoding="utf-8")
            before = (self.project / ".agent-fabric/memory.db").read_bytes()
            with self.assertRaisesRegex(ValueError, "one Next open question"):
                restore_task(self.project, result["task_id"])
            self.assertEqual(state.read_text(encoding="utf-8"), content)
            self.assertEqual((self.project / ".agent-fabric/memory.db").read_bytes(), before)

    def test_new_product_cli_keeps_both_previews_separate_from_apply(self) -> None:
        project = self.project.parent / "empty-product"
        project.mkdir()
        init_arguments = [
            "ai-agent-fabric", "project", "init", str(project), "--client", "codex",
            "--home", str(self.home), "--require-empty",
        ]
        output = io.StringIO()
        with mock.patch.object(sys, "argv", init_arguments + ["--preview"]), redirect_stdout(output):
            main()
        self.assertIn(str(project / ".agent-fabric/profile.json"), output.getvalue())
        self.assertEqual(list(project.iterdir()), [])
        with mock.patch.object(sys, "argv", init_arguments), redirect_stdout(io.StringIO()):
            main()
        start_arguments = [
            "ai-agent-fabric", "start", str(project), "--title", "New product", "--type", "planned",
            "--new-product", "--home", str(self.home), "--json",
        ]
        output = io.StringIO()
        with mock.patch.object(sys, "argv", start_arguments), redirect_stdout(output):
            main()
        self.assertEqual(json.loads(output.getvalue())["mode"], "new-product")
        self.assertFalse((project / "docs").exists())
        output = io.StringIO()
        with mock.patch.object(sys, "argv", start_arguments + ["--apply"]), redirect_stdout(output):
            main()
        applied = json.loads(output.getvalue())
        self.assertEqual(applied["created"]["socrates_chat_request"]["mode"], "new-product")
        self.assertEqual(restore_task(project, applied["task_id"])["memory"]["session"]["status"], "awaiting-socrates-chat")

    def _new_product_discovery(self, task_id: str = "new-product") -> tuple[Path, dict[str, object], str]:
        """Подготовить только fixture discovery; решение в memory намеренно ещё отсутствует."""
        result = start_task(self.project, "New product", "planned", task_id, new_product=True)
        package = Path(result["package"])
        claim_socrates_chat(self.project, task_id, f"socrates-{task_id}")
        (package / "spec.md").write_text(
            "# MVP\n\n## Scope\n\nOne offline checklist for one user.\n\n"
            "## Non-Goals\n\nNo synchronization.\n\n## Acceptance Criteria\n\nA saved checklist opens offline.\n",
            encoding="utf-8",
        )
        intake = package / "evidence/intake.md"
        intake.write_text("# Intake complete\n", encoding="utf-8")
        transition_step(
            self.project, task_id, "intake", "done",
            str(intake.relative_to(self.project)).replace("\\", "/"), "intake-complete",
        )
        decision = package / "evidence/mvp-owner-decision.md"
        decision.write_text("# Owner decision\n\nOwner approves the exact MVP scope and acceptance criteria; source owner-chat-1.\n", encoding="utf-8")
        return package, new_product_mvp_preview(self.project, task_id), str(decision.relative_to(self.project)).replace("\\", "/")

    def test_new_product_mvp_gate_rejects_prose_closure_skip_and_planning_request(self) -> None:
        package, preview, decision = self._new_product_discovery()
        source = self.project.parent / "historical-product-notes.md"
        source.write_text(
            "# Earlier MVP decision\n\nMVP approved for the earlier offline checklist proposal.\n",
            encoding="utf-8",
        )
        research = package / "research.md"
        research.write_text(
            research.read_text(encoding="utf-8")
            + "\n## Existing materials review\n\n"
            "historical-product-notes.md, Earlier MVP decision: says MVP approved historically, "
            "not a current owner decision on this scope and acceptance criteria.\n"
            "Next question: which earlier decisions still apply?\n",
            encoding="utf-8",
        )
        state = package / "session-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Pending.", "Approved by owner."), encoding="utf-8")
        before = (self.project / ".agent-fabric/memory.db").read_bytes()
        for status in ("done", "skipped"):
            with self.assertRaisesRegex(PermissionError, "current MVP owner approval"):
                transition_step(self.project, "new-product", "discovery", status, decision, "discovery-complete")
        with self.assertRaisesRegex(PermissionError, "current MVP owner approval"):
            transition_step(self.project, "new-product", "plan", "in-progress")
        with self.assertRaisesRegex(PermissionError, "current MVP owner approval"):
            submit_request(self.project, {
                "idempotency_key": "unapproved-plan",
                "session_id": "new-product",
                "task_id": "new-product",
                "agent": "plan",
                "scope_artifact": preview["scope_artifact"],
                "input_artifacts": [preview["scope_artifact"]],
                "required_outputs": ["plan.md"],
            })
        restored = restore_task(self.project, "new-product")
        self.assertFalse(any(item["kind"] == "new-product-mvp-approved" for item in restored["memory"]["records"]))
        self.assertEqual(restored["memory"]["lifecycle"]["next_action"], "discovery")
        self.assertEqual(restored["memory"]["steps"][1]["status"], "in-progress")
        self.assertEqual(restored["memory"]["steps"][2]["status"], "pending")
        self.assertEqual(restored["pending_requests"], [])
        self.assertEqual((self.project / ".agent-fabric/memory.db").read_bytes(), before)

    def test_new_product_mvp_approval_survives_restore_and_unlocks_only_planning(self) -> None:
        package, preview, decision = self._new_product_discovery()
        before = (self.project / ".agent-fabric/memory.db").read_bytes()
        self.assertEqual(new_product_mvp_preview(self.project, "new-product"), preview)
        self.assertEqual((self.project / ".agent-fabric/memory.db").read_bytes(), before)

        approved = attest_new_product_mvp_approval(
            self.project, "new-product", preview["spec_sha256"], preview["spec_revision"], "owner-chat-1", decision,
        )
        restored = restore_task(self.project, "new-product")
        approval_records = [item for item in restored["memory"]["records"] if item["kind"] == "new-product-mvp-approved"]
        self.assertEqual(approval_records[0]["evidence"], approved)
        self.assertEqual(approved["spec_sha256"], preview["spec_sha256"])
        self.assertEqual(approved["spec_revision"], preview["spec_revision"])
        self.assertEqual(approved["task_id"], "new-product")
        self.assertEqual(approved["approval_method"], "agent-attested-chat")
        self.assertEqual(restored["memory"]["lifecycle"]["next_action"], "discovery")
        result = transition_step(self.project, "new-product", "discovery", "done", decision, "mvp-approved")
        self.assertEqual(result["next_action"], "plan")
        self.assertEqual(restore_task(self.project, "new-product")["memory"]["steps"][2]["status"], "in-progress")
        self.assertFalse(implementation_readiness(self.project, "new-product")["ready"])
        self.assertFalse(json.loads((package / "approval.json").read_text(encoding="utf-8"))["approved"])

    def test_new_product_mvp_gate_rechecks_spec_revision_content_and_decision_evidence(self) -> None:
        for change in ("content", "revision", "decision"):
            with self.subTest(change=change):
                task_id = f"product-{change}"
                package, preview, decision = self._new_product_discovery(task_id)
                attest_new_product_mvp_approval(
                    self.project, task_id, preview["spec_sha256"], preview["spec_revision"], "owner-chat-1", decision,
                )
                request = {
                    "idempotency_key": f"{task_id}-plan",
                    "session_id": task_id,
                    "task_id": task_id,
                    "agent": "plan",
                    "scope_artifact": preview["scope_artifact"],
                    "input_artifacts": [preview["scope_artifact"]],
                    "required_outputs": ["plan.md"],
                }
                submit_request(self.project, request)
                if change == "content":
                    spec = package / "spec.md"
                    spec.write_text(spec.read_text(encoding="utf-8") + "\nAdded a second user workflow.\n", encoding="utf-8")
                elif change == "revision":
                    metadata_path = package / "task.json"
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    metadata["workflow"]["spec_revision"] += 1
                    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                else:
                    (self.project / decision).write_text("# Changed decision evidence\n", encoding="utf-8")
                with self.assertRaisesRegex(PermissionError, "current MVP owner approval"):
                    transition_step(self.project, task_id, "discovery", "done", decision, "mvp-approved")
                with self.assertRaisesRegex(PermissionError, "current MVP owner approval"):
                    mark_request_dispatched(self.project, request["idempotency_key"])
                with self.assertRaisesRegex(PermissionError, "current MVP owner approval"):
                    submit_request(self.project, {**request, "idempotency_key": f"{task_id}-new-plan"})
                fresh = new_product_mvp_preview(self.project, task_id)
                attest_new_product_mvp_approval(
                    self.project, task_id, fresh["spec_sha256"], fresh["spec_revision"], "owner-chat-2", decision,
                )
                self.assertEqual(transition_step(self.project, task_id, "discovery", "done", decision, "mvp-reapproved")["next_action"], "plan")
                self.assertTrue(mark_request_dispatched(self.project, request["idempotency_key"]))
                approvals = [item for item in restore_task(self.project, task_id)["memory"]["records"] if item["kind"] == "new-product-mvp-approved"]
                self.assertEqual(len(approvals), 2)

    def test_new_product_mvp_attestation_requires_claim_current_preview_and_local_evidence(self) -> None:
        result = start_task(self.project, "New product", "planned", new_product=True)
        package = Path(result["package"])
        preview = new_product_mvp_preview(self.project, "new-product")
        decision_path = package / "evidence/mvp.md"
        decision_path.write_text("# Explicit owner decision\n", encoding="utf-8")
        decision = str(decision_path.relative_to(self.project)).replace("\\", "/")
        arguments = (self.project, "new-product", preview["spec_sha256"], preview["spec_revision"], "owner-chat-1", decision)
        with self.assertRaisesRegex(PermissionError, "claimed separate Socrates chat"):
            attest_new_product_mvp_approval(*arguments)
        with self.assertRaisesRegex(ValueError, "only the orchestrator"):
            attest_new_product_mvp_approval(*arguments, actor="explore")
        claim_socrates_chat(self.project, "new-product", "socrates-new-product")
        with self.assertRaisesRegex(ValueError, "changed after preview"):
            attest_new_product_mvp_approval(
                self.project, "new-product", preview["spec_sha256"], preview["spec_revision"] + 1, "owner-chat-1", decision,
            )
        spec = package / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\nChanged scope.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after preview"):
            attest_new_product_mvp_approval(*arguments)
        fresh = new_product_mvp_preview(self.project, "new-product")
        (self.project / "foreign.md").write_text("# Not task-local evidence\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside this task"):
            attest_new_product_mvp_approval(
                self.project, "new-product", fresh["spec_sha256"], fresh["spec_revision"], "owner-chat-1", "foreign.md",
            )
        with self.assertRaises((OSError, ValueError)):
            attest_new_product_mvp_approval(
                self.project, "new-product", fresh["spec_sha256"], fresh["spec_revision"], "owner-chat-1",
                "docs/specs/active/new-product/evidence/missing.md",
            )
        with self.assertRaisesRegex(ValueError, "claimed Socrates attestation"):
            record(self.project, "new-product", "new-product-mvp-approved", "orchestrator", "prose-approval", {})
        self.assertFalse(any(item["kind"] == "new-product-mvp-approved" for item in restore_task(self.project, "new-product")["memory"]["records"]))

    def test_new_product_task_start_audit_prevents_removing_mode_to_bypass_mvp_gate(self) -> None:
        package, preview, decision = self._new_product_discovery()
        state = package / "session-state.md"
        state.write_text(state.read_text(encoding="utf-8").replace("Mode: new-product\n", ""), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "saved New Product mode"):
            transition_step(self.project, "new-product", "discovery", "done", decision, "remove-marker")

    def test_new_product_mvp_cli_preview_and_attestation_keep_steps_separate(self) -> None:
        package, preview, decision = self._new_product_discovery()
        arguments = [
            "ai-agent-fabric", "socrates", "approve-mvp", str(self.project),
            "--session", "new-product", "--home", str(self.home), "--json",
        ]
        before = (self.project / ".agent-fabric/memory.db").read_bytes()
        output = io.StringIO()
        with mock.patch.object(sys, "argv", arguments + ["--preview"]), redirect_stdout(output):
            main()
        self.assertEqual(json.loads(output.getvalue()), preview)
        self.assertEqual((self.project / ".agent-fabric/memory.db").read_bytes(), before)
        output = io.StringIO()
        with mock.patch.object(sys, "argv", arguments + [
            "--reviewed-spec-sha256", preview["spec_sha256"],
            "--reviewed-spec-revision", str(preview["spec_revision"]),
            "--chat-reference", "owner-chat-1", "--artifact", decision,
        ]), redirect_stdout(output):
            main()
        self.assertTrue(json.loads(output.getvalue())["approved"])
        self.assertEqual(restore_task(self.project, "new-product")["memory"]["lifecycle"]["next_action"], "discovery")

    def test_new_product_v1_rejects_other_client_bindings_without_changing_normal_plumbing(self) -> None:
        for client in ("copilot", "claude"):
            with self.subTest(client=client):
                project = self.project.parent / f"project-{client}"
                project.mkdir()
                onboard_project(project, client, self.home, "test")
                before = (project / ".agent-fabric/memory.db").read_bytes()
                arguments = [
                    "ai-agent-fabric", "start", str(project), "--title", "New product", "--type", "planned",
                    "--new-product", "--home", str(self.home), "--json",
                ]
                for extra in ([], ["--apply"]):
                    with mock.patch.object(sys, "argv", arguments + extra), redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(ValueError, "Codex plugin surface"):
                            main()
                with self.assertRaisesRegex(ValueError, "Codex plugin surface"):
                    create_task(project, "New product", "planned", new_product=True)
                self.assertFalse((project / "docs").exists())
                self.assertEqual((project / ".agent-fabric/memory.db").read_bytes(), before)
                ordinary = start_task(project, "Ordinary feature", "planned")
                self.assertNotIn("mode", ordinary)
                claim_socrates_chat(project, ordinary["task_id"], f"socrates-{client}")
                package = Path(ordinary["package"])
                for step in ("intake", "discovery"):
                    evidence = package / "evidence" / f"{step}.md"
                    evidence.write_text(f"# Ordinary {step}\n", encoding="utf-8")
                    result = transition_step(
                        project, ordinary["task_id"], step, "done",
                        str(evidence.relative_to(project)).replace("\\", "/"), f"{step}-complete",
                    )
                self.assertEqual(result["next_action"], "plan")

    def test_start_requires_a_separate_socrates_chat_claim(self) -> None:
        result = start_task(self.project, "Example task", "small-bug", "example-task")

        request = result["socrates_chat_request"]
        self.assertEqual(request["owner"], "root")
        self.assertEqual(request["action"], "create-separate-socrates-chat")
        self.assertNotIn("socrates_handoff", result)
        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["socrates_chat_request"], request)
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
        self.assertEqual(len(restored["memory"]["steps"]), 7)

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
        self.assertIn("Restore an existing task only when it matches the user's current request", context)
        self.assertIn("an unrelated active task must not prevent new authorized work", context)
        self.assertIn("If the request is ambiguous, ask which task to continue", context)
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
        self.assertEqual(result["next_action"], "guard-blocked")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["continuation"],
            {"kind": "blocked", "reason": "guard-blocked", "recommended_action": "resolve-guard-blocker"},
        )

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

    def test_diagnose_reports_observed_state_without_advancing_it(self) -> None:
        from ai_agent_fabric.socrates import diagnose
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        before = restore_task(self.project, "example-task")["memory"]["steps"]
        report = diagnose(self.project, "example-task")
        after = restore_task(self.project, "example-task")["memory"]["steps"]
        self.assertEqual(report["reason"], "workflow-running")
        self.assertEqual(report["recommended_action"], "continue-current-step")
        self.assertEqual(report["observed"]["next_action"], "intake")
        self.assertEqual(before, after)

    def test_internal_closure_atomically_resumes_the_next_step(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        evidence = self.project / "docs/specs/active/example-task/evidence/intake.md"
        evidence.write_text("# Intake complete\n", encoding="utf-8")

        result = transition_step(
            self.project, "example-task", "intake", "done",
            "docs/specs/active/example-task/evidence/intake.md", "intake-evidence-complete",
        )

        self.assertEqual(result["next_action"], "evidence")
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["continuation"], {"kind": "resume", "step_id": "evidence"})
        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["steps"][1]["status"], "in-progress")

    def test_kepler_closure_waits_for_owner_with_actionable_reason(self) -> None:
        start_task(self.project, "Example task", "planned", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        evidence_root = self.project / "docs/specs/active/example-task/evidence"
        for step in ("intake", "discovery", "plan", "kepler"):
            artifact = evidence_root / f"{step}.md"
            artifact.write_text(f"# {step}\n", encoding="utf-8")
            result = transition_step(
                self.project, "example-task", step, "done",
                f"docs/specs/active/example-task/evidence/{step}.md", f"{step}-complete",
            )

        self.assertEqual(result["next_action"], "owner-approval")
        self.assertEqual(result["status"], "awaiting-owner-approval")
        self.assertEqual(
            result["continuation"],
            {
                "kind": "await-owner-approval",
                "reason": "owner-approval-required",
                "recommended_action": "approve-reviewed-package",
            },
        )
        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["steps"][4]["status"], "in-progress")
        self.assertEqual(restored["memory"]["lifecycle"]["continuation"], result["continuation"])

    def test_final_closure_is_actionable_completion(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        evidence_root = self.project / "docs/specs/active/example-task/evidence"
        for step in ("intake", "evidence", "implementation", "review", "validation", "close-out"):
            artifact = evidence_root / f"{step}.md"
            artifact.write_text(f"# {step}\n", encoding="utf-8")
            result = transition_step(
                self.project, "example-task", step, "done",
                f"docs/specs/active/example-task/evidence/{step}.md", f"{step}-complete",
            )

        self.assertEqual(result["next_action"], "rollout")
        self.assertEqual(result["continuation"], {"kind": "resume", "step_id": "rollout"})
        artifact = evidence_root / "rollout.md"
        artifact.write_text("# rollout\n", encoding="utf-8")
        result = transition_step(
            self.project, "example-task", "rollout", "done",
            "docs/specs/active/example-task/evidence/rollout.md", "rollout-complete",
        )

        self.assertEqual(result["next_action"], "archive")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            result["continuation"],
            {"kind": "completed", "reason": "workflow-complete", "recommended_action": "archive-task"},
        )

    def test_owner_direction_resolves_an_escalated_guard_without_rewriting_history(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        evidence_root = self.project / "docs/specs/active/example-task/evidence"
        failure_keys = []
        for attempt in range(1, 4):
            artifact = evidence_root / f"command-{attempt}.md"
            artifact.write_text(f"# command attempt {attempt}\n", encoding="utf-8")
            failure_key = f"command-failure-{attempt}"
            failure_keys.append(failure_key)
            result = record_guard_failure(
                self.project, "example-task", failure_key, "command-incident", "command",
                f"docs/specs/active/example-task/evidence/command-{attempt}.md", self.home,
            )
        self.assertEqual(result["status"], "escalated")
        resolution = evidence_root / "command-resolved.md"
        resolution.write_text("# Cause resolved\n", encoding="utf-8")

        resumed = resolve_guard(
            self.project, "example-task", failure_keys[-1],
            "docs/specs/active/example-task/evidence/command-resolved.md",
            "continue-after-repaired-command",
        )

        self.assertTrue(resumed["created"])
        self.assertEqual(resumed["status"], "active")
        self.assertEqual(resumed["next_action"], "intake")
        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["guard_failures"][-1]["status"], "escalated")
        self.assertEqual(restored["memory"]["guard_resolutions"][0]["failure_key"], failure_keys[-1])
        self.assertEqual(restored["memory"]["lifecycle"]["continuation"], {"kind": "resume", "step_id": "intake"})

    def test_archive_completed_task_unblocks_new_task_routing(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        evidence_root = self.project / "docs/specs/active/example-task/evidence"
        for step in ("intake", "evidence", "implementation", "review", "validation", "close-out", "rollout"):
            artifact = evidence_root / f"{step}.md"
            artifact.write_text(f"# {step}\n", encoding="utf-8")
            transition_step(
                self.project, "example-task", step, "done",
                f"docs/specs/active/example-task/evidence/{step}.md", f"{step}-complete",
            )

        archived = archive_completed_task(self.project, "example-task", "delivery-complete")

        self.assertEqual(archived["status"], "archived")
        self.assertFalse((self.project / "docs/specs/active/example-task").exists())
        self.assertTrue((self.project / "docs/specs/archived/example-task").is_dir())
        self.assertEqual(work_router(self.project)["route"], "start")
        restored = initialize(self.project)
        self.assertEqual(restored, self.project / ".agent-fabric/memory.db")

    def test_archive_rejects_an_incomplete_task_without_moving_its_package(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        with self.assertRaisesRegex(PermissionError, "claimed separate Socrates chat"):
            archive_completed_task(self.project, "example-task", "not-complete")
        self.assertTrue((self.project / "docs/specs/active/example-task").is_dir())
        self.assertFalse((self.project / "docs/specs/archived/example-task").exists())

    def test_schema_migration_resumes_a_legacy_pending_internal_step(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        connection = sqlite3.connect(self.project / ".agent-fabric/memory.db")
        try:
            connection.execute("ALTER TABLE task_lifecycles RENAME TO task_lifecycles_current")
            connection.execute(
                "CREATE TABLE task_lifecycles (session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE, "
                "task_package TEXT NOT NULL, next_action TEXT NOT NULL, "
                "status TEXT NOT NULL CHECK(status IN ('active', 'blocked', 'escalated')), "
                "started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, resumed_at TEXT)"
            )
            connection.execute(
                "INSERT INTO task_lifecycles(session_id, task_package, next_action, status, started_at, resumed_at) "
                "SELECT session_id, task_package, 'evidence', 'active', started_at, resumed_at FROM task_lifecycles_current"
            )
            connection.execute("DROP TABLE task_lifecycles_current")
            connection.execute("UPDATE task_steps SET status='done' WHERE session_id='example-task' AND step_id='intake'")
            connection.execute("UPDATE task_steps SET status='pending' WHERE session_id='example-task' AND step_id='evidence'")
            connection.execute("PRAGMA user_version=10")
            connection.commit()
        finally:
            connection.close()

        initialize(self.project)

        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["lifecycle"]["next_action"], "evidence")
        self.assertEqual(restored["memory"]["lifecycle"]["status"], "active")
        self.assertEqual(restored["memory"]["steps"][1]["status"], "in-progress")

    def test_schema_migration_adds_rollout_to_active_legacy_task(self) -> None:
        start_task(self.project, "Example task", "small-bug", "example-task")
        claim_socrates_chat(self.project, "example-task", "socrates-example-task")
        connection = sqlite3.connect(self.project / ".agent-fabric/memory.db")
        try:
            connection.execute("DELETE FROM task_steps WHERE session_id='example-task' AND step_id='rollout'")
            connection.execute("PRAGMA user_version=11")
            connection.commit()
        finally:
            connection.close()

        initialize(self.project)

        restored = restore_task(self.project, "example-task")
        self.assertEqual(restored["memory"]["steps"][-1]["step_id"], "rollout")
        self.assertEqual(restored["memory"]["steps"][-1]["status"], "pending")
        connection = sqlite3.connect(self.project / ".agent-fabric/memory.db")
        try:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 13)
            self.assertIsNotNone(connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='guard_resolutions'").fetchone())
        finally:
            connection.close()

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
