# Validation

## Target

The Codex start/restore handoff contract, generated bootstrap, lifecycle claim gate,
and recovery-only Root boundary.

## Checks

- Full isolated suite: `python scripts/run-tests.py`.
- Start and restore return the same `socrates_chat_request` for a task.
- An unclaimed chat cannot advance a lifecycle step; the named claim can, and a
  restored claimed task retains its bound thread.
- Picker output grants no handoff ownership.
- Generated Codex bootstrap requires the separate chat, prohibits Root impersonation,
  and makes Root recovery-only when chat creation or activation-packet delivery fails.

## Result

PASS: 44 tests passed; 1 expected Windows symlink-capability test was skipped because
the non-elevated process lacks `SeCreateSymbolicLinkPrivilege` (`WinError 1314`).

The final release-install and bound-project verification remain pending explicit
approval of the installer preview.
