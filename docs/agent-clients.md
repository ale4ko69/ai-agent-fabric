# Agent clients

AI Agent Fabric is model-client neutral. The versioned shared Fabric defines roles,
memory, contracts, and safety behavior; client adapters render one explicit global
bootstrap for the selected client. A project binding supplies its local overlay.

The table below describes user-level adapter mode. Explicit `project install
--client codex` installs a **runtime only**, with `client_activation: none` and no
adapter manifest in its context (`adapter_manifest: null`). Dormant persona TOMLs and
the project-entry skill are prepared inside the pinned release, not activated in a
client. It writes no user/global client configuration, native project instructions,
hooks or Desktop plugin. It does not create/reopen a Socrates chat.

A separate `project codex-install` preview/apply, available only through the scoped
launcher, installs relative native symlinks for `socrates`, `aristotle`, `plato`,
`kepler`, `heracles`, `athena`, `euclid` and `metis` under `.codex/agents`, plus
`.agents/skills/agent-fabric-project`. The TOMLs contain `name`, `description` and
`developer_instructions` from the pinned canonical profiles and their readable
companions; they do not choose a model, elevate sandbox permissions or grant task
authority. The Socrates persona explicitly refuses task claiming when invoked as a
native subagent.

Any existing `.codex` entry blocks installation, including an empty directory.
Existing config, instructions or agents are never merged, rewritten or claimed.
Other ordinary project skill directories may coexist, but the selected entry must be
absent. No global config, copy, junction, plugin or elevation fallback is attempted.
Inspect `project codex-status`: `file_installation` is separate from
`desktop_discovery: unverified` and `claim_restore: unverified`. A broken/replaced link
reports `invalid`; an interrupted install retains pending ownership for manual
inspection. App visibility is not inferred from link existence.

Root uses the entry only for routing and recovery. Transfer to Socrates is manual and
requires a real separate Desktop chat and its actual thread ID. Missing identity or
exact reopening means stop. Native subagent labels, synthetic IDs and undocumented
Desktop API calls are not substitutes. See [pinned source evidence](client-adapter-evidence.md#project-local-codex-source-contract)
and [next-machine validation](using-fabric.md#project-local-codex-next-machine-validation).

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

The common Fabric protocol can use lifecycle events, but a hook belongs to a concrete
client adapter—not to a generic model or the global Fabric. The Codex adapter ships a
plugin-owned, read-only `SessionStart` hook. It reads only the bound project path and
the launcher-provided active-task metadata, then returns task-selection context. It
does not read chat text, start/restore work, or record a Guard or Harness signal.

The Copilot and Claude adapter manifests remain `unsupported`: that means this Fabric
release has no installed handler for those adapters, not that the vendors have no hook
API. Codex Cloud orchestration does not execute this local/plugin command hook.
See [client-adapter evidence](client-adapter-evidence.md) and the operator explanation
in [Using Fabric](using-fabric.md).

The selected project model-routing configuration declares capability and cost policies
per role; the current runtime validates them but does not select a provider model or
look up live prices. Client configuration may use those policies, but they cannot create a hook, expose a
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
