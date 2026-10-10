# Guards and concrete failures

Guards process concrete, evidenced execution failures. They are not the Harness
retrospective and they do not store conversation text.

## Ownership and flow

```text
specialist returns typed result or command evidence
  -> Socrates writes a project-local evidence artifact
  -> Socrates invokes `guards failure`
  -> durable failure + deterministic Guard outcome are written to memory.db
  -> identifier-only Guard audit is appended to harness/trace.jsonl
  -> Socrates obeys retry, block, or escalation outcome
```

Specialists never call the Guards writer and never write `memory.db`, Harness signals,
failure records, or outcomes. They return artifacts and typed results to Socrates. The
Socrates lifecycle is started by `start task` and resumed by `restore task`; it is the
only actor allowed to invoke the Guards command.

## Durable record

Every failure needs these fields:

- `session`: the task-local Socrates session;
- `idempotency-key`: one stable key for this observed failure;
- `incident-id`: a stable key shared only by retries of the same incident;
- `guard`: a release-declared immutable policy boundary (which supplies its taxonomy
  and policy); and
- `artifact`: an existing, project-relative evidence artifact.

The database stores the failure and its outcome separately in `guard_failures` and
`guard_outcomes`. Replaying the same idempotency key returns the original outcome; it
does not create another failure or consume another retry. Task restoration includes
both lists, so Socrates sees unresolved blocked or escalated work before choosing the
next action.

```bash
ai-agent-fabric guards failure /path/to/project \
  --session <task-id> \
  --idempotency-key <stable-observation-id> \
  --incident-id <stable-incident-id> \
  --guard command \
  --artifact docs/specs/active/<task-id>/evidence/test-failure.md --json
```

`block` returns `block` immediately. `retry-then-escalate` returns `retry` for the
first and second recorded failures for the same session/taxonomy/guard; the third
returns `escalate`. Guards do not silently rerun a command: Socrates must create a new
bounded attempt, preserve its evidence, and record a new failure only if that attempt
also fails.

The retry counter is additionally scoped to `incident-id`. While an incident is in its
`retry` state, that id is locked for the task and Guard: a caller cannot reset the
counter by submitting a different id. A new incident begins at attempt one only after
the older incident has reached a terminal `block` or `escalate` outcome.

The guard identifier is resolved against immutable `core/guards.json` from the release
pinned by the project. The recorder cannot supply its own taxonomy or retry policy.
When `harness checkpoint` fails, it automatically records the pinned `checkpoint`
Guard using its required session, failure id, and pre-written evidence artifact.

## Interrupted trace delivery

The database transaction writes both the failure/outcome and an identifier-only pending
trace event. The event is then delivered to `harness/trace.jsonl` using its failure key
as an idempotency key. If the process stops between those operations, the next
`restore` flushes pending events exactly once before Socrates chooses the next action.

## Different from Harness signals

```text
concrete failure + evidence artifact -> Guards -> retry/block/escalate
user correction or behaviour concern -> Harness signal -> retrospective investigation
```

`socrates signal` stores only category, optional task id, and artifact reference in
`harness/signals.jsonl`. It never creates a Guard failure, never changes a Guard
outcome, and never retries, blocks, or escalates work. A later retrospective requires
evidence, Kepler review, and human approval before it can propose an improvement.
