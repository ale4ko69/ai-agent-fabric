---
name: agent-fabric-new-product
description: Codex-plugin-only New Product v1. Explicitly opt into collaborative discovery in an existing empty local folder, then hand the ordinary planned task to its claimed Socrates chat. Not the default start workflow.
---

# New Product

Use only when the owner explicitly chooses New Product. Do not infer this mode from
an empty repository, a feature request, or an ordinary `work`, `start`, or `restore`.
This is a discovery skill inside the existing workflow, not another agent or pipeline.
Use only the portable Fabric release and this project's own context.

V1 is delivered only through the supported **Codex plugin** surface and its separate
chat handoff. Copilot and Claude end-to-end New Product delivery is not supported.
Their normal Fabric onboarding/start/restore plumbing remains unchanged. Do not
substitute another client, install a plugin, or implement a project-only installation
path to get around this limitation; report the unsupported surface and stop.

## Root: local entry only

1. **Choose the folder first.** Ask the owner to select an existing empty local
   folder. Confirm its resolved path. Count hidden entries too; `.git` or
   `.agent-fabric` means it is not empty. Do not create a folder, initialize Git,
   clone a repository, or select a remote on the owner's behalf. A non-empty folder
   belongs in normal project onboarding, not fresh New Product initialization.
2. Detect the host and available Bash before selecting shell commands. Use
   `detect-client <project-root>` and the actual conversation client to confirm the
   supported Codex plugin surface; no local marker in an empty folder is not proof
   of a client. If the surface or separate-chat capability is unavailable or unclear,
   stop before initialization. Use the canonical installed Fabric launcher, not a
   target-project executable. Inspect read-only `project status`.
3. **Preview normal project initialization:**

   ```text
   <fabric-launcher> project init <project-root> --client codex --require-empty --preview
   ```

   Explain the returned project-local binding, profile, config, overlay, and memory
   paths. There is no global reinstall, client enablement, source scaffolding,
   dependency install, GitHub repository, or remote write. Obtain explicit owner
   approval of this exact path/client/release preview. Only then repeat the command
   without `--preview`, keeping `--require-empty`. If the folder acquired any entry
   in the meantime, stop rather than deleting or overlooking it.
4. Read the bound `project context`. Collect only a provisional task title for
   entry; do not conduct product brainstorming as Root. **Preview normal task start:**

   ```text
   <fabric-launcher> start <project-root> --title "<title>" --type planned --new-product --json
   ```

   Show the id, mode, and local package path, normally
   `docs/specs/active/<task-id>/` or the profile's configured task root. This is a
   separate approval from initialization. After explicit confirmation of the task
   preview, repeat with `--apply`. Declining either preview leaves that operation
   unapplied; initialization approval never implies task creation approval.
5. Follow the ordinary start skill's separate-chat handoff through the Codex plugin
   surface. Forward the complete `socrates_chat_request`, including `mode`,
   `skill`, `session_state`, and `next_open_question`. Create the separate
   chat with `create_thread`, then deliver the activation packet using its returned
   thread id. Do not say Socrates is running merely because the package exists.
   Only that separate chat runs `socrates_activation` and claims the durable task id.

Root stops at entry/recovery. Root must not brainstorm, plan, delegate, implement,
or write discovery decisions. If binding, task creation, chat creation/reopening, or
activation delivery fails, report it and use the explicit recovery path only.
Do not continue task work in Root.

## Claimed Socrates: collaborative discovery

After claiming, load the pinned contracts, local profile, task artifacts, relevant
existing project memory, pending delegation requests, and unacknowledged results.
Use the existing project-local memory and outbox; do not introduce a new store.
Socrates alone persists discovery decisions and durable memory and acknowledges
specialist results. Specialists return bounded structured results through the normal
outbox rather than writing session state or episodic memory themselves.

Work with the owner, not as a one-shot requirements generator:

- Begin with the saved next open question. Ask a small, focused question at a time
  about the first user, concrete problem, current workaround, desired outcome, and
  constraints. Reflect the answer and check understanding before narrowing scope.
- Explore meaningful alternatives and their trade-offs, including a simpler or
  no-build option. Separate evidence, owner preferences, assumptions, and unknowns.
  Keep rejected alternatives and deferred ideas in `research.md` and the session
  decisions; do not silently discard or implement them.
- Delegate selectively to Aristotle only when a specific uncertainty needs evidence.
  State the question, bounded scope, expected evidence, and stop condition in the
  normal delegation contract. Reuse relevant evidence rather than automatically
  researching every topic. Socrates discusses the returned evidence with the owner.
  External access is subject to the project's ordinary permissions.
- Offer a prototype only to answer an agreed question. First agree the question,
  smallest experiment, success signal, and time/scope boundary. A text walkthrough
  or paper sketch can be discovery evidence. Executable prototypes, UI code,
  scaffolding, dependencies, services, and implementation commands still require the
  ordinary approved plan and implementation gates; “prototype” is not a bypass.

Before normal planning, summarize the proposed MVP in `spec.md`: user value, included
scope, non-goals, observable acceptance criteria, constraints, and unresolved risks.
Present that exact proposal to the owner and ask for explicit scope-and-acceptance
approval. Keep `discovery` open until the owner decides. First obtain the read-only
scope binding:

```text
<fabric-launcher> socrates approve-mvp <project-root> --session <task-id> --preview --json
```

Present that spec revision and full `spec.md` to the owner. After an explicit approval,
write a concise task-local decision artifact under this package's `evidence/`, naming
the accepted scope/acceptance criteria and decision source, not a raw conversation.
Then, only in the claimed Socrates chat, record the agent-attested decision:

```text
<fabric-launcher> socrates approve-mvp <project-root> --session <task-id> --reviewed-spec-sha256 <preview-digest> --reviewed-spec-revision <preview-revision> --chat-reference <decision-source> --artifact <task-package>/evidence/mvp-owner-decision.md --json
```

This uses existing task memory records, not another database or approval file format.
Like the existing chat-approval method, it trusts Socrates' assertion of an explicit
owner decision; it is not independently authenticated identity. Summarize the result
under `## MVP owner decision` in `session-state.md`, but a prose note alone does not
unlock planning. Discovery cannot be closed or skipped, and planning cannot be
advanced or delegated, without a current approval record. Any change to `spec.md`,
its spec revision, or the bound decision artifact invalidates that binding and
requires a fresh owner decision/attestation. A suggestion, brainstorming answer, or
interest in a prototype is not approval.

Then continue the ordinary planned workflow: evidence/research, Plato plan, independent
Kepler verdict, explicit owner approval of that reviewed package, scoped implementation,
Athena review, authorized validation, and normal close-out/rollout/archive. MVP approval
does not authorize implementation, tests, installation, delivery, or remote actions.
All ordinary project permissions and gates still apply.

## Interruption and restore

After each meaningful answer or decision, Socrates updates the existing task artifacts
and `session-state.md`, preserving the exact `Mode: new-product` line. Keep one
`## Next open question` section with the actual next unanswered question (or leave it
empty when none remains), plus decisions, alternatives, assumptions, research
references, progress, and the MVP owner decision. Never store secrets or raw chat logs.

Resume through ordinary `restore`, not another init or start. It returns the saved
mode and next question in the chat request without changing state. Root reopens the
saved Socrates thread when present and forwards the complete request. After claim,
Socrates reads the referenced session state and current lifecycle before continuing;
do not restart brainstorming or repeat completed research or approvals. If initialization
succeeded but task creation has not, inspect the binding and resume the task-preview
step without requiring the now-bound folder to be empty again. Partial initialization
requires explicit recovery, not a reinstall or cleanup of owner files.
The durable MVP approval remains in the existing memory audit trail; restore is not
an approval operation. Preserve its referenced evidence and re-attest only when the
scope/revision or decision evidence has changed.
