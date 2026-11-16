# CLI operations

Use the installed global `ai-agent-fabric` launcher for a bound project. Before a
release has been installed, the source wrapper is `python scripts/run-fabric.py`.
Use `--help` after any command for its exact arguments. A path named `<project>` is
the selected repository; `--home` selects a Fabric installation where supported.
`--json` selects structured output and does not itself make an operation read-only.

## Discovery and task routing

| Command | Prerequisites and state change | Typical next step |
| --- | --- | --- |
| `detect` | Reads host capabilities; does not execute a project command. | Inspect requirements with `preflight`. |
| `detect-client <project>` | Reads local client markers; does not bind. | Select the appropriate client explicitly. |
| `preflight <project>` | Reads declared capabilities and host tools. | Resolve missing prerequisites. |
| `work <project> [task-id]` | Requires a bound project; routes without creating a task. | Choose a task or prepare `start`. |
| `start <project> --title <title> --type <class>` | Bound project; preview by default, `--apply` creates task state. | Create or reopen the requested Socrates chat. |
| `restore <project> [selection]` | Bound project; no selection lists tasks, selection restores durable context. It runs no project command. | Reopen the returned Socrates chat. |
| `recover-unicode-package <project> <source>` | Existing legacy package; preview by default, `--apply` migrates its local identity and lifecycle. | Claim the returned chat. |

Examples:

```bash
ai-agent-fabric project status /path/to/project --json
ai-agent-fabric work /path/to/project --json
ai-agent-fabric start /path/to/project --title "Fix save error" --type small-bug --json
```

## Socrates and task specifications

| Command | Prerequisites and state change | Typical next step |
| --- | --- | --- |
| `socrates claim <project> --session <id> --thread-id <id>` | Prepared task; records its separate chat claim. | Read the durable continuation. |
| `socrates step <project> --session <id> --step <step> --status <status>` | Claimed chat; advances a checklist step. Closing requires existing evidence and a reason. | Follow the returned continuation. |
| `socrates diagnose <project> --session <id>` | Bound project and existing session; reads state and Guard outcomes only. | Follow the reported next action. |
| `socrates resolve-guard <project> ...` | Claimed task and existing blocked or escalated Guard; records owner direction and evidence. | Resume the preserved step. |
| `socrates archive <project> ...` | Completed eligible task; moves its package to the recoverable archive. | Route the next task. |
| `socrates signal <project> ...` | Bound project; records a minimal project-local behavioural signal. | Review it in a future retrospective. |
| `spec create <project> ...` | Bound project; compatibility task-creation entry. | Claim the separate Socrates chat. |
| `spec validate <project> <task-id>` | Reads a local package. | Correct missing or malformed artifacts. |
| `spec readiness <project> <task-id>` | Reads the package and current approval. | Resolve reported evidence or approval gaps. |
| `spec approve <project> <task-id> --preview` | Current Kepler advice; reads the exact package and digest. Without `--preview`, terminal confirmation writes approval. | Present the reviewed package. |
| `spec attest-chat-approval <project> <task-id> ...` | Exact reviewed package and explicit owner chat decision; records an agent assertion, not independently authenticated identity. | Recheck readiness. |
| `spec archive <project> <task-id> --reason <reason>` | Valid package; moves it to the local archive. For lifecycle close-out, use `socrates archive`. | Verify the archive record. |

## Memory, Guards and Harness

`memory init` writes project-local memory; `memory restore`, `memory quarantine`,
`memory pending-requests` and `memory pending-results` inspect local state. They take a
project, with a session identifier where shown by `--help`.

`guards failure` requires a claimed task, a declared Guard and an existing evidence
artifact. It records the result and trace; it does not itself retry. Follow the returned
`retry`, `block` or `escalate` outcome.

| Harness command | Prerequisites and state change | Typical next step |
| --- | --- | --- |
| `resume <project> <task-id>` / `health <project>` | Read task snapshot or health; no project command runs. | Inspect missing evidence or configuration. |
| `checkpoint <project> --session <id> --gate <gate> --evidence <json>` | Bound project; validates labels and appends an audit trace, not proof of work. | Inspect the result. |
| `retrospective-input <project>` / `review <project>` | Bound project; reads signals after the local cursor. | Investigate the evidence and obtain review. |
| `maintenance-digest <project> --candidate <file>` | Bound project and local candidate; returns a digest without approving or changing it. | Bind the digest into the task spec before review and owner decision. |
| `maintenance-preview <project> --task-id <id> --candidate <file>` | Approved task, enabled policy and capability; read-only. | Inspect candidate, scope and evidence. |
| `maintenance-apply <project> --task-id <id> --candidate <file>` | Claimed implementation step, approved candidate digest, policy and preimage checks; writes one supported configuration file. | Review result and preserve any conflict. |
| `maintenance-inspect <project> --candidate-sha256 <digest>` | Reads a journal and saved preimage; does not restore or change files. | Review the result; preserve and resolve a conflict. |
| `close-retrospective <project> ...` | Existing report, Kepler and owner-decision evidence and unchanged snapshot; advances the local cursor. | Start the next signal window. |

## Installation and project binding

`distribution home` and `distribution adapter-manifest <client>` read installation
locations and adapter contracts. The following mutations should first be run with
`--preview`; inspect the shown paths and requirements before omitting that option:

| Command | Effect | Typical next step |
| --- | --- | --- |
| `distribution install-release <source>` | Installs a new immutable version in the selected Fabric home. JSON preview includes a source digest; cross-version installation requires it as `--expected-source-sha256`. | Preview client delivery. |
| `distribution bind-project <project> --release <version> --client <client>` | Binds the selected project to an installed release. | Inspect `project context`. |
| `distribution update-project <project> --release <version>` | Backs up and updates a binding after required local memory migration. | Verify the resulting context. |
| `distribution repair-project-update <project>` | Resumes a journaled interrupted project update. | Verify project status. |
| `distribution rollback-project <project>` | Restores a compatible project binding backup. | Verify binding and memory compatibility. |
| `distribution enable-client <client>` | Enables the selected user-level managed adapter. | Verify client entry and loading. |
| `distribution rollback-client <client>` / `uninstall-client <client>` | Restores or removes only installer-owned client artifacts. | Inspect client delivery state. |
| `distribution enable-codex-skills` / `disable-codex-skills` | Adds or removes Fabric-owned direct skill links. | Verify the selected client surface. |
| `project init <project> --client <client>` | Creates a binding and project-owned state; preview first. | Inspect `project context`. |
| `project status <project>` / `context <project>` | Read binding status or pinned contract paths. | Initialize only on explicit request or enter work. |
| `project command-preview <project> <name>` | Resolves a declared command after host checks; it does not execute it. | Decide whether the declared action is authorized. |

`bootstrap bash` reports an installation plan; `--install` explicitly applies it.
`secret prompt <project> --destination <relative-path> --label <label> --preview`
checks the destination without accepting a secret. Without `--preview`, it uses the
declared hidden terminal entry; never put a secret in an argument or chat.
