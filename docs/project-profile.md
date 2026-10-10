# Project profiles

Each bound target repository contains `.agent-fabric/profile.json`. It is the only
place for repository-specific operating rules and integrations. Canonical agent
semantics live in the pinned Fabric release at `core/agent-profiles.json`; target
requirements live in `.agent-fabric/config/capabilities.json`.

```json
{
  "schema_version": 3,
  "project_name": "Example",
  "commands": {
    "test": { "family": "python", "command": "python -m pytest" }
  },
  "integrations": {
    "work_tracking": ".agent-fabric/config/work-tracking.json"
  },
  "task_specs": { "root": "docs/specs" },
  "fabric": { "binding": ".agent-fabric/fabric-binding.json" },
  "memory": { "retention": "project-local" },
  "secrets": { "allowed_root": ".agent-fabric/secrets" }
}
```

Profiles must not contain secrets. `secrets.allowed_root` is a relative project-local
directory, not a secret or a credential reference. The interactive secret helper reads
that declaration before it accepts a destination.

`integrations.work_tracking` is deliberately fixed to
`.agent-fabric/config/work-tracking.json`. The profile selects the stable Fabric
contract; the provider, its write policy, and any project-specific tracker rules belong
in that local configuration file, not in a second profile path that the runtime would
ignore.

The profile is validated against `schemas/project-profile.schema.json`; undeclared
top-level fields are rejected. It deliberately contains no role catalog or gate
definition: those are shared, immutable release contracts rather than project-owned
policy.

`family` is either `python` or `bash`. `project command-preview` is the Fabric command
resolver: it refuses a declared Bash or Python command unless that family is available
on the detected Windows, WSL, or Linux host. The resolver only reveals the checked
command; it does not execute project code. A client adapter must use this resolver
before presenting or invoking a profile-declared command.

`capabilities.json` declares what the target needs; it is not a snapshot of the host.
The runtime detector compares this declaration to actual executable capabilities before
it selects a command. A profile renderer for Codex, Copilot, or Claude must consume the
pinned release's `agent-profiles.json`; it must not define role authority independently.

The task-package root is always relative to the project root. Both native and
Windows-style absolute paths and parent-directory traversal are rejected even when the
current host is Linux or WSL; a profile cannot escape the repository merely by being
created on another operating system.
