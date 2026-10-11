# Fabric gates and checkpoints

The pinned Fabric release owns the complete gate registry. A project may supply
evidence, but may not redefine a gate, transition, or required evidence name.

| Gate | Transition | Required evidence names |
|---|---|---|
| `intake` | `task-accepted` | `task-classification`, `task-state` |
| `discovery` | `research-complete` | `source-evidence` |
| `plan-freshness` | `implementation-ready` | `approved-plan`, `current-evidence`, `opponent-verdict` |
| `scope` | `implementation-continues` | `approved-spec`, `scope-check` |
| `review` | `review-complete` | `changed-artifacts`, `review-result` |
| `validation` | `task-close-ready` | `validation-evidence` |
| `close-out` | `rollout-ready` | `close-out-evidence` |
| `rollout` | `archived` | `delivery-evidence`, `archive-record` |
| `resume` | `resumed` | `task-state`, `memory-restore` |

`harness checkpoint <project> --gate <id> --evidence '["..."]' [--home <fabric-home>]` reads the gate
registry from the release pinned by the project binding. It rejects unknown gates,
missing, duplicate, or unexpected evidence names, and unbound projects. On success it appends only
the gate identifier, transition, and evidence names to
`.agent-fabric/harness/trace.jsonl`; it does not execute a project command or store
evidence values. Trace fields are identifier-only and reject common credential formats;
free-text observations belong in task artifacts.

The command is intentionally an auditable checkpoint, not an assertion that a test,
deployment, review, or tracker action actually occurred. Concrete evidence is retained
in the task package and project-local memory.
