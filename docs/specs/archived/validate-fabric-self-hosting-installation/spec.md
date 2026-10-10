# Validate Fabric self-hosting installation

## User Value

Verify that a global Fabric installation can safely serve this repository without
replacing the user's existing Codex instructions or using the unavailable WSL shim.

## Scope

- Install one versioned release in the user-level Fabric home.
- Add the installer-owned Fabric block to the existing global Codex instructions.
- Bind this repository to the installed release as the first self-hosted project.
- Verify global routing, task restoration, project-local memory, and Harness input.

## Non-Goals

- Installing or changing Copilot or Claude adapters.
- Replacing user-owned skills or instructions.
- Adding credentials or external integrations.

## Acceptance Criteria

- Existing global Codex instructions retain the Designer rule and exactly one Fabric block.
- The global launcher uses Git Bash directly rather than the WSL shim.
- This repository is bound to one installed release and has only local Fabric state.
- `work` restores the active task; memory and Harness commands use only this project.
- Codex discovers the four global Fabric skills from its user-scoped skill directory
  without replacing unrelated user skills.

## Constraints

- Keep the installation user-level and reversible.
- Do not delete or overwrite user-owned configuration.
- Do not test Linux or WSL in this task.

## Open Questions

- Codex uses user-scoped skill directories. Other clients remain out of scope for
  this verification task.
