# Portable development workflow

This is the common workflow for a bound project. It is intentionally free of repository
paths, tracker identities, service ports, client-specific commands, and credentials.
Those belong to the project profile and optional adapters.

```text
Root opens project through a selected client
        |
        v
read-only Fabric status -> bound release + local profile + local memory
        |
        v
detect host/client capabilities -> restore relevant task state
        |
        v
Root creates or reopens the task's separate Socrates chat
        |
        v
Socrates claims the durable task id and owns all remaining transitions
        |
        v
triage the work
  | local correction        | small bug             | planned work
  v                         v                       v
bounded edit + evidence   tasks + evidence     spec -> research -> plan
                                                  |              |
                                                  v              v
                              Aristotle evidence -> Plato plan -> Kepler verdict
                                                  |
                                                  v
                                           revision, if required
                                                  |
                                     required human approval
                                                  |
                                                  v
                                        scoped implementation
                                                  |
                                      Athena review -> validation
                                                  |
                                                  v
                                      evidence -> close-out -> rollout -> archive
```

## Session start

1. The global bootstrap checks Fabric status without writing files.
2. A bound project loads only its pinned release, project profile, local overlay, and
   relevant project-local memory.
3. Detect host, Bash, Python, Git, and selected client before selecting a command.
4. Restore the active task package and pending specialist results when work resumes.
5. If the repository is not bound, report that fact and show initialization preview
   only after the person asks to enable Fabric for it.

## Entry and restore discipline

A client-facing `work` entrypoint is a router, not another workflow: it either restores
one known active task or starts new-task intake. It never silently starts over and never
mixes multiple task packages. `start --apply` creates a prepared task package and a
`socrates_chat_request`; it must not claim that Socrates is running. The selected client
adapter creates or reopens a separate chat for that task. Socrates claims the returned
task id with that chat's thread id before lifecycle activation. Root remains only the
entry and recovery boundary and must not impersonate Socrates or progress the task.

For new planned work, Socrates materializes the applicable workflow checklist in the
task package. Each step is `pending`, `in_progress`, `done`, or `skipped`; a completed
step names evidence, while a skipped step names its reason. Discovery records facts,
conflicts, confidence, and blocking questions before planning or implementation.
Client-specific slash commands may render this protocol only through a selected adapter;
the protocol itself never assumes a Copilot command folder or a global project path.

## Triage and planning

- A local correction is a known isolated textual or styling fix; it retains changed-file
  evidence but needs no task package or plan.
- A small bug is reproducible, narrow, and already understood. It uses `tasks.md` and
  proportionate evidence without a spec or plan.
- A feature, a reproducible bug that is not already understood, or a feature rework is
  planned work. It requires a task package containing spec, research, plan, Kepler
  verdict, tasks, evidence, and session state.

For planned work, Aristotle establishes evidence, Plato creates the bounded plan, and
Kepler independently challenges it. Kepler cannot widen the spec: a new concern is
deferred or explicitly accepted by the human owner as a spec amendment, after which
Plato revises the plan and Kepler gives a fresh verdict.

## New Product (opt-in)

The explicit `new-product` skill is a discovery mode for ordinary planned work, not
the default entry, a new role, or a second lifecycle. **V1 delivery supports only the
Codex plugin surface and its separate-chat handoff.** It does not claim end-to-end
Copilot or Claude New Product support; their ordinary Fabric plumbing is unchanged.
On an unsupported surface, stop without initialization, installation, or a substitute
handoff. Project-only installation remains a separate future design, not this feature.

First the owner chooses an existing
empty local folder. Root detects host/Bash and client, presents canonical
`project init --client codex --require-empty --preview`, and obtains explicit approval before applying
the local binding/profile/config/overlay/memory writes. No source scaffold, Git setup,
remote repository, dependency installation, or global reinstall belongs to this entry.

After initialization, Root separately previews
`start --type planned --new-product`, obtains confirmation, and applies the ordinary
start. It creates the normal task package under the configured root
(`docs/specs/active/<task-id>/` by default) and requests a separate Socrates chat.
Root forwards the entire request, including the saved mode and next open question,
and stops. Root remains entry/recovery only; real brainstorming starts only in the
separate chat after its durable claim.

Socrates collaboratively explores users, problems, outcomes, constraints, alternatives,
and trade-offs. It asks focused questions, distinguishes assumptions from facts, and
uses Aristotle selectively for bounded research rather than launching a mandatory
research phase for every idea. An optional question-led prototype must have an agreed
learning question, scope, and success signal; executable implementation still needs
the normal reviewed plan and owner approval.

Before normal planning, Socrates fills task-local `mvp-scope.json` with the agreed
scope, exclusions/non-goals, observable acceptance criteria, and constraints.
It is the authoritative MVP contract; `spec.md` remains editable explanation including
user value, rationale, and unresolved risks. The [exact JSON shape](cli.md#explicit-new-product-discovery)
has no undeclared fields or duplicate keys.
`socrates approve-mvp --preview` reads that structured scope and its canonical digest;
spec digest/revision remain informational. Socrates presents the contract and relevant
risks, keeping discovery open until the owner's explicit decision. If the owner already
explicitly approved this exact contract in chat, record that decision instead of asking
again. A suggestion or historical proposal is not a decision on changed scope.
Claimed Socrates records the agent-attested decision with `--reviewed-scope-sha256`,
the actual current thread id, a chat reference, and an existing decision artifact inside
this task's `evidence/`. This uses existing memory records and the authorization trust
model, not a new database schema or independent proof of owner identity.

The runtime rejects closing or skipping discovery, further lifecycle transitions, and
planning delegation submission/dispatch without a current MVP approval. The record
binds the task id, authoritative scope path, structured contract/canonical digest, and
exact decision-artifact digest. Formatting the JSON, editing explanatory prose, or
incrementing spec revision does not revoke MVP approval. Changing the contract requires
an explicit owner decision covering the change; reuse an already explicit matching
decision without a duplicate question. Changed decision evidence still requires
re-attestation, never silent acceptance. Legacy approvals bound only to full spec text
fail closed: populate the structured contract from the agreed MVP and explicitly attest
the prior decision only if it matches. No automatic conversion or database migration.
A prose session-state note alone cannot unlock planning. A task-start audit marker
preserves the opt-in even if its markdown marker is subsequently removed. This gate
authorizes planning only, not implementation; ordinary reviewed-plan approvals still
bind their full artifacts/revisions and are not weakened by this MVP rule.

Fold intersecting owner instructions into the same task and update the contract only
when scope, non-goals, acceptance, or constraints actually change. Preserve completed
progress, findings, and current work; continue unaffected permitted steps rather than
restarting discovery or opening a duplicate task. Reconcile only the impacted work
with the explicit owner decision and ordinary gates.

At enqueue, a New Product Plato (`plan`) request must reference this task's authoritative
MVP scope path and is internally pinned to the approved digest. At dispatch, stale
or legacy unpinned queued requests fail closed even after a new approval. Socrates
replaces them with a fresh request/idempotency key using the current approval, without
asking the owner again. Pending-request/restore views retain obsolete rows with an
actionable read-only `dispatch_guard` diagnostic, not another SQLite status or a deleted
task. Unaffected requests keep their public shape; already-running Plato is outside this
queue case and is not reset or cancelled.

Only Socrates persists discovery decisions and episodic memory. Aristotle and other
specialists use the existing delegation/outbox protocol. The existing
`session-state.md` stores `Mode: new-product`, progress, alternatives, the MVP owner
decision, and one `## Next open question` section. Socrates updates it after meaningful
answers; restore returns the saved question and state reference without writing or
restarting discovery. The saved chat, pending results, and ordinary checklist remain
authoritative. No new memory store or schema is introduced.

After MVP approval, all ordinary planning, Kepler review, reviewed-package owner
approval, implementation, review, authorized validation, and delivery gates remain.
Ordinary start/restore outputs and workflow are unchanged unless this mode was chosen.

## Execution and review

Heracles implements only the approved scope. After a state-changing action, the
orchestrator records fresh evidence before deciding the next action; it does not repeat
an assumed-successful command. Athena independently reviews changed work against the
acceptance criteria. Euclid performs validation only when the project has enabled its
validation capability. A checkpoint records evidence labels against the immutable gate
registry; it is not a substitute for the underlying evidence.

Any agent editing a file first inspects its current state and preserves the owner's and
other agents' changes. When the intended edit conflicts, stop on that file, report it
and agree on a resolution instead of overwriting or reverting those changes. This is a
practical operational rule, not an atomic guarantee against all concurrent processes.

## Interruption and close-out

Specialist results enter the project-local outbox with an idempotency key. Socrates is
the sole durable-memory writer and can replay unacknowledged results safely after an
interruption. `harness resume` remains read-only; `restore` returns the saved Socrates
chat binding or a request to create it, but does not execute project work. Closing a
task requires the applicable local evidence and moves its package to a recoverable
archive; it never deletes history. When the owner has declared autonomous delivery,
successful review and validation automatically resume the durable `rollout` step.
Socrates commits only task-scoped changes, pushes to the configured remote, and invokes
the project's declared release action before it may complete the task. A Guard outcome,
missing delivery mechanism, or newly required scope/credential is an actionable
blocker; routine commit, push, and release operations do not require separate approval.

After `rollout` completes, the claimed Socrates chat uses `socrates archive` with an
auditable reason. The package moves from `active` to `archived`; the router can then
start the next task without mistaking completed work for an active lifecycle. A terminal
Guard resumes only through `socrates resolve-guard`, with a fresh project-local evidence
artifact and the owner's recorded direction.

## Guards and concrete failures

When a declared Gate or concrete command fails, Socrates first writes an evidence
artifact, then records it through `guards failure`. Guards return a deterministic
`retry`, `block`, or `escalate` outcome and never rerun work themselves. A
`retry-then-escalate` policy retries only the first two failures for the same
session/taxonomy/Guard, then escalates the third. A Harness behaviour signal is not a
Guard failure and does not invoke a Guard. See [Guards](guards.md).

## Harness retrospective

When a user corrects agent behaviour, a required instruction is missed, or a repeated
failure appears, Socrates records a minimal project-local Harness signal without copying
the conversation. On demand, Harness reads all signals since its last approved run, and
Socrates creates an evidence-backed retrospective report. Kepler reviews each proposal
for proof and scope; the human accepts, rejects, or defers it. The Harness cursor
advances only after that approval using the input's immutable signal-log watermark. It does not use calendar gaps, so a project may be
inactive between runs without losing the correct analysis window. Client hooks may help
capture or restore this state, but only through the selected adapter. See
[Harness](harness.md).

## Optional integrations

Tracker, repository-host, notification, documentation, and UI/UX actions are not
workflow prerequisites. A project enables each through a declared capability and
configuration. No remote update happens solely because a task was opened or resumed.
