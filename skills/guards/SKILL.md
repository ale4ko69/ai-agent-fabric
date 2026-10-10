---
name: agent-fabric-guards
description: Record and process one concrete AI Agent Fabric Guard failure from durable project evidence. Use after a declared gate or command failure, never for a user correction alone.
---

# Guards

Use this workflow only as the task-local Socrates orchestrator. A specialist returns a
typed result and evidence artifact; it does not write the failure record itself.

Before recording a failure, ensure there is an existing non-secret, project-relative
evidence artifact that explains what failed and how it was observed. Then invoke:

```bash
<fabric-launcher> guards failure <project-root> \
  --session <task-id> \
  --idempotency-key <stable-observation-id> \
  --incident-id <stable-incident-id> \
  --guard <release-declared-guard-id> \
  --artifact <project-relative-evidence-artifact> --json
```

Do not invoke this command for ordinary user feedback, drift, friction, or an
instruction correction; record those as a minimal Harness signal through Socrates.
The Guard result is authoritative for the next bounded action:

- `retry`: create a new bounded attempt and preserve fresh evidence if it fails;
- `block`: stop that path and ask the user for direction; or
- `escalate`: stop retrying and escalate to the user.

The same idempotency key is safe to replay and returns its original decision. Do not
run a command automatically after a Guard result, change task scope, or edit
instructions. `restore` returns pending Guard failures/outcomes to Socrates.

While a Guard outcome is `retry`, its incident id is locked for that task and Guard:
the next observation must retain it. A new incident can begin only after the prior one
has reached its terminal `block` or `escalate` outcome.
