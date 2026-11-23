# CLI operations

Use the installed `ai-agent-fabric` launcher for a user-level binding. Replace
`ai-agent-fabric` in task examples with
`python -I -S -B <project>/.agent-fabric/runtime/bin/ai-agent-fabric.py` for a
project-only binding. Use the selected trusted source wrapper for the explicit
source installation or Git cleanup shown below.
Use `--help` after any command for its exact arguments. A path named `<project>` is
the selected repository; `--home` selects a Fabric installation where supported.
`--json` selects structured output and does not itself make an operation read-only.

## Explicit project-only installation

From the reviewed source checkout:

```bash
python -I -S -B scripts/run-fabric.py project install <target> --source <source> --client codex --preview --json
python -I -S -B scripts/run-fabric.py project install <target> --source <source> --client codex --apply --expected-preview-sha256 <preview_sha256> --json
```

Invoke the selected source's own script; cross-source dispatch is refused. The target
must already exist. A fresh target gets the default contracts. A contract-only
target must supply all six compatible files and vacant generated paths. Exactly one
of `--preview` or `--apply` is required. Preview returns `preview_sha256`, the source
digest, project-relative `files`, `directories`, possible SQLite
`transient_paths`, and the Git exclusion plan. Apply rechecks the reviewed digest
and writes project-owned state under `.agent-fabric`. It publishes any planned
exclusions in local Git metadata after the final receipt and ownership checks. See [project-only Git policy](global-distribution.md#project-only-git-policy).

After installation, explicitly use:

```bash
python -I -S -B <target>/.agent-fabric/runtime/bin/ai-agent-fabric.py project status <target> --json
python -I -S -B <target>/.agent-fabric/runtime/bin/ai-agent-fabric.py project context <target> --json
```

The launcher pins this target, local home and release; it cannot dispatch
`distribution`, `bootstrap` or `project init/install`, or accept another target/home.
Existing local workflow CLI operations remain available. Dormant project persona
profiles are prepared in the release; no Desktop plugin or automatic Socrates handoff
is supplied.
`client_activation` is `none`. There is no project-only update, rollback or uninstall
command; interrupted state blocks reinstall and requires manual inspection.

### Separate project Codex adapter

Use the **pinned local launcher**, not a source/global launcher:

```bash
python -I -S -B <target>/.agent-fabric/runtime/bin/ai-agent-fabric.py project codex-install <target> --preview --json
python -I -S -B <target>/.agent-fabric/runtime/bin/ai-agent-fabric.py project codex-install <target> --apply --expected-preview-sha256 <adapter_preview_sha256> --json
python -I -S -B <target>/.agent-fabric/runtime/bin/ai-agent-fabric.py project codex-status <target> --json
```

The adapter preview lists newly created directories, three relative native directory `links`,
its local ownership `files`, and the transient pending ownership path. It writes
nothing and does not probe symlink creation or launch Codex. Apply rechecks that
separate digest, Git exclusion plan and the intact pinned runtime before its first write.

Any existing `.codex` blocks install, including empty directories, links and existing
config/instructions/agents. An existing `.agents/skills` may retain unrelated skills,
but both skill link names must be free. No existing file is overwritten; no
config merge, global client write, copy, junction or elevation fallback is available.
If native links cannot be installed/observed, report the exact failing path and
inspect the retained `.agent-fabric/codex-project-pending.json` manually. There is no
automatic retry, repair or uninstall for partially owned state. If the command
reports a completed receipt followed by a Git publication error, use a fresh
`project git-cleanup` preview.

`codex-status` distinguishes filesystem `file_installation` (`absent`, `unmanaged`,
`incomplete`, `invalid`, `installed`) from the independent `desktop_discovery` and
`claim_restore` fields, both always `unverified` in this version. Runtime `status`
and `context` include this separate `project_adapter` report; adapter damage does not
silently convert into a global installation or an active Desktop claim.

### Git cleanup for installed project-only runtime and adapter

From the trusted source checkout implementing this command:

```bash
python -I -S -B scripts/run-fabric.py project git-cleanup <target> --preview --json
python -I -S -B scripts/run-fabric.py project git-cleanup <target> --apply --expected-preview-sha256 <preview_sha256> --json
```

Review the layout and Git exclusions before applying the digest. This updates
local Git exclusions for validated installed assets and preserves the pinned
runtime, memory, tasks, binding, settings and index. Run this after an install whose
receipt completed before Git publication failed. With a legacy pinned launcher,
preview cleanup again if a subsequent adapter installation adds links. See the
[existing-installation procedure](project-onboarding.md#git-cleanup-for-an-existing-project-only-installation).

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

### Explicit New Product discovery

New Product runs in Codex Desktop through either the project-local adapter or the
Codex plugin. Each path needs a real separate Socrates chat. For a project-only
installation, verify the bound Codex project, pinned context and installed adapter
with the local launcher and continue to the task preview below. For the plugin, choose
an existing empty folder, including no hidden entries. Detect the host/Bash and client,
then preview initialization with the user-level launcher:

```text
ai-agent-fabric project init <project> --client codex --require-empty --preview
```

Only after explicit approval of that preview, repeat without `--preview`.
`--require-empty` rechecks the folder before both preview and application; it never
creates a missing folder or removes entries. Initialization writes only the normal
local binding/profile/config/overlay/memory. It does not initialize Git, create a
remote repository, install dependencies, or reinstall global Fabric.

Both paths now preview a separate planned task with their own launcher. This
example uses the user-level launcher:

```text
ai-agent-fabric start <project> --title "<title>" --type planned --new-product --json
```

Repeat with `--apply` only after confirmation. `--new-product` is opt-in and rejected
for `small-bug`. The package and lifecycle remain ordinary planned work, defaulting to
`docs/specs/active/<task-id>/`. Mode is stored in the existing `session-state.md`,
without changing task metadata or the memory schema. Its `Mode: new-product` line and
single `## Next open question` section must be preserved by Socrates.
The existing task-start audit record also preserves the opt-in so removing that
markdown marker cannot turn a newly created New Product task into an ordinary task
to bypass MVP approval.

Start and restore pass `mode`, `skill`, `session_state`, and `next_open_question` to the
separate Socrates chat only for opted-in tasks. Root still only opens/reopens the chat;
brainstorming begins after claim. Ordinary starts/restores retain their existing output
shape. Restore is read-only and neither restarts discovery nor reinitializes the folder.
See the [New Product guide](new-product.md) for both launch paths, handoff and discovery.

New Product adds task-local `mvp-scope.json`, the authoritative MVP contract, distinct
from editable explanatory `spec.md`. Populate the initially empty contract before
preview. Its exact fields are:

```json
{
  "schema_version": 1,
  "scope": ["One offline checklist for one user"],
  "exclusions": ["Synchronization"],
  "acceptance_criteria": ["A saved checklist opens offline"],
  "constraints": []
}
```

All four content fields are arrays of non-blank strings; `scope` and
`acceptance_criteria` must be non-empty. Unknown fields and duplicate JSON keys are
rejected. Object-key order and JSON formatting do not change the canonical SHA-256;
array order and string content remain part of the contract.
Before closing or skipping discovery, claimed Socrates previews the exact MVP binding:

```text
ai-agent-fabric socrates approve-mvp <project> --session <id> --preview --json
```

Preview is read-only and returns structured `scope`, `scope_sha256`, and
`scope_artifact`. `spec_sha256` and `spec_revision` are informational, not approval
inputs. Present the structured contract and relevant explanatory risks to the owner.
After an explicit decision, write concise evidence inside this task's `evidence/`
directory, then record it. If the owner already explicitly decided this exact contract
in chat, cite and record that decision without asking again:

```text
ai-agent-fabric socrates approve-mvp <project> --session <id> --thread-id <current-thread-id> --reviewed-scope-sha256 <scope_sha256> --chat-reference <source> --artifact <task-package>/evidence/mvp-owner-decision.md --json
```

Approval writes require an explicit `--thread-id` exactly matching this task's stored
Socrates claim; read-only `--preview` does not. The id is not inferred from memory or
`--chat-reference`, which identifies the owner decision's source, not the calling chat.
This compares a caller-supplied id with the stored claim; it does not independently
authenticate the current Codex Desktop chat.

The existing memory `records` table stores this agent-attested approval, bound to the
task id, authoritative scope path, structured contract/canonical digest, and exact
decision-artifact digest. It does not authenticate the owner's identity independently.
Prose in session state cannot substitute for it.
Missing or stale approval rejects discovery closure/skip, subsequent lifecycle
transitions, and planning request submission/dispatch without advancing the task.
Editorial spec edits or spec-revision increments do not revoke MVP approval. Contract
changes require an explicit owner decision covering the new contract, not necessarily
a new question. Decision evidence is still byte-bound; changing it requires a new
attestation backed by the exact decision, not an automatic refresh.
Legacy full-spec-only approvals do not authorize a newly populated contract.
For an existing task, create `mvp-scope.json` from its agreed MVP, preview it, and attest
the exact prior explicit decision only if it really matches; otherwise resolve the
changed contract with the owner. There is no database migration or automatic conversion.
MVP approval never replaces the ordinary Kepler/reviewed-plan implementation approval.

New Product Plan requests must name this task's authoritative `mvp-scope.json` as
`scope_artifact` and the same task/session id. Enqueue internally pins the approved
scope digest without adding a public request input. After changed-scope approval,
old pinned or legacy unpinned queued requests still cannot dispatch. Socrates replaces
them using a fresh idempotency key and the current approval; no second owner approval
is needed. `memory pending-requests` and restore retain the old rows and add a bounded
`dispatch_guard` only for affected pending Plan requests: `state` (`obsolete` or
`blocked`), `reason`, and `recommended_action`. An obsolete request recommends
`replace-plan-request`; a missing decision recommends `record-exact-owner-decision`;
an unavailable contract recommends `inspect-mvp-scope-preview`. This is a read-only
diagnostic, not a new database status. Unaffected request output shapes are unchanged.
Already-dispatched work is not cancelled or restarted by this queued-request guard.

## Socrates and task specifications

| Command | Prerequisites and state change | Typical next step |
| --- | --- | --- |
| `socrates claim <project> --session <id> --thread-id <id>` | Prepared task; records its separate chat claim. | Read the durable continuation. |
| `socrates approve-mvp <project> --session <id> --preview` | New Product on Codex; reads structured MVP scope and canonical digest. Without `--preview`, requires explicit `--thread-id` matching this task's claimed Socrates chat, matching `--reviewed-scope-sha256`, decision source and task-local evidence; appends an approval record. | Close discovery through the ordinary step command; normal implementation gates still apply. |
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

### Project journal and release notes

Before the final lifecycle transition completes, Socrates records factual changes
and check outcomes in `close-out.json` in the task package. Use the
`schemas/close-out-facts.schema.json` contract. All evidence references in the facts
file are relative to the package.

```json
{
  "schema_version": 1,
  "changes": [
    {"summary": "Added a report filter", "evidence": ["evidence/implementation.md"]}
  ],
  "checks": [
    {"name": "Unit suite", "outcome": "skipped", "reason": "Not requested", "evidence": []}
  ]
}
```

Use `passed` and `failed` with a reference to the observed result. Use `skipped`
or `unknown` with a reason when execution or its outcome cannot be established.
Fabric validates evidence paths and records their digests. Invalid or missing
facts prevent completion and can be corrected before retrying. A task's entry
survives archive and includes only locally verified specialist contributions.

Run `project journal <project> --json` to read the captured entries. To assemble
notes, run `project release-notes <project> --version 1.2.0 --task first-task --task second-task`.
The operation writes one local file at
`.agent-fabric/release-notes/whats-new-1.2.0.md`. Select each included task
explicitly. Tasks completed before journal capture was available can be viewed
through their existing history and are ineligible for this operation.

Versions use 1–64 ASCII letters and digits, with optional dot or hyphen separators
between groups. Filenames and headers use the lowercase version. The command
requires a filesystem supporting atomic hard-link creation. Identical input can
be replayed. An existing file with different bytes produces a conflict. Closing a
task records its journal entry. Creating release notes and publishing them are
separate actions.

## Memory, Guards and Harness

`memory init` writes project-local memory; `memory restore`, `memory quarantine`,
`memory pending-requests` and `memory pending-results` inspect local state. They take a
project, with a session identifier where shown by `--help`.

Specialists hand off a validated delegation-result envelope with
`memory submit-result <project> --result <json> --json`. The command enqueues
the result for its matching dispatched request. Socrates manages the queue with
`socrates submit-request <project> --session <id> --thread-id <id> --request <json>`,
`socrates dispatch-request <project> --session <id> --thread-id <id> --key <request-key>`,
and `socrates acknowledge-result <project> --session <id> --thread-id <id> --key <result-key>`.
These commands require the session's claimed thread ID. The ID is checked against
project-local state and does not independently authenticate the calling client.

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

The Codex plugin ships New Product. The project-only runtime includes the same
skill in its pinned release, and the optional project adapter links it into the
project's `.agents/skills`. Legacy direct user-level Codex skill links retain their
five-name registry. Starting or restoring a project task makes no adapter changes.

`bootstrap bash` reports an installation plan; `--install` explicitly applies it.
`secret prompt <project> --destination <relative-path> --label <label> --preview`
checks the destination without accepting a secret. Without `--preview`, it uses the
declared hidden terminal entry; never put a secret in an argument or chat.
