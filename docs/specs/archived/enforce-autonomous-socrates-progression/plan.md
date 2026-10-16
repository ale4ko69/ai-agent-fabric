# Plan — Enforce autonomous Socrates progression

## Analysis

The defect is a state-machine gap, not a missing prompt. `next_action` is descriptive
rather than a persisted continuation outcome. The new transition must make a next
internal step active in the same database transaction that closes its predecessor.

## Architecture

- Extend the memory schema with explicit lifecycle states for owner approval and
  completion.
- Centralize outcome selection after each step transition: Guard outcomes retain
  precedence; final closure becomes completion; `kepler` hands off to an
  owner-approval wait; all other internal successors become `in-progress`.
- Return a typed continuation descriptor so callers can distinguish `resume`,
  `await-owner-approval`, `blocked`, `escalated`, and `completed`; each non-running
  descriptor carries a bounded reason and recommended next action.
- During schema initialization, explicitly migrate valid legacy active lifecycles to
  their derived safe state, resuming an unfinished internal step where appropriate.
- Add `rollout` after close-out in each workflow. It becomes the final internal action
  and cannot be skipped by reporting a completed lifecycle.

## Implementation

1. Add lifecycle-state/continuation helpers in `memory.py` and update the step
   transition transaction.
2. Surface the descriptor through `socrates.transition_step` and the existing CLI.
3. Document the non-silent stop contract at the lifecycle boundary.
4. Add focused lifecycle tests, including explicit migration coverage and asserted
   stop explanations/recommendations.
5. Generate a Codex close-out contract that treats the owner's accepted task goal as
   authorization for the bounded commit, push, and declared release sequence after
   clean review and validation.

## Validation

- Run the targeted lifecycle test module through the project-declared Python command
  after implementation.
- Inspect the emitted transition payloads and task memory snapshot for each path.
