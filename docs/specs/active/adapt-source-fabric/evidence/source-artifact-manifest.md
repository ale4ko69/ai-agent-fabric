# Source artifact manifest

This manifest is the artifact-level companion to the migration register. Generated
runtime data, caches, logs, and database snapshots are identified separately so they
cannot be mistaken for a portable source mechanism.

## Root documents

| Source artifact | Purpose | Disposition | Portable destination |
|---|---|---|---|
| Architecture document | authority boundaries and flow model | adapt | architecture + capability model |
| Plan/source-of-truth document | migration history and decisions | adapt | task spec/plan and migration register |
| Handoff document | resume and continuity guidance | adapt | session-state + resume protocol |
| Client instruction document | client-specific bootstrap | adapter | selected client renderer |
| Installer script | installation and recovery behaviour | split | project-local installer + archive of global actions |
| Development workflow | full lifecycle and operating rules | adapt | migration register plus 267-occurrence audit |

## Source configuration families

| Source configuration family | Artifact count | Disposition | Portable destination |
|---|---:|---|---|
| Editor baseline | 1 | profile | target repository editor policy |
| Backup command/configuration pair | 3 | pack | optional backup/recovery pack |
| Global shell startup templates | 2 | archive | intentionally excluded from project-local Fabric |
| Client configuration and instruction artifacts | 2 | adapter | selected client renderer |
| Dependency and formatting configuration | 4 | profile | target build/format policy |
| Design-tool configuration and secret template | 3 | pack | UI/UX integration pack; secret entry remains local |
| Version-control template | 1 | profile | target VCS policy |
| Work-tracking configuration pairs | 4 | adapter | optional work-tracking adapter |
| Runtime launch configuration pairs | 4 | profile | target runtime-service profile |
| External-tool configuration template | 1 | adapter | selected external-tool adapter |
| Process-manager configuration | 1 | profile | target runtime profile |
| IDE code-style configuration | 1 | profile | target repository editor policy |
| Post-merge hook | 1 | profile | opt-in target repository hook |

## Agents, contracts, and skills

| Source family | Artifact count | Disposition | Destination |
|---|---:|---|---|
| Coordinator, exploration, planning, implementation, review roles | 5 role files | adapt | Socrates, Aristotle, Plato, Heracles, Athena profiles |
| Validation role | 1 role file | adapt | permanent Euclid profile; activation through project capability |
| Domain-analysis role | 1 role file | merge | Aristotle exploration mode |
| Documentation, UI/UX, UI-verification roles | 3 role files | pack | corresponding optional packs |
| Knowledge-research role | 1 role file | pack | knowledge-publication pack |
| Role-specific delegation contracts | 9 contracts plus common readme | adapt | common schema plus profile-specific policy |
| Orchestration/exploration/planning/development/review skills | 5 skills | adapt | core profiles and gate semantics |
| Domain-analysis skill | 1 skill | merge | Aristotle evidence mode |
| Validation/UI/UX/UI-test skills | 3 skills | pack | project-enabled specialist packs |
| Signal-mode skill | 1 skill | adapt | client-neutral communication policy |

## Memory and migration tools

| Source artifact | Purpose | Disposition | Portable destination |
|---|---|---|---|
| Memory command tool: session lifecycle | create, update, and inspect durable work sessions | adapt | global `memory start-session`; task lifecycle remains the source of closure |
| Memory command tool: facts | decisions, findings, artifacts, review observations, failures, proposals, and todos | adapt | global `memory record` with a safe `kind` and non-secret evidence object |
| Memory command tool: delegation | queue requests, record specialist results, and atomically acknowledge them | adapt | global request/result commands backed by the local outbox |
| Memory command tool: recovery | reconstruct one session after an interrupted run | adapt | global `memory restore` plus task `restore` |
| Memory command tool: list, search, and recurrence scan | cross-session browsing and historical pattern lookup | defer | a future local search capability; do not copy the source query interface before its project-memory contract is designed |
| Tool registry | least-privilege mapping | adapt | capability and role-policy schema |
| Memory schema document and initialization SQL | storage model | adapt | versioned local database schema |
| Identifier normalization migration | repairs historical task identity | adapt | versioned migration framework, if schema retains equivalent field |
| Case-restoration migration | repairs historical identity formatting | profile/archive | only if target identity rules require it |
| History archive migration | retention/size control | adapt | recoverable archive policy |
| Search-index backfill migration | historical search repair | adapt | optional full-text capability migration |
| Semantic/user/project memory Markdown | accumulated source facts | profile/archive | no direct copy; target profile begins empty and project-scoped |
| Database files and backups | runtime state | archive | never copied; new project initializes its own state |

## Gates and harness

| Source artifact family | Artifact count | Disposition | Portable destination |
|---|---:|---|---|
| Task/session-state creation | 1 script | adapt | task package creator |
| Intake, branch, discovery, data evidence, plan freshness, checkpoint, close-out gates | 8 scripts | adapt | declarative core gates + profile predicates |
| Runtime-change and repository/tracker gates | 5 scripts | split | profile and adapter predicates |
| Gate-registry and orchestrator assertions | 2 scripts | adapt | gate/contract conformance checks |
| Legacy-client-command prohibition | 1 script | archive | capability/adapter policy supersedes it |
| Writer functions and checkpoint log | 2 scripts | adapt | Bash gate library and trace writer |
| Resume and automatic checkpoint | 2 scripts | adapt | local resume/checkpoint harness |
| Health report and schedule example | 2 artifacts | split | core diagnostic + optional scheduler profile |
| Shared-component matrix/synchronizer | 2 artifacts | profile | multi-repository profile only |
| Client hook extension | 2 artifacts | adapter | selected-client event adapter |
| Gate tests | 2 test artifacts | archive as evidence | re-author only in final validation phase |
| Harness logs | 3 data files | archive | never migrate runtime logs |

## Client commands and bootstrap

| Source artifact family | Artifact count | Disposition | Portable destination |
|---|---:|---|---|
| Orchestration/start/restore commands | 4 skill artifacts | core + adapter | portable entry/restore protocol; selected client command renderer |
| Harness optimisation command | 1 skill | core | project-local retrospective protocol |
| Environment-bound operational commands | 4 artifacts | archive | excluded from AI Agent Fabric |
| Auto-loaded bootstrap instruction | 1 artifact | adapter | selected client bootstrap renderer |

## Follow-up reconciliation: implementation evidence

The classifications above are source-audit decisions, not proof of target delivery.
The following comparison was added after an attempted Harness invocation exposed a
gap between documented protocol and callable client surface.

| Portable source mechanism | Actual target evidence | Status |
|---|---|---|
| Global client bootstrap with reversible installation | Release installation, client enablement, rollback, and uninstall commands | implemented for the declared client adapters |
| Project-local task package and approval gate | Task-package creator, readiness check, approval, and archive commands | implemented |
| Local memory and Harness backend | Memory API plus local trace, checkpoint, signal, resume snapshot, and retrospective commands | implemented backend; target project must be bound before stateful use |
| Single task-entry router | Global `work` command routes a bound project to restore, start, or explicit selection without creating state | implemented; native client rendering remains separate |
| New-task command | Global `start` previews a task package and creates it only with explicit `--apply` | implemented; native client rendering remains separate |
| Focused restore command | Global `restore` and local resume snapshot return one task's durable context without project execution | implemented; native client rendering remains separate |
| Harness retrospective command | Global `harness review` returns bounded evidence for Kepler and human review | implemented; native client rendering remains separate |
| Alias command | No duplicate core workflow; aliases remain intentionally deferred until a client declares a verified native alias mechanism | deferred by adapter boundary |

| Durable memory command surface | Global `memory` commands now expose local session creation, non-secret records, bounded delegation hand-off/result acknowledgement, pending queues, and read-only restore | implemented; all writes require a bound project |

No item in this table authorizes a source copy. Missing rows require a portable design
and selected-client lifecycle before implementation; source-bound commands and data
remain excluded by the baseline transfer filter.

## Excluded generated data

The manifest explicitly excludes bytecode caches, logs, live databases, database
backups, and other generated runtime state. They are retained in the source repository
as evidence but do not become Fabric source or project-profile data.
