# Implement trusted Codex lifecycle hooks and cross-client behavior

## User Value

A bound project opened in Codex Desktop should expose its own active task choices at
session start, without relying on a root chat and without copying private conversation
content into Fabric state.

## Scope

- Ship a plugin-owned Codex `SessionStart` command hook that discovers only the bound
  project from its working directory and invokes the read-only restore picker.
- Package the hook with the installed marketplace source and show its replacement path
  in the immutable-release preview.
- Keep `start` and `restore` explicit Socrates operations; the hook supplies context
  only.
- Verify GitHub Copilot CLI, Copilot Cloud, and Codex Cloud behaviour and document the
  supported/unsupported boundary with vendor evidence.
- Explain the hook, Guard outcomes, and Harness signals in the operator documentation.

## Non-Goals

- Do not read a chat transcript, classify every user prompt, or automatically record a
  `user-correction` Harness signal.
- Do not give cloud jobs access to a user's local Fabric home or local memory database.
- Do not silently create Copilot `.github/hooks` files in user projects.

## Acceptance Criteria

- The generated Codex marketplace plugin contains `hooks/hooks.json` and the handler.
- The handler returns only bounded active-task metadata and does not create/restore a
  session.
- Release preview includes the marketplace paths that the installer will replace.
- Documentation distinguishes a concrete Guard failure from a behavioural Harness
  signal and names who acts after every Guard outcome.
- Client documentation explicitly states the Copilot CLI/Cloud and Codex Cloud limits.

## Constraints

- Hook execution remains subject to Codex's own review/trust decision.
- Project state remains project-local and no target-specific path enters the release.

## Open Questions

None for this release. A future Copilot project integration requires a separate,
explicit preview and a cloud-safe persisted state design.
