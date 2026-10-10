# Plan — Restore per-project Socrates task lifecycle

## Analysis

1. Map the source task-start orchestration protocol and Process Gate / `fabric-mem
   failure` lifecycle to the current portable runtime.
2. Compare it with the current Harness-only implementation and preserve the distinction
   between behavioural signals and concrete failures.

## Architecture

1. Specify `start task` and `restore task` as the project-local Socrates lifecycle
   boundary, together with ownership, role delegation contracts, and return channels.
2. Define the failure record and Guard decision model: schema, evidence reference,
   idempotency, retry counter, block/escalation state, and recovery representation.
3. Specify the boundary between Guards and Harness retrospective learning.

## Implementation

1. Change the task-start and task-restore paths so they activate the corresponding
   project-local Socrates lifecycle; do not add a standalone orchestrator command.
2. Add Socrates-owned persistence and read-only recovery for failures and Guard
   outcomes.
3. Add explicit Guard commands or internal invocation, then update adapter and workflow
   documentation without claiming unsupported hooks.

## Validation

1. Test signal-only correction, failed Guard, retry limit, escalation, recovery, and
   retrospective cursor behaviour independently.
2. Verify that no specialist can persist failure/Guard state directly and no record
   contains raw chat or secrets.

## Required Completion Review

1. Submit the changed implementation, tests, and transfer map to Kepler. Treat the
   verdict as an independent opponent review, not as a replacement for validation.
2. After Kepler's review is resolved, conduct a separate source-to-target audit as the
   implementation owner. Compare the source Process Gate and task-start lifecycle with
   the portable target; record transferred behaviour, deliberate exclusions, and gaps.
3. Do not mark the task complete until the Kepler verdict, the audit artifact, and all
   applicable validation evidence are present.
