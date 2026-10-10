# Evidence — self-hosting installation

This directory contains only non-secret verification facts. It does not copy
conversation history, local machine configuration beyond the selected launcher,
or the SQLite memory database.

## Verification snapshot (2026-10-10)

- Global Fabric home: the platform-default per-user Fabric home.
- Active installed release and bound project release: `0.1.11`.
- Codex instruction file: the user-scoped `~/.codex/AGENTS.md` entry point.
  It retains the pre-existing Designer instruction and contains exactly one
  Fabric managed block, delimited by the Fabric begin/end markers.
- Bootstrap source: `<fabric-home>/adapters/codex/bootstrap.md`.
  It names an explicit detected Git Bash launcher; bare `bash` is not used.
- Project binding: `.agent-fabric/fabric-binding.json`.
- Project-local memory database exists at `.agent-fabric/memory.db`. A restore
  returned one installation record for the self-hosting task, with only the
  release number and client as evidence.
- `harness health` reported all expected project contracts, a current memory
  schema, and the bound `0.1.11` release.

## Update and recovery route exercised

An intentional self-host update from `0.1.1` to `0.1.2` exposed a release
launcher path error before the binding was changed. Fabric correctly retained a
`pending-update` journal and did not silently claim success. Release `0.1.3`
fixes the migration invocation by starting the selected release with Python and
its explicit source path. The standard `repair-project-update` then completed
the interrupted `0.1.1 → 0.1.2` update. A normal preview and update completed
`0.1.2 → 0.1.3`; its backup is under `.agent-fabric/backups/`.

## Integrity checks

The installed release, stable bootstrap, and project binding were validated by their
respective Fabric commands. Machine-specific paths and local file digests are excluded
from public evidence.

## Scope not exercised

- Copilot and Claude instruction files were not altered.
- Native slash-command discovery was not claimed or verified.
- The isolated repository suite passed with 19 tests and one host-capability skip.
