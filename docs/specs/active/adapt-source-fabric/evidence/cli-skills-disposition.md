# CLI skills disposition

**Reviewed:** 2026-10-10. This is a read-only analysis of the source CLI-skill family.
It records reusable behaviour without reproducing source workspace names, tracker
identities, repository names, or user-calendar rules.

## Implementation status correction

This document classifies source behaviour; it is **not** proof that a native client
command has been installed. The current release supplies one global launcher with
portable `work`, `start`, `restore`, and `harness review` commands. It deliberately
does not claim that those commands are native slash commands in every client: a client
renderer still needs its own verified installation, update, rollback, and removal path.

| Source skill | Portable value | AI Agent Fabric destination | Disposition |
|---|---|---|---|
| `work` | One entry router: resume a known task, otherwise create a new task; do not invent a third workflow. | Global `work` entrypoint; selected-client renderer may expose it after its native command surface is established. | Implemented as global command; native renderer is not installed. |
| `start-orchestrator` | Classify task, materialize checklist state, take one named step at a time, close steps only with evidence, make skips explicit, and publish a discovery stub before implementation. | Socrates workflow, task package and local memory/checkpoint contracts. | Global `start` previews then explicitly creates task state; durable checklist refinement remains pending. |
| `orchestrate` | Alias rather than a second orchestration procedure. | Client-rendered alias only. | No core duplicate; alias is not implemented. |
| `restore` | Restore one selected task, preserve closed steps, identify the next unfinished step, and make restoration read-only. | Global `restore`, project-local resume protocol, task/session artifacts. | Implemented as global command; native renderer is not installed. |
| `harness-optimization` | Evidence-first failure analysis, one bounded proposal per target, Kepler/human review before writes, and explicit missing-evidence reporting. | Global `harness review`, project Harness retrospective. | Bounded input command implemented; report authoring remains the opponent/human workflow. |

## Reuse boundary

The source skills are Copilot command files. They cannot be copied as a universal
command surface: Codex, Copilot CLI, and Claude Code expose different invocation and
installation mechanisms. The global Fabric therefore owns client-neutral protocol and
data contracts; a selected client adapter may render a command only after its own
native command capability, ownership, update, rollback, and uninstall path are
declared. Until then, the bootstrap guides the same protocol through ordinary
conversation and the release launcher.

## Adopted rules

1. A task entrypoint routes only to restore or new-task intake.
2. A checklist is durable state, not prose: every step has `pending`, `in_progress`,
   `done`, or `skipped`; `done` needs an artifact and `skipped` needs a reason.
3. Discovery evidence precedes planning and implementation. A low-confidence or
   conflicting discovery result is a focused question, not a guess.
4. Restore preserves completed work and resumes only the first unfinished applicable
   step. It does not execute project commands by itself.
5. Harness reports evidence, gaps, root-cause uncertainty, and bounded proposals. It
   never edits global or local policy automatically.
6. External mutations require a fresh preflight, a visible diff or declared affected
   artifacts, and explicit confirmation.

## Explicit exclusions

- Work-item providers, work-item keys, fixed project classes, and comments;
- absolute directories, user configuration files, fixed repositories, release lines,
  and branch conventions;
- calendar/weekday assumptions and reading multiple projects' session stores;
- source-specific scripts and their command paths.

These are excluded from AI Agent Fabric. A future project may define its own integration
only through project-owned configuration approved by that project's owner.
