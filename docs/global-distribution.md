# Global Fabric distribution and project binding

## Decision

AI Agent Fabric is installed once as a versioned user-level distribution. It provides
the common agent structure for every project: the canonical role profiles, shared
memory protocol, workflow rules, schemas, and client renderers. A project is bound to
that installation but keeps every project-specific fact in its own repository.

This is a two-layer system, not a choice between a "global" and a "project" Fabric.

```text
user-level Fabric release
  -> client bootstrap for a selected client
  -> project binding and local profile
  -> task package and project-local memory
```

## Ownership and precedence

| Layer | Owns | May change |
|---|---|---|
| Global Fabric release | Seven canonical roles, portable workflow, schemas, shared policy, client renderers | Only a Fabric update |
| Client bootstrap | Finds the active Fabric release and then the current project binding | Only the selected client adapter |
| Project binding | Selected Fabric release, enabled packs, selected client, project profile location | A project installer or explicit update |
| Project profile | Commands, paths, integrations, tracker rules, model mapping, local policy | The project owner |
| Task package | Scope, specification, plan, opponent verdict, task state and evidence | The approved task workflow |

The project layer may refine a global rule only where that rule declares a project
configuration point. It cannot disable universal safety rules, reinterpret a role, or
make global memory contain project facts.

Client products do not have one universal precedence rule. Every adapter declares a
`loading.mode`: `ordered` only when the client documents an order, `combined` when it
merges applicable files without a general priority rule, and `additive` when all
applicable layers contribute context. Its `loading.sequence` describes the Fabric
layers that participate; it is not a fabricated conflict-resolution rule. Codex is
currently `ordered` (global bootstrap, then repository instructions). Copilot CLI is
`combined`, so Fabric bootstrap and local overlay must not contradict one another.
Claude Code is `additive`, so its global and project `CLAUDE.md` layers likewise must
remain compatible. Client-specific behaviour is never inferred from a directory name
alone.

## Release layout

The default user-level Fabric home is platform-specific and may be explicitly
overridden at installation time:

| Host | Default Fabric home | Rationale |
|---|---|---|
| Windows | `%LOCALAPPDATA%\\AI-Agent-Fabric` | Per-user mutable application data; no administrator access or source checkout required |
| Linux / WSL | `${XDG_DATA_HOME:-~/.local/share}/ai-agent-fabric` | Per-user application-data convention |

The source checkout is never used as a runtime installation. The development repository
remains separate from the user-level installer, which creates releases in the Fabric
home.

Before the first release exists, run the source checkout through
`python scripts/run-fabric.py`. This helper adds only that checkout's `src/` directory
to its own Python process; it is not installed into a project and is not used by any
release after installation.

```text
<fabric-home>/
  bin/
    ai-agent-fabric              # one global launcher for the active release
  adapters/
    <client>/bootstrap.md        # stable client target, refreshed on Fabric update
  releases/<version>/
    core/
    bin/ai-agent-fabric
    adapters/
      <client>/adapter-manifest.json
      <client>/bootstrap.md
    schemas/
    release-manifest.json
  installation.json
```

`installation.json` records the managed current release for newly bound projects.
Existing projects pin a compatible release in their own binding file rather than
silently changing when that current-release record advances. A filesystem link is not
required for release selection, which keeps this behaviour portable on Windows.

No project profile, task package, memory database, tracker setting, credential, or
project command is stored in this global distribution.

## Project binding

Each bound repository owns `.agent-fabric/fabric-binding.json`:

```json
{
  "schema_version": 1,
  "fabric_release": "1.0.0",
  "client": "codex",
  "profile": ".agent-fabric/profile.json",
  "project_overlay": ".agent-fabric/project-overlay.md",
  "enabled_packs": []
}
```

The binding is the only durable relationship between a repository and the central
Fabric. `profile.json`, `memory.db`, `docs/specs/`, and client-local project wrappers
remain in the repository.

## Installation modes

| Mode | Purpose | Writes |
|---|---|---|
| `distribution install-release` | Install a versioned common Fabric release | Only the chosen Fabric home |
| `distribution enable-client` | Connect a client’s user-level entry point to the selected release | Only the explicitly approved client configuration location and installer manifest |
| `project init` | Create a project overlay and pin a release | Only the target repository |
| `distribution update-project` | Move one project to a reviewed compatible release | Only its binding and declared migration artifacts |
| `distribution rollback-project` | Restore a reviewed previous project binding | Only its binding and a new recoverable backup |
| `distribution rollback-client` | Restore the preceding installer-owned client artifact | Only the selected client entry point and its ownership record |
| `distribution uninstall-client` | Remove an adapter owned by this installer | Only manifest-owned client artifacts |

No command may switch from project binding to user-level installation implicitly.
Every release, project-binding, and client-adapter mutation has a preview; ownership
records and backups make replacement, rollback, and uninstall reversible.

`<fabric-home>/bin/ai-agent-fabric` is the single global Bash launcher. It reads the
current release from `installation.json` and delegates to that release's immutable
launcher. The client bootstrap names this global launcher, so a Fabric command is never
installed inside a project. A project path only selects project-owned context: its
binding, local memory, task packages, specs, and Harness trace. The immutable launcher
sets its own `AI_AGENT_FABRIC_HOME` and `PYTHONPATH`, then selects `python3`, with
`python` as a fallback, choosing the first interpreter that is Python 3.10 or newer.
It disables Python bytecode writing so normal use cannot mutate the immutable release
tree.

The client entry point likewise targets `<fabric-home>/adapters/<client>/bootstrap.md`,
not a file inside a versioned release. Installing an update refreshes that stable
bootstrap and the global launcher together. Existing client links therefore pick up the
active shared Fabric while each project remains pinned through its own binding.

## Links, imports, and wrappers

A client adapter declares one of four supported delivery methods for every client
surface:

- `symlink`: a standard client location links to a Fabric-managed artifact;
- `import`: a client-supported instruction import refers to the installed Fabric;
- `wrapper`: a small generated client file delegates to the selected release;
- `unsupported`: the installer does not guess a mechanism.

Symlinks are valid delivery mechanisms, not a global prohibition. The installer records
their source, destination, owner, and release in its manifest. It never replaces a
user-owned link or file. A symlink for an agent adapter does not grant a project access
to another project's profile, memory, tasks, or credentials.

### Windows permission prompt for a symlink

Before requesting a Windows UAC confirmation, the installer preview must show a plain
language permission notice. It names the one client-entry file that will become a
symbolic link and its Fabric bootstrap target, and explains that Windows may require
this permission to create a native NTFS link. It must also say that the request does
not grant the Fabric access to the project, its secrets, or unrelated user files.

UAC is Windows' **User Account Control** prompt: it asks the signed-in person whether
to run this narrowly scoped operation with administrator-level rights. A “raised” or
“elevated” PowerShell is simply a PowerShell process launched after that confirmation.
Those rights are used only to create the declared link. Cancelling leaves the client
configuration unchanged. A user can instead choose the declared `wrapper` delivery
method; the installer must never silently replace a requested link with a wrapper or a
Git-Bash compatibility link.

The command deliberately requires two explicit choices for this path: first select
`--method symlink`, then add `--elevate`. Before it sends the UAC request, it prints
the permission notice from the preview. Without `--elevate`, a Windows `1314` result
stops the installation and tells the user to review the preview; it never requests UAC
unexpectedly. Programmatic callers must likewise show and acknowledge the preview's
`windows_elevation_notice` before enabling elevation; the public API rejects an
unacknowledged request. The elevated child is the trusted System32 PowerShell resolved
by Windows itself, never a `powershell.exe` found through `PATH` or the working
directory. The same explicit notice and `--elevate` choice apply to
`distribution rollback-client` when restoring an installer-owned native link.

Binding paths are resolved before use and must remain below the resolved project root.
Thus a project-owned profile or overlay cannot use a link to escape into another
project or user-level state; this restriction does not apply to the explicitly declared
client-adapter link itself. The `.agent-fabric` state directory and all of its internal
state parents reject symbolic links outright, so bindings, memory, Harness records,
updates, and configuration cannot be redirected outside the selected project.

Secret storage is separate from adapter delivery: a project profile explicitly declares
only a project-local secret destination. External credential stores are not part of the
baseline and require a separately designed project integration.

## Update policy

1. A new Fabric version is installed beside existing releases.
2. Its immutable release manifest declares the exact local-memory schema and minimum
   compatible schema for that release.
3. The manifest's current-release record can advance for new projects without moving
   existing bindings.
4. A project update previews profile, adapter, and exact source/target local-memory
   schema versions. It invokes the selected release's explicit memory migration before
   changing the binding; if migration fails, the binding remains untouched.
5. Local-memory migrations are forward-only. Historical result rows that cannot meet a
   newer contract are retained in a project-local quarantine table rather than being
   discarded. Binding rollback changes the pinned release only; it does not downgrade
   a migrated database.
6. Rollback validates the project-local binding and the retained target release, then
   restores the previous binding even if the current release has failed integrity.

This makes central improvements reusable while preventing an update of global agents
from silently changing an active project.

`project status` and the client-facing `project context` expose both the pinned
`release` and the global `current_release`. When they differ, `update_available` is
`true`. This is a visible prompt to review `distribution update-project --preview`,
not authorization to change the project automatically.

If an update is interrupted after its project database migration, Fabric retains a
project-local pending-update journal and binding backup. `project status` reports the
pending update as `update-pending`, which makes every Fabric-managed project write
ineligible until the issue is repaired. `distribution repair-project-update --preview`
shows the exact forward-only resume before `distribution repair-project-update` changes
anything. Binding and journal files are replaced atomically; if a torn binding is
detected, the repair path may restore only the journal's trusted project-local backup.
Rollback is blocked until that repair succeeds. Fabric never guesses that a migrated
database should be downgraded.

## Client adapter decision record

Before enabling a client, its adapter must record:

- exact client surface and detected version/capabilities;
- supported user-level and repository-level instruction locations;
- actual loading mode and, where documented, order;
- supported delivery method and its fallback;
- whether external links or imports require user approval;
- how the adapter is updated, disabled, and removed.

The first implementations are Codex, Copilot, and Claude. A ChatGPT surface receives
an adapter only after its concrete local runtime and supported instruction mechanism
are identified.

For the end-to-end behaviour of a fresh or cloned repository, see
[project onboarding](project-onboarding.md).
