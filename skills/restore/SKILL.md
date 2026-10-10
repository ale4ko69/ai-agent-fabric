---
name: agent-fabric-restore
description: Restore one AI Agent Fabric task from durable local state without restarting completed work. Use after the work router selects an existing task.
---

# Restore a task

If the user does not know the task id, first run the picker:

```bash
<fabric-launcher> restore <project-root> --json
```

It returns every active task with a one-based number, title, id, and work class. Show
that list and let the user select a number, exact title, or task id. Then run:

```bash
<fabric-launcher> restore <project-root> <number|exact-title|task-id> --json
```

The command resumes that task's project-local Socrates session, then returns task
metadata, local artifacts, memory snapshot, Guard failures/outcomes, pending delegation
requests, pending results, and the durable checklist. Treat completed artifacts as closed evidence; do not
recreate them or restart the task from the beginning.

Restoration may reactivate Socrates' durable session record, but it does not execute a
project command, edit project files, or advance a Harness cursor. Socrates must inspect
any returned retry, block, or escalation outcome before selecting the next bounded
action.
