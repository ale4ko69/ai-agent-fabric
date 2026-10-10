# Duplicate and archival audit

## Scope and method

The audit covered the portable target Fabric only: `docs/`, `schemas/`, `src/`,
`scripts/`, and `tests/`. The read-only comparison grouped every regular file by its
SHA-256 digest and then checked declared canonical/retired references and Python import
edges. The personal source Fabric remains outside this deletion decision.

## Result

No byte-identical duplicate files exist in the target Fabric. No file qualifies for
archival or deletion in this pass.

The similarly named artifacts below are intentional contract pairs, not competing
sources of truth:

| Concern | Canonical authority | Companion | Why both remain |
|---|---|---|---|
| Agent roles | Release `core/agent-profiles.json` generated from `agent_profiles.py` | One readable file per role under `docs/agents/` | Clients and humans need different representations; Markdown does not define authority. |
| Gates | Release `core/gates.json` generated from `gates.py` | `docs/gates.md` | The former is checked by runtime; the latter explains evidence semantics. |
| Binding/profile/adapter shapes | JSON schemas under `schemas/` | Runtime validators in `distribution.py` and `installer.py` | Schema documents the interchange contract; runtime rejects unsafe filesystem and host-specific conditions that JSON Schema cannot express. |
| Workflow/Harness | `docs/workflow.md` and `docs/harness.md` | Task-local plan and session state | Shared policy remains global; a task record captures only one project execution. |

## Deferred cleanup rule

Future removal requires all three conditions from the active specification:

1. a named canonical replacement;
2. a reference search showing no live consumer; and
3. recoverable archival evidence before deletion.

This audit found no such candidate. In particular, source-workspace artifacts and
historical migration evidence are not target duplicates and are not deletion targets.
