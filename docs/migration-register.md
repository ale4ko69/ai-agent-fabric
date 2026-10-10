# Migration register

This is the source-of-truth register for adapting the established Fabric. An entry is
not copied until it has a target classification, a destination, and validation
evidence. Source-specific names, paths, commands, credentials, and network endpoints
are intentionally not repeated here.

Supporting Phase 1 evidence is kept with the task package: the source interface
register, source artifact manifest, and environment-binding audit. Together they
provide the source locations, inputs, outputs, side effects, dependencies, and
occurrence-level audit trail that this concise decision register indexes.

## Classification

| Value | Meaning |
|---|---|
| `core` | Portable behaviour implemented once in this Fabric. |
| `profile` | Behaviour declared by an individual target project. |
| `adapter` | Rendering or integration for a selected AI client or work tracker. |
| `pack` | Optional specialist capability, enabled by a project profile. |
| `archive` | Retained as source evidence; no portable consumer presently exists. |

## Workflow and lifecycle

| ID | Source mechanism | Problem prevented | Class | Portable destination | Status |
|---|---|---|---|---|---|
| W-01 | Start-of-session capability tier | Commands assume unavailable tools | core | environment preflight | queued |
| W-02 | Restore context before acting | Lost work after interruption | core | memory restore + task session state | queued |
| W-03 | Incremental state persistence | End-of-session reconstruction and missing evidence | core | orchestrator memory writer | queued |
| W-04 | Deterministic checkpoint registry | Conversational claims substitute for evidence | core | declarative gate registry and local checkpoint record | implemented; final validation deferred |
| W-05 | Freshness marker for plans | Execution of obsolete plans | core | revision-matched Kepler verdict and human approval gate | implemented; final validation deferred |
| W-06 | Re-check after a state-changing action | Repeating failed action without observing state | core | mutation follow-up gate | queued |
| W-07 | External-artifact preflight | Acting on unavailable or stale inputs | profile | tracker/artifact profile | queued |
| W-08 | Secure credential acquisition | Secrets in command line or logs | core | hidden-prompt secret entry | specified |
| W-09 | Generated-artifact discovery | Editing generated output as source | profile | project build profile | queued |
| W-10 | Task intake and classification | Applying heavyweight flow to trivial work or vice versa | core | task triage and read-only implementation readiness | implemented; final validation deferred |
| W-11 | Branch preparation | Work without an isolated, known base | profile | version-control profile + generic gate | queued |
| W-12 | Research before non-trivial change | Plans based on guesses | core | Aristotle contract + discovery gate | queued |
| W-13 | Data/domain analysis when relevant | UI or data changes without full flow evidence | core | Aristotle exploration mode | queued |
| W-14 | Plan and revision loop | Unreviewed or stale implementation direction | core | Plato plan revision, Kepler verdict, and human approval artifacts | implemented; final validation deferred |
| W-15 | Scope checkpoint during implementation | Silent scope expansion | core | Heracles scope gate | queued |
| W-16 | Independent review | Self-confirmed correctness | core | Athena contract + review gate | queued |
| W-17 | Evidence-based UI verification | Declaring visual behaviour without proof | pack | UI-verification pack | queued |
| W-18 | Publish/change-request step | Untraceable remote change | adapter | selected tracker/repository adapter | queued |
| W-19 | Task closure, archive, cleanup | Orphaned active state and stale queues | core | task close-out/archive gate | queued |
| W-20 | Optional knowledge publication | Automatic publication outside user intent | pack | knowledge-publication pack | queued |
| W-21 | Resume prompt and reorientation | Idle task after restoration | core | resume protocol | queued |

## Durable memory and recovery

| ID | Source mechanism | Class | Portable destination | Status |
|---|---|---|---|---|
| M-01 | Project semantic facts | profile | project profile and curated Markdown | queued |
| M-02 | User preferences | profile | local user-preferences file, opt-in | queued |
| M-03 | Session lifecycle | core | project-local SQLite sessions table and state transitions | implemented; final validation deferred |
| M-04 | Decisions | core | SQLite decision record | queued |
| M-05 | Agent results | core | typed, project-local delegation-result outbox record | implemented; final validation deferred |
| M-06 | Changed artifacts | core | artifact evidence record | queued |
| M-07 | Research findings | core | finding record | queued |
| M-08 | Review findings | core | review record | queued |
| M-09 | Domain/data maps | core | typed exploration finding | queued |
| M-10 | Test/validation evidence | core | validation-evidence record | queued |
| M-11 | Failure and correction proposals | core | failure/proposal record | queued |
| M-12 | Task todos | core | task package and session state | queued |
| M-13 | Restore active context | core | read-only task and memory restore helper | implemented; final validation deferred |
| M-14 | Search across history | core | local search API with safe query handling | queued |
| M-15 | Recurrence detection | core | finding correlation query | queued |
| M-16 | Archive completed history | core | recoverable archive policy | queued |
| M-17 | Sole writer rule | core | orchestrator-only acknowledgement into durable memory | implemented; final validation deferred |
| M-18 | Schema migrations | core | versioned database migration protocol | queued |

## Roles, contracts, and procedural knowledge

| ID | Source mechanism | Class | Portable destination | Status |
|---|---|---|---|---|
| A-01 | Coordinator role | core | `docs/agents/socrates.md` | queued |
| A-02 | Exploration role | core | `docs/agents/aristotle.md` | queued |
| A-03 | Planning role | core | `docs/agents/plato.md` | queued |
| A-04 | Independent opponent role | core | `docs/agents/kepler.md` | specified; review pending |
| A-05 | Implementation role | core | `docs/agents/heracles.md` | queued |
| A-06 | Read-only code review role | core | `docs/agents/athena.md` | queued |
| A-07 | Validation role | core + pack activation | permanent `docs/agents/euclid.md`; tools activate through validation capability | queued |
| A-08 | Domain-analysis role | core | Aristotle mode; no duplicate role | queued |
| A-09 | Documentation-maintenance role | pack | documentation pack | queued |
| A-10 | UI/UX role | pack | UI/UX pack | queued |
| A-11 | UI-testing role | pack | UI-verification pack | queued |
| A-12 | Knowledge-page research role | pack | knowledge-publication pack | queued |
| C-01 | Delegation request envelope | core | shared JSON schema, project-local request queue, and documentation | implemented; final validation deferred |
| C-02 | Delegation result envelope | core | shared JSON schema, project-local result outbox, and documentation | implemented; final validation deferred |
| C-03 | Evidence/artifact/retry requirements | core | contract validation | queued |
| C-04 | Role-specific contracts | core/pack | individual profiles reference common envelope | queued |
| S-01 | Orchestration playbook | core | Socrates profile + gate registry + portable workflow | implemented; final validation deferred |
| S-02 | Exploration playbook | core | Aristotle profile + portable workflow | implemented; final validation deferred |
| S-03 | Planning playbook | core | Plato profile + portable workflow | implemented; final validation deferred |
| S-04 | Development playbook | core | Heracles profile + portable workflow | implemented; final validation deferred |
| S-05 | Review playbook | core | Athena profile + portable workflow | implemented; final validation deferred |
| S-06 | Domain-analysis playbook | core | Aristotle evidence mode | queued |
| S-07 | Validation-schema playbook | pack | validation pack | queued |
| S-08 | UI/UX playbook | pack | UI/UX pack | queued |
| S-09 | UI-test playbook | pack | UI-verification pack | queued |
| S-10 | Signal/minimal-response mode | core | client-neutral interaction policy | queued |

## Gates and harness

| ID | Source mechanism | Class | Portable destination | Status |
|---|---|---|---|---|
| G-01 | New-task preflight | core | intake gate | queued |
| G-02 | Queue intake | profile | optional work-tracking adapter | queued |
| G-03 | Branch bootstrap | profile | version-control profile | queued |
| G-04 | Discovery complete | core | discovery gate | queued |
| G-05 | Data-evidence verification | core | evidence gate with profile predicates | queued |
| G-06 | Plan freshness | core | plan gate | queued |
| G-07 | Proposal evidence | core | decision gate | queued |
| G-08 | Checkpoint consistency | core | state-transition gate | queued |
| G-09 | Post-service-change verification | profile | project runtime profile | queued |
| G-10 | Repository request wiring | adapter | repository-host adapter | queued |
| G-11 | Work-item open/ready check | adapter | optional tracker adapter | queued |
| G-12 | Task close | core | close-out gate | queued |
| G-13 | No forbidden legacy client command | archive | superseded by adapter capability policy | pending confirmation |
| G-14 | Gate registry self-check | core | gate registry validation | implemented; final validation deferred |
| G-15 | Orchestrator assertion audit | core | contract conformance check | queued |
| H-01 | Checkpoint writer functions | core | release-gate validator plus local harness checkpoint | implemented; final validation deferred |
| H-02 | Append-only event trace | core | typed project-local harness trace | implemented; final validation deferred |
| H-03 | Automatic checkpointing | core | harness/session checkpoint helper | queued |
| H-04 | Resume helper | core | project-local resume command | queued |
| H-05 | Health report | core | read-only project-local harness diagnostic | implemented; final validation deferred |
| H-06 | Shared-component synchronisation | profile | multi-repository project profile | queued |
| H-07 | Scheduled health report | profile | optional local scheduler profile | queued |
| H-08 | Behavioural retrospective | core | project-local signal cursor, proposal protocol, Kepler and human gate | implemented; final validation deferred |

## Installer and environment

| ID | Source mechanism | Class | Portable destination | Status |
|---|---|---|---|---|
| I-01 | Reproducible installer | core | versioned user-level release installer plus project binding | implemented; final validation deferred |
| I-02 | Generated-artifact manifest | core | release manifest, installation manifest, and mutation preview | implemented; final validation deferred |
| I-03 | Backup before replacement | core | reversible release, project-binding, and client-adapter backups | implemented; final validation deferred |
| I-04 | Reinstall/update safety | core | immutable releases, ownership records, and explicit project updates | implemented; final validation deferred |
| I-05 | Project registration template | profile | generated target profile skeleton | queued |
| I-06 | Global links/configuration | adapter | explicit reversible user-level bootstrap; project overlay remains local | implemented; final validation deferred |
| E-01 | Executable shell probe | core | Bash capability detection | implemented |
| E-02 | Host classification | core | Windows/WSL/Linux detector | implemented |
| E-03 | Runtime tool probe | core | Bash/Python/Git and concrete client capability probes | implemented; final validation deferred |
| E-04 | Client selection | core | selected-client configuration and concrete surface preflight | implemented; final validation deferred |
| E-05 | Client-specific artifacts | adapter | Codex/Copilot/Claude global bootstrap renderers with verified `ordered`/`combined`/`additive` loading semantics; native hook surfaces remain separately unconfigured | implemented; final validation deferred |
| E-06 | Secret entry | core | selected-release Bash hidden prompt + project-profile declared destination | implemented; final validation deferred |

## Client skill adaptations

The reviewed source CLI skill family is indexed in the task evidence disposition. Its
portable entry, restore, checklist, discovery, and retrospective rules are core
workflow candidates; client command renderers remain adapter-specific. Source-specific
tracker, workspace, calendar, and branch rules are excluded from the core.

## Environment-binding audit

The source workflow has a large number of environment-bound references. They are
enumerated and reviewed one by one in the task evidence file
`docs/specs/active/adapt-source-fabric/evidence/environment-binding-audit.md` before
source commands are adapted. The register records the decision rather than reproducing
sensitive or non-portable values.

| Audit batch | Detection method | Required disposition |
|---|---|---|
| Paths and home locations | static scan of absolute, home-relative, and mount paths | capability probe, target-profile path, or archive |
| Shell and operating-system commands | static scan of shell syntax and platform executables | Bash/Python abstraction or profile command |
| Ports, hosts, and local services | static scan of endpoint-like values | runtime profile only |
| Client settings and global locations | static scan of client directories/configuration | selected client adapter or archive |
| Tracker and watcher calls | static scan of work-item commands | optional work-tracking adapter |
| Cross-repository coupling | static scan of cross-repository references | multi-repository profile or archive |

No source-bound command may enter the portable core until this audit assigns it a
non-source resolution path.

## Completion criteria

An entry becomes `migrated` only after its destination has an implementation or an
approved profile representation, a reference link, and proportionate final validation
evidence. An `archive` entry needs a reason, absence of active consumers, and a
recoverable source location before cleanup can be proposed. No executable tests are
run while this inventory is being assembled.
