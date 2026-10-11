# Research — Make Socrates own project chat orchestration after start and restore

## Evidence

- `start --apply` and `restore` create/resume lifecycle rows and return state,
  but `entrypoints.py` has no handoff envelope.
- The trusted Codex `SessionStart` hook is intentionally read-only and only
  returns a task picker; README explicitly says it never starts work.
- The generated adapter bootstrap tells Root to stop on failed start/restore,
  but has no corresponding successful-handoff authority transition.

## End-to-end map

```text
User request
  -> Root runs work router
  -> [start | restore | select]
       -> lifecycle succeeds?
          yes -> Socrates handoff packet -> chat instruction: Socrates owns task
                 -> Socrates chooses/communicates next safe action
          no  -> Root recovery-only notice -> explicit recovery command or user
       -> select -> Root asks only for selection; no task work
```

## Options

- Native role transfer: preferred only if Codex publishes a supported API.
- Adapter handoff packet plus strict generated instructions: portable fallback;
  it makes authority observable but cannot impersonate a client-native identity.

## Rejected approaches

- Treating the durable SQLite lifecycle as proof that the chat switched roles.
- Letting Root continue task work merely because it has restore context.

## Rejected approaches
