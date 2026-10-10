# Execution policy

1. Detect the host and capabilities before selecting a command.
2. Use Bash for filesystem, process, Git, and standard system operations after its
   presence is verified. Use Python for durable state, structured data, validation,
   installation, and integrations.
3. If Bash is missing, use `bootstrap bash` to inspect a supported installation plan.
   `bootstrap bash --install` is explicit, runs exactly that plan, and verifies Bash
   afterwards.
4. Do not make workflow behavior depend on PowerShell, a shell profile, or a global
   agent configuration directory.
5. Do not emulate an unavailable environment. A profile that requires Bash blocks
   with a clear prerequisite instead of attempting another shell.

The detector is capability-based: it does not infer Bash merely because a Git command
is available. The bootstrap is platform-aware and does not try to install a package
through an unsupported package manager.
