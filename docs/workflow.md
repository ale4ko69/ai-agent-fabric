# Portable development workflow

This is the common workflow for a bound project. It is intentionally free of repository
paths, tracker identities, service ports, client-specific commands, and credentials.
Those belong to the project profile and optional adapters.

```text
User-level client bootstrap        Project-only pinned launcher
                 |                  |
                 +--> status, host/client detection, project context
                                      |
                              Root previews start or restores
                                      |
                  +-------------------+-------------------+
            Supported client handoff           Project-only manual transfer
                  |                                       |
                  +--------> separate Socrates chat <-----+
                                      |
                                  task claim
                                      |
                       +--------------+--------------+
                   local correction  small bug    planned work
                     edit + evidence  tasks        Aristotle evidence
                                      + evidence       -> Plato plan
                                                       -> Kepler verdict
                                                       -> owner approval
                                                       -> Heracles implementation
                                                       -> Athena review
                                                       -> authorized validation
                                      |
                          local evidence and close-out
                                      |
                        rollout done or skipped with evidence
                                      |
                          completion and journal capture*
                                      |
                               recoverable archive
```

*Journal capture applies on releases that support the project journal.*

## Session start

1. Enter through the launcher for the chosen installation path. Use the user-level
   bootstrap for a user-level binding and the pinned local launcher from the
   verified root for project-only Fabric. See [the two setup paths](using-fabric.md).
2. Read project status and context. Resolve the detected host, available executables
   and selected client before choosing commands. An unbound project needs the
   owner's explicit instruction before setup.
3. Load the pinned release contracts and the project profile and overlay. Use
   `work` to route to a known task or intake for new work. On resume, inspect the
   saved package and pending results.

## Entry and restore discipline

Preview a new task with `start`. After the owner confirms the preview,
`start --apply` prepares the package and returns a `socrates_chat_request` for
a separate chat. With the Codex plugin, Root uses its supported client handoff.
With the project-only Codex adapter, follow the pinned project-entry skill and ask
the owner to create a separate real Desktop project chat or reopen the exact saved
chat. Transfer the task id, pinned context, Socrates profile, task package and
activation packet. File installation and visible links establish only filesystem
state. Desktop skill discovery and claim/restore need evidence from the actual
client.

Only the separate chat can run `socrates claim`, using its real thread identity
from the client. If the identity or required handoff is unavailable, stop at the
entry or recovery boundary. `restore` reads the binding and pending state. Reopen
the exact bound chat to continue; preserve its claim and progress.

Socrates records checklist transitions with evidence for completed steps and a
reason and evidence for skipped steps. Discovery records findings, conflicts,
confidence and open questions before planning or implementation.

## Triage and planning

- A local correction is a known isolated textual or styling fix; it retains changed-file
  evidence but needs no task package or plan.
- A small bug is reproducible, narrow, and already understood. It uses `tasks.md` and
  proportionate evidence without a spec or plan.
- A feature, a reproducible bug that is not already understood, or a feature rework is
  planned work. It requires a task package containing spec, research, plan, Kepler
  verdict, tasks, evidence, and session state.

For planned work, Aristotle establishes evidence, Plato creates the bounded plan, and
Kepler independently challenges it. Kepler cannot widen the spec: a new concern is
deferred or explicitly accepted by the human owner as a spec amendment, after which
Plato revises the plan and Kepler gives a fresh verdict.

## New Product (opt-in)

Choose New Product explicitly to explore an idea before ordinary planned work.
Codex Desktop supports entry through the user-level plugin or a bound project-only
Codex adapter. In both routes, the claimed Socrates chat records discovery and
presents an exact MVP contract for explicit owner approval before planning. The
reviewed implementation plan has its own approval. Follow the
[New Product guide](new-product.md) for both launch paths, handoff, discovery,
decision evidence, and restore.

## Execution and review

Heracles implements only the approved scope. After a state-changing action, the
orchestrator records fresh evidence before deciding the next action; it does not repeat
an assumed-successful command. Athena independently reviews changed work against the
acceptance criteria. Euclid performs validation only when the project has enabled its
validation capability. A checkpoint records evidence labels against the immutable gate
registry; it is not a substitute for the underlying evidence.

Any agent editing a file first inspects its current state and preserves the owner's and
other agents' changes. When the intended edit conflicts, stop on that file, report it
and agree on a resolution instead of overwriting or reverting those changes. This is a
practical operational rule, not an atomic guarantee against all concurrent processes.

## Interruption and close-out

Socrates submits and dispatches bounded requests. Specialists enqueue results by
idempotency key. Socrates acknowledges each result into durable project-local
memory and advances the workflow on the referenced evidence. On interruption,
inspect pending requests and results and acknowledge any completed handoffs. See
[delegation and artifact evidence](delegation.md).

Socrates records the task's changes and observed checks as close-out facts on
releases with journal capture. A completed task's journal entry survives
archival. `project journal` reads the local entries. `project release-notes`
writes versioned local notes from explicitly selected journal entries. Publishing
them is a separate action. See [project journal and release notes](cli.md#project-journal-and-release-notes).

An owner-authorized rollout may include committing task-scoped changes, pushing
to the configured remote and invoking the project's declared release action.
Record the actual outcome before completing a required rollout. When the owner
has declared autonomous delivery for the task, proceed through its authorized
steps on successful review and validation. A Guard outcome, missing delivery
mechanism, or scope or credential change requires an actionable status. When
rollout falls outside the accepted task, Socrates closes the durable `rollout`
step as `skipped` with an existing evidence artifact and a reason that records
the task's delivery boundary. Fabric captures the journal entry on releases with
journal support and marks the task complete only after every durable step is
`done` or `skipped`.

The claimed chat uses `socrates archive` with an auditable reason after
completion. The package moves from `active` to `archived`, keeping its history
available. A terminal Guard resumes only through `socrates resolve-guard` with
fresh project-local evidence and the owner's recorded direction.

## Guards and concrete failures

When a declared Gate or concrete command fails, Socrates first writes an evidence
artifact, then records it through `guards failure`. Guards return a deterministic
`retry`, `block`, or `escalate` outcome and never rerun work themselves. A
`retry-then-escalate` policy retries only the first two failures for the same
session/taxonomy/Guard, then escalates the third. A Harness behaviour signal is not a
Guard failure and does not invoke a Guard. See [Guards](guards.md).

## Harness retrospective

When a user corrects agent behaviour, a required instruction is missed, or a repeated
failure appears, Socrates records a minimal project-local Harness signal without copying
the conversation. On demand, Harness reads all signals since its last approved run, and
Socrates creates an evidence-backed retrospective report. Kepler reviews each proposal
for proof and scope; the human accepts, rejects, or defers it. The Harness cursor
advances only after that approval using the input's immutable signal-log watermark. It does not use calendar gaps, so a project may be
inactive between runs without losing the correct analysis window. Client hooks may help
capture or restore this state, but only through the selected adapter. See
[Harness](harness.md).

## Optional integrations

Tracker, repository-host, notification, documentation, and UI/UX actions are not
workflow prerequisites. A project enables each through a declared capability and
configuration. No remote update happens solely because a task was opened or resumed.
