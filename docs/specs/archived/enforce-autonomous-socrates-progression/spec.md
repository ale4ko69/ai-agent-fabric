# Enforce autonomous Socrates progression

## User Value

Once a claimed Socrates chat completes an internal lifecycle step, the Fabric runtime
must durably resume the next bounded internal action. A task must not appear to be a
safe stopping point merely because `next_action` has been recomputed in SQLite.

## Scope

- Make the task-lifecycle transition atomically close the current internal step and
  resume the next internal step.
- Model the three legitimate non-running states: an explicit owner-approval wait, a
  Guard-derived external block or escalation, and completed work.
- Return the resulting continuation state through the Socrates step API and CLI.
- Require every non-running outcome to state why execution stopped and recommend the
  next owner action; the runtime must not return a silent wait.
- After clean review and validation, require a durable rollout step that owns the
  already-authorized task-scoped commit, push, and declared project release.
- Preserve existing claimed-chat, evidence, ordering, and immutable-closure rules.
- Add regression coverage for automatic internal continuation, explicit approval
  waiting, final completion, and migration of existing project memory.

## Non-Goals

- Do not create a background worker, send messages, or let the runtime impersonate a
  human owner or specialist.
- Do not change Fabric releases, bindings, Git history, or task approval semantics.
- Do not infer owner approval from a generic pending step.

## Acceptance Criteria

1. Completing or skipping an internal step atomically moves the next internal step to
   `in-progress` and exposes it as the active bounded continuation.
2. The only lifecycle waits are `awaiting-owner-approval`, Guard-derived blocked or
   escalated states, and `completed` after the final workflow step.
3. The approval boundary is explicit: after Kepler, the runtime reports an owner
   approval wait rather than leaving a generic internal step pending.
4. Every approval wait, Guard block/escalation, and completion response includes a
   stable reason and a concrete recommended next action.
5. Existing current-schema project memory migrates explicitly and safely.
6. Targeted regression tests demonstrate each transition and preserve existing
   lifecycle invariants.
7. A task cannot reach completed state until its rollout step has durable delivery
   evidence; autonomous delivery does not prompt for each routine command.

## Constraints

- Keep the core portable and client-neutral; no Codex-specific task progression
  mechanism belongs in the runtime.
- Keep durable mutation inside the claimed Socrates boundary.
- Do not run the full test suite unless validation is explicitly requested.

## Open Questions

None. The owner explicitly authorized this scoped runtime change and regression
coverage; no external integration is required.
