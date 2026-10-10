# Task artifacts by work class

| Work class | Required durable files | Not required |
|---|---|---|
| Local correction | Memory record and changed-file evidence | Task package, spec, plan |
| Small bug | `tasks.md`, concise reproduction/verification evidence, optional `session-state.md` when interrupted | `spec.md`, `plan.md` |
| Planned work | `spec.md`, `research.md`, `plan.md`, `kepler.md`, `tasks.md`, `session-state.md` | None of these may be silently omitted |

`session-state.md` is needed only when work spans multiple steps, sessions, or an
interruption risk. `tasks.md` is the executable checklist; it never expands the scope
defined by `spec.md`.

The default project-local root is `docs/specs/active/<task-id>/`. Each package contains
`task.json` with its stable ID, title, work class, and an optional tracker reference.
The package is useful without any external tracker; synchronisation is an optional
future adapter, not a requirement for task creation.
