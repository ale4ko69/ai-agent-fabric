---
name: agent-fabric-harness
description: Review project-local AI Agent Fabric behavioural signals since the last approved retrospective. Use when the user asks to inspect agent failures, drift, friction, or Harness lessons.
---

# Harness retrospective

The mandatory first action is the bounded local input command:

```bash
<fabric-launcher> harness review <project-root> --json
```

`<fabric-launcher>` means the canonical global Fabric launcher declared by the
installed global bootstrap. It is never a project-local executable.

Use signals as leads, not proof. Substantiate each proposed lesson from the active task
artifacts and current-session evidence. Report only:

- failure patterns and their evidence;
- root causes or explicit uncertainty;
- one bounded instruction, workflow, or Harness proposal per target;
- findings outside the current task as deferred, never delegated work.

Do not edit instructions, profiles, workflow, skills, or global Fabric during this
skill. Kepler reviews the report and the human decides which proposals to apply. Only
after both approvals may the retrospective cursor be closed with the explicit Harness
command.
