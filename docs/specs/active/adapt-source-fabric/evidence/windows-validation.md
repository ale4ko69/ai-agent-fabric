# Windows final-validation evidence

Date: 2026-10-10

## Host boundary

- Detector output: `kind=windows`, `system=windows`, `release=11`,
  `python_available=true`, with a detected Git Bash executable.
- Git Bash was runnable. The resolver selected the detected executable both
  with the `WindowsApps\\bash.exe` launcher present and with that launcher absent.
  The resulting Bash bootstrap plan is already available (`command=None`), so no
  PowerShell command is generated.
- WSL is intentionally absent from this host; it is an unsupported matrix row, not a
  failed or substituted Linux result.
- Every mutating check used temporary Fabric and client-home directories. No existing
  user `.codex`, `.copilot`, or `.claude` path was changed.

## Repository suite

Command:

```text
python scripts/run-tests.py
```

Result: 19 tests passed; 1 test was skipped. The skipped test attempts to create a
temporary directory symlink and the current Codex Python process returned Windows
`WinError 1314`. This is a non-elevated process-capability limitation, not a Fabric
policy. The separate native-link probe below establishes the supported Windows route.

## Client preflight and isolated lifecycle

For each client, the lifecycle used releases `validation-a` and `validation-b` inside a
temporary Fabric home. The validation harness replaced the entry-point resolver only
inside its own process with disposable destinations; this is not a Fabric option and
does not alter normal installation behaviour. The successful sequence was: install
`validation-a`, enable the client, install `validation-b`, replace the Fabric-owned
entry, roll back to `validation-a`, then uninstall the Fabric-owned entry and ownership
record.

| Client | Preflight executable | Observed version | Delivery exercised | Result |
| --- | --- | --- | --- | --- |
| Codex | Detected Codex executable | `codex-cli 0.157.1` | wrapper at `.codex/AGENTS.md` | pass |
| Copilot CLI | Detected Copilot executable | `GitHub Copilot CLI 1.0.40`; update notice returned | wrapper at `.copilot/copilot-instructions.md` | pass |
| Claude Code | Detected Claude executable | `2.1.114 (Claude Code)` | import at `.claude/CLAUDE.md` | pass |

This evidence verifies only the declared current adapter lifecycle. It does not claim
that a client automatically reloads instructions during an already-running session.

Claude's declared fallback wrapper was also exercised in a separate disposable home:
the wrapper preview selected `wrapper`, the managed `CLAUDE.md` referenced
`bootstrap.md`, an ownership record was written, and uninstall removed both the
wrapper and the record. No user Claude configuration was changed.

## Project and Harness lifecycle

A separate disposable repository first returned `project status=unbound` and created no
`.agent-fabric` state. Its `project init --preview` equivalent listed only paths below
the project root. An installed release manifest passed its file-integrity validation.
The project was then bound explicitly, updated from `matrix-a` to `matrix-b`, and its
rollback preview and rollback returned it from `matrix-b` to `matrix-a`. A malformed
`.agent-fabric` file returned controlled `status=invalid` without external writes.

A read-only client context exposed contracts but reported project memory as not exposed.
The following project-local Harness lifecycle passed: record one minimal
`user-correction` signal, obtain its retrospective snapshot, create the required local
report/Kepler/human-decision artifacts, and close the retrospective with the unchanged
snapshot descriptor. The resulting cursor was `170`; the next retrospective input had
no signals. No source repository, existing project, or global Fabric home was used.

The repository suite was rerun after the update-lifecycle correction: 19 tests passed;
the same one symlink-capability test remained skipped for this non-elevated Codex
process.

## Native Windows symbolic-link permission

The owner approved a one-time, disposable UAC probe on this host. The sequence was:

1. A normal Python process attempted `os.symlink` and received `WinError 1314`.
2. An elevated PowerShell process was then started through Windows UAC and created a
   link in a unique `%TEMP%` directory.
3. The original Python process confirmed `link_created=true` and
   `python_islink=true`; the temporary directory was removed.

This proves that the host supports real NTFS symbolic links through the expected UAC
route. It also establishes the required interaction contract: Fabric previews the
single declared source and destination and explains UAC before asking Windows to
elevate; cancelling must leave client configuration unchanged. It must not use the
Git-Bash compatibility form of a link as a silent substitute.

The exact Fabric path was then exercised in disposable Fabric and client directories:
install a release, select Codex `symlink` delivery with the preview notice acknowledged,
receive UAC, create the native link, write its ownership record, and uninstall it. The
observed result was `destination_is_native_symlink=true`, `record_exists=true` before
uninstall, then `destination_exists=false`, `record_exists=false` afterwards.

A second disposable lifecycle covered the recovery boundary: native link through UAC,
update to an installer-owned wrapper, rollback with the rollback preview notice and
UAC, then uninstall. The restored artifact was a native symlink whose resolved target
was the declared `bootstrap.md`; uninstall again removed it. The elevation code checks
that the link target equals the previewed source before writing its ownership record,
and rollback applies the same explicit UAC contract. Both tests temporarily redirected
the entry-point resolver inside their own Python process; neither changed a real user
client configuration.

## Explicitly unverified matrix rows

- WSL: unsupported on this computer because its distribution was intentionally removed.
- Native Linux: unavailable on this Windows host.

Native Linux and WSL remain deferred host rows. They are not passing evidence and must
be run before a future release claims those hosts.
