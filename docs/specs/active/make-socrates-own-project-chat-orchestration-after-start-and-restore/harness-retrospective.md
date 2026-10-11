# Harness retrospective — 2026-10-11

## Signal window

One `user-correction` signal is pending since the last approved cursor. It is associated
with the archived self-hosting verification task. The signal is a lead, not proof.

## Evidence-backed pattern

During the current Socrates task, release-install preview policy was incorrectly
presented as a general precondition for task close-out. The user corrected that
interpretation.

The archived self-hosting specification included a versioned installation in its own
scope. Its evidence records a release preview and installation as task-specific
verification. The current task plan also contains a preview/install validation route,
but the current specification does not make that route an acceptance criterion and no
current human approval records it as a rollout action. It therefore cannot be presented
as a task-close-out blocker. Project-binding updates, commits, pushes, and GitHub actions
likewise require their own authorization.

## Root cause

Scope separation was lost: a conditional safety rule for an explicitly requested global
installation was conflated with a universal completion gate. Confidence: high, based on
the current-session correction and the task-specific archived scope.

## Bounded proposal

Target: Socrates close-out communication.

Before describing an item as required for task completion, label it as exactly one of:

1. an acceptance criterion of the current task;
2. a validation step explicitly requested by the user; or
3. a separate rollout action requiring its own user authorization.

Do not convert category 3 into a task-close-out blocker unless the current task
explicitly makes the rollout its acceptance criterion and the user has authorized it.

## Deferred findings

No change to the global bootstrap, project profile, workflow, or other projects is
proposed. Kepler reviewed the proposal as bounded and required the corrected evidence
framing above. The user then approved this proposal for implementation.
