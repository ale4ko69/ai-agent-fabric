# Memory boundary and recovery protocol

AI Agent Fabric has no cross-project episodic memory. The global release carries the
memory *protocol*—the SQLite schema, outbox contract, role authority, recovery rules,
and validation—but not project facts.

## Storage boundary

| Scope | Stored here | Never stored here |
|---|---|---|
| Versioned user-level Fabric release | Memory code, schema, contracts, agent roles | Project sessions, prompts, tracker data, task evidence, credentials |
| Project `.agent-fabric/` | `memory.db`, harness trace, binding, local configuration | Another project's facts or memory database |
| Task package | Spec, research, plan, review, evidence, session state | Secrets or global user preferences |

`installation.json` and adapter ownership records are release-management metadata only.
They are not a knowledge store and must not become one.

## Sessions and agents

Each project has one local SQLite database, shared across its task sessions. A session
is not a private global memory for an agent: it is project state with an `actor` field
for provenance. Specialists submit structured, idempotent results to the local outbox;
only Socrates (`orchestrator`) can start sessions, persist records, or acknowledge a
result into durable memory. The acknowledgement record names Socrates as its writer;
the original specialist remains in the structured payload. This gives each later session
of any Fabric role the relevant project context without exposing it to another project.

`memory restore` and `harness resume` are deliberately read-only: they reconstruct
task artifacts, memory records, and unacknowledged results without executing a project
command or querying a tracker or remote service. The task-level `restore` command is
different: it reactivates that task's Socrates session and then returns the same durable
context; it still does not execute project work.

## Guard failures

Concrete failures are stored separately from generic memory records in
`guard_failures` and `guard_outcomes`. Only the Socrates protocol may write them. Each
record carries safe identifiers plus an existing project-relative evidence artifact;
the detail remains in that artifact. Restoring a task returns these records, including
the current retry, block, or escalation outcome. Harness signals remain a separate
identifier-only retrospective input. See [Guards](guards.md).

A Guard failure transaction also creates a pending identifier-only trace event in local
memory. Delivery to `harness/trace.jsonl` is idempotent and is retried by task restore,
so an interruption after durable failure persistence cannot silently lose the audit
event or duplicate it.

## Schema changes

Project onboarding explicitly initializes the local database. A release update applies
the selected release's explicitly declared forward-only memory migration before the
project binding changes; normal reads and writes never create or silently migrate a
database. `harness health` reports one of
`current`, `migration-required`, or `missing` so an agent cannot mistake an old schema
for valid recovery state. If a historic delegation result cannot be safely bound to its
original request, the migration retains it in a project-local quarantine table for a
human review instead of inventing a link or deleting it; `memory quarantine <project>`
is the read-only inspection path. Rolling back a project binding does not downgrade its
local database and is blocked if the older release cannot read the current schema.

## Sensitive data and promotion

Secrets are entered only through the declared hidden-prompt flow and are not memory
inputs. Memory and trace writers reject secret-like field names and common credential
formats; detailed work evidence belongs in project task artifacts.

If a project produces a reusable improvement, it is not copied automatically into a
global memory. A person must first turn it into an anonymized Fabric change, review it
for project facts and secrets, and ship it in a new immutable release. This is how a
good project practice improves the common Fabric without creating cross-project data
leakage.

Harness behavioural signals follow the same boundary. They are project-local pointers
to evidence, not captured chat transcripts; their retrospective cursor is also local to
the project. See [Harness](harness.md).
