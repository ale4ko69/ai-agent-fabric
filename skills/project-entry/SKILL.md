---
name: agent-fabric-project
description: Enter or restore this project's pinned Fabric workflow, with explicit manual transfer to a separate real Socrates chat. Never substitutes native subagents or invents chat identity.
---

# Project-local Fabric entry

Run only from the verified project root. Use the pinned local launcher, not a global
Fabric command, plugin, service, or client configuration:

```bash
python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py project context <project-root> --json
python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py project codex-status <project-root> --json
python -I -S -B .agent-fabric/runtime/bin/ai-agent-fabric.py work <project-root> --json
```

For an explicit New Product request, load the pinned `skills/new-product/SKILL.md`
from the release in the returned context and follow its discovery entry.

Read the returned pinned contracts and project overlay. Root is entry and recovery
only: it cannot claim, plan, implement, delegate to specialists, or write durable
task memory. Use the existing read-only task picker/restore command to select an
existing task, or preview a new task with `start` and apply only after explicit
owner authorization.

`start --apply` creates a pending claim, not a running Socrates. `restore` returns
the durable task id, state and existing chat binding; it does not reopen a chat.

## Explicit/manual transfer

1. Ask the owner to create a separate **real Desktop project chat**, or manually
   reopen the exact chat already bound to this task. Do not silently use the current
   Root chat, another task's chat, or a native role/subagent named `socrates`.
2. Transfer the exact task id, pinned project context, applicable
   `docs/agents/socrates.md`, task package and returned activation packet to that
   separate chat. Use the docs path inside the release returned by `project context`.
3. Obtain that chat's **real Desktop thread ID from an actually available client
   identity surface**. Never invent an ID, use a title/agent label as identity,
   guess a conversation URL, or call a nonexistent `create_thread`/reopen API.
4. Only that separate chat, after verifying the transfer and its actual identity,
   may execute the existing `socrates claim` with the task id and real thread ID.
   Root does not execute this claim on the chat's behalf. On restore, preserve the
   durable binding and completed steps; never rebind to a different chat.
5. If identity, creation, or exact reopening is unavailable, **stop**. Report the
   limitation and leave the task awaiting its real Socrates chat. Do not fabricate
   activation or continue implementation in Root.

Specialist native agents remain bounded specialists delegated by the claimed Socrates
chat. The Socrates persona TOML is an instruction companion, not an automatic
Desktop-chat creation mechanism or permission for a native subagent to claim a task.

File installation and filesystem link observation are not proof of app discovery.
Desktop discovery and claim/restore remain **unverified** until the owner tests them
on the actual Desktop installation. Report missing/hidden links exactly; do not
silently replace them with copied files, junctions, global configuration or elevation.
