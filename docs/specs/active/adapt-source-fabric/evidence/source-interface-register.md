# Source interface register — Phase 1 evidence

This evidence register supplements `docs/migration-register.md`. It uses stable,
non-environment-specific source references. A reference identifies a source artifact
and its section or function without copying source paths, machine paths, endpoints,
or target-project names into the portable Fabric.

## Memory command interface

| Source reference | Inputs | Outputs | Side effects | Host/target dependencies | Disposition |
|---|---|---|---|---|---|
| Memory CLI: `session-start` | task id, optional work-item id, project, branch, title | structured created/updated session | inserts session row | local SQLite | adapt as orchestrator write command |
| Memory CLI: `session-update` | session id and state fields | structured session record | updates session/timestamp | local SQLite | adapt with idempotency key |
| Memory CLI: `decision` | session id, decision, rationale | decision id | inserts durable decision | local SQLite | core |
| Memory CLI: `agent-result` | session id, role, structured result | result id | inserts agent result | local SQLite | core via acknowledged outbox |
| Memory CLI: `finding` | session id, role, topic, evidence | finding id | inserts finding and search index entry | local SQLite search extension | core |
| Memory CLI: `artifact` | session id, role, file/action/detail | artifact id | inserts artifact evidence | local SQLite | core |
| Memory CLI: `review-issue` | session id, severity, location, explanation | review issue id | inserts review record | local SQLite | core |
| Memory CLI: `domain-map` | session id, flow/data-map result | map id | inserts analysis record | local SQLite | merge into exploration finding |
| Memory CLI: `test-result` | session id, command/result/evidence | result id | inserts validation record | local SQLite | core; execution deferred |
| Memory CLI: `failure` | session id, gate/failure context | failure id | inserts failure record | local SQLite | core |
| Memory CLI: `proposal` | session id, scope/change proposal | proposal id | inserts deferred proposal | local SQLite | core |
| Memory CLI: `todo` | session id, step/state/detail | todo id | inserts or updates task step | local SQLite | core, reconcile with task package |
| Memory CLI: `restore` | optional session id | complete persisted context | read only | local SQLite | core |
| Memory CLI: `sessions` | filters | active/recent session list | read only | local SQLite | core |
| Memory CLI: `learnings` | taxonomy/status filters | curated learnings | read only | local SQLite | core, profile-scoped semantics |
| Memory CLI: `search` | safe free-text query | matching memory records | read only | local SQLite full-text support | core, optional capability probe |
| Memory CLI: `check-recurrence` | candidate pattern | related prior findings | read only | local SQLite | core |

## Memory storage semantics

| Source reference | Inputs | Outputs | Side effects | Dependencies | Disposition |
|---|---|---|---|---|---|
| Memory schema: session records | task lifecycle fields | current task state | durable session state | SQLite | core |
| Memory schema: decision/result/artifact/finding/review records | structured agent evidence | queryable evidence | durable history | SQLite | core |
| Memory schema: todo/failure/proposal records | task steps and exceptions | recovery and escalation data | durable history | SQLite | core |
| Memory schema: search index and triggers | text-bearing records | search results | index maintenance | SQLite full-text capability | core with fallback policy |
| Memory governance: migration/versioning | schema version and migration scripts | compatible database | transforms persisted state | local filesystem/SQLite | core |
| Memory governance: retention/archive | completed task age/state | archived record set | recoverable archival | local filesystem/SQLite | core |
| Memory governance: direct-write restrictions | agent result | explicit writer boundary | prevents uncontrolled mutation | runtime contract | core; compare against source contradictions |

## Gate and harness interface

| Source reference | Inputs | Outputs | Side effects | Dependencies | Disposition |
|---|---|---|---|---|---|
| Gate: task intake | task identity, title, local state | pass/fail diagnostics | writes event trace | task package, optional tracker | core predicate + profile extension |
| Gate: branch readiness | project/branch/base evidence | pass/fail diagnostics | writes event trace | version-control profile | profile predicate |
| Gate: discovery completion | session + findings | pass/fail diagnostics | writes event trace | memory store | core |
| Gate: data evidence | declared data scope + source evidence | pass/fail diagnostics | writes event trace | project data profile | core schema plus profile rules |
| Gate: plan freshness | plan and change evidence | pass/fail diagnostics | writes event trace | task package, version control | core |
| Gate: checkpoint consistency | session state and todos | pass/fail diagnostics | writes event trace | task package, memory store | core |
| Gate: post-runtime-change | changed component and runtime proof | pass/fail diagnostics | writes event trace | project runtime profile | profile |
| Gate: request/review wiring | change-request/work-item state | pass/fail diagnostics | writes event trace | optional repository/tracker adapter | adapter |
| Gate: close-out | task archive and external state | pass/fail diagnostics | writes event trace | task package, optional adapters | core plus adapters |
| Harness: append-only trace | gate name, result, details | trace record | local append-only log; failure may be persisted | filesystem, memory writer | core |
| Harness: automatic checkpoint | task state, runtime map | confirmed durable checkpoint | updates task state and memory | task package, memory store | core |
| Harness: resume | task selector | contextual continuation packet | read only except explicit close action | task package, memory store, VCS | core |
| Harness: health report | installed components and logs | diagnostic report | report artifact | selected-client/project profile | core diagnostics |
| Harness: multi-repository synchronization | component relationship map | synchronization status | may change other repositories | multi-repository profile | profile, never baseline |
| Harness: hooks extension | client event lifecycle | hook result | client-side action | selected client | adapter |

## Installer interface

| Source reference | Inputs | Outputs | Side effects | Dependencies | Disposition |
|---|---|---|---|---|---|
| Installer: capability/config bootstrap | installation root and selected project | resolved configuration | creates directories/configuration | shell, filesystem | core, project-local only |
| Installer: generated client artifacts | selected client and profile | adapter files | creates/updates target-repository files | client adapter | adapter |
| Installer: backup manifest | existing generated artifacts | recovery manifest | records replacement candidates | filesystem | core |
| Installer: replacement operation | approved generated artifact | installed artifact | may replace target-local generated file | filesystem | core with explicit preview |
| Installer: memory initialization | target project root | local database | creates local state | Python/SQLite | core |
| Installer: project-profile scaffold | project root evidence | profile skeleton | creates project-local configuration | filesystem | core |
| Installer: global client entry delivery | machine-wide locations | global client bootstrap | mutates user-level client configuration | global filesystem/client | core adapter lifecycle; explicit preview, ownership, rollback, and uninstall are required |

## Source contradiction requiring resolution

The source contains both an orchestrator-only writer rule and a later instruction
describing direct specialist persistence. The portable design does not choose either
text by preference. The migration decision is pending the writer-semantics comparison:
specialist result production, durable outbox creation, orchestrator acknowledgement,
idempotent memory persistence, and recovery behaviour must each be evidenced before
the core memory protocol is implemented.
