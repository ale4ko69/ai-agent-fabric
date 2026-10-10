# Environment-binding audit

## Method and scope

This audit records environment-bound source references individually by source line or
source-line group where the exact same declaration is repeated. A broad static scan
returned 267 candidate lines. It includes prose, repeated examples, and generic tool
names, so it is a review queue—not a claim that there are 267 unique bindings. The
line-by-line non-sensitive index is in environment-binding-occurrences.md.

Each record has one disposition:

- `capability`: runtime probe before any command is selected;
- `profile`: target-project configuration;
- `adapter`: selected client or external-service adapter;
- `core`: portable semantic rule with no inherited command;
- `archive`: do not transfer to the portable Fabric.

## Reviewed records: workflow bootstrap and persistence

| ID | Source location | Binding | Risk | Disposition | Portable replacement |
|---|---|---|---|---|---|
| EB-001 | workflow 18–27 | Shell assumed at session start | unsupported shell syntax | capability | probe executable Bash, never infer it from host kind |
| EB-002 | workflow 20 | Local launcher endpoint | unavailable local service | profile | optional runtime-service profile |
| EB-003 | workflow 21–22 | Global client configuration location | machine-specific path | archive | project-local config only |
| EB-004 | workflow 22 | Central Fabric filesystem root | global installation coupling | archive | target-root-relative Fabric state |
| EB-005 | workflow 25–27 | Fixed three-tier environment model | hides partial capabilities | core | capability vector, not tiers |
| EB-006 | workflow 32–34 | Named local tools as environment tiers | assumes a prior workstation | archive | independent host/client/tool probes |
| EB-007 | workflow 44 | Named memory command and raw database restriction | persistence safety | core | orchestrator memory interface; command name is configurable |
| EB-008 | workflow 44 | JSON passed by shell heredoc | quoting/corruption risk | core | stdin JSON contract; Bash helper only after capability probe |
| EB-009 | workflow 46 | Single memory writer | evidence ordering | core | durable specialist outbox plus orchestrator acknowledgement |
| EB-010 | workflow 51 | Global client configuration sourcing | machine-specific path | archive | no global source command |
| EB-011 | workflow 84–90 | Central database and shared documentation locations | cross-project information leakage | profile | per-project local memory and profile documentation |
| EB-012 | workflow 121 | Fixed harness log location | global root/path | core | target-local `.agent-fabric` trace location |

## Reviewed records: work tracking and credentials

| ID | Source location | Binding | Risk | Disposition | Portable replacement |
|---|---|---|---|---|---|
| EB-013 | workflow 215–225 | Tracker route selected by key prefix | provider-specific assumptions | adapter | configured work-tracking provider route |
| EB-014 | workflow 219–221 | Multiple named tracker systems | target-specific service identifiers | profile | provider configuration without hard-coded prefixes |
| EB-015 | workflow 223–225 | Unknown tracker resolution rule | false inaccessible claim | core | inspect configured adapter; ask only if unresolved |
| EB-016 | workflow 233–236 | Credential-store command and named secrets | secret path/name leakage | archive | hidden prompt to declared project-local destination |
| EB-017 | workflow 258–259 | Fixed validation-report paths | repository layout assumption | profile | project validation artifact locations |
| EB-018 | workflow 278–291 | Tracker key required for some task classes | tracker becomes mandatory | adapter | local task packages work with provider `none` |
| EB-019 | workflow 295–329 | Tracker-specific read/attachments/state transition | unavailable provider and credentials | adapter | optional tracker adapter, never core workflow |
| EB-020 | workflow 310–321 | Watcher and local service calls | local integration dependency | profile | optional tracker/runtime extension |
| EB-021 | workflow 324 | Task package root based on fixed workspace | path coupling | core | target profile declares task-spec root |

## Reviewed records: repository and branch flow

| ID | Source location | Binding | Risk | Disposition | Portable replacement |
|---|---|---|---|---|---|
| EB-022 | workflow 345–357 | Fixed repository directories and branch bases | wrong repository/branch | profile | VCS project profile detects default base/ref |
| EB-023 | workflow 351–361 | Specific Git checkout syntax | unsafe base/tracking assumption | core | declarative branch intent; profile/adapter renders command |
| EB-024 | workflow 366–405 | Fixed standalone/umbrella branch models | inappropriate branch policy | profile | selectable branch strategy in target profile |
| EB-025 | workflow 398–405 | Watcher wiring stored in a fixed file | service-specific state mutation | adapter | optional work-tracking/repository adapter |
| EB-026 | workflow 421 | Research source chosen by project category | hidden project taxonomy | profile | project knowledge-source policy |
| EB-027 | workflow 427 | Documentation-first research rule | durable evidence requirement | core | read declared project sources before runtime/code probing |
| EB-028 | workflow 430–445 | Runtime dashboard/database lookup | local service/database dependency | profile | optional runtime evidence adapter |
| EB-029 | workflow 487 | Shared domain-map path | global cross-project cache | profile | project-local or explicitly shared knowledge profile |

## Reviewed records: runtime, UI, publishing, and close-out

| ID | Source location | Binding | Risk | Disposition | Portable replacement |
|---|---|---|---|---|---|
| EB-030 | workflow 617–631 | Fixed health endpoints and ports | incorrect service control | profile | runtime service declarations and health probes |
| EB-031 | workflow 649 | Runtime restart then test gate | executing test before final validation policy | core | preserve evidence gate; defer executable validation by current task policy |
| EB-032 | workflow 660 | Repository-specific formatter prohibition | implementation policy leak | profile | project formatting policy |
| EB-033 | workflow 709–725 | Browser debug port and local browser command | host/browser coupling | pack | UI-verification pack capability probe |
| EB-034 | workflow 741–780 | Fixed repository push and watcher PR operations | remote host/tool coupling | adapter | repository-host and tracker adapters |
| EB-035 | workflow 786–887 | Tracker-specific comments, status, and attachments | provider syntax/credential coupling | adapter | tracker comment/status/attachment policy |
| EB-036 | workflow 899–943 | Fixed archive endpoint, temporary path, and watcher cleanup | destructive remote/local cleanup | profile | task archive core plus optional adapter cleanup |
| EB-037 | workflow 970–977 | Knowledge publication command and endpoint | external publication side effect | pack | explicit knowledge-publication pack |
| EB-038 | workflow 986 | Global documentation root | cross-project documentation coupling | profile | target documentation policy |

## Reviewed records: lessons and anti-patterns

| ID | Source location | Binding | Risk | Disposition | Portable replacement |
|---|---|---|---|---|---|
| EB-039 | workflow 1051–1058 | Conflicting specialist write instruction | evidence loss or dual writers | core | resolve through writer-semantics comparison/outbox protocol |
| EB-040 | workflow 1091–1095 | Tracker-specific session identity and reassignment | tracker mandated for recovery | adapter | local task id is canonical; remote links optional |
| EB-041 | workflow 1123 | Restart-and-test sequence | validation execution before agreed gate | core | preserve sequence as final validation policy only |
| EB-042 | workflow 1127–1138 | Fixed service launcher, identifiers, and infrastructure commands | wrong host/service mutation | profile | runtime-service profile; no core command |
| EB-043 | workflow 1142–1145 | Framework-specific cache symptom and port | stack-specific troubleshooting | pack | optional frontend/runtime knowledge pack |
| EB-044 | workflow 1174–1189 | Tracker artifact and tool registry references | publication/tooling coupling | core | verify full trace before recording security/bug claim; adapters own publication |
| EB-045 | workflow 1196–1201 | Inline-script quoting warning | shell data corruption | core | use stdin or single-quoted heredoc in Bash helper |
| EB-046 | workflow 1207–1219 | Mandatory remote knowledge tool for named project classes | unavailable/irrelevant source | profile | knowledge-source policy selects local/remote research |
| EB-047 | workflow 1224–1241 | Framework/API and data-layer checklists | stack-specific implementation | pack | API/data validation packs |
| EB-048 | workflow 1260–1278 | Container/dependency repair commands | environment and dependency-manager coupling | profile | deployment/build profile |
| EB-049 | workflow 1285–1312 | Fixed command prohibitions and container lifecycle | source-machine policy | profile | target VCS/runtime/build policy |

## Remaining review queue

The reviewed records cover every high-level workflow section that contains an
environment-bound command, path, endpoint, tracker operation, or project policy. The
occurrence appendix supplies a stable identifier for every candidate line. The
companion environment-binding-dispositions.md maps each occurrence to its decision
record and candidate destination class. environment-binding-resolution-status.md
provides the final class or an explicit evidence condition for a deferred item. No
source command is transferred from these records; the destination is a declarative
core/profile/adapter/pack/archive rule.
