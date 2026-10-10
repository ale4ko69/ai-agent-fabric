# Kepler review

**Status:** advice; Phase 1 inventory accepted.

## claim_challenged

1. The plan scheduled Bash gate implementation before a complete capability model.
2. It contained intermediate test checkpoints despite the current instruction not to
   run tests until the design and transfer are complete.
3. It did not name one machine-readable source of agent profile data from which client
   renderers can be derived.
4. It changed the memory writer model without defining a durable hand-off protocol for
   specialist results.

## evidence_gaps_or_conflicts

- The inventory is not yet a complete per-artifact register.
- Validation was described both as a canonical persona and as an optional pack without
  clarifying that its profile is permanent while activation is project-controlled.
- The register must include non-agent mechanisms such as database migrations and
  retention, installer backups, recovery, diagnostics, checkpoints, and extensions.

## risk_and_severity

- Important: a gate implementation before capability modelling can reintroduce a
  host-specific core.
- Important: profile documentation can diverge from client renderers without a
  canonical data source.
- Important: a non-atomic hand-off can lose evidence during interruption.
- Minor: unclear validation activation can confuse project installation.

## safer_alternative_or_needed_evidence

1. Complete only the full migration register before implementation.
2. Define capabilities and declarative gates before Bash/Python execution.
3. Use one schema-validated machine-readable agent profile; Markdown is its readable
   rendering or a validated companion.
4. Compare old and new memory writes by writer, timing, idempotency, retry, recovery,
   and retention; use a durable inbox/outbox or equivalent atomic hand-off if the
   orchestrator remains sole writer.
5. Move all executable tests to the final validation gate.
6. Keep a permanent Validation profile, activated only when the project enables it.

## fresh review of revision 2

The Phase 1 inventory is accepted with `advice`:

- all 267 environment-binding occurrences have one authoritative resolution record;
- each record has a single destination class or an explicit deferred evidence condition
  that prohibits transfer until it is met;
- source configuration artifacts and the workflow are now represented in the manifest;
- the evidence remains within the spec.

Implementation must treat `deferred` as a prohibition, not as permission to choose a
destination later. Aggregated manifest rows are indexes only; a concrete transfer must
link to an occurrence or source-interface decision.

## verdict

`advice`

## Targeted implementation review: client loading, gates, and memory

The opponent reviewed the implemented global/client boundary, immutable gate registry,
custom Fabric-home propagation, trace constraints, and project-local memory protocol.

**Resolved challenges:**

- client manifests no longer claim that Fabric creates native project instruction files;
  the managed project overlay is loaded only through the global bootstrap;
- every manifest declares actual client loading semantics rather than a fictional common
  precedence rule;
- all current project write commands accept the selected Fabric home when they need to
  validate a binding;
- only `orchestrator` may start sessions, persist records, or acknowledge specialist
  results into durable memory;
- checkpoint evidence is exact, trace is identifier-only, and common credential
  formats are rejected before memory or trace persistence.

**Verdict:** `approve` for these bounded transfers. Final runtime and environment
validation remains explicitly deferred under the task spec.

## Targeted implementation review: hooks, retrospective Harness, and recovery

The opponent reviewed the client-owned hook contract, the project-local Harness cursor,
and the forward-only release/memory recovery path without running tests.

**Resolved challenges:**

- hooks are declared as `unsupported` or as a concrete adapter implementation; a real
  implementation must name its supported client version or version range, event set,
  hook point, handler, delivery, ownership record, rollback, and uninstall;
- the initial adapters do not claim automatic hooks they do not implement;
- Harness uses a project-local append-only signal log and byte/digest snapshot from the
  last approved retrospective, not a calendar day; its cursor advances only after
  Kepler evidence and a human decision artifact;
- release updates write an atomic pending journal before forward-only memory migration;
  a pending update makes managed project writes ineligible until explicit repair;
- repair has a read-only preview, can restore only the journal's trusted local backup
  for a torn binding, and rollback stays blocked while recovery is pending.

**Verdict:** `approve` for these bounded transfers. End-to-end and runtime validation
remain deferred to the final validation gate at the user's direction.

## Targeted implementation review: secret-entry lifecycle

The opponent reviewed the release-bound secret prompt transfer without running tests.

**Resolved challenges:**

- the CLI resolves the helper from the integrity-validated release pinned by the bound
  project, not from a mutable source checkout;
- preview is read-only and checks the bound project, local profile, declared secret
  root, and Bash availability before a prompt can be opened;
- Bash owns the hidden terminal prompt; the value is never supplied in an argument,
  configuration, trace, memory record, or log;
- a minimal isolated Python writer receives the value only through an inherited pipe
  descriptor because descriptor-relative `openat`/`O_NOFOLLOW` is required to prevent
  parent-directory symlink races that Bash cannot safely close;
- hosts without those safe descriptor primitives fail closed, and descriptor-relative
  cleanup removes only the newly created destination; writes loop until all bytes are
  persisted.

**Verdict:** `approve` for this bounded transfer. Windows/WSL/Linux runtime behaviour
remains deferred to the single final validation gate.

## Targeted implementation review: project context and Bash migration

The opponent reviewed the read-only project-context boundary and the selected-release
memory-migration launcher without running tests.

**Resolved challenges:**

- context returns only pinned-release contracts and local contract files, never memory,
  task, or secret locations;
- all local context files are resolved and required to remain regular files inside the
  selected project, including through a symlink;
- memory migration uses the independently detected Bash path, so it does not silently
  assume Bash on `PATH` on Windows, WSL, or Linux.

**Verdict:** `approve` for this bounded transfer. Runtime validation remains deferred
to the single final validation gate.

## Broad implementation review: local-state hardening and schema alignment

Kepler reviewed the completed project-state boundary and the contract validators without
running tests.

**Resolved challenges:**

- `.agent-fabric` and each managed child path reject symlinks and path traversal before
  a Fabric write; a project cannot redirect state, memory, task metadata, or config
  outside its own repository through a substituted state directory;
- every release-dependent project operation integrity-validates the selected release;
  client rollback preserves the prior owned artifact and restores it on a failed
  replacement;
- profile integrations use the canonical local work-tracking configuration path that
  the runtime actually reads; no ignored alternate path can be declared;
- profile path fields reject secret-like values, and routing/work-tracking validators
  match the schemas' undeclared-field and unique-list constraints;
- malformed top-level JSON values now become controlled validation errors rather than
  an uncontrolled status failure.

**Verdict:** `approve` after the final malformed-object guard was applied. Runtime and
end-to-end validation remain deferred to the single final validation gate by user
direction.

## Closure review: release eligibility and strict manifest values

Kepler reviewed only the frozen remediation batch without running tests or opening new
scope. The review confirms that legacy release manifests remain readable for an
existing binding but cannot become a new bind or update target, adapter entry points
are user-scoped as declared by schema, booleans cannot stand in for JSON integer
schema/revision values, and installation release versions are non-empty valid release
identities. The two durable internal records, client ownership and pending project
update, also reject boolean schema versions with controlled validation errors.

**Verdict:** `approve`. Any further static or runtime concern belongs to the explicit
final validation gate or a separately approved follow-up; it must not reopen this
implementation scope automatically.
