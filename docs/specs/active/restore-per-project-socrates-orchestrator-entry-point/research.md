# Research — Restore per-project Socrates task lifecycle

## Evidence

- The current portable runtime exposes `start`, `work`, and `restore`, but none starts
  a durable project-local Socrates lifecycle. `start` creates a task only after an
  explicit apply; `work` routes read-only; `restore` reads state only.
- The current Harness implementation is signal-only: it appends minimal behavioural
  pointers to `harness/signals.jsonl`, then retrospective review reads them. It does
  not create structured failure records or invoke Guards.
- The source Fabric's Process Gate wrote a gate audit record on every run and, on
  failure, wrote `failure_reports` through `fabric-mem failure`. Its learning loop
  could then connect evidenced failures to correction proposals.
- The source new-task flow first created durable session/checklist state and passed its
  initial gate, then entered orchestrator behaviour for that task. The portable target
  must preserve that order through `start task`, rather than add a second command that
  starts an unbound/global orchestrator.
- Current command dispatch confirms the gap: `start --apply` only calls `start_task`;
  `restore` only calls `restore_task`; neither creates or resumes an orchestrator
  session. `harness signal` appends a separate minimal JSONL record.

## Options

1. Separate `start orchestrator` command: rejected by the user because it duplicates
   the task lifecycle boundary.
2. `start task` activates Socrates; `restore task` resumes the same Socrates task
   lifecycle: selected direction.

## Rejected approaches

- Treating a Harness signal as a Guard failure. A user correction is a retrospective
  pointer, while a Guard failure is a concrete policy decision with an evidence record.
