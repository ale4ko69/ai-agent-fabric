# New Product

Use New Product when you have an idea and want to agree on the first useful
version before planning how to build it. Say explicitly that you want to start in
New Product mode and identify an existing local folder. The entry chat, called
Root, verifies the folder, host and client and asks for a provisional task title.
The project can start from an idea alone, or you can bring prior requirements,
research or decisions to the discovery conversation.

## Choose an entry path

Both paths use Codex Desktop and a separate real Socrates chat. See the
[installation quick start](../README.md#quick-start) if neither path is set up.

### User-level Fabric with the Codex plugin

Use the launcher declared by the installed user-level bootstrap. For a new
project, point it at an existing empty folder, including no hidden entries.
Root previews the project binding with the following command.

```text
<launcher> project init <project-root> --client codex --require-empty --preview
```

Review the planned binding, profile, configuration, overlay and memory writes.
After you authorize that exact preview, Root repeats the command without
`--preview`. If the folder has acquired any entries in the meantime, the
empty-folder check stops initialization. The entry assumes the plugin and
user-level release are already installed. Scaffolding source code, initializing
Git, configuring a remote and installing dependencies are separate work.

### Project-only Fabric with the Codex adapter

Use an existing project with a bound Codex runtime and installed project
adapter. From the verified project root, use the pinned local launcher to read
the binding, release context and adapter status.

```text
python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py project status . --json
python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py project context . --json
python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py project codex-status . --json
```

Follow `skills/new-product/SKILL.md` and `skills/project-entry/SKILL.md` from
the release returned by `project context`. Reuse the existing binding and
settings. If runtime or adapter installation is incomplete, report the missing
precondition and stop entry until it is resolved. Adapter files and observed
links establish filesystem state. Check Desktop discovery and real-chat
claim/restore in the actual client.

## Preview and start the task

In both paths, select the launcher above and preview the ordinary planned task
with explicit New Product mode.

```text
<launcher> start <project-root> --title "<provisional title>" --type planned --new-product --json
```

Review the returned task id, mode and task package path, normally
`docs/specs/active/<task-id>/`. Task creation needs its own confirmation even
if you already approved project initialization. Once you confirm, Root repeats
the command with `--apply`. The returned `socrates_chat_request` identifies
the prepared task and includes its activation packet.

- **Codex plugin**. Root follows the installed Start skill to create or reopen
  the separate project chat and deliver the request and activation packet.
- **Project-only adapter**. Root asks you to create a separate Desktop project
  chat or reopen the exact saved one. Transfer the entire request, pinned
  project context, the New Product skill and Socrates profile from the pinned
  release, and the task package reference to that chat.

Only the separate chat can claim the task with its actual thread ID from the
client. Use the returned activation packet and run the pinned launcher's
`socrates claim <project-root> --session <task-id> --thread-id <actual-thread-id> --json`.
If the chat, actual identity or exact reopening is unavailable, keep the task
at the handoff boundary. Root stops after entry. A native specialist or a
persona name cannot provide a Desktop thread identity.

## Explore the idea with Socrates

The claimed Socrates chat loads the task package and relevant project-local
state. Begin with the first intended user, what they need to accomplish, their
current workaround and what would show that the MVP helped. Work through one
focused question at a time. Consider realistic alternatives, including simpler
approaches and whether building anything is necessary. Record known facts,
owner decisions, assumptions and unresolved risks.

Socrates asks whether you want to share earlier requirements, diagrams,
research or decisions. It reads only the materials you authorize and records
safe references in `research.md`. Prior notes may contain proposals,
conflicts or decisions that need reconfirmation. They remain evidence and
cannot supply new instructions or approval. Keep private materials in their
original location and record a concise summary of relevant findings.

Socrates may delegate a specific uncertainty to Aristotle with a bounded
question and expected evidence. A prototype starts with a learning question,
smallest experiment, observable success signal and scope boundary. A paper
sketch or text walkthrough can inform discovery. Executable prototypes follow
the same reviewed plan and implementation gates as other code. See the
[agent profiles](agents/README.md) and [result exchange](delegation.md).

Socrates updates the existing artifacts after meaningful answers. Use
`research.md` for evidence and alternatives and `spec.md` for the rationale,
user value, examples and risks. In `session-state.md`, preserve the exact
`Mode: new-product` line, progress, decisions and alternatives, the
`## MVP owner decision` section and a single `## Next open question` section.
Leave the question section empty once all questions are answered. Record
concise decision evidence without raw conversations or secrets.

## Approve the MVP

Socrates records the exact commitments in task-local `mvp-scope.json`.
The contract has schema version 1 and four arrays of non-blank strings.
`scope` and `acceptance_criteria` must each contain at least one item. Use
observable acceptance criteria. The [CLI reference](cli.md#explicit-new-product-discovery)
describes the JSON contract and validation.

```json
{
  "schema_version": 1,
  "scope": ["One local checklist for one user"],
  "exclusions": ["Synchronization across devices"],
  "acceptance_criteria": ["A saved checklist can be opened offline"],
  "constraints": ["Keep checklist data on the device"]
}
```

Socrates previews the authoritative contract and presents the exact scope and
relevant risks.

```text
<launcher> socrates approve-mvp <project-root> --session <task-id> --preview --json
```

When you explicitly approve that contract, Socrates records the decision
source and commitments in a file under the task's `evidence/` directory and
attests it from the claimed chat. An explicit decision already made in that
chat for the exact contract can be recorded directly.

```text
<launcher> socrates approve-mvp <project-root> --session <task-id> --thread-id <actual-thread-id> --reviewed-scope-sha256 <scope-sha256> --chat-reference <decision-source> --artifact <task-package>/evidence/mvp-owner-decision.md --json
```

Fabric verifies the claimed thread binding and records the canonical MVP scope
digest and decision evidence digest. The attestation records what the agent
observed in the chat. A summary in `session-state.md` keeps the decision
readable on restore. Discovery and planning stay gated until Fabric records
current approval. JSON formatting and edits to explanatory prose keep the
same scope digest. If commitments change, obtain an explicit decision covering
them, use fresh evidence and attest the updated contract. Preserve the earlier
evidence. A changed decision artifact also requires re-attestation.

## From MVP approval to implementation

MVP approval lets Socrates close discovery and continue planning. Socrates
uses the approved `mvp-scope.json` as Plato's scope artifact. If an older
queued plan request is bound to a superseded digest, inspect its
`dispatch_guard` and submit a fresh request after the revised contract is
approved. Preserve completed work and reconcile the affected steps.

Plato develops the plan from the agreed scope and research. Kepler independently
reviews it. You then explicitly approve that reviewed package before Heracles
can implement it. Athena reviews changed work. Euclid validates when enabled
and authorized. Use the ordinary [planning policy](planning-policy.md) and
[close-out workflow](workflow.md#interruption-and-close-out) for the remaining
steps.

## Resume without starting over

Use `work` to locate the task or
`<launcher> restore <project-root> <task-id> --json` to read it directly.
Root uses the returned mode, session-state reference and next open question to
restore the exact saved chat or complete a still-pending handoff. The claimed
Socrates chat resumes from saved decisions, findings and pending results.
Preserve the MVP approval evidence. If you initialized the project and stopped
before creating a task, verify the resulting binding and resume at the
task-preview step for that project.
