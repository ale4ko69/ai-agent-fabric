# Task specs

`spec create` is a compatibility alias that creates a durable, project-local task package and a pending separate-Socrates-chat claim under
`<profile.task_specs.root>/active/<task-id>/` (by default,
`docs/specs/active/<task-id>/`). It never contacts an external tracker. The configured
root must be a relative path inside the target project; absolute paths and parent
traversal are rejected.

## Portable task identifiers

Task titles may use any language and are retained verbatim in `task.json.title`.
Fabric derives task IDs only as lowercase ASCII kebab-case. Russian titles use a
deterministic English glossary with ASCII transliteration fallback; explicit `--id`
values must already be ASCII kebab-case and are rejected before any state is written.
Use `recover-unicode-package <project> <legacy-directory> --json` to preview a
legacy Unicode package migration, then repeat with `--apply` to rename it, update its
metadata, and prepare its Socrates chat claim through the supported API.

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

## Separate Socrates chat claim

`start --apply` creates the package in `awaiting-socrates-chat` state and returns a
machine-readable `socrates_chat_request`. Root creates or reopens the named separate
client chat and provides its thread id to that chat. Before any lifecycle step or
delegation, the separate chat runs:

```text
ai-agent-fabric socrates claim <project> --session <task-id> --thread-id <chat-thread-id> --json
```

The claim is durable and idempotent for the same chat; a different chat is rejected.
`restore` returns the saved chat binding so Root reopens the same chat rather than
creating a replacement. A prepared task is not evidence that Socrates, Aristotle,
Plato, Kepler, Heracles, Athena, or Euclid has executed.

## Implementation gate

`spec readiness` is read-only. For a `small-bug`, it confirms the lightweight local
package path. For planned work, it requires that `kepler.json` reviews the current spec
and plan revisions and returns `advice`, and that `approval.json` records explicit
approval by a human for those same revisions. `challenge`, `block`, a pending verdict,
stale approval, or an `amendment-request` all keep implementation blocked.

The verdict and approval also carry SHA-256 values for the exact current `spec.md`,
`research.md`, and `plan.md`; approval additionally binds the exact `kepler.json`.
The reviewed `research.md` prefix is immutable, but complete-line runtime observations
may be appended after approval without re-opening the scope gate. An edit inside the
reviewed prefix, or any edit to `spec.md` or `plan.md`, makes the package not ready
until a fresh review and approval. `spec approve` first offers a non-mutating preview, then requires a person at
an interactive TTY to type a confirmation containing the previewed Kepler-verdict hash.
If any reviewed artifact changes while the person is deciding, the command fails closed
and requires a new preview. This is a controlled workflow confirmation, not a
cryptographic identity system; a future signed external approval adapter would be a
separate, project-specific integration.

Kepler may record an out-of-scope finding only as `backlog` or `amendment-request`.
The latter requires the owner to amend the spec, then a revised plan and a new Kepler
verdict; it never adds work silently.
