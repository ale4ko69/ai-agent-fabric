# Final validation matrix

This is the single runtime-validation gate for AI Agent Fabric. The project owner opened
it on 2026-10-10. The isolated Windows/Git-Bash row is recorded in the active task
package; this matrix remains the procedure for each still-unavailable host or delivery
variant. A completed row is evidence only for that exact host and client surface.

## Validated release scope

On 2026-10-10, the owner accepted Windows with Git Bash as the validation scope for
the current release. Native Linux and WSL rows are explicitly deferred, not substituted
by Windows and not marked passed. They remain required procedures before any future
release claims those host rows.

## Isolation rules

- Use a disposable Fabric home and disposable target repository for every row.
- Do not write to an existing user's client configuration, project profile, memory,
  task package, tracker, or secret store.
- Record the exact executable path and `--version` output from the client preflight.
  If a vendor release or its documented instruction surface has changed since the
  adapter evidence review, stop that row and re-review the adapter before claiming
  compatibility.
- A missing client or unavailable host is `unsupported`, not a passing row and not a
  reason to substitute another shell or client.
- No tracker credentials, remote updates, task execution, or secret entry are part of
  this matrix.
- Run the repository test suite through `python scripts/run-tests.py`, not a shell
  assignment such as `PYTHONPATH=src ...`. The runner establishes the source path in
  Python itself, so a Windows host with unavailable WSL is not forced through a Bash
  launcher for a Python-only check.

## Host rows

Run the common lifecycle for each available host:

| Host | Required shell evidence | Expected result |
|---|---|---|
| Windows with Git Bash | Detector identifies `windows` and a runnable Git Bash path. | Bash profile commands may be resolved; no PowerShell command is generated. |
| WSL | Detector identifies `wsl` and its runnable Bash path. | Linux-style Bash is selected without treating WSL as native Windows. |
| Linux | Detector identifies `linux` and a runnable Bash path. | Linux-style Bash is selected. |
| Any host with no Bash | Detector reports no Bash path. | Bash command preview and secret entry fail closed; bootstrap gives only its host-appropriate installation plan. |

On Windows, test the resolver while `WindowsApps\\bash.exe` is present as well as when
it is absent. A runnable Git Bash must win; a WSL launcher is not treated as a Bash
runtime merely because it appears first in `PATH`.

For each host, verify only these lifecycle operations in order:

1. Install a disposable versioned release and verify its manifest/file integrity.
2. Run read-only `project status` against a fresh repository; it must remain `unbound`
   and create nothing.
3. Inspect `project init --preview`; every proposed project path must be below the
   target repository.
4. Bind the target explicitly, then verify `project status` is `bound` and
   `project context` lists contracts but not memory, tasks, or secret paths.
5. Exercise a release update preview, client update preview, rollback preview, and
   uninstall preview. Apply mutations only in disposable directories and check that
   each ownership record restores or removes only artifacts it owns.
6. Confirm a malformed profile, linked `.agent-fabric` directory, or external contract
   symlink produces controlled `invalid`/error status without a write outside the
   target.

## Client rows

The selected delivery method is part of the row. A version string observed by
preflight is evidence for that specific execution, not a permanent compatibility
promise.

| Client surface | Required delivery check | Expected loading boundary |
|---|---|---|
| Codex local runtime | Test the declared wrapper and, where the host permits it, the reversible symlink. | User-level bootstrap supplies only the global contract; applicable repository instructions refine it; Fabric project overlay is reached only after read-only bound-project context. |
| Copilot CLI | Test the declared wrapper and, where the host permits it, the reversible symlink. | Applicable user, repository, agent, and path instructions are combined. The Fabric bootstrap must therefore remain non-conflicting and must not claim precedence. |
| Claude Code | Test the managed `@` import and the wrapper fallback. | User and project `CLAUDE.md` layers are additive. The imported bootstrap must not overwrite project rules or use an external import created by the repository. |

For every client row, run preflight first. If it cannot inspect that client executable
or the client no longer exposes the documented instruction surface, the row stops as
unsupported. Do not force a generic adapter, add a native instruction file to the
repository, or enable a hook to compensate.

## Hooks and Harness

The baseline manifests declare no installed Fabric hook. Validate the launcher-based
Harness flow only: signal -> retrospective input -> Kepler/human artifacts -> close
retrospective. The cursor must be project-local, advance only after approved artifacts,
and leave signals recorded after the sampled watermark for the next run. Native hook
validation is a separate future adapter gate that must name a supported client version,
event, delivery method, rollback, and uninstall procedure.

## Completion record

Save one non-secret report per executed matrix row under the validation task package:
host kind, client surface, exact preflight version output, delivery method, paths
mutated, results for each lifecycle operation, and any unsupported/blocked reason.
Kepler reviews the report for scope and evidence before the owner decides whether the
release is ready.
