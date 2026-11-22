# Project onboarding

## Project-only runtime

No global Fabric or client adapter is required for this mode. From the selected,
reviewed source checkout, use an existing target with no `.agent-fabric` entry:

```bash
python -I -S -B scripts/run-fabric.py project install /path/to/project --source . --client codex --preview --json
python -I -S -B scripts/run-fabric.py project install /path/to/project --source . --client codex --apply --expected-preview-sha256 <preview_sha256> --json
python -I -S -B /path/to/project/.agent-fabric/runtime/bin/ai-agent-fabric.py project context /path/to/project --json
```

Review the exact files, directories and possible SQLite sidecars in the preview.
The digest covers source contents, target identity, selected mode/client and the
write inventory. If anything changes, obtain a fresh preview rather than guessing
a replacement digest. Preview never opens SQLite or creates state. Apply creates
the current database schema only in a new target state tree; it does not migrate
an existing project.

The runtime, release registry, launcher, ownership, binding, configuration and memory
all stay under `.agent-fabric`. No user-level client files, native repository
instructions, plugin, hooks or role renderer are installed. Client activation is
**none**, not Codex Desktop support or a Socrates handoff. Inspecting context through
the explicit local launcher is the supported entry point.

The local launcher cannot target another project, change home, install a release,
enable a client or bootstrap host software. There is no global fallback. An existing
or interrupted `.agent-fabric` tree must be inspected manually; this command will
not merge, replace, repair or remove it. See [runtime ownership and boundaries](global-distribution.md#project-only-runtime).

## Onboarding from a global Fabric

This flow applies when a person creates a repository or clones one that has no AI Agent
Fabric project binding. The global Fabric is already installed and the selected client
bootstrap is enabled.

```text
open or clone repository
          |
          v
selected client loads its global Fabric bootstrap
          |
          v
read-only `project status` checks .agent-fabric/fabric-binding.json
          |
          v
is the project bound, complete, and compatible?
   | yes                                  | no
   v                                      v
read-only `project context` ->        report "Fabric available;
pinned release contracts +            this project is not bound"
project profile + overlay
   |                                      |
   v                                      v
run the task workflow                 user explicitly requests initialization
                                          |
                                          v
                              show project-init preview
                                          |
                        user confirms   |   user declines
                              |          |        |
                              v          |        v
                  create project-owned   |   leave repository untouched
                  binding, profile,
                  local config, memory,
                  project overlay
                              |
                              v
                    start normal task workflow
```

## Global bootstrap behaviour

The global client bootstrap provides the same read-only onboarding instruction on every
supported surface: check `.agent-fabric/fabric-binding.json` with `project status`.
Codex loads the global bootstrap before repository instructions. Copilot CLI combines
the applicable bootstrap and repository files without a general precedence rule, and
Claude Code loads applicable `CLAUDE.md` layers additively. Therefore the global
bootstrap and project overlay are deliberately compatible rather than depending on a
client-independent override. The status reports `unbound`, `partial`, `invalid`, or
`bound` and does not create a directory, a binding, or a client file.

- If a binding exists, it runs read-only `project context` to obtain the exact paths to
  pinned shared contracts, the project profile, and the project overlay. This result
  intentionally never names `memory.db`, task contents, or a secret path.
- If no binding exists, it states that the Fabric is available but the repository has not
  opted in. It does not create files merely because a repository was opened.
- When the user explicitly asks to initialize, install, or bind Fabric for that project,
  it uses the client currently running the conversation and invokes project initialization
  in preview mode first.

## Commands

```text
# First action after opening or cloning a repository.
ai-agent-fabric project status <project-root> --json

# Only after status says `bound`: reveal read-only contract paths for this pinned release.
ai-agent-fabric project context <project-root> --json

# Show the relevant project paths before initialization.
ai-agent-fabric project init <project-root> --client codex --preview

# After review, create the project binding and project-owned state.
ai-agent-fabric project init <project-root> --client codex
```

Replace `codex` with `copilot` or `claude` when that is the active client surface.
The command selects the current installed release unless `--release` explicitly pins a
different installed version.

The release launcher also sets its own `AI_AGENT_FABRIC_HOME`. A bootstrap installed
in a non-default user-level home therefore resolves the same registry, while the
project binding remains portable because it stores a release identity rather than a
machine-specific installation path.

The initialization creates only project-owned artifacts:

```text
.agent-fabric/
  fabric-binding.json
  profile.json
  project-overlay.md
  config/
  memory.db
```

Task packages under the profile's configured task root are created later, only when a
real task begins. No global agent, project command, tracker configuration, credential,
or task data is copied into another scope.

Project initialization does not create, replace, or claim client-native instruction
files such as `AGENTS.md`, `CLAUDE.md`, or `.github/copilot-instructions.md`. The
global bootstrap reads the local Fabric overlay indirectly, while any such pre-existing
repository instructions remain the project's own responsibility.

Afterward, every Fabric-managed write (memory initialization or repair, task-package
creation or archival, and harness trace append) first requires status `bound`. This
prevents an older command path from creating project state without a release binding.

## Existing repositories in global mode

For a cloned repository, initialization refuses to replace an existing binding or
project overlay. An existing `.agent-fabric` directory alone does not cause a stop:
the initializer preserves existing profile and config files and may initialize or
migrate local memory. Inspect partial state and the preview before choosing whether to
continue. Existing bound projects use the update/rollback lifecycle.
This preservation behaviour belongs to `project init`, not `project install`, which
refuses every pre-existing `.agent-fabric` entry.
