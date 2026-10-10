---
name: agent-fabric-work
description: Route a bound AI Agent Fabric project to one existing task or new-task intake. Use when the user asks to begin, continue, resume, or work on a project.
---

# Work router

Run the canonical global Fabric launcher declared by the installed global bootstrap:

```bash
<fabric-launcher> work <project-root> [task-id] --json
```

It is read-only and returns exactly one route: `restore`, `start`, or
`select-task`.

- `restore`: use the `restore` skill for the returned task id.
- `start`: collect only the title and work class needed by the `start` skill.
- `select-task`: show the returned local task list and ask the user to choose one.

Do not create task state, infer an active task, or execute project commands in this
router. If the project is unbound, explain that initialization is required and follow
the installed global bootstrap's explicit preview flow.
