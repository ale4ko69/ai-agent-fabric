# Make Socrates own project chat orchestration after start and restore

## User Value

After a user starts or restores a bound project task, the visible chat must be
owned by that task's Socrates. Root is only the entry and recovery boundary, so
the user never receives competing orchestration from two roles.

## Scope

- Define one explicit Codex handoff contract after successful `start --apply` and
  `restore <task-id>`.
- Make the returned task-local Socrates packet the authoritative visible-chat
  instruction, including its task id, lifecycle state, next action, and limits.
- Require Root to stop project planning, delegation, implementation, and task
  state mutation after success; it may report or recover a failed handoff only.
- Cover start, restore, picker selection, handoff failure, and recovery in the
  generated Codex bootstrap, skills, runtime output, and tests.

## Non-Goals

- Do not read or persist private conversation transcripts.
- Do not claim a native Codex role-switch API unless the client exposes one.
- Do not change project code, external trackers, or another client adapter's
  runtime behavior without its own declared delivery contract.

## Acceptance Criteria

- A successful start or restore returns a machine-readable Socrates handoff
  packet and visible instruction that makes Socrates the sole project-chat owner.
- Root's post-handoff limitations are identical for start and restore and tested.
- A failed handoff leaves Root in recovery-only mode and never permits it to do
  the project task.
- The flow remains explicit about the current client limitation when a true
  native conversation transfer is unavailable.

## Constraints

- Preserve project-local task/memory ownership and the existing no-transcript
  privacy boundary.
- Keep all service identifiers ASCII-safe and require previewed release install.

## Open Questions

- Whether Codex exposes a native, durable in-chat role-transfer primitive; if
  not, the adapter must render an enforceable instruction/context boundary.
