# Independent source-to-target transfer audit

Date: 2026-10-10

This is the implementation owner's audit after Kepler's final PASS. It compares the
source `dev-agent-fabric` Start Orchestrator and Process Gate contracts with this
portable repository, rather than treating file presence as proof of transfer.

| Source contract | Target contract | Evidence | Result |
| --- | --- | --- | --- |
| New-task bootstrap creates durable session state before orchestration. | `start --apply` creates the package, initializes absent memory, activates `task_lifecycles`, and records `task-started`. | `entrypoints.start_task`; lifecycle start test. | transferred |
| Workflow is materialized as durable objects, not prose. | Work-class steps are stored in `task_steps`, with a computed `next_action`. | `task_specs.workflow_steps`; `memory.activate_task_lifecycle`. | transferred |
| No action outside an ordered step; completed work is not restarted. | Socrates transitions steps in order, preserves `done`/`skipped`, and restore returns the checklist. | `memory.advance_task_step`; recovery test. | transferred |
| Closing requires evidence; skipping is explicit with a reason. | `done` and `skipped` require an existing project-relative closure artifact and a non-secret reason. | `memory.advance_task_step`; closure rejection test. | transferred |
| Failed gates create a distinct durable failure record. | Runtime `record_checkpoint` converts only gate-validation failure into the pinned `checkpoint` Guard; failures/outcomes are separate from Harness signals. | `harness.record_checkpoint`; runtime checkpoint and signal-isolation tests. | transferred |
| Failure record and audit log survive interruption. | Failure/outcome and trace outbox are one database transaction; restore flushes trace idempotently. | `_persist_guard_failure`; trace recovery test. | transferred |
| Retry has bounded escalation. | Pinned Guard policy produces retry/retry/escalate and retains the active incident id. | `core/guards.json`; incident test. | transferred |
| Restart restores work rather than creating a new task. | `restore` resumes the exact lifecycle, returns records, outcomes, checklist and next action; missing `memory.db` fails closed. | `entrypoints.restore_task`; missing-memory test. | transferred |

## Intentional exclusions

The source's Jira key, workspace location, CI commands, raw failure text, and its
specific Step 0–12 catalogue are employer/workspace-specific. They are not portable
Fabric core. Target projects supply their own facts through profiles and task artifacts;
the transferable lifecycle, evidence, ordering, recovery, and Guard semantics above are
preserved.

## Audit conclusion

No source lifecycle or Process Gate control that belongs in portable Fabric remains
unmapped. The remaining source-specific integrations are intentionally excluded, not
missing transfer work.
