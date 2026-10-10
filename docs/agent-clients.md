# Agent clients

AI Agent Fabric is model-client neutral. The versioned shared Fabric defines roles,
memory, contracts, and safety behavior; client adapters render one explicit global
bootstrap for the selected client. A project binding supplies its local overlay.

| Client surface | Project marker | User-level bootstrap | Fabric project overlay |
|---|---|---|---|
| Codex local runtime | `.codex/` or `AGENTS.md` | `~/.codex/AGENTS.md` | `.agent-fabric/project-overlay.md`, read by the global bootstrap |
| Copilot CLI | `.github/copilot-instructions.md`, `.github/instructions/`, or `.github/agents/` | `~/.copilot/copilot-instructions.md` | `.agent-fabric/project-overlay.md`, read by the global bootstrap |
| Claude Code | `.claude/` or `CLAUDE.md` | `~/.claude/CLAUDE.md` | `.agent-fabric/project-overlay.md`, read by the global bootstrap |

The selected adapter is installed only through an explicit user-level lifecycle and
records ownership, backup, rollback, and removal data in the Fabric home. It may use a
supported link, import, or wrapper. Markers are evidence, not authority. If more than
one is present, project binding requires `--client codex`, `--client copilot`, or
`--client claude`.

Fabric never creates, replaces, or claims a repository's native `AGENTS.md`,
`CLAUDE.md`, or `.github/copilot-instructions.md` during project binding. Those remain
user/project-owned instructions. The shared bootstrap reads the binding and managed
local overlay indirectly, which keeps initialization reversible and prevents Fabric
from taking ownership of a pre-existing client file.

## Hooks and model routing

The common Fabric protocol can use lifecycle events for safe Harness signals, context
restore, and checkpoints, but a hook belongs to a concrete client adapter—not to a
generic model or the global Fabric. Each adapter manifest explicitly says whether this
Fabric adapter has an installed hook implementation (`adapter`) or not (`unsupported`).
`unsupported` does not assert that the vendor client lacks hooks; it only prevents
Fabric from claiming an uninstalled handler. The initial adapters ship with no Fabric
hook handler until a concrete implementation, delivery, client-version, host strategy,
and reversible lifecycle are reviewed. See [client-adapter evidence](client-adapter-evidence.md).

The selected project model-routing configuration chooses affordable models per role.
It may affect what work an agent performs, but it cannot create a hook, expose a
different project's memory, or override an adapter's declared capability. Without an
adapter hook, the task-local Socrates workflow invokes the launcher to record the same
project-local Harness signals manually. Specialists return evidence to Socrates; they
do not write Harness signals or Guard failures themselves.

## Loading semantics

| Client surface | Fabric loading mode | Fabric rule |
|---|---|---|
| Codex local runtime | `ordered` | Global bootstrap is read before repository instructions; the project overlay refines the common Fabric contract. |
| Copilot CLI | `combined` | Applicable user, repository, and agent instruction files are combined without a general precedence rule. Fabric files must therefore be non-conflicting. |
| Claude Code | `additive` | Applicable `CLAUDE.md` layers all contribute context. Fabric's user bootstrap and project overlay must remain compatible rather than relying on an override. |

`loading.sequence` in an adapter manifest identifies the relevant Fabric layers. It is
not a claim that the client resolves conflicts in that sequence. Claude's supported
`@path` import is the default global delivery method; Codex and Copilot retain an
explicit choice of a wrapper or an installer-owned symlink. The Claude renderer emits
an unquoted absolute import and escapes spaces, because quotes would prevent an import
from loading. A user-scope Claude import is trusted as personal configuration; no
project repository is permitted to create an external import on the user's behalf.
