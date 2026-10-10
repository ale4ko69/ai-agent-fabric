# Research — Implement trusted Codex lifecycle hooks and cross-client behavior

## Evidence

- Codex plugin hooks support a `SessionStart` command and can return additional context
  through the hook JSON output. Codex requires review/trust for command hooks.
- The old Fabric marketplace copied skills only and did not ship a hooks directory or
  expose its replacement paths in release preview.
- GitHub documents `sessionStart`, tool, error, and stop hooks for Copilot CLI. It also
  documents cloud hooks, but those run in an ephemeral Linux sandbox from a repository
  configuration on the default branch.
- Codex Cloud orchestration does not run local/plugin command hooks.

## Options

1. Infer corrections from prompt text: rejected because it would inspect private chat
   content and turn an uncertain interpretation into durable state.
2. Start/restore a task from `SessionStart`: rejected because session startup has no
   user task selection and must remain read-only.
3. Return the numbered restore picker and require explicit selection: selected.

## Rejected approaches

- Installing a generic Copilot hook in every project: rejected because it changes a
  project-owned `.github/hooks` surface without a project-specific preview.
- Claiming a Cloud hook can reach the developer's local Fabric release: rejected;
  cloud execution is ephemeral and repository-bound.
