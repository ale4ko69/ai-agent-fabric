# Using Fabric in a project

This is the operator guide for a person using a bound project through Codex, Copilot,
or Claude. It describes what the task commands do, who decides after a failure, and
when Fabric behaviour is actually live.

If `start` or `restore` fails in Codex, Root stops project work. It may only report
the failure or run the explicit Fabric recovery path; it must not execute the task in
place of the task-local Socrates lifecycle.

## Project-local Codex next-machine validation

The project-only path is **runtime installation, then a separate adapter
preview/apply**. Use only its scoped Python launcher. It links `.codex/agents` to the eight persona TOML files
and links the project entry and New Product skills under `.agents/skills`, not a Desktop plugin or
global configuration. `project codex-status <project> --json` observes filesystem
ownership; `file_installation: installed` does not mean the app discovered anything.
Both `desktop_discovery` and `claim_restore` remain `unverified`.

On the next computer, with a reviewed fresh runtime and explicit owner approval:

1. Preview `project codex-install`, inspect all relative targets and the pinned
   release, then apply its exact `--expected-preview-sha256`. Existing `.codex`
   state blocks install, even if empty; never delete user state merely to make
   installation succeed. Inspect it and agree on a separate target instead.
2. Record the OS/filesystem, actual Desktop version, project root and trust state.
   Run `project codex-status`. Native symlink failure is a concrete blocker; no
   junction, copy, elevation or global-config workaround is silently authorized.
3. Open/trust that exact project in Desktop using its real UI. Observe all eight
   personas (`socrates`, `aristotle`, `plato`, `kepler`, `heracles`, `athena`, `euclid`,
   `metis`) and the `agent-fabric-project` skill. Check the content/targets, not
   merely names. If they are hidden or ignored, record which links the app cannot
   observe, the build and any actual error; stop instead of claiming support.
   Project/config-layer discovery in the pinned upstream code does not prove that
   the installed Desktop build exposes the same surface.
4. Invoke the governed project entry as Root. Preview a bounded throwaway task and
   create it only after approval. Verify the task is awaiting its separate Socrates
   chat and Root has not planned, implemented, delegated or claimed it.
5. **Explicit/manual transfer:** the owner creates a real separate project chat or
   reopens the exact previously bound one, then transfers the task id, pinned
   context, Socrates companion and activation packet. Obtain that chat's real
   Desktop thread ID from an actually available identity surface. Never use a
   synthetic identifier, chat title, guessed URL, native agent id or undocumented
   `create_thread`/reopen API. Only that separate chat runs `socrates claim`.
6. If creation, real identity or exact reopening is unavailable, stop and leave the
   task pending. Do not have Root claim on another chat's behalf. The existing claim
   command checks durable binding consistency; it trusts the supplied identifier
   and is **not independent Desktop identity attestation**.
7. Where the real surface supports it, observe claim, a bounded evidenced step, chat
   closure, and manual reopening of that exact bound chat. Restore using the local
   launcher, verify the same thread binding and preserved checklist, and confirm a
   different chat cannot rebind the task. Native specialist subagents are never
   substitutes for this separate Socrates chat.

Record live evidence separately for file installation, app discovery, and genuine
claim/restore. Automated tests use fixture IDs and cannot supply that evidence.
No automatic promotion of the adapter record to “Desktop verified” is implemented.

## The three states that must not be confused

```mermaid
flowchart LR
    source["Source branch\nnew code and documentation"] --> install["Installed Fabric release\nimmutable version in Fabric home"]
    install --> binding["Project binding\nproject chooses one installed release"]
    binding --> task["Task lifecycle\nSocrates, checklist, memory"]
```

Changing or pushing a source branch does not change an installed release. Installing a
release does not change existing projects. A project begins using a release only after
its binding is explicitly updated. Use `project context <project> --json` to see the
release currently selected by that project; use the installer preview before any
installation or binding update.

## Starting or returning to work

In a client conversation, ask to work on the project. The Fabric work skill runs the
read-only router first. If you specifically ask to restore but do not remember a task,
`restore <project> --json` itself returns the same numbered picker and makes no change.

```mermaid
flowchart TD
    work["work project"] --> count{Active task packages?}
    count -->|0| intake["Ask for title and work class"]
    intake --> start["start --apply\ncreates package and Socrates-chat request"]
    start --> chat["Root creates or reopens\nthe separate Socrates chat"]
    chat --> claim["Socrates claims task id\nwith its chat thread id"]
    count -->|1| one["Show the task and restore it"]
    count -->|2 or more| list["Show numbered list:\nnumber, title, task id, work class"]
    list --> choice["You choose number, title, or task id"]
    choice --> restore["restore exact task id"]
    one --> restore
    restore --> packet["Return checklist, chat binding, evidence,\npending results, Guards and memory"]
    packet --> chat
```

You do not need to remember ids. `restore` without an argument shows every active task
as a numbered list. You can answer with that number, the exact title, or the task id;
the launcher resolves it to the durable id before restoring. The conversational number
is only a convenient selection label.

Saying or typing the ordinary word `start` is not an operating-system action. A task
starts only when the Fabric skill invokes `start ... --apply`. This is intentional: it
prevents a casual sentence from creating project state.

`start --apply` does not prove that Socrates is live. It creates a pending chat claim.
Root creates the separate Socrates chat, delivers the returned activation packet, and
does not continue the task. `restore` does not execute the next step or run a project
command. It reconstructs the chosen task packet and returns the bound chat id when one
exists, so Root can reopen that exact chat. Socrates claims the task and then reads its
`next_action` before doing work. A completed checklist step remains completed; a
missing memory database is reported as a recovery problem rather than recreated as an
empty task.

## What Socrates is

Socrates is the project-local orchestration role, not a background daemon. A task has
one durable Socrates lifecycle in its project-local memory and one visible, claimed
Socrates chat. It owns task transitions, delegation records, Guard outcomes, and
Harness signals. Specialists return bounded results and evidence artifacts; they do
not choose retry policy or persist project memory. Root opens that chat and remains an
entry/recovery coordinator; it is not Socrates and must not create specialist chats.

## Guards: what happens after an error

A Guard is a deterministic response to a concrete, evidenced technical failure. It is
not a pop-up asking you to approve every error and it never reruns a command by itself.

```mermaid
flowchart TD
    failure["Command or gate fails"] --> evidence["Socrates writes/identifies an\nexisting evidence artifact"]
    evidence --> guard["Pinned Guard policy"]
    guard --> retry{"Outcome"}
    retry -->|retry| attempt["Socrates may make one new\nbounded attempt with fresh evidence"]
    attempt -->|fails again| guard
    retry -->|block| user["Stop this path; ask you for direction"]
    retry -->|escalate| user
    retry -->|success on retry| next["Continue the normal next step"]
```

The baseline policies are:

| Failure kind | Outcome | Who acts next |
| --- | --- | --- |
| Failed checkpoint/gate | `block` immediately | You decide whether to supply missing evidence, change scope, or stop. |
| Failed bounded command, attempts 1–2 | `retry` | Socrates may make the next bounded attempt; it reports the result and records fresh evidence. |
| Failed bounded command, attempt 3 | `escalate` | You decide how to proceed; Socrates must stop retrying. |

So you are not interrupted for a normal first retry. You are explicitly asked when the
policy says `block` or `escalate`, or whenever the next attempt would require a new
scope, authority, or external action.

## Harness signals are not Guards

Use a Harness signal when the issue is agent behaviour rather than an execution failure:
for example, “you ignored my instruction”, “you used the wrong project”, or “you kept
repeating a mistake”. Socrates records only a category, task id, and optional evidence
artifact—not the chat transcript.

```mermaid
flowchart LR
    correction["Your correction\nof agent behaviour"] --> signal["Socrates signal"]
    signal --> review["Harness retrospective\nsince prior approved cursor"]
    review --> kepler["Kepler challenges proposal"]
    kepler --> human["You accept, reject, or defer"]
    human --> close["Close retrospective\nand advance cursor"]

    technical["Concrete gate or command failure"] --> guard["Guard\nretry / block / escalate"]
```

A signal is written at the time Socrates records it. A Harness *result* arrives only
when a retrospective is run: it groups the signals since the last approved cursor,
collects evidence, and produces a proposal for Kepler and you. Nothing changes
automatically.

## Hooks: what is automatic, and what is not

This section describes the separate **user-level plugin mode**. The project-local
Codex adapter above installs no plugin or lifecycle hook.

The Fabric Codex plugin now includes one deliberately narrow, trusted `SessionStart`
hook. Once the plugin version is installed and trusted in Codex, it finds a bound
project from the session working directory and asks the installed launcher for the
read-only active-task list. The agent uses that list as data to match your request;
an unrelated active task does not block new authorized work. If the request is
ambiguous, the agent asks which task you mean. The hook does **not** start or restore
a task, execute a project command, read a transcript, or write a signal.

If the hook cannot read task metadata, its empty result says only that no active task
record was visible. It is not proof that no task exists; inspect the project state when
the launcher or hook reports a problem.

```mermaid
sequenceDiagram
    participant C as Codex Desktop
    participant H as Trusted plugin hook
    participant L as Fabric launcher
    participant S as Socrates
    participant U as You
    C->>H: SessionStart with working directory
    H->>L: read-only restore task picker
    L-->>H: active task metadata
    H-->>S: bounded task list context
    S->>S: match current request to task metadata
    opt Request is ambiguous
        S->>U: ask which task to continue
        U-->>S: selection
    end
    S->>L: explicit restore or start when authorized
```

Codex treats command hooks as executable plugin code. You must review and trust it in
the client hook UI before it runs; Fabric does not bypass that consent. The installation
preview shows the marketplace source and the hook file that will be replaced.

No lifecycle hook automatically turns a correction into a Harness signal. That would
require copying or classifying private conversation text. When you correct behaviour,
Socrates records the explicit minimal `user-correction` signal; when a command or gate
fails, Socrates records the separate evidenced Guard failure. The hook merely makes
task selection available at session start.

### Client support boundary

| Surface | Fabric hook status | Why |
| --- | --- | --- |
| Codex Desktop/local plugin | Implemented: trusted plugin `SessionStart`, read-only picker. | Codex plugin hooks can return bounded session context after the user trusts their current hash. |
| GitHub Copilot CLI | Vendor hooks exist, but no Fabric hook is installed. | Its project/user hook configuration is a separate Copilot-owned surface; Fabric does not silently create `.github/hooks` in every project. |
| GitHub Copilot cloud agent | No Fabric local-Socrates hook. | Cloud hooks run in an ephemeral Linux job and only use repository files from the default branch; they cannot safely reach the user's local Fabric release or project-local memory. |
| Codex Cloud orchestration | No Fabric local command hook. | Local/plugin command hooks are not run by Cloud orchestration. |

The Copilot and Cloud entries are explicit limitations, not claims that the vendors lack
hooks. A future Copilot project integration must be previewed, committed to that
project's default branch, and use a cloud-safe task-state design rather than silently
reaching into a developer machine.

See [Guards](guards.md), [Harness](harness.md), and [the workflow](workflow.md) for the
underlying contracts.
