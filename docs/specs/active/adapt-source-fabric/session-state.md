# Session state

## Current phase

Phase 1 inventory accepted by Kepler with `advice`; implementation is active with the
approved global-distribution and project-overlay architecture.

## Durable decisions

- The source Fabric is adapted, not discarded or copied verbatim.
- Task packages are the local canonical record.
- Every adopted agent will receive exactly one authoritative profile.
- Project-specific facts are profile data; client and host choices are resolved by
  capability detection.
- Agent profile data is schema-validated and machine-readable; Markdown and client
  renderers are derived or validated companions.
- Specialist results use a durable outbox and orchestrator acknowledgement before a
  memory/state transition is considered complete.
- Every executable test, including the environment matrix, is deferred until the single
  final validation gate after the transfer and design are complete.
- The workflow environment scan found 267 candidate lines. Each has a stable
  occurrence id in task evidence; they are queued for final disposition rather than
  being copied as commands.
- A `deferred` disposition explicitly prohibits transfer until its evidence condition is
  satisfied.
- The shared Fabric is a versioned user-level distribution. Projects bind to a selected
  release and keep all project facts, memory, tasks, commands, integrations, and
  credentials outside the global distribution.
- Client adapters may use an explicit, reversible symlink, import, or wrapper. The
  adapter manifest decides the supported method for that specific client surface.
- A global client bootstrap starts every repository interaction with a read-only binding
  status check. Only an explicit initialization request may create `.agent-fabric`.
- Shared roles and portable gates are materialized in each immutable release under
  `core/`; the bound project never receives a copied competing role catalog.

## Next transition

Implement approved, non-deferred mechanisms in plan order: release and adapter
manifests, project binding, then explicit client installation/update/rollback flows.

## Current implementation evidence

- Canonical baseline agent semantics now have a machine-readable profile source.
- Target capabilities are declared separately from runtime detection.
- Client context artifacts point to that source rather than defining role authority.
- Portable gates are declarative data; project commands and thresholds remain profile
  data and no Bash gate execution has been transferred yet.
- Task packages can now archive recoverably without a remote tracker.
- The user-level lifecycle now has installation, release integrity metadata, client
  ownership records, preflight, preview, update, rollback, and uninstall paths.
- Project onboarding starts with a non-mutating `project status` classification and
  initializes only a release binding plus project-owned overlay state after approval.
- The installed release now includes its own Bash/Python launcher; all subsequent
  project writes require a complete binding rather than an old standalone initializer.
- The release launcher selects `python3` first and `python` second, with an explicit
  missing-runtime message and a Python 3.10 floor, so the discovery path is portable
  across Bash hosts.
- Binding status resolves and validates the profile location named in the binding; the
  profile rejects undeclared fields so it cannot introduce an unowned core override.
- Project binding paths are resolved inside the project boundary even when a local
  symlink exists; adapter symlinks remain separately permitted and reversible.
- Release integrity rejects missing, changed, linked, or extra files; rollback can
  recover from a failed current release by validating the retained target release and
  the project-local binding independently.
- Hooks are a concrete selected-client adapter capability, never an assumed property of
  a model. The first release declares all hooks unsupported until an implementation
  can name its compatible client version, reversible delivery, and ownership lifecycle.
- Harness now analyses minimal project-local behavioural signals since its last approved
  retrospective cursor. It retains a byte watermark and digest, and advances only after
  Kepler review plus a human decision artifact.
- Project-release updates use an atomic pending journal and forward-only memory
  migration. `update-pending` blocks every Fabric-managed project write until the
  explicit repair path has been previewed and completed.
- A bound project can invoke the pinned release's Bash hidden secret prompt through a
  preview-first CLI entry point. The secret is never an argument, profile value, trace,
  memory record, or log; descriptor-relative safe writing fails closed on hosts lacking
  the needed primitives. Runtime matrix validation remains deferred.
- Official client loading and hook facts are recorded separately from the adapter
  contract. `hooks.mode: unsupported` now means no Fabric-managed handler is installed,
  not that the vendor client lacks hooks; model routing cannot change that fact.
- A bound project now exposes a read-only client context from its pinned release. Every
  profile, overlay, and local configuration path is resolved to an existing in-project
  file before it is returned, so a project symlink cannot redirect a client to another
  project. Memory, tasks, and secret paths remain undisclosed.
- Release-memory migration invokes the detected Bash runtime rather than assuming a
  `bash` executable on `PATH`.
- Planned task packages now carry machine-readable Kepler and human-approval artifacts.
  Read-only readiness allows implementation only when both apply to the current plan
  revision; an amendment request blocks work until a fresh plan and review exist.
- The Kepler verdict and human approval bind SHA-256 digests of the actual spec,
  research, and plan, so editing a reviewed artifact invalidates the gate. Human
  approval is recorded only through an interactive terminal confirmation and is
  intentionally documented as workflow evidence, not a cryptographic identity claim.
- Source CLI skills were reviewed as a family. Their portable entry/restore/checklist/
  discovery/retrospective rules are now recorded separately from Copilot invocation,
  trackers, source workspaces, package publishing, calendar and branch assumptions.
- A broad Kepler audit identified and started resolving the project-state boundary:
  `.agent-fabric` and its state-path parents are rejected when linked, release integrity
  is checked before binding or client enablement, and bound status validates all local
  contracts before exposing their paths.
- The same remediation adds reversible client rollback recovery, rejects secret-like
  profile values, aligns selected schemas with runtime contracts, and offers a checked
  project-command resolver without executing project commands.
- The workflow, Harness, host detector, Bash bootstrap, versioned release installer,
  project binding, and client-adapter lifecycle are now implemented as portable
  Bash/Python contracts. Their Windows/Git-Bash, WSL, Linux, and supported-client
  runtime matrix remains deliberately unexecuted until the single validation gate.
- A static target-only duplicate audit found no byte-identical duplicate or safe
  archival candidate. Canonical machine-readable contracts and their readable
  documentation remain complementary rather than competing copies; see
  `evidence/duplicate-audit.md`.
- The deferred final gate now has an explicit isolated host/client matrix. It records
  exact client preflight versions as execution evidence, treats unavailable surfaces as
  unsupported rather than passed, and never substitutes PowerShell, another client, or
  a fabricated hook; see `docs/validation-matrix.md`.
- The owner opened that gate on 2026-10-10. The Windows/Git-Bash row is complete and
  approved by Kepler in `evidence/windows-validation.md`; WSL, native Linux, and any
  unavailable delivery variants remain unverified matrix rows rather than failures or
  fabricated substitutes.

## Closure baseline

The implementation scope is frozen after the current Kepler remediation batch:
legacy-release binding eligibility, adapter scope/schema alignment, strict JSON numeric
types, and installation-version validation. Kepler's next review may verify only those
remediations. Any unrelated finding is recorded as deferred follow-up and must not
start another implementation loop. The next permitted broad execution activity is the
single final host/client validation gate, and only after explicit owner direction.
