# Individual source-mechanism disposition register

This is the required per-mechanism decision ledger for the initial source audit.
The IDs preserve the reviewed inventory without carrying source workspace names,
absolute paths, credentials, provider identities, or operational topology into this
repository. `Adapt` means a portable behaviour is deliberately redesigned here;
`Optional` means a project may explicitly enable a future pack; `Exclude` means the
mechanism is not part of AI Agent Fabric; `Defer` is a portable idea with no approved
contract yet.

## Root and installation units

| ID | Reviewed mechanism | Decision | Target outcome |
|---|---|---|---|
| R01 | Source ignore policy | Adapt | target ignore policy only |
| R02 | Architecture narrative | Adapt | architecture and authority boundaries |
| R03 | Operational plan history | Adapt | task spec, plan, and evidence lifecycle |
| R04 | Handoff notes | Adapt | restore and session-memory protocol |
| R05 | Client bootstrap text | Adapt | selected client adapter bootstrap |
| R06 | Machine installer shell script | Split | global distribution lifecycle; source-side setup excluded |

## Configuration units

The source configuration scan covered all 28 files without copying their values. It
found 13 files with secret-bearing field names, 9 with absolute-path markers, and 13
with source-context markers. Therefore no configuration file is copied verbatim:
even `Optional` entries are redesigned as an empty project-owned profile or template,
and secret values may enter only through the hidden project-local prompt.

| ID | Reviewed mechanism | Decision | Target outcome |
|---|---|---|---|
| C01 | Generic editor baseline | Optional | project editor policy |
| C02 | Backup launcher template | Optional | recovery pack only |
| C03 | Backup configuration | Optional | recovery pack only |
| C04 | Backup configuration example | Optional | recovery pack documentation |
| C05 | Shell alias template | Exclude | no global shell mutation |
| C06 | Shell startup template | Exclude | no global shell mutation |
| C07 | Client configuration example | Adapt | client-adapter manifest, never copied settings |
| C08 | Client instruction text | Adapt | generated global bootstrap |
| C09 | Dependency list | Optional | project-owned dependency profile |
| C10 | Formatting ignore policy | Optional | project formatting profile |
| C11 | Formatting executable policy | Optional | project formatting profile |
| C12 | Formatting data policy | Optional | project formatting profile |
| C13 | Design-tool local configuration | Optional | explicit UI integration pack |
| C14 | Design-tool configuration example | Optional | explicit UI integration pack |
| C15 | Design-tool secret example | Optional | hidden project-local secret entry only |
| C16 | Version-control template | Optional | project VCS profile |
| C17 | External work-item configuration | Exclude | provider configuration belongs to a project integration, never the core |
| C18 | External work-item configuration example | Exclude | provider configuration belongs to a project integration, never the core |
| C19 | Runtime launch configuration A | Exclude | project runtime profile only |
| C20 | Runtime launch template A | Exclude | project runtime profile only |
| C21 | Runtime launch configuration B | Exclude | project runtime profile only |
| C22 | Runtime launch template B | Exclude | project runtime profile only |
| C23 | External tool configuration example | Optional | explicit project tool adapter |
| C24 | Process manager configuration | Optional | project runtime profile |
| C25 | External command-line integration configuration | Exclude | provider configuration belongs to a project integration |
| C26 | External command-line integration example | Exclude | provider configuration belongs to a project integration |
| C27 | IDE code-style policy | Optional | project editor policy |
| C28 | Post-update repository hook | Optional | explicit project hook with ownership and removal |

## Agent, contract, and skill units

| IDs | Reviewed mechanisms | Decision | Target outcome |
|---|---|---|---|
| A01 | Coordination role | Adapt | Socrates |
| A02 | Exploration role | Adapt | Aristotle |
| A03 | Planning role | Adapt | Plato |
| A04 | Implementation role | Adapt | Heracles |
| A05 | Independent review role | Adapt | Athena |
| A06 | Validation role | Adapt | Euclid, capability-controlled |
| A07 | Domain-analysis role | Merge | Aristotle evidence mode |
| A08 | Documentation role | Optional | documentation pack |
| A09 | Interface-design role | Optional | UI pack |
| A10 | Interface-verification role | Optional | UI validation pack |
| A11 | Knowledge-publication role | Optional | knowledge pack |
| K01-K06 | Core-role delegation contracts | Adapt | common request/result schemas plus role profiles |
| K07 | Domain-analysis contract | Merge | Aristotle evidence mode |
| K08-K10 | Optional specialist contracts | Optional | corresponding enabled packs |
| S01 | Code-review practice | Adapt | Athena acceptance-evidence policy |
| S02 | Development workflow practice | Adapt | task/spec/plan/gate lifecycle |
| S03 | Domain-analysis practice | Merge | Aristotle evidence mode |
| S04 | Exploration practice | Adapt | evidence-first discovery |
| S05 | Orchestration practice | Adapt | Socrates workflow |
| S06 | Planning practice | Adapt | Plato workflow |
| S07 | Communication-signal practice | Adapt | client-neutral status policy |
| S08 | Interface testing practice | Optional | UI validation pack |
| S09 | Interface design practice | Optional | UI pack |
| S10 | Schema validation practice | Adapt | Euclid capability pack |

## Command-skill units

| ID | Reviewed mechanism | Decision | Target outcome |
|---|---|---|---|
| Q01 | Task entry router | Adapt | global `work` command and skill |
| Q02 | Orchestration alias | Defer | no alias until a client exposes a verified native alias surface |
| Q03 | Recovery command | Adapt | global `restore` command and skill |
| Q04 | Task-start command | Adapt | global `start` command and skill |
| Q05 | Harness retrospective command | Adapt | global `harness review` and skill |
| Q06 | Shared publication command | Exclude | source-specific release operation |
| Q07 | Shared publication launcher | Exclude | source-specific release operation |
| Q08 | Cross-repository change command | Exclude | source-specific multi-repository operation |
| Q09 | Cross-repository launcher | Exclude | source-specific multi-repository operation |

## Memory and migration units

| ID | Reviewed mechanism | Decision | Target outcome |
|---|---|---|---|
| M01 | Durable memory command interface | Adapt | global `memory` CLI backed by project-local SQLite |
| M02 | Identity-normalization migration | Defer | only if a future target schema needs it |
| M03 | Identity-format restoration migration | Exclude | historic source repair, not a target requirement |
| M04 | History-retention migration | Adapt | recoverable project-local retention policy |
| M05 | Full-text index backfill | Defer | requires an approved local-search contract |
| M06 | Tool authority registry | Adapt | role capabilities and schemas |

## Gate, trace, and Harness units

| ID | Reviewed mechanism | Decision | Target outcome |
|---|---|---|---|
| G01 | Automatic checkpoint writer | Adapt | explicit local Harness checkpoint |
| G02 | Development-flow trace writer | Adapt | local Harness trace |
| G03 | Scheduled health configuration | Optional | scheduler pack, never implicit |
| G04 | Health diagnostic | Adapt | Harness health report |
| G05 | Client event extension | Defer | selected-client hook adapter only |
| G06 | Client event extension guide | Defer | selected-client hook adapter only |
| G07 | New-session state materializer | Adapt | task package creation and session start |
| G08 | Gate framework guide | Adapt | declarative gate policy |
| G09 | Resume shell helper | Adapt | global `restore` and `memory restore` |
| G10 | Shared-component map | Exclude | source-specific multi-repository data |
| G11 | Shared-component synchronizer | Exclude | source-specific multi-repository operation |
| G12 | Harness safeguard test | Preserve as evidence | re-author only for final target validation |
| G13 | Trace writer test | Preserve as evidence | re-author only for final target validation |
| G14 | Runtime-change verification | Optional | project runtime profile |
| G15 | Branch-bootstrap verification | Optional | project VCS profile |
| G16 | Branch-created verification | Optional | project VCS profile |
| G17 | Checkpoint-consistency verification | Adapt | Harness checkpoint contract |
| G18 | Memory-evidence verification | Adapt | local memory contract |
| G19 | Discovery-complete verification | Adapt | planned-task readiness gate |
| G20 | Gate-registry verification | Adapt | core gate schema check |
| G21 | External-provider open-state verification | Exclude | provider integration only |
| G22 | External-provider transition verification | Exclude | provider integration only |
| G23 | New-task verification | Adapt | start/task-package contract |
| G24 | Legacy client prohibition | Exclude | replaced by adapter capability declaration |
| G25 | Orchestrator assertion verification | Adapt | Socrates profile/contract check |
| G26 | Plan-freshness verification | Adapt | spec/plan revision gate |
| G27 | Cross-repository publication verification | Exclude | source-specific multi-repository operation |
| G28 | Proposal-evidence verification | Adapt | Kepler and human decision gate |
| G29 | Deferred-message intake verification | Defer | requires a concrete client event contract |
| G30 | Task-close verification | Adapt | archive and close-out gate |
| G31 | Shell writer library | Adapt | Bash helper library only where a portable command needs it |
| G32 | Aggregate verification dispatcher | Defer | final validation runner after the target gate suite is authored |

## Generated or non-source units

| Units | Decision | Reason |
|---|---|---|
| Runtime logs, live databases, backups, bytecode caches, and snapshots | Exclude | evidence only; never migrate data into a new Fabric |
| Source semantic and user-memory notes | Exclude | project-local memory starts empty and may not inherit another environment's facts |

## Audit result

The reviewed portable baseline is limited to: global distribution and stable client
bootstrap; named roles; task/spec/plan lifecycle; local memory; Harness evidence and
retrospective discipline; environment detection; and explicit project-owned profiles.
Everything else is either opt-in per project, deferred pending a concrete contract, or
excluded. This register authorizes no source-file copy.
