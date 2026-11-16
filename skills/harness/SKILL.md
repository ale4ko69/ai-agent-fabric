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

This review remains read-only: do not edit instructions, profiles, workflow, skills,
or global Fabric during the review. Kepler reviews the report and the human decides
which proposals to apply. Only after both approvals may the retrospective cursor be
closed with the explicit Harness command.

Separately, if the active task already authorizes a digest-bound maintenance candidate
and the project has explicitly enabled the `maintenance` capability and policy,
Socrates may preview it and use the release's bounded maintenance action. That action
is limited to the supported typed retrospective configuration, checks the current
file and reports conflicts, and does not execute commands or deliver a release. Do not
treat a signal, an allowlist entry or a preview as approval of an unrelated candidate.
