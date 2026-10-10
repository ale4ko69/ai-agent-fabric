# Spec: adapt the established Agent Fabric with global distribution and project overlays

## Problem

The established personal Fabric contains months of operational knowledge: agent
contracts, durable memory, recovery, gates, harness controls, and installation
behaviour. The new repository initially captured only a subset of this knowledge and
scattered the agent description between a catalogue, a persona table, and a special
case for one agent.

## Goal

Create a portable Agent Fabric with a versioned user-level distribution and
project-local overlays. The result must retain the established workflow discipline,
make common agents reusable across projects, and remove environment and target-project
assumptions from the core.

## In scope

- Complete an evidence-based inventory of the source Fabric.
- Classify every source mechanism as portable core, project profile, client adapter,
  optional capability pack, or archive candidate.
- Establish one authoritative profile file for each adopted agent.
- Adapt contracts, memory, gates, harness, environment probing, client rendering, and
  global distribution plus project binding in a controlled order.
- Define installation, client-adapter, and project-binding manifests for Codex,
  Copilot, and Claude.
- Use local task artifacts as the canonical state, with optional tracker sync later.
- Preserve the opponent's scope lock: findings outside this spec require a human
  decision to amend the spec or defer the finding.

## Out of scope

- Copying source instructions or environment commands verbatim.
- Copying project-specific data into a global Fabric installation.
- Adding a ChatGPT adapter before its concrete local runtime and supported instruction
  mechanism are identified.
- Enabling optional integrations or specialist packs before their project profiles are
  defined.
- Deleting source material before a canonical replacement, reference audit, and
  recoverable archive path exist.

## Constraints

- A scope filter precedes every source inventory. It classifies a source artifact as
  baseline, optional project pack, or excluded. Excluded artifacts receive no target
  destination and cannot be reintroduced by a completeness audit without an explicit
  human scope amendment.

- The common Fabric is a versioned user-level distribution. Each target project binds
  to a compatible release and stores project-specific configuration, memory, task
  packages, and credentials only inside the project boundary or an explicitly declared
  credential store.
- Client integration distinguishes a global bootstrap from a project overlay. Links,
  imports, and wrappers are supported adapter delivery mechanisms when explicitly
  declared and reversible; they are not globally forbidden.

- Bash is the command-workflow shell when an executable Bash is detected; Python owns
  structured state and integration logic.
- The host and selected AI client are independently detected before commands or
  generated artifacts are chosen.
- Secrets are accepted only through a hidden terminal prompt and stored at a declared
  project-local destination; they never appear in chat, arguments, or logs.
- Work tracking is optional. A local task package must function with no tracker.

## Acceptance criteria

- Every source subsystem and rule has a recorded classification and destination.
- Seven canonical agents have exactly one authoritative profile each; no separate
  catalogue/persona/exception documents define their behaviour.
- A generic task can persist, restore, and validate its state locally on supported
  hosts without a project-specific command embedded in the core.
- Client adapters have an explicit global bootstrap and a project-local overlay, both
  driven by declared manifests and shared contracts/profile data.
- Updating a Fabric release does not silently move an existing project binding.
- Tests cover the environment matrix, task artifacts, recovery, gates, client
  detection, and installer isolation.
