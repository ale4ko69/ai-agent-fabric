# Architecture

## Boundaries

The core owns behavior that is valid for every repository:

- a stable agent-role catalog;
- a typed delegation-result envelope;
- durable, local episodic memory;
- environment detection before command selection;
- project-local installation.

The canonical agent profiles and portable gate semantics are machine-readable data in
the selected immutable Fabric release. Target capabilities are project-local data.
Client adapters may render the shared contracts but cannot redefine their authority or
transitions.

## Runtime responsibilities

| Concern | Runtime | Reason |
|---|---|---|
| Files, Git, processes, ordinary system commands, simple gates | Bash | Native shell semantics and composable standard tools |
| Memory, SQLite, JSON, installer, validation, integrations | Python | Typed data handling and standard-library portability |
| PowerShell | Not a workflow dependency | Avoid version-specific behavior |

A project profile owns facts that are valid only for one repository: its language,
commands, integrations, delivery process, local acceptance criteria, and local paths.
A profile cannot alter the Fabric's safety rules, shared gate semantics, or install
global state.

The Fabric itself is a versioned user-level distribution; a project binds to one
compatible release and supplies a local overlay. This is distinct from global project
configuration: no project-specific facts, memory, tasks, or credentials enter the
common distribution. See [global distribution and project binding](global-distribution.md)
and the [memory boundary](memory.md).

## Work-tracking configuration

Work tracking is an optional project-local integration category, not a core workflow
rule. A target repository may declare its own adapter, allowed state transitions, and
templates for descriptions and comments. Adapter credentials and personal endpoints
are excluded from configuration and memory. Network calls belong to the project adapter
and are not made by profile loading or validation.

## Secret-entry protocol

When a project needs a token, password, key, or other secret, the agent opens an
interactive hidden Bash prompt and tells the person what credential is needed. The
secret is entered directly in the terminal and written to the project profile's
declared secret destination; it is never requested in chat, printed, logged, placed
in a command argument, or recorded in memory. Bash is required for this operation.

## State flow

```text
user task
  -> environment detection (read-only)
  -> project profile + relevant memory recall
  -> orchestrator creates a delegation contract
  -> specialist returns a structured result
  -> orchestrator records result and evidence
  -> gate validates the next state transition
```

Only the orchestrator persists task results to the episodic store. Specialists return
structured data into a durable project-local outbox. The orchestrator acknowledges an
outbox result in the same database transaction that persists its evidence record and
updates the session. Unacknowledged results are replayable by idempotency key after an
interruption; this creates one ordered audit trail without concurrent memory writers.
Structured memory evidence and delegation payloads reject secret-like field names and
common credential formats before persistence. The outbox keeps only typed identifiers
and artifact references; detailed findings belong in task artifacts. Secrets belong
only in the declared credential destination.

The matching project-local request envelope keeps delegation scope as references to
task artifacts rather than copying mutable prompt text. See [delegation contract](delegation.md).

## Project-local harness

The harness appends typed, identifier-only trace events to
`.agent-fabric/harness/trace.jsonl`. It rejects secret-like fields, free-text payloads,
and non-canonical evidence labels, including in nested agent results. It can
reconstruct a task's local artifact list, memory state, and pending specialist results.
Resume is read-only: it never starts a service, executes a project command, or contacts
an external tracker.

`harness checkpoint` validates the named evidence *labels* against the immutable gate
registry of the release pinned by the project, then appends an auditable local
checkpoint. It never executes a project command and does not treat a checkpoint as
proof that an external action happened. See [gates](gates.md).

`harness health` is also read-only. It separately reports project-owned artifacts and,
when a binding exists, the selected shared release and client adapter. Presence is not
treated as behavioural proof.

The Harness learning loop is separate from health: it stores minimal project-local
behavioural signals, analyses them from the last approved local retrospective cursor,
and proposes—not automatically applies—improvements. Its common protocol is client
neutral; client lifecycle hooks are optional adapter features. See [Harness](harness.md).

## Environment contract

`detect` is read-only and returns one of `windows`, `wsl`, `linux`, or `unknown`.
Python is mandatory everywhere. Bash is the standard workflow shell and is permitted
only after the detector finds an executable; on Windows this includes a Git Bash
installation when present. On Windows, a runnable Git Bash is preferred over the
WindowsApps `bash.exe` WSL launcher, so a missing or broken WSL distribution cannot
shadow the selected shell. PowerShell is not a Fabric workflow dependency. A project
profile may declare Python or Bash commands, but may not request Bash where it is not
available.

## Agent-client contract

The runtime identifies the agent client independently of the operating system. A
project binding chooses the client and pins a Fabric release; repository-local markers
are only an optional discovery signal before a project is bound. Supported concrete
adapters are `codex`, `copilot`, and `claude`. A generic `.github` directory is not a
Copilot signal; detection requires a Copilot instruction or agent location.

```text
global client bootstrap -> read-only project status -> read-only project context -> pinned release contracts + project overlay -> task package
```

No binding means Fabric is merely available: the bootstrap reports `unbound` and does
not write files. Multiple local client signals are ambiguous during discovery, so
initialization requires an explicit `--client` choice. User-level client adapters are
an explicit installation mode with their own manifest, ownership record, preview,
rollback, and uninstall. They may use a declared link, import, or wrapper. Project
configuration remains solely under `.agent-fabric`.

A hook is also adapter-owned rather than a global assumption. The release defines safe
event semantics; the selected adapter may implement a compatible client hook only when
the client exposes that lifecycle point. Unsupported clients retain the launcher-based
workflow and must not claim automatic event capture.
