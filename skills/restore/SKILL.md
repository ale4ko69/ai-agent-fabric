---
name: agent-fabric-restore
description: Restore one AI Agent Fabric task from durable local state without restarting completed work. Use after the work router selects an existing task.
---

# Restore a task

First run:

```bash
<fabric-launcher> restore <project-root> <task-id> --json
```

Use the returned task metadata, local artifacts, memory snapshot, pending delegation
requests, and pending results to identify the next unfinished action. Treat completed
artifacts as closed evidence; do not recreate them or restart the task from the
beginning.

This command is read-only. Do not execute a project command, edit files, or advance a
Harness cursor merely because context was restored.
