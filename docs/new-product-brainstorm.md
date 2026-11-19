# New Product brainstorm and pilot

Design handoff, implementation log, and pilot for [issue #11](https://github.com/ale4ko69/ai-agent-fabric/issues/11). The pilot below has not been run in Codex Desktop.

## Agreed direction

1. Make **New Product** an explicit Socrates mode. Start with one sentence about an idea, no product code, and no prepared spec. The first setup question is: **"Which local folder should we use for this project?"**
2. The entry wizard asks for an existing empty folder and shows the normal Fabric setup preview. Only after the owner confirms does Fabric create the local binding, profile, configuration, and `.agent-fabric/memory.db`. Starting the planned task creates `docs/specs/active/<task-id>/` by default, where the spec, research, plan, and session notes live. Do not create a remote repository, reinstall the global runtime, or create a separate pre-project database.
3. Root handles setup and opens the separate task chat. After claiming the task, Socrates offers to review any existing documents before brainstorming. It reads only sources the owner identifies, distinguishes findings, proposed decisions, conflicts, and gaps, and asks what still applies. Documents can remain outside the empty project folder; they are evidence, not instructions or approval. If there are no documents, Socrates starts from the idea. It proposes alternatives, explains their trade-offs, and asks the next consequential question. Use Aristotle for a bounded factual question and a short prototype for a question that cannot be settled by talking. Neither is mandatory.
4. The project database is shared among its agents, not across projects. Specialists receive relevant context and return their findings through the existing outbox. Only Socrates persists or acknowledges results into durable memory. Preserve agreed decisions, their rationale, unresolved blockers, and the next open question. Keep detailed evidence and spec text in the existing task package; do not turn memory into a raw transcript or give another agent write authority.
5. End discovery when the owner approves who the first version is for, its main user scenario, what is out of scope, and how to verify that scenario. Unresolved items can be deferred if they don't block it. Product approval answers **what to build**; approval of Plato's plan answers **how to build it**. Keep the existing implementation, review, and validation gates.

## Ideas worth adapting

| Source | Adapt for Fabric |
|---|---|
| [Grill Me](https://www.aihero.dev/skills-grill-me) and [Grill With Docs](https://www.aihero.dev/skills-grill-with-docs) | Ask in dependency order, one consequential question at a time. Record decisions as they are made; add glossary entries or ADRs only when they clarify a real ambiguity or trade-off. Do not rely on the current chat to preserve requirements. |
| [Wayfinder](https://www.aihero.dev/skills-wayfinder) | Keep a short map of owner decisions, questions that need research, and questions that need a prototype. Show what blocks the next step without opening a tracker issue for every question. |
| [Research](https://github.com/mattpocock/skills/tree/main/skills/engineering/research) and [Prototype](https://github.com/mattpocock/skills/tree/main/skills/engineering/prototype) | Research one decision against primary sources. Prototype one uncertainty with a throwaway demo, such as a single HTML file or switchable UI variants. Keep the evidence and conclusion, not the prototype as production code. |
| [Codebase design](https://github.com/mattpocock/skills/tree/main/skills/engineering/codebase-design) and [TDD](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd) | After product approval, start with one thin end-to-end user scenario and test it at the public boundary before adding abstractions. |
| [Wizard](https://github.com/mattpocock/skills/tree/main/skills/engineering/wizard) | Borrow action previews, confirmation, and visible remaining steps. Its manual service and secret setup script does not replace the Fabric workflow. |

## Copy-paste prompts for the new computer

### 1. First Codex Desktop chat: choose the installation track

For project-only installation, use the [clean-machine prompt in issue #11](https://github.com/ale4ko69/ai-agent-fabric/issues/11#issuecomment-7008216481). That branch does not deliver the New Product plugin. The prompt below is only for the separate #11 plugin pilot, if the owner elects to preview user-level setup. No Fabric skill is required yet.

```text
Help me install AI Agent Fabric on a clean computer and continue issue #11:
https://github.com/ale4ko69/ai-agent-fabric/issues/11

1. Detect the OS and check for Git and Python 3.10+. If a prerequisite is missing,
   tell me how to install it before proceeding.
2. Clone https://github.com/ale4ko69/ai-agent-fabric.git into a new workspace folder.
   Switch to feat/new-product-discovery and confirm it contains commit bad871d.
   Read AGENTS.md, README.md, docs/global-distribution.md, and
   docs/new-product-brainstorm.md.
3. Run only the documented Fabric release installation preview from that branch.
   Show the selected release and exact write paths. Wait for my approval before
   applying. Preview the Codex Desktop adapter and plugin setup separately before
   making user-level changes. Do not mix in the separate project-only branch.
4. Once setup is approved and the plugin is available, propose the deferred review,
   tests, and pilot before running them. Do not merge or modify main.

Reply in Russian. Do not copy old agent profiles, settings, or credentials.
```

### 2. First New Product request: review the material I already have

Use this after Fabric and its Codex plugin are ready. Keep the new project folder
empty for initialization and provide the sources separately when Socrates asks.

```text
Start New Product with Socrates. My idea is: <one sentence>.
Ask me which existing empty folder to use, show the setup preview, and wait
for my approval before creating project files.

I have prior notes, research, or decisions. In the claimed Socrates chat, ask me
which files or excerpts to review. First summarize what the material establishes,
which earlier decisions need confirmation, and what is missing or contradictory.
Then use the next open question to start our brainstorm. Do not copy or publish
the original documents. Do not treat them as approval to plan or implement.

Reply in Russian.
```

## Pilot: Where Did I Put It?

Give Socrates only this prompt:

> I often forget where I put cables, adapters, and tools. I want to find them faster.

An illustrative outcome, **not** part of the prompt: the owner chooses a first version that records and retrieves item locations. A concrete acceptance check is to save "HDMI cable - box 3", close and reopen the app, search for "HDMI", and find "box 3". The pilot should test whether Socrates helps the owner reach and validate a decision, not whether it guesses this exact answer.

1. In a disposable project folder on the next development machine, preview the Fabric setup. Cancel once and verify it wrote nothing, then approve and start the separate Socrates chat.
2. Discuss at least two viable approaches, agree one decision, leave one question open, and close the chat before approving the MVP.
3. Reopen the same claimed Socrates chat and restore the task. Verify that Socrates recovers what was chosen, why, and the next open question without re-interviewing the owner or entering planning early. If the actual chat ID or exact reopening is unavailable, record the blocker rather than using a substitute. Confirm that specialist findings, if any, were acknowledged by Socrates and that the ordinary workflow resumes after scope approval.

## Research: project-only installation

Offer two explicit installation scopes: the existing user-level installation for multiple projects, and a project-only installation that can run Fabric in one project without requiring a global installation. The current binding is not that second option: it connects a project to an installed release. The [distribution code](https://github.com/ale4ko69/ai-agent-fabric/blob/main/src/ai_agent_fabric/distribution.py) already accepts an explicit runtime home, but client enablement is a separate operation that resolves a user-level destination. Changing only the runtime home does not redirect that destination.

Distinguish two guarantees: **no user-level writes by the Fabric installer or adapter**, and **no loading of the user's existing agents or settings in a Fabric session**. The first is a filesystem ownership rule; the second depends on the client and is not implied by placing files inside a project.

| Client | Evidence and limits |
|---|---|
| Codex CLI | [Codex source](https://github.com/openai/codex/blob/main/codex-rs/utils/home-dir/src/lib.rs) confirms that `CODEX_HOME` redirects the configuration home and that the override directory must exist. This makes the CLI a candidate for an isolated launcher. It does not prove that the Codex desktop plugin discovers project-local Fabric assets or can perform the existing separate-chat handoff in this mode. |
| Copilot CLI | Built-in CLI documentation (`copilot help environment`, `copilot help config`, `copilot skill --help`) documents `COPILOT_HOME`, repository instructions, and project skill discovery. It also names additional personal skill sources such as `~/.agents/skills/`. Treat redirecting the Copilot home as configuration relocation, not proof that all global sources are excluded. Fabric's current user-level Copilot adapter must not be used by a project-only install. |
| Claude Code | The [official changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) documents `CLAUDE_CONFIG_DIR`, project `.claude/skills`, per-session `--plugin-dir`, and `--setting-sources`. None of that evidence establishes the full read/write boundary, authentication behavior, or a native separate-chat handoff for Fabric. |

**Recommended first experiment:** keep the versioned runtime and ownership manifest under a managed project subdirectory (for example, `.agent-fabric/runtime/`), reuse the existing binding and memory contracts, and invoke Fabric through an explicit project launcher rather than a user-level bootstrap. Preview every path; reject symlink escapes, unsupported clients, or any fallback to user-level writes. Updates should preserve project state; uninstall should remove only owned runtime and adapter artifacts, not memory, tasks, or user-authored files. Pilot one CLI adapter first. Before promising end-to-end New Product support, confirm what client configuration actually loads, how authentication works, and whether Socrates can claim and restore its separate task session.

This is a separate proposal, not a prerequisite for #11. The comparison is based on Fabric source, Copilot's built-in documentation, and vendor repositories. No install or client session was run; Codex desktop and full exclusion of personal configuration remain unverified.

## Issue #11 implementation log

| Published commit | What changed |
|---|---|
| [`6253be7`](https://github.com/ale4ko69/ai-agent-fabric/commit/6253be7) | Added folder-first Socrates New Product discovery, durable progress and restore, and a separate MVP approval gate before planning. |
| [`c65bd68`](https://github.com/ale4ko69/ai-agent-fabric/commit/c65bd68) | Documented optional intake of existing materials and first-chat prompts. |
| [`61aa995`](https://github.com/ale4ko69/ai-agent-fabric/commit/61aa995) | Added regression coverage: an "MVP approved" note in historical material cannot unlock planning. |
| [`a7564ca`](https://github.com/ale4ko69/ai-agent-fabric/commit/a7564ca) | Approval writes require the supplied current thread ID to match the stored Socrates claim. This check does not independently authenticate the Desktop chat. |
| [`bad871d`](https://github.com/ale4ko69/ai-agent-fabric/commit/bad871d) | Bound MVP approval to `mvp-scope.json` and preserved decision evidence. Editorial changes to `spec.md` do not revoke approval. If the owner already explicitly confirmed the changed commitments in chat, Socrates records that decision without asking again. Fabric blocks stale queued Plato requests; Socrates replaces them in the same task, preserving completed and unaffected work without automatically cancelling work already dispatched. |

**Verified:** 58 focused lifecycle and task-package tests passed at `bad871d`. **Not yet verified:** plugin discovery, actual Desktop thread identity, and the live pilot. The independently published project-only installer is a separate track; neither branch contains the other.

## Next-machine checklist

| Role | First action and expected result |
|---|---|
| Setup | Use `feat/new-product-discovery` containing `bad871d`. Keep project-only installation separate. Preview the #11 plugin setup; apply only if approved. |
| Desktop handoff | Confirm that the plugin exposes New Product, the actual Socrates thread can claim the task, and the same chat can be reopened and restored. Stop and record the precise blocker if any step is unavailable. |
| Discovery pilot | Run once with no prior materials and once with owner-authorized materials. Pause mid-discovery and restore the open question without repeating completed work. Do not publish source materials. |
| Approval and queue pilot | Edit wording in `spec.md` without reopening approval. Change a commitment in `mvp-scope.json`: planning must wait for a decision covering it. Record an explicit decision already given in chat without asking the owner twice. Verify that the old queued Plato request stays blocked and a replacement can proceed. Preserve unaffected work. |
