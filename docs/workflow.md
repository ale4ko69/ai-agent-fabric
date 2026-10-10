# Portable development workflow

This is the common workflow for a bound project. It is intentionally free of repository
paths, tracker identities, service ports, client-specific commands, and credentials.
Those belong to the project profile and optional adapters.

```text
open project through a selected client
        |
        v
read-only Fabric status -> bound release + local profile + local memory
        |
        v
detect host/client capabilities -> restore relevant task state
        |
        v
triage the work
  | local correction        | small bug             | planned work
  v                         v                       v
bounded edit + evidence   tasks + evidence     spec -> research -> plan
                                                  |              |
                                                  v              v
                                           Kepler verdict <- revision
                                                  |
                                     required human approval
                                                  |
                                                  v
                                        scoped implementation
                                                  |
                                      Athena review -> validation
                                                  |
                                                  v
                                      evidence -> close-out/archive
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

A client-facing task entrypoint is a router, not another workflow: it either restores
one known active task or starts new-task intake. It never silently starts over and never
mixes multiple task packages. Restore is read-only: it reports the first unfinished
applicable step, retains evidence for completed steps, and waits for direction before
executing project work.

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
interruption. Resume is read-only until the task is reoriented. Closing a task requires
the applicable local evidence and moves its package to a recoverable archive; it never
deletes history.

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
