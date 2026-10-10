# Evidence

## Installed-release verification — 2026-10-10

- `main` was updated to commit `1926649` before release installation.
- The required release preview listed the immutable `0.1.13` path, the replacement
  launcher/bootstrap paths, and the Fabric-owned marketplace plugin + hooks paths.
- Installation created release `0.1.13`; project update preview declared a memory
  migration from schema 2 to 8 and a binding backup.
- The update completed successfully. `project context` reported matching bound/current
  release `0.1.13` and `update_available: false`.
- The installed launcher returned a numbered picker for all active tasks. Selecting
  number 2 restored the Socrates lifecycle successfully without a project command.
