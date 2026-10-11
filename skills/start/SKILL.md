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

`--apply` creates the package and returns a `socrates_chat_request`; it does **not**
claim that Socrates is running. Root must create a separate Codex chat with the returned
`chat_title`, pass it the task id and the created chat thread id, and stop task work.
Only that chat may run the returned `socrates_activation` command and become Socrates.

In Codex, use `create_thread` for that separate local project chat. Its initial prompt
must identify the role as Socrates, task id, and the rule that it must not begin task
work before receiving its activation packet. After creation, use the returned thread id
in the `socrates_activation` packet and deliver that packet to the new chat. Do not
create role-labelled specialist chats from Root. Socrates creates specialists only from
inside its own task chat.

Do not introduce Root as Socrates. The separate Socrates chat owns all task planning,
delegation, implementation decisions, durable memory, Guard failures, Harness signals,
and user communication for the task.

If `start`, separate-chat creation, or activation-packet delivery fails, stop project
work. Report the failure and use only the explicit Fabric recovery path when applicable;
Root must not implement the requested task.

Choose `planned` for a feature, an understood bug requiring investigation, or a
feature rework. It creates the spec, research, plan, Kepler verdict, and human
approval artifacts. Choose `small-bug` only for a bounded known correction; it uses
tasks and evidence without spec or plan.

Do not add external tracking, branch rules, commands, integrations, or secrets unless
the bound project's own profile declares and authorizes them.
