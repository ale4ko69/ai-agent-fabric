---
name: agent-fabric-start
description: Create a new AI Agent Fabric task package after task intake identifies a title and work class. Use after the work router selects new-task intake.
---

# Start a task

Use the canonical global Fabric launcher declared by the installed global bootstrap
to preview the exact package first:

```bash
<fabric-launcher> start <project-root> --title "<title>" --type <planned|small-bug> --json
```

Report the returned task id, local package path, and work class. Create it only after
the user explicitly confirms that preview:

```bash
<fabric-launcher> start <project-root> --title "<title>" --type <planned|small-bug> --apply --json
```

Choose `planned` for a feature, an understood bug requiring investigation, or a
feature rework. It creates the spec, research, plan, Kepler verdict, and human
approval artifacts. Choose `small-bug` only for a bounded known correction; it uses
tasks and evidence without spec or plan.

Do not add external tracking, branch rules, commands, integrations, or secrets unless
the bound project's own profile declares and authorizes them.
