from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .clients import detect_client
from .capabilities import load_capabilities, unmet_requirements
from .bootstrap import bash_install_plan, install_bash
from .installer import load_project_profile, resolve_project_command
from .environment import detect_environment
from .memory import acknowledge_result, initialize, mark_request_dispatched, pending_requests, pending_results, quarantined_results, record, restore as restore_memory, start_session, submit_request, submit_result
from .task_specs import approve_planned_task, approval_preview, archive_task, create_task, implementation_readiness, validate_task
from .harness import close_retrospective, flush_guard_traces, health_report, record_checkpoint, resume_snapshot, retrospective_input
from .entrypoints import restore_picker, restore_task, start_preview, start_task, work_router
from .distribution import adapter_manifest, bind_project, binding_preview, client_enable_preview, client_rollback_preview, client_uninstall_preview, codex_skill_enable_preview, default_fabric_home, disable_codex_skills, enable_client, enable_codex_skills, enter_secret, install_release, onboard_project, project_context, project_onboarding_preview, project_rollback_preview, project_status, project_update_preview, release_preview, repair_project_update, repair_project_update_preview, require_bound_project, rollback_client, rollback_project, secret_entry_preview, uninstall_client, update_project
from .socrates import record_guard_failure, record_harness_signal, transition_step


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-agent-fabric")
    sub = parser.add_subparsers(dest="command", required=True)
    detect = sub.add_parser("detect", help="Detect host environment without executing project commands")
    detect.add_argument("--json", action="store_true")
    detect_client_command = sub.add_parser("detect-client", help="Detect a repository-local agent client")
    detect_client_command.add_argument("target", type=Path)
    detect_client_command.add_argument("--json", action="store_true")
    preflight = sub.add_parser("preflight", help="Compare declared project requirements to detected capabilities")
    preflight.add_argument("target", type=Path)
    preflight.add_argument("--json", action="store_true")
    work = sub.add_parser("work", help="Route a bound project to one restore or new-task path without writing")
    work.add_argument("target", type=Path)
    work.add_argument("selector", nargs="?")
    work.add_argument("--home", type=Path, default=default_fabric_home())
    work.add_argument("--json", action="store_true")
    start = sub.add_parser("start", help="Preview or explicitly create one project-local task package and start Socrates")
    start.add_argument("target", type=Path)
    start.add_argument("--title", required=True)
    start.add_argument("--type", dest="work_class", required=True, choices=("small-bug", "planned"))
    start.add_argument("--id")
    start.add_argument("--home", type=Path, default=default_fabric_home())
    start.add_argument("--apply", action="store_true", help="Create the previewed package; omitted by default")
    start.add_argument("--json", action="store_true")
    restore = sub.add_parser("restore", help="Resume one bound task's Socrates lifecycle without running project commands")
    restore.add_argument("target", type=Path)
    restore.add_argument("task_id", nargs="?", help="Task id, exact title, or one-based number from the restore task list")
    restore.add_argument("--home", type=Path, default=default_fabric_home())
    restore.add_argument("--json", action="store_true")
    memory = sub.add_parser("memory", help="Manage a target repository's local memory")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    memory_init = memory_sub.add_parser("init")
    memory_init.add_argument("target", type=Path)
    memory_init.add_argument("--home", type=Path, default=default_fabric_home())
    memory_quarantine = memory_sub.add_parser("quarantine", help="Inspect retained local results that need human relinking")
    memory_quarantine.add_argument("target", type=Path)
    memory_quarantine.add_argument("--home", type=Path, default=default_fabric_home())
    memory_quarantine.add_argument("--json", action="store_true")
    memory_pending_requests = memory_sub.add_parser("pending-requests", help="List outstanding project-local delegation requests")
    memory_pending_requests.add_argument("target", type=Path)
    memory_pending_requests.add_argument("--session", required=True)
    memory_pending_requests.add_argument("--home", type=Path, default=default_fabric_home())
    memory_pending_requests.add_argument("--json", action="store_true")
    memory_pending_results = memory_sub.add_parser("pending-results", help="List specialist results waiting for acknowledgement")
    memory_pending_results.add_argument("target", type=Path)
    memory_pending_results.add_argument("--session", required=True)
    memory_pending_results.add_argument("--home", type=Path, default=default_fabric_home())
    memory_pending_results.add_argument("--json", action="store_true")
    memory_restore = memory_sub.add_parser("restore", help="Read one project-local memory session")
    memory_restore.add_argument("target", type=Path)
    memory_restore.add_argument("--session", required=True)
    memory_restore.add_argument("--home", type=Path, default=default_fabric_home())
    memory_restore.add_argument("--json", action="store_true")
    guard = sub.add_parser("guards", help="Record and process concrete project-local Guard failures")
    guard_sub = guard.add_subparsers(dest="guard_command", required=True)
    guard_failure = guard_sub.add_parser("failure", help="Record one Guard failure and its declared policy outcome")
    guard_failure.add_argument("target", type=Path)
    guard_failure.add_argument("--session", required=True)
    guard_failure.add_argument("--idempotency-key", required=True)
    guard_failure.add_argument("--incident-id", required=True, help="Stable id for one retry lineage")
    guard_failure.add_argument("--guard", required=True)
    guard_failure.add_argument("--artifact", required=True, help="Safe project-relative evidence artifact reference")
    guard_failure.add_argument("--home", type=Path, default=default_fabric_home())
    guard_failure.add_argument("--json", action="store_true")
    socrates = sub.add_parser("socrates", help="Run one task-local Socrates lifecycle transition")
    socrates_sub = socrates.add_subparsers(dest="socrates_command", required=True)
    socrates_step = socrates_sub.add_parser("step", help="Advance one declared checklist step")
    socrates_step.add_argument("target", type=Path)
    socrates_step.add_argument("--session", required=True)
    socrates_step.add_argument("--step", required=True)
    socrates_step.add_argument("--status", required=True, choices=("in-progress", "done", "skipped"))
    socrates_step.add_argument("--closure-artifact", help="Existing project-relative evidence required for done or skipped")
    socrates_step.add_argument("--closure-reason", help="Non-secret reason required for done or skipped")
    socrates_step.add_argument("--home", type=Path, default=default_fabric_home())
    socrates_step.add_argument("--json", action="store_true")
    socrates_signal = socrates_sub.add_parser("signal", help="Record one Socrates-owned Harness signal")
    socrates_signal.add_argument("target", type=Path)
    socrates_signal.add_argument("--category", required=True, choices=("user-correction", "agent-drift", "missed-instruction", "scope-violation", "memory-gap", "repeated-failure", "security-concern", "friction"))
    socrates_signal.add_argument("--task-id")
    socrates_signal.add_argument("--artifact", help="Optional safe project-relative evidence artifact reference")
    socrates_signal.add_argument("--home", type=Path, default=default_fabric_home())
    socrates_signal.add_argument("--json", action="store_true")
    secret = sub.add_parser("secret", help="Use the selected release's hidden terminal prompt for a project-local secret")
    secret_sub = secret.add_subparsers(dest="secret_command", required=True)
    secret_prompt = secret_sub.add_parser("prompt", help="Store one secret through a hidden Bash prompt")
    secret_prompt.add_argument("target", type=Path)
    secret_prompt.add_argument("--destination", required=True, help="Profile-allowed project-relative destination; never a secret value")
    secret_prompt.add_argument("--label", required=True, help="Non-secret prompt label")
    secret_prompt.add_argument("--home", type=Path, default=default_fabric_home())
    secret_prompt.add_argument("--preview", action="store_true")
    secret_prompt.add_argument("--json", action="store_true")
    spec = sub.add_parser("spec", help="Create and validate project-local task packages")
    spec_sub = spec.add_subparsers(dest="spec_command", required=True)
    spec_create = spec_sub.add_parser("create")
    spec_create.add_argument("target", type=Path)
    spec_create.add_argument("--type", dest="work_class", required=True, choices=("small-bug", "planned"))
    spec_create.add_argument("--title", required=True)
    spec_create.add_argument("--id")
    spec_create.add_argument("--home", type=Path, default=default_fabric_home())
    spec_validate = spec_sub.add_parser("validate")
    spec_validate.add_argument("target", type=Path)
    spec_validate.add_argument("task_id")
    spec_readiness = spec_sub.add_parser("readiness", help="Read whether a task package satisfies its implementation gate")
    spec_readiness.add_argument("target", type=Path)
    spec_readiness.add_argument("task_id")
    spec_readiness.add_argument("--json", action="store_true")
    spec_approve = spec_sub.add_parser("approve", help="Record an interactive human approval for the current Kepler-reviewed package")
    spec_approve.add_argument("target", type=Path)
    spec_approve.add_argument("task_id")
    spec_approve.add_argument("--home", type=Path, default=default_fabric_home())
    spec_approve.add_argument("--preview", action="store_true")
    spec_approve.add_argument("--json", action="store_true")
    spec_archive = spec_sub.add_parser("archive")
    spec_archive.add_argument("target", type=Path)
    spec_archive.add_argument("task_id")
    spec_archive.add_argument("--reason", required=True)
    spec_archive.add_argument("--home", type=Path, default=default_fabric_home())
    bootstrap = sub.add_parser("bootstrap", help="Inspect or explicitly install host prerequisites")
    bootstrap_sub = bootstrap.add_subparsers(dest="bootstrap_target", required=True)
    bootstrap_bash = bootstrap_sub.add_parser("bash", help="Prepare Bash for Fabric workflows")
    bootstrap_bash.add_argument("--install", action="store_true")
    bootstrap_bash.add_argument("--json", action="store_true")
    harness = sub.add_parser("harness", help="Use project-local trace and recovery helpers")
    harness_sub = harness.add_subparsers(dest="harness_command", required=True)
    harness_resume = harness_sub.add_parser("resume")
    harness_resume.add_argument("target", type=Path)
    harness_resume.add_argument("task_id")
    harness_resume.add_argument("--json", action="store_true")
    harness_checkpoint = harness_sub.add_parser("checkpoint", help="Validate a shared Fabric gate and append its local checkpoint")
    harness_checkpoint.add_argument("target", type=Path)
    harness_checkpoint.add_argument("--gate", required=True)
    harness_checkpoint.add_argument("--evidence", required=True, help="JSON list of evidence names, never secret values")
    harness_checkpoint.add_argument("--session", required=True, help="Task-local Socrates session that owns this gate")
    harness_checkpoint.add_argument("--failure-id", help="Stable idempotency key required if the checkpoint fails")
    harness_checkpoint.add_argument("--failure-artifact", help="Existing evidence artifact required if the checkpoint fails")
    harness_checkpoint.add_argument("--home", type=Path, default=default_fabric_home())
    harness_checkpoint.add_argument("--json", action="store_true")
    harness_health = harness_sub.add_parser("health")
    harness_health.add_argument("target", type=Path)
    harness_health.add_argument("--home", type=Path, default=default_fabric_home())
    harness_health.add_argument("--json", action="store_true")
    harness_retro_input = harness_sub.add_parser("retrospective-input", help="Read local Harness signals since the last approved retrospective")
    harness_retro_input.add_argument("target", type=Path)
    harness_retro_input.add_argument("--home", type=Path, default=default_fabric_home())
    harness_retro_input.add_argument("--json", action="store_true")
    harness_review = harness_sub.add_parser("review", help="Read the bounded Harness retrospective input for Kepler and human review")
    harness_review.add_argument("target", type=Path)
    harness_review.add_argument("--home", type=Path, default=default_fabric_home())
    harness_review.add_argument("--json", action="store_true")
    harness_retro_close = harness_sub.add_parser("close-retrospective", help="Advance the project Harness cursor after Kepler and human approval")
    harness_retro_close.add_argument("target", type=Path)
    harness_retro_close.add_argument("--report-artifact", required=True, help="Safe project-relative retrospective report path")
    harness_retro_close.add_argument("--kepler-verdict-artifact", required=True, help="Safe project-relative Kepler verdict path")
    harness_retro_close.add_argument("--human-decision-artifact", required=True, help="Safe project-relative approved human decision path")
    harness_retro_close.add_argument("--snapshot-start-offset", type=int, required=True, help="Unchanged snapshot start_offset returned by retrospective-input")
    harness_retro_close.add_argument("--watermark", type=int, required=True, help="Unchanged byte watermark returned by retrospective-input")
    harness_retro_close.add_argument("--snapshot-digest", required=True, help="Unchanged snapshot SHA-256 returned by retrospective-input")
    harness_retro_close.add_argument("--reviewer", required=True, choices=("opponent",))
    harness_retro_close.add_argument("--human-approved", action="store_true")
    harness_retro_close.add_argument("--home", type=Path, default=default_fabric_home())
    harness_retro_close.add_argument("--json", action="store_true")
    distribution = sub.add_parser("distribution", help="Manage versioned user-level Fabric releases and project bindings")
    distribution_sub = distribution.add_subparsers(dest="distribution_command", required=True)
    distribution_home = distribution_sub.add_parser("home", help="Show the default Fabric installation home")
    distribution_home.add_argument("--json", action="store_true")
    distribution_adapter = distribution_sub.add_parser("adapter-manifest", help="Show a client adapter contract")
    distribution_adapter.add_argument("client", choices=("codex", "copilot", "claude"))
    distribution_adapter.add_argument("--json", action="store_true")
    distribution_install = distribution_sub.add_parser("install-release", help="Install a new immutable Fabric release")
    distribution_install.add_argument("source", type=Path)
    distribution_install.add_argument("--home", type=Path)
    distribution_install.add_argument("--version")
    distribution_install.add_argument("--preview", action="store_true")
    distribution_bind = distribution_sub.add_parser("bind-project", help="Bind a project to an installed Fabric release")
    distribution_bind.add_argument("target", type=Path)
    distribution_bind.add_argument("--release", required=True)
    distribution_bind.add_argument("--client", required=True, choices=("codex", "copilot", "claude"))
    distribution_bind.add_argument("--home", type=Path)
    distribution_bind.add_argument("--preview", action="store_true")
    distribution_update = distribution_sub.add_parser("update-project", help="Move one project binding to another installed release")
    distribution_update.add_argument("target", type=Path)
    distribution_update.add_argument("--release", required=True)
    distribution_update.add_argument("--home", type=Path)
    distribution_update.add_argument("--preview", action="store_true")
    distribution_repair_update = distribution_sub.add_parser("repair-project-update", help="Explicitly finish an interrupted project update from its recovery journal")
    distribution_repair_update.add_argument("target", type=Path)
    distribution_repair_update.add_argument("--home", type=Path)
    distribution_repair_update.add_argument("--preview", action="store_true")
    distribution_project_rollback = distribution_sub.add_parser("rollback-project", help="Restore the most recent project binding backup")
    distribution_project_rollback.add_argument("target", type=Path)
    distribution_project_rollback.add_argument("--home", type=Path)
    distribution_project_rollback.add_argument("--preview", action="store_true")
    distribution_enable = distribution_sub.add_parser("enable-client", help="Connect a user-level client entry point to the active release")
    distribution_enable.add_argument("client", choices=("codex", "copilot", "claude"))
    distribution_enable.add_argument("--home", type=Path, default=default_fabric_home())
    distribution_enable.add_argument("--method", choices=("symlink", "import", "wrapper", "managed-block"))
    distribution_enable.add_argument("--elevate", action="store_true", help="On Windows, permit a UAC request only for the selected symlink delivery")
    distribution_enable.add_argument("--preview", action="store_true")
    distribution_rollback = distribution_sub.add_parser("rollback-client", help="Restore the prior installer-owned client artifact")
    distribution_rollback.add_argument("client", choices=("codex", "copilot", "claude"))
    distribution_rollback.add_argument("--home", type=Path, default=default_fabric_home())
    distribution_rollback.add_argument("--elevate", action="store_true", help="On Windows, permit a UAC request only when rollback restores a symlink")
    distribution_rollback.add_argument("--preview", action="store_true")
    distribution_uninstall = distribution_sub.add_parser("uninstall-client", help="Remove an installer-owned client artifact")
    distribution_uninstall.add_argument("client", choices=("codex", "copilot", "claude"))
    distribution_uninstall.add_argument("--home", type=Path, default=default_fabric_home())
    distribution_uninstall.add_argument("--preview", action="store_true")
    distribution_codex_skills = distribution_sub.add_parser("enable-codex-skills", help="Install Fabric-owned user-scoped Codex skill links")
    distribution_codex_skills.add_argument("--home", type=Path, default=default_fabric_home())
    distribution_codex_skills.add_argument("--elevate", action="store_true", help="On Windows, permit UAC only if native skill links require it")
    distribution_codex_skills.add_argument("--preview", action="store_true")
    distribution_disable_codex_skills = distribution_sub.add_parser("disable-codex-skills", help="Remove Fabric-owned legacy direct Codex skill links")
    distribution_disable_codex_skills.add_argument("--home", type=Path, default=default_fabric_home())
    project = sub.add_parser("project", help="Initialize and manage project-owned Fabric overlays")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    project_status_command = project_sub.add_parser("status", help="Inspect Fabric state in a project without writing")
    project_status_command.add_argument("target", type=Path)
    project_status_command.add_argument("--home", type=Path, default=default_fabric_home())
    project_status_command.add_argument("--json", action="store_true")
    project_context_command = project_sub.add_parser("context", help="Show read-only pinned release and project-contract paths for a bound project")
    project_context_command.add_argument("target", type=Path)
    project_context_command.add_argument("--home", type=Path, default=default_fabric_home())
    project_context_command.add_argument("--json", action="store_true")
    project_command_preview = project_sub.add_parser("command-preview", help="Resolve one declared project command after host capability checks")
    project_command_preview.add_argument("target", type=Path)
    project_command_preview.add_argument("name")
    project_command_preview.add_argument("--home", type=Path, default=default_fabric_home())
    project_command_preview.add_argument("--json", action="store_true")
    project_init = project_sub.add_parser("init", help="Bind a fresh or cloned project to the active Fabric release")
    project_init.add_argument("target", type=Path)
    project_init.add_argument("--client", required=True, choices=("codex", "copilot", "claude"))
    project_init.add_argument("--release")
    project_init.add_argument("--home", type=Path, default=default_fabric_home())
    project_init.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    if args.command == "detect":
        environment = detect_environment().as_dict()
        print(json.dumps(environment) if args.json else environment)
    elif args.command == "detect-client":
        result = detect_client(args.target).as_dict()
        print(json.dumps(result) if args.json else result)
    elif args.command == "preflight":
        missing = unmet_requirements(load_capabilities(args.target))
        result = {"ready": not missing, "missing": missing}
        print(json.dumps(result) if args.json else result)
    elif args.command == "work":
        require_bound_project(args.target, args.home)
        result = work_router(args.target, args.selector)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "start":
        require_bound_project(args.target, args.home)
        result = start_preview(args.target, args.title, args.work_class, args.id)
        if args.apply:
            result["created"] = start_task(args.target, args.title, args.work_class, args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "restore":
        require_bound_project(args.target, args.home)
        picker = restore_picker(args.target, args.task_id)
        result = restore_task(args.target, picker["task_id"]) if picker["route"] == "restore" else picker
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "memory" and args.memory_command == "init":
        # A release update journals its pending state before invoking the selected
        # release's memory initializer. This narrowly permits that initializer to
        # finish the durable migration; other state-changing commands remain blocked.
        require_bound_project(args.target, args.home, allow_pending_update=True)
        print(initialize(args.target.resolve()))
    elif args.command == "memory" and args.memory_command == "quarantine":
        require_bound_project(args.target, args.home)
        entries = quarantined_results(args.target.resolve())
        print(json.dumps(entries, ensure_ascii=False, indent=2) if args.json else entries)
    elif args.command == "memory" and args.memory_command == "pending-requests":
        require_bound_project(args.target, args.home)
        items = pending_requests(args.target.resolve(), args.session)
        print(json.dumps(items, ensure_ascii=False, indent=2) if args.json else items)
    elif args.command == "memory" and args.memory_command == "pending-results":
        require_bound_project(args.target, args.home)
        items = pending_results(args.target.resolve(), args.session)
        print(json.dumps(items, ensure_ascii=False, indent=2) if args.json else items)
    elif args.command == "memory" and args.memory_command == "restore":
        require_bound_project(args.target, args.home)
        snapshot = restore_memory(args.target.resolve(), args.session)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2) if args.json else snapshot)
    elif args.command == "guards" and args.guard_command == "failure":
        require_bound_project(args.target, args.home)
        result = record_guard_failure(
            args.target.resolve(),
            args.session,
            args.idempotency_key,
            args.incident_id,
            args.guard,
            args.artifact,
            args.home,
        )
        flush_guard_traces(args.target)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "socrates" and args.socrates_command == "step":
        require_bound_project(args.target, args.home)
        result = transition_step(args.target.resolve(), args.session, args.step, args.status, args.closure_artifact, args.closure_reason)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "socrates" and args.socrates_command == "signal":
        require_bound_project(args.target, args.home)
        result = record_harness_signal(args.target, args.category, args.task_id, args.artifact)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "secret" and args.secret_command == "prompt":
        preview = secret_entry_preview(args.target, args.destination, args.label, args.home)
        if args.preview:
            print(json.dumps(preview, ensure_ascii=False, indent=2) if args.json else preview)
        else:
            enter_secret(args.target, args.destination, args.label, args.home)
    elif args.command == "spec" and args.spec_command == "create":
        require_bound_project(args.target, args.home)
        print(start_task(args.target, args.title, args.work_class, args.id)["package"])
    elif args.command == "spec" and args.spec_command == "validate":
        errors = validate_task(args.target, args.task_id)
        if errors:
            parser.error("; ".join(errors))
        print("Task package is valid.")
    elif args.command == "spec" and args.spec_command == "readiness":
        result = implementation_readiness(args.target, args.task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "spec" and args.spec_command == "approve":
        require_bound_project(args.target, args.home)
        preview = approval_preview(args.target, args.task_id)
        if args.preview:
            print(json.dumps(preview, ensure_ascii=False, indent=2) if args.json else preview)
        else:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                parser.error("spec approve requires an interactive terminal; use --preview for read-only inspection")
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            reviewed_sha256 = str(preview["kepler_verdict_sha256"])
            confirmation = input(
                f"Review the package above and type exactly `approve {preview['task_id']} {reviewed_sha256}` to continue: "
            )
            path = approve_planned_task(args.target, args.task_id, confirmation, reviewed_sha256)
            print(path)
    elif args.command == "spec" and args.spec_command == "archive":
        require_bound_project(args.target, args.home)
        print(archive_task(args.target, args.task_id, args.reason))
    elif args.command == "bootstrap" and args.bootstrap_target == "bash":
        if args.install:
            install_bash()
            print("Bash is available.")
        else:
            plan = asdict(bash_install_plan())
            print(json.dumps(plan) if args.json else plan)
    elif args.command == "harness" and args.harness_command == "resume":
        snapshot = resume_snapshot(args.target, args.task_id)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2) if args.json else snapshot)
    elif args.command == "harness" and args.harness_command == "checkpoint":
        require_bound_project(args.target, args.home)
        if bool(args.failure_id) != bool(args.failure_artifact):
            parser.error("--failure-id and --failure-artifact must be supplied together")
        try:
            evidence = json.loads(args.evidence)
        except json.JSONDecodeError as error:
            parser.error(f"--evidence must be a JSON list: {error}")
        result = record_checkpoint(
            args.target, args.gate, evidence, args.home,
            session_id=args.session, failure_id=args.failure_id, failure_artifact=args.failure_artifact,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "harness" and args.harness_command == "health":
        report = health_report(args.target, args.home)
        print(json.dumps(report) if args.json else report)
    elif args.command == "harness" and args.harness_command == "retrospective-input":
        require_bound_project(args.target, args.home)
        report = retrospective_input(args.target)
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report)
    elif args.command == "harness" and args.harness_command == "review":
        require_bound_project(args.target, args.home)
        report = retrospective_input(args.target)
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report)
    elif args.command == "harness" and args.harness_command == "close-retrospective":
        require_bound_project(args.target, args.home)
        result = close_retrospective(
            args.target,
            args.report_artifact,
            args.kepler_verdict_artifact,
            args.human_decision_artifact,
            args.snapshot_start_offset,
            args.watermark,
            args.snapshot_digest,
            args.reviewer,
            args.human_approved,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    elif args.command == "distribution" and args.distribution_command == "home":
        home = default_fabric_home()
        print(json.dumps({"fabric_home": str(home)}) if args.json else home)
    elif args.command == "distribution" and args.distribution_command == "adapter-manifest":
        manifest = adapter_manifest(args.client)
        print(json.dumps(manifest, ensure_ascii=False, indent=2) if args.json else manifest)
    elif args.command == "distribution" and args.distribution_command == "install-release":
        paths = release_preview(args.source, args.home, args.version) if args.preview else [install_release(args.source, args.home, args.version)]
        for path in paths:
            print(path)
    elif args.command == "distribution" and args.distribution_command == "bind-project":
        paths = binding_preview(args.target, args.release, args.client, args.home) if args.preview else [bind_project(args.target, args.release, args.client, args.home)]
        for path in paths:
            print(path)
    elif args.command == "distribution" and args.distribution_command == "update-project":
        if args.preview:
            print(json.dumps(project_update_preview(args.target, args.release, args.home), ensure_ascii=False, indent=2))
        else:
            print(update_project(args.target, args.release, args.home))
    elif args.command == "distribution" and args.distribution_command == "repair-project-update":
        if args.preview:
            print(json.dumps(repair_project_update_preview(args.target, args.home), ensure_ascii=False, indent=2))
        else:
            print(repair_project_update(args.target, args.home))
    elif args.command == "distribution" and args.distribution_command == "rollback-project":
        if args.preview:
            print(json.dumps(project_rollback_preview(args.target, args.home), ensure_ascii=False, indent=2))
        else:
            print(rollback_project(args.target, args.home))
    elif args.command == "distribution" and args.distribution_command == "enable-client":
        if args.preview:
            print(json.dumps(client_enable_preview(args.home, args.client, args.method), ensure_ascii=False, indent=2))
        else:
            preview = client_enable_preview(args.home, args.client, args.method)
            if args.elevate:
                notice = preview.get("windows_elevation_notice")
                if notice is None:
                    raise ValueError("--elevate is valid only for the symlink delivery method on Windows")
                print(json.dumps(notice, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)
            print(enable_client(
                args.home,
                args.client,
                args.method,
                allow_windows_elevation=args.elevate,
                elevation_notice_acknowledged=args.elevate,
            ))
    elif args.command == "distribution" and args.distribution_command == "rollback-client":
        if args.preview:
            print(json.dumps(client_rollback_preview(args.home, args.client), ensure_ascii=False, indent=2))
        else:
            preview = client_rollback_preview(args.home, args.client)
            if args.elevate:
                notice = preview.get("windows_elevation_notice")
                if notice is None:
                    raise ValueError("--elevate is valid only when Windows rollback may restore a symlink")
                print(json.dumps(notice, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)
            print(rollback_client(
                args.home,
                args.client,
                allow_windows_elevation=args.elevate,
                elevation_notice_acknowledged=args.elevate,
            ))
    elif args.command == "distribution" and args.distribution_command == "uninstall-client":
        if args.preview:
            print(json.dumps(client_uninstall_preview(args.home, args.client), ensure_ascii=False, indent=2))
        else:
            uninstall_client(args.home, args.client)
            print("Client adapter removed.")
    elif args.command == "distribution" and args.distribution_command == "enable-codex-skills":
        preview = codex_skill_enable_preview(args.home)
        if args.preview:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        else:
            if args.elevate:
                print(json.dumps(preview["windows_elevation_notice"], ensure_ascii=False, indent=2), file=sys.stderr, flush=True)
            print(enable_codex_skills(args.home, allow_windows_elevation=args.elevate))
    elif args.command == "distribution" and args.distribution_command == "disable-codex-skills":
        disable_codex_skills(args.home)
        print("Legacy direct Codex skill links removed.")
    elif args.command == "project" and args.project_command == "init":
        paths = project_onboarding_preview(args.target, args.client, args.home, args.release) if args.preview else [onboard_project(args.target, args.client, args.home, args.release)]
        for path in paths:
            print(path)
    elif args.command == "project" and args.project_command == "context":
        context = project_context(args.target, args.home)
        print(json.dumps(context, ensure_ascii=False, indent=2) if args.json else context)
    elif args.command == "project" and args.project_command == "command-preview":
        require_bound_project(args.target, args.home)
        command = resolve_project_command(load_project_profile(args.target), args.name)
        print(json.dumps(command, ensure_ascii=False, indent=2) if args.json else command)
    elif args.command == "project" and args.project_command == "status":
        report = project_status(args.target, args.home)
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report)


if __name__ == "__main__":
    main()
