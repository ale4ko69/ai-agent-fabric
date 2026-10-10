# Plan — Implement trusted Codex lifecycle hooks and cross-client behavior

## Analysis

Compare the installed marketplace writer, release preview, adapter manifest, and task
router. Preserve the existing rule that only Socrates records memory, Guards, and
Harness signals.

## Architecture

`Codex SessionStart -> trusted plugin handler -> global launcher restore picker ->
additional bounded context -> explicit user selection -> Socrates start/restore`.
The handler has no write path and never opens the transcript.

## Implementation

1. Add a Codex hook manifest and a Python handler to release assets.
2. Declare the concrete Codex adapter hook and package it into the local marketplace.
3. Extend release preview with marketplace replacement paths.
4. Add regression tests for packaging and for handler output/no lifecycle mutation.
5. Update README and operator/client evidence documentation.

## Validation

1. Run the isolated full test suite.
2. Run the source restore picker and record its migration boundary for the old binding.
3. After `main` contains the release, preview and install it; then update the project
   binding before re-running restore against the installed launcher.
