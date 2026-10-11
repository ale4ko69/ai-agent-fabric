# Portable development workflow

This is the common workflow for a bound project. It is intentionally free of repository
paths, tracker identities, service ports, client-specific commands, and credentials.
Those belong to the project profile and optional adapters.

```text
Root opens project through a selected client
        |
        v
read-only Fabric status -> bound release + local profile + local memory
        |
        v
detect host/client capabilities -> restore relevant task state
        |
        v
Root creates or reopens the task's separate Socrates chat
        |
        v
Socrates claims the durable task id and owns all remaining transitions
        |
        v
triage the work
  | local correction        | small bug             | planned work
  v                         v                       v
bounded edit + evidence   tasks + evidence     spec -> research -> plan
                                                  |              |
                                                  v              v
                              Aristotle evidence -> Plato plan -> Kepler verdict
                                                  |
                                                  v
                                           revision, if required
                                                  |
                                     required human approval
                                                  |
                                                  v
                                        scoped implementation
                                                  |
                                      Athena review -> validation
                                                  |
                                                  v
                                      evidence -> close-out -> rollout -> archive
```

## Session start

1. The global bootstrap checks Fabric status without writing files.
2. A bound project loads only its pinned release, project profile, local overlay, and
   relevant project-local memory.
3. Detect host, Bash, Python, Git, and selected client before selecting a command.
4. Restore the active task package and pending specialist results when work resumes.
5. If the repository is not bound, report that fact and show initialization preview
   only after the person asks to enable Fabric for it.

## Entry and restore discipline

A client-facing `work` entrypoint is a router, not another workflow: it either restores
one known active task or starts new-task intake. It never silently starts over and never
mixes multiple task packages. `start --apply` creates a prepared task package and a
`socrates_chat_request`; it must not claim that Socrates is running. The selected client
adapter creates or reopens a separate chat for that task. Socrates claims the returned
task id with that chat's thread id before lifecycle activation. Root remains only the
entry and recovery boundary and must not impersonate Socrates or progress the task.

For new planned work, Socrates materializes the applicable workflow checklist in the
task package. Each step is `pending`, `in_progress`, `done`, or `skipped`; a completed
step names evidence, while a skipped step names its reason. Discovery records facts,
conflicts, confidence, and blocking questions before planning or implementation.
Client-specific slash commands may render this protocol only through a selected adapter;
the protocol itself never assumes a Copilot command folder or a global project path.

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

## Execution and review

Heracles implements only the approved scope. After a state-changing action, the
orchestrator records fresh evidence before deciding the next action; it does not repeat
an assumed-successful command. Athena independently reviews changed work against the
acceptance criteria. Euclid performs validation only when the project has enabled its
validation capability. A checkpoint records evidence labels against the immutable gate
registry; it is not a substitute for the underlying evidence.

## Interruption and close-out

Specialist results enter the project-local outbox with an idempotency key. Socrates is
the sole durable-memory writer and can replay unacknowledged results safely after an
interruption. `harness resume` remains read-only; `restore` returns the saved Socrates
chat binding or a request to create it, but does not execute project work. Closing a
task requires the applicable local evidence and moves its package to a recoverable
archive; it never deletes history. When the owner has declared autonomous delivery,
successful review and validation automatically resume the durable `rollout` step.
Socrates commits only task-scoped changes, pushes to the configured remote, and invokes
the project's declared release action before it may complete the task. A Guard outcome,
missing delivery mechanism, or newly required scope/credential is an actionable
blocker; routine commit, push, and release operations do not require separate approval.

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
