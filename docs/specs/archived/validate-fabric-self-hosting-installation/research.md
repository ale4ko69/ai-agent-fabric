# Research — Validate Fabric self-hosting installation

## Evidence

- No Fabric home existed before installation.
- Existing Codex instructions contained the independent Designer rule; no old Fabric
  reference was found in Codex or Copilot instructions.
- Bare `bash` in the current PowerShell resolved to the WSL shim, while Git Bash was
  available at the standard Git installation path.
- Release `0.1.3` installed successfully, and its generated Codex bootstrap names the
  absolute Git Bash executable.
- The bound project now reports release `0.1.3`, a current local memory schema, and all
  required local project contracts.
- Update and recovery were exercised: an interrupted update stayed journaled,
  then `repair-project-update` completed it; a subsequent standard update moved
  the project to `0.1.3` with no memory-schema migration.

## Options

- Managed block in an existing user-owned instruction file.
- Replacement wrapper or symbolic link.

## Rejected approaches

- Replacing the existing Codex instruction file, because it would remove the Designer rule.
- Invoking bare `bash`, because it reaches the unavailable WSL shim on this host.
