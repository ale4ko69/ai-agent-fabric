# Plan: adapt the established Fabric

## Architecture

The portable Fabric has five separable layers:

```text
Portable core
  ├─ contracts, memory, declarative gates, harness, task lifecycle
  ├─ capability model and machine-readable agent profiles
  └─ Bash/Python runtime helpers, after capability resolution
        ↓
Target project profile
  ├─ repository facts, commands, tests, integrations, secret destinations
        ↓
Readable documentation
  └─ generated or validated companion to a machine-readable profile
        ↓
Selected client adapter
  └─ explicit user-level bootstrap plus project-local binding and overlay
```

The task package is the durable work record. Remote trackers may mirror a package but
do not replace it. A specialist produces a structured result into a durable local
outbox. The orchestrator atomically acknowledges it, persists the corresponding memory
record, and then records the task-state transition. Recovery retries an unacknowledged
outbox entry by idempotency key.

## Ordered steps

### 1. Build the complete migration register

- Inventory every source workflow rule, contract, skill, memory command, gate,
  installer action, and harness check.
- Record source location, purpose, inputs, outputs, side effects, host assumptions,
  target dependencies, classification, target destination, and validation evidence.
- Include agent roles, contracts, skills, workflow rules, memory tables and commands,
  schema migrations and retention, gates, harness/checkpoint/resume controls,
  installer actions and backups, and extensions.
- Search and account for every environment binding before it can be adapted.

**Deliverables:** `docs/migration-register.md`, later a validated machine-readable
register under `schemas/`.

### 2. Define capability, profile, and gate data before execution

- Define a schema-validated machine-readable profile as the canonical definition of
  every adopted agent. Its readable Markdown profile is generated from, or validated
  against, that data; no adapter owns role semantics.
- Define a capability model for executable Bash, Python, Git, host kind, selected
  client, filesystem, tracker, and optional automation tools.
- Define declarative gate types, evidence types, state transitions, and profile-bound
  predicates. Client adapters may render a gate but cannot change its logic.
- Fix Validation's status: it has a permanent canonical profile but is activated only
  when the target project enables its validation capability.

**Validation:** documentation and renderers can be checked for schema conformance only
after all planned transfer work is complete; no tests run during this phase.

### 3. Define reusable core contracts and memory hand-off

- Adapt delegation request/result envelopes and retry semantics.
- Extend project-local memory with durable sessions, decisions, artifacts, findings,
  review/validation evidence, recovery, search, and archive semantics.
- Produce a comparison table for source and target memory semantics: writer, timing,
  idempotency key, retry behaviour, recovery source, and retention.
- Implement or specify a durable specialist outbox and orchestrator acknowledgement
  protocol before replacing any direct memory write.
- Adapt generic evidence gates: intake, discovery, plan freshness, scope,
  implementation, review, validation, close-out, and resume.
- Implement portable Bash gates with Python for structured state.

**Constraint:** executable Bash/Python gate work starts only after the capability and
declarative-gate models from Step 2 are accepted. All tests remain deferred to the
final validation gate.

### 4. Consolidate agent profiles

- Create `docs/agents/README.md` as a minimal index.
- Create seven profiles: Socrates, Aristotle, Plato, Kepler, Heracles, Athena, and
  Euclid. Each contains role, authority, allowed capabilities, inputs/outputs,
  lifecycle, model policy, and source migration notes.
- Merge source domain analysis into Aristotle's exploration modes.
- Keep documentation, UI/UX, UI verification, validation extensions, and knowledge
  publication as configuration-gated packs.
- Once all profile facts are migrated and references are clean, remove the temporary
  catalogue, persona table, and standalone opponent document.

**Constraint:** each role has one authoritative machine-readable definition; readable
profiles and adapters derive from the same data. No tests run at this point.

### 5. Adapt task workflow and tracker boundary

- Complete the planned-task state machine: specification, research, plan, opponent
  verdict, approval, tasks, evidence, session state, and archive.
- Preserve lightweight handling for a known small bug.
- Add optional tracker synchronisation only through configured provider adapters.

**Validation:** a task package validates locally whether the tracker is configured or
not.

### 6. Adapt harness, detection, and project-local installation

- Port diagnostics, trace, safety checks, and resume entry points.
- Probe executable Bash, Python, Git, host, and client before generating commands.
- Render only selected-client artifacts under the target repository.
- Add hidden-prompt secret setup, preview, idempotency, backup, and restore.

**Deferred final validation:** after all agreed transfer work is complete, run the same
profile under Windows with Git Bash, WSL, and Linux and verify no installer output
escapes the chosen target root. No executable test or environment-matrix run occurs
before the single final validation gate.

### 7. Optional packs and controlled cleanup

- Add tracker adapters and capability packs only after each has a declared project
  profile and tests.
- Archive or remove only duplicates with a named canonical replacement, a reference
  search with no consumers, and recovery evidence.

## Risks and controls

| Risk | Control |
|---|---|
| Useful source behaviour is lost | Migration register requires a disposition for every item. |
| Core becomes tied to a host | Capability probing and profile resolution precede command generation. |
| Agent rules diverge across clients | One profile data source, client-specific rendering only. |
| Kepler expands scope | Scope-lock plus explicit human spec-amendment path. |
| Documentation duplicates again | One profile per agent and removal only after reference audit. |

## Approval gate

Kepler challenged revision 0 and revision 1. Revision 2 must include a complete,
source-linked register with per-binding environment dispositions before it receives a
fresh independent verdict. That review returned `advice`: implementation may transfer
only mechanisms already classified as portable and not explicitly deferred. Every
transfer remains subject to a targeted Kepler review, must retain its migration-register
link, and cannot choose a destination for a deferred source mechanism. Kepler may
challenge or block the plan but cannot add work outside the spec.
