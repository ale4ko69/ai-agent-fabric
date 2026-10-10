# Plan — Validate Fabric self-hosting installation

## Analysis

The global runtime must be versioned and independent of the development checkout. The
client entrypoint must preserve user instructions, while project state remains local.

## Architecture

`%LOCALAPPDATA%/AI-Agent-Fabric` owns releases, a stable launcher, and stable adapter
bootstraps. The Codex instruction file contains one managed bootstrap block. This
repository owns `.agent-fabric` and the task package.

## Implementation

1. Add managed-block lifecycle to the Codex adapter.
2. Generate a Windows bootstrap command using Git Bash's absolute path.
3. Install release `0.1.1` and enable the Codex managed block.
4. Bind this repository and initialize its local memory.
5. Install only the Codex-facing global Fabric skill links, preserving unrelated
   user skills and tracking Fabric ownership for removal.

## Validation

1. Confirm the global instructions retain the Designer rule and one managed block.
2. Confirm global `work` selects restore after task creation.
3. Confirm memory restore and Harness review remain project-local.
4. Obtain Kepler review before closing this verification task.
5. Confirm `/skills` can list the skills and an explicit `$work` invocation is
   discoverable in a read-only Codex run.
