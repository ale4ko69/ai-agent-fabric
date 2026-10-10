# Distribution manifests

The Fabric uses three separate manifest contracts. None contains a project secret,
project memory, task content, or project command.

| Contract | Owner | Location | Purpose |
|---|---|---|---|
| Installation manifest | Fabric installer | `<fabric-home>/installation.json` | Retained releases, active release, and release integrity metadata |
| Client adapter manifest | Fabric release | `<release>/adapters/<client>/adapter-manifest.json` | Client surface, actual loading semantics, global delivery, managed local-overlay loader, lifecycle, and hook support |
| Project binding | Target project | `.agent-fabric/fabric-binding.json` | Pinned release, selected client, project profile, local overlay, and enabled packs |

An adapter installation produces a second, user-local ownership record below the Fabric
home. It identifies only artifacts created by that installer, their backups, and their
rollback source. It must not treat a pre-existing user file or link as installer-owned.

## Required lifecycle

1. Inspect the selected client surface and release compatibility.
2. Render a preview showing every global or project-local path that would change;
   this applies equally to install, update, rollback, and uninstall.
3. Obtain explicit selection of the delivery method when more than one is supported.
4. Back up only an installer-owned replacement or stop for a user-owned target.
5. Write an ownership record after a successful connection.
6. Uninstall or rollback only files and links named in that ownership record.

The ownership record is stored as `<fabric-home>/clients/<client>.json`. A pre-existing
entry point with no matching ownership record is user-owned and blocks installation;
the installer never overwrites it. Updating an owned file or link stores a recoverable
backup before replacement. A symlink may point to the selected release bootstrap, while
an import or wrapper records the same bootstrap as an explicit source.

Before a client entry point can be enabled, the adapter runs a read-only preflight for
its declared concrete client surface. It records the executable path, version output,
and selected entry point. Missing or uninspectable client surfaces are unsupported and
block installation rather than causing the installer to guess a location or syntax.

The schemas for these files are `installation.schema.json`,
`release-manifest.schema.json`, `client-adapter-manifest.schema.json`, and
`project-binding.schema.json`.

The installation manifest binds each release identity to exactly
`releases/<version>` and stores the SHA-256 of that release's own manifest. A release
is accepted only after that manifest, its complete declared file set, and every file
hash it declares are verified. Undeclared files and all release-tree symlinks are
rejected, including a symlinked release-storage root or release directory.

The release manifest also declares the exact project-memory schema produced by that
release and its minimum compatible schema. An update preview compares the current
project database to the selected release before binding changes. Migration is executed
by the selected release's launcher; a rollback is blocked when it would require a
memory downgrade.

Each client adapter manifest declares a concrete client *surface*, not merely a vendor
name. The first surfaces are Codex local runtime, Copilot CLI, and Claude Code. A later
Copilot IDE surface or ChatGPT runtime receives a separate manifest only after its
instruction locations and loading semantics are established.

## Hook declaration

Every adapter manifest explicitly declares `hooks`. `unsupported` means the installed
adapter has no lifecycle hook and the launcher remains the only Harness entry point.
`adapter` names the concrete supported events (`session-start`, `pre-tool-use`,
`post-tool-use`, or `checkpoint`) and requires a declared supported client version or
version range, concrete hook point and handler, delivery method, client ownership record,
rollback, and uninstall contract. A manifest must not imply a hook merely because a
client or a model vendor exists.

Hooks are selected by the concrete client runtime and its capabilities. Model routing is
project-local policy: it decides which model a role may use, but it does not by itself
grant a lifecycle hook or access to project state. The initial release declares hooks
unsupported until a client-specific implementation is reviewed and shipped.
