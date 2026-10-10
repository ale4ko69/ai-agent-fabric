# Baseline transfer filter

Date: 2026-10-10

This is the authoritative filter applied before comparing source artifacts with AI
Agent Fabric. It prevents a broad source inventory from turning unrelated source
automation into a Fabric requirement.

## Baseline for this release

Only these mechanisms belong to the common Fabric:

1. The seven canonical roles and their shared workflow boundaries.
2. Planned-task and small-bug artifacts, Kepler review, human approval, and archive.
3. Project-local memory protocol, specialist outbox, read-only restore, and Harness
   retrospective signals.
4. Host and selected-client detection, project command resolution, and secret entry.
5. Versioned user-level release installation, project binding, client adapters, update,
   rollback, uninstall, and reversible symbolic-link delivery.

## Optional project packs

These are not installed or enabled by the baseline. They require a project profile and
a separate implementation decision: specialised validation rules, domain-specific
analysis, documentation maintenance, UI/UX work, UI verification, knowledge
publication, tracker or repository-host integration, multi-repository coordination,
and scheduled automation.

## Excluded source artifacts

Source-bound commands, environment assumptions, local paths, service endpoints,
repository-specific publishing, work-item operations, cross-repository synchronization,
calendar rules, and generated runtime data are excluded. They have no target mapping,
must not be copied into an adapter or workflow, and are not evidence of an incomplete
baseline.

## Re-entry rule

To change this filter, a human must amend the active task scope with the artifact's
purpose, project profile requirements, security boundary, delivery lifecycle, and
validation evidence. Kepler may challenge that amendment but cannot add it on its own.
