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

The command returns task metadata, local artifacts, memory snapshot, Guard failures/outcomes,
pending delegation requests, pending results, the durable checklist, and a
`socrates_chat_request`. It never lets Root resume or impersonate Socrates.

Root opens or returns the user to the named separate Socrates chat. That chat claims its
thread id with the returned activation command, then inspects the durable state before
selecting the next bounded action.

When `memory.socrates_chat.thread_id` is present, reopen that exact Codex chat; do not
create a replacement. When it is absent, create the Socrates chat as described by the
start skill, then deliver the activation packet.

Root must not continue task work after issuing the chat request.

If `restore` fails, stop project work. Root may only report the failure and perform
an explicit Socrates recovery; it must not continue the task itself.
