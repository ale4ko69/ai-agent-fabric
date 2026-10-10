# Restore per-project Socrates task lifecycle

## User Value

Each bound project must be able to start its own Socrates orchestrator. That
orchestrator, rather than a host/root chat, owns task routing, bounded delegation,
durable project state, Harness signals, and the safe next action for that project.

## Scope

- Make `start task` the creation-and-activation boundary: after explicit approval has
  created a task package, it starts that task's project-local Socrates session.
- Make `restore task` the recovery-and-activation boundary: it restores the selected
  task and resumes its project-local Socrates session without restarting completed
  work. There is no separate `start orchestrator` command.
- Make Socrates the sole writer of project memory, Harness signals, structured failure
  records, and Guard outcomes. Specialists return bounded results and artifacts only.
- Restore an explicit Guards / Process Gate path for concrete failures: record the
  failure with an evidence reference, then apply the declared block, retry, or
  escalation policy. It must not be confused with a Harness behavioural signal.
- Preserve the separate Harness path: a user correction or behavioural concern records
  only a minimal pointer; retrospective analysis requires evidence, Kepler review, and
  human approval before any improvement is applied.

## Non-Goals

- Do not make agents write memory, signals, failures, or Guard outcomes directly.
- Do not capture private chat transcripts or create an implicit lifecycle hook.
- Do not automatically modify instructions, profiles, workflow, or a global release
  from a signal or failure.

## Acceptance Criteria

- `start task` creates the approved task package and starts its local Socrates session;
  `restore task` resumes that same session from durable state before doing work.
- Neither command creates a global/root orchestrator or requires a separate
  `start orchestrator` command.
- Delegation flow shows each role, its bounded responsibility, and the return path to
  Socrates.
- A concrete Guard failure is persisted with a category/taxonomy, task/session link,
  safe evidence artifact reference, policy outcome, and idempotency protection.
- A Harness signal remains an identifier-only retrospective pointer and never triggers
  a Guard automatically.
- Guards can make only their declared decision: permit, block, request bounded retry,
  or require user escalation; they cannot mutate the task scope or instructions.
- Recovery exposes pending failures and Guard outcomes to Socrates without restarting
  a completed step.
- Before the task is reported complete, Kepler reviews the implemented lifecycle and
  the transfer evidence; after that verdict, the implementing agent performs a separate
  source-to-target audit for omissions and records the result in task evidence.

## Constraints

- State remains below the bound project's `.agent-fabric/` directory and task package.
- The implementation must remain portable and client-neutral; client hooks are optional
  adapter capabilities, not a requirement for correctness.
- Project facts, credentials, and raw conversation text are excluded from all records.

## Open Questions

- The first portable contract exposes Guards through the launcher and requires
  Socrates to invoke it. A future adapter hook may call the same contract only after
  declaring an installed, reversible hook implementation.
- The portable initial retry policy is fixed at two retries followed by escalation for
  the same task/taxonomy/Guard; project-specific policy remains future profile work.

## Completion Sequence

1. Run the targeted and full validation required by the implemented contracts.
2. Ask Kepler to review the changed implementation, tests, and transfer evidence.
3. Resolve or explicitly defer every Kepler finding with evidence.
4. Perform a separate implementation-owner audit against the source Fabric inventory:
   compare lifecycle, failure-record, Guard, recovery, and client-adapter behaviour;
   record every transferred, intentionally excluded, and still-missing item.
5. Report completion only after both the Kepler verdict and this post-transfer audit
   are present and the open omissions are either fixed or explicitly approved as
   deferred.
