# Task specs

`spec create` is a compatibility alias that creates a durable, project-local task package and starts its Socrates lifecycle under
`<profile.task_specs.root>/active/<task-id>/` (by default,
`docs/specs/active/<task-id>/`). It never contacts an external tracker. The configured
root must be a relative path inside the target project; absolute paths and parent
traversal are rejected.

## Work classes

```text
small-bug
  task.json + tasks.md + evidence/

planned
  task.json + spec.md + research.md + plan.md + kepler.md + kepler.json
  + approval.json + tasks.md + session-state.md + evidence/
```

`task.json` stores the local identity and a tracker reference whose default provider
is `none`. It is deliberately not a mirror of remote issue content.
The global release owns the corresponding schemas: `task-metadata.schema.json`,
`kepler-verdict.schema.json`, and `task-approval.schema.json`. The package keeps the
instances local to the project.

## Commands

```text
ai-agent-fabric start <project> --type small-bug --title "Fix save error" --apply
ai-agent-fabric start <project> --type planned --title "Add account export" --apply
ai-agent-fabric spec validate <project> <task-id>
ai-agent-fabric spec readiness <project> <task-id> --json
ai-agent-fabric spec approve <project> <task-id> --preview
ai-agent-fabric spec approve <project> <task-id>
```

Use `--id` when a project already has a stable task identifier. A new command refuses
to overwrite an existing package. Planned work may not proceed while its required
artifacts are missing. `spec archive <project> <task-id> --reason "..."` validates and
moves the complete package to `<profile.task_specs.root>/archived/`; it does not delete
evidence.

## Implementation gate

`spec readiness` is read-only. For a `small-bug`, it confirms the lightweight local
package path. For planned work, it requires that `kepler.json` reviews the current spec
and plan revisions and returns `advice`, and that `approval.json` records explicit
approval by a human for those same revisions. `challenge`, `block`, a pending verdict,
stale approval, or an `amendment-request` all keep implementation blocked.

The verdict and approval also carry SHA-256 values for the exact current `spec.md`,
`research.md`, and `plan.md`; approval additionally binds the exact `kepler.json`.
Any edit to one of those artifacts makes the package not ready until a fresh review and
approval. `spec approve` first offers a non-mutating preview, then requires a person at
an interactive TTY to type a confirmation containing the previewed Kepler-verdict hash.
If any reviewed artifact changes while the person is deciding, the command fails closed
and requires a new preview. This is a controlled workflow confirmation, not a
cryptographic identity system; a future signed external approval adapter would be a
separate, project-specific integration.

Kepler may record an out-of-scope finding only as `backlog` or `amendment-request`.
The latter requires the owner to amend the spec, then a revised plan and a new Kepler
verdict; it never adds work silently.
