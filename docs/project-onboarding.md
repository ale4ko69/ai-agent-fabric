# Project onboarding

## Project-only runtime

No global Fabric or client adapter is required for this mode. From the selected,
reviewed source checkout, use an existing target:

```bash
python -I -S -B scripts/run-fabric.py project install /path/to/project --source . --client codex --preview --json
python -I -S -B scripts/run-fabric.py project install /path/to/project --source . --client codex --apply --expected-preview-sha256 <preview_sha256> --json
python -I -S -B /path/to/project/.agent-fabric/runtime/bin/ai-agent-fabric.py project context /path/to/project --json
```

Review the files, directories, possible SQLite sidecars and Git-local exclusions.
An existing contract-only target must have the six compatible regular files: the
binding, profile, overlay and three configuration files. The binding must select the
same client and release. Fabric preserves the existing contract bytes and creates
only the missing installation state. Ambiguous, incompatible or occupied generated
paths block installation. Obtain a fresh preview if the inputs change.

At a Git worktree root, Fabric excludes its generated installation state with
escaped, anchored rules for individual generated files and link paths after
installation ownership is complete. Editable contracts and task packages keep
their existing Git visibility. Generated paths already tracked or staged, user rules that override the
exclusions, and an exclusion write shared by linked worktrees each require owner
review before installation can proceed. A non-Git target proceeds without Git writes.
See [Git policy](global-distribution.md#project-only-git-policy).

The runtime, release registry, launcher, ownership, binding, configuration and memory
stay under `.agent-fabric`. The release contains dormant Codex personas and both
project skills. Client activation is **none**. For Codex Desktop, follow the
[separate adapter preview and apply](cli.md#separate-project-codex-adapter)
through the pinned launcher, then check file installation and Desktop evidence
separately.

The local launcher cannot target another project, change home, install a release,
enable a user-level client or bootstrap host software. If installation reports
that its final receipt was published but Git exclusion publication failed, use the
cleanup preview below. Inspect remaining paths and receipts when installation
ownership is incomplete. See [runtime ownership](global-distribution.md#project-only-runtime).

## Migrate this repository's existing Fabric contracts

This one-time transition applies to existing checkouts of this repository. The
profile, model routing, work tracking, capabilities, binding and overlay stay
at their existing paths. Fresh checkouts use the installation procedure above.
The installer supplies the defaults, including the selected client and release
for the binding. Project-specific rules in the overlay refine only configuration
points declared by the selected release.

Publish the bridge commit and this procedure first. Keep the bridge and its
deletion-only successor separately addressable by commit ID. Hold the successor
outside the ordinary update ref until affected worktrees have migrated or their
operators acknowledge this procedure. A regular pull or checkout to the
successor can delete clean copies and reject locally edited ones.

### Before moving the branch

Fetch the reviewed commits without pulling. Identify the trusted IDs of the
bridge and successor from the rollout instructions. In the intended checkout,
confirm Bash is available, verify the repository root and branch, and stop
Fabric, editors and any Git clients that could write there. Use the normal
worktree index. Stop if `GIT_INDEX_FILE` is set or a merge, rebase, cherry-pick
or revert is in progress. Stop if the branch diverged or if moving to the
bridge would touch any of the six paths below. Fast-forward to the bridge only.

Record the intended branch, bridge and successor IDs, and the SHA-256 of the exact
bytes of each of the following regular files in an operator record outside the
worktree. Retain those hashes across retries. Check the current release, client,
and project status with the pinned launcher's `project context . --json`, and
record the active task and chat binding using `restore . <task-id> --json` when
applicable.

```text
.agent-fabric/config/capabilities.json
.agent-fabric/config/model-routing.json
.agent-fabric/config/work-tracking.json
.agent-fabric/fabric-binding.json
.agent-fabric/profile.json
.agent-fabric/project-overlay.md
```

Verify that HEAD equals the bridge ID and the successor has the bridge as its
sole parent with `git rev-list --parents -n 1 "$successor"`. Examine its full
tree diff with `git diff-tree --no-commit-id --no-renames --name-status -r
"$bridge" "$successor"`. It must contain only the six deletions above. Use
`git diff --cached --exit-code HEAD` and `git ls-files --unmerged` to confirm an
unchanged index without unmerged entries. Inspect `git ls-files -v` and stop
if any entry is marked skip-worktree or assume-unchanged. Stop on any failed
check or changed hash.

### Apply and verify

Immediately recheck the conditions above. From the intended worktree and branch
run `git reset --mixed "$successor"`, using the verified full commit ID.
The mixed reset updates the branch and index while preserving working files.
Compare all six SHA-256 values with the operator record, confirm they are
absent from `git ls-files` and covered by the anchored repository rules with
`git check-ignore -v`, and rerun the same pinned context and task restore
checks. Investigate remaining changes using `git status --short`. Preserve
unrelated edits and task packages.

If interrupted, stop if the original hashes are missing or any working file
is missing or differs. Recheck worktree identity and both commit IDs. If HEAD
and index match the bridge, rerun preflight. If both match the successor, rerun
postflight. If HEAD is the bridge and the index matches the successor tree, or
HEAD is the successor and the index matches the bridge tree, verify the exact
index tree with `git write-tree` and repeat the mixed reset to the verified
successor. Stop and inspect any other state. Keep the original operator record
until postflight passes.

A branch that still tracks these paths may overwrite ignored copies when
switching back. Use `git checkout --no-overwrite-ignore <branch>` so Git
refuses to overwrite an ignored file, and stop if it reports a conflict.
Use a separate worktree when you need to consult a legacy branch.


## Git cleanup for an existing project-only installation

Use a trusted source checkout that implements Git cleanup, including for a target
whose older pinned launcher predates this command. The target must already have an
intact project-only release, launcher and runtime receipt. Cleanup covers
adapter paths when it verifies a completed adapter. Pending or invalid ownership
and edited launcher files require inspection of the reported paths. If you add an
adapter later through an older pinned launcher, preview cleanup again to cover the
newly installed links.

```bash
python -I -S -B scripts/run-fabric.py project git-cleanup /path/to/project --preview --json
python -I -S -B scripts/run-fabric.py project git-cleanup /path/to/project --apply --expected-preview-sha256 <preview_sha256> --json
```

Compare the previewed paths with the installation receipts and your existing Git
rules before applying. The cleanup preserves the pinned release, memory, task
packages, binding, tracked settings and index. It only adds effective local Git
exclusions where safe. An already-covered installation needs no exclusion write.
If Git already tracks a generated path, the preview reports the conflict. Review
the index and file yourself before deciding how to resolve it. Cleanup never
untracks or resets files for you.

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
This is the user-level binding lifecycle. The project-only path above uses a
separate contract compatibility check and a separate Git cleanup command.
