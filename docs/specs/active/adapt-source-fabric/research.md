# Research: source Fabric inventory snapshot

## Evidence inspected

The established Fabric was inspected as source material. Its structure includes agent
definitions, role-specific delegation contracts, procedural skills, SQLite-plus-
Markdown memory, a memory command tool, deterministic process gates, a diagnostic
harness, and a Bash installer.

The development workflow contains a full lifecycle: environment preflight, context
recovery, task intake, branch preparation, research, planning, implementation,
review, validation, close-out, and resume. It also contains target-environment routing
and integrations that must become profile data or optional adapters rather than core
instructions.

## Reusable invariants

1. The orchestrator coordinates; specialists perform specialised work.
2. Delegation has constrained inputs and structured results.
3. Important state is recorded during work, not reconstructed from a final summary.
4. Gates check observable evidence rather than relying on conversational memory.
5. Recovery can resume an interrupted task from persisted task and memory state.
6. Installation is reproducible and knows every artifact it produces.
7. Destructive cleanup follows reference checks and a recoverable archive path.

## Required adaptations

| Source pattern | Portable treatment |
|---|---|
| Central shared database | Per-target-project local database; orchestrator remains the sole writer. |
| Global client links and configuration | Explicit, reversible user-level bootstrap plus project-local binding and overlay. |
| Environment-specific shell commands | Capability probe plus Bash/Python abstraction. |
| Work-item and service routing | Optional target-profile integrations. |
| Specialist roles tied to a stack | Optional capability packs declared by the target project. |
| Role contracts and process checks | Client-neutral schemas, profiles, and generic gates. |

## Open evidence to collect

- Full per-rule inventory of the development workflow.
- Full per-contract/skill/gate mapping and dependencies.
- Memory schema field mapping and retention/recovery semantics.
- Installer artifact manifest and portability constraints.
