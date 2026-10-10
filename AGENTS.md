# AI Agent Fabric repository instructions

Read `docs/architecture.md` and `docs/project-profile.md` before changing the
runtime. Keep this repository free of client, employer, machine, credential, path,
or infrastructure-specific details.

The core must be portable. Use Bash for ordinary system, file, process, and Git work;
use Python for memory, structured data, installation, validation, and integrations.
Bash must be detected before use. Do not add PowerShell workflow dependencies. Detect
both the execution environment and repository-local agent client before selecting a
command or adapter. Target-project facts
belong only in that target's `.agent-fabric/profile.json` and its selected
client-specific project context.

The Fabric itself is installed globally only through its versioned installer and only
after an explicit preview. Do not manually replace user-owned client instruction files:
use the Fabric-managed block lifecycle so uninstall removes only Fabric's own block.
Projects remain local bindings with local memory, tasks, and profiles. Run the test
suite only during an explicitly requested validation phase.
