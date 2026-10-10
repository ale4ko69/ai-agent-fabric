# Secret entry

The Fabric never accepts a token, password, key, or secret in chat, an argument, a
configuration file, memory, or a log. When a selected project integration needs one,
first inspect the non-mutating release-bound invocation:

```text
ai-agent-fabric secret prompt <project-root> --destination <relative-destination> --label <secret-label> --preview
```

Then run the same command without `--preview`. Fabric checks the selected project's
binding, local profile, declared secret root, Bash availability, and the helper inside
the pinned release before it opens a hidden terminal prompt. Only the destination and
label are arguments; neither is a secret. The prompt itself is executed by:

```text
scripts/secret-entry.sh <project-root> <relative-destination> <secret-label>
```

The helper reads `secrets.allowed_root` from the target project's profile, then asks for
the value through a hidden terminal prompt. It refuses absolute paths, parent traversal,
overwrite, symlinked destination directories, or a destination outside that declared
root. The final file is created exclusively with owner-only permissions. It prints
neither the value nor the destination's contents. A project profile names the allowed
root; no secret is stored in that profile. Bash owns the hidden prompt. To prevent a
time-of-check/time-of-use symlink race, a minimal Python writer receives the value only
through an inherited pipe descriptor and uses descriptor-relative exclusive creation with
`O_NOFOLLOW`. If the host lacks those safe primitives, Fabric refuses to store the
secret rather than falling back to unsafe path-based creation. The value never appears
in a process argument, configuration, memory, or log.
