# Research — Enforce autonomous Socrates progression

## Evidence

- `memory.advance_task_step` only changes one `task_steps` row, then calls
  `_next_task_action`. The latter returns the first pending or in-progress step, so a
  completed step can leave a later internal step merely pending.
- `task_lifecycles.status` currently accepts only `active`, `blocked`, and
  `escalated`; it cannot distinguish an owner-approval wait from an incorrectly
  abandoned active task or from completion.
- Claimed-chat enforcement, workflow ordering, closure evidence, and Guard-derived
  block/escalation are already implemented and must remain the authority boundary.

## End-to-end progression map

```text
claimed Socrates chat
  -> closes current step with existing evidence
  -> transaction derives outcome
       -> next internal step: mark it in-progress + return continuation
       -> human-approval: awaiting-owner-approval + return approval request
       -> Guard block/escalation: blocked or escalated + return blocker
       -> no remaining step: completed + return completion
  -> Socrates continues the returned bounded action, waits only for the returned
     explicit approval/blocker state, or reports completed work
```

The map is used as the design invariant: no successful internal closure may leave an
`active` lifecycle with its next internal step still `pending`.

For every non-running branch, the returned state must include `reason` and
`recommended_action`. They are bounded runtime values, not free-form chat output:
for example, an approval wait instructs the owner to approve the reviewed package, a
blocker identifies its Guard state and asks for the required external resolution, and
completion recommends archive or close-out according to the task lifecycle.

## Options

1. Add more wording to the generated Socrates instruction. Rejected: it cannot
   prevent a model from returning while durable state still represents a pending
   internal action.
2. Add a separate manual `resume` command. Rejected: it creates the same gap between
   a completed step and the resumption call.
3. Make the closure transaction derive and persist the continuation state. Selected:
   the durable runtime itself guarantees the transition, while the chat remains
   responsible for actually carrying out the returned bounded action.
4. Leave explanation to the chat alone. Rejected: an interrupted or poorly behaving
   chat could still expose an opaque idle lifecycle. The runtime must return the
   bounded explanation and recommendation with the stop outcome.

## Rejected approaches

- A background dispatcher or automatic agent messaging would be client-specific and
  expand the runtime beyond its portable, local contract.
- Treating every `in-progress` row as an approval wait would conflate internal work
  with the one human-owned gate.
