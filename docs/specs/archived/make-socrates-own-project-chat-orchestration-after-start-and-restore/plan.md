# Plan — Make Socrates own project chat orchestration after start and restore

## Analysis

1. Map all Codex start/restore/picker outputs and generated bootstrap ownership
   instructions to identify the single transition point.

## Architecture

1. Add one reusable `SocratesHandoff` envelope built from the existing lifecycle
   result; it has no transcript content and names task id, lifecycle, next action,
   owner, Root limits, and recovery command.
2. Return it only after successful start/restore. Picker and failure paths return
   no ownership grant.
3. Render the same contract in the Codex adapter/bootstrap and start/restore skills.

## Implementation

1. Add the envelope builder and attach it to start/restore results.
2. Update Codex-specific generated bootstrap and skills to enforce the ownership
   transition and recovery-only Root behavior.
3. Update docs without claiming unsupported native client role transfer.

## Validation

1. Add start/restore success, picker, failed lifecycle, and generated-bootstrap
   contract tests.
2. Run the full isolated suite, then preview/install a new immutable release and
   verify a bound project receives the handoff packet.

## Architecture

## Implementation

## Validation
