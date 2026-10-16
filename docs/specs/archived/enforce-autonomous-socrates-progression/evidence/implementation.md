# Implementation evidence

`memory.py` now derives a continuation inside the same transaction that closes a task
step. It resumes the next internal step by marking it `in-progress`, or persists one
of the only legitimate non-running outcomes: owner approval, Guard block/escalation,
or completion. Stop outcomes expose a stable reason and recommended action.

The memory schema is version 11. Its explicit migration expands lifecycle state values
and resumes a claimed legacy lifecycle's first unfinished internal step without
changing an unclaimed Socrates task.
