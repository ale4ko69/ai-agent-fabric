# Implementation and amended owner direction

The owner explicitly selected temporary agent trust for personal use and asked for rollout to their projects, with passkeys and stronger provenance deferred. This changes the initial requirement for independently verifiable chat provenance. No historical task decision is inferred or recorded.

The new `spec attest-chat-approval` records an agent assertion identifying the task, source chat, revisions, artifact digests, Kepler digest and 24-hour validity. It revalidates Kepler advice on recording and the gate rechecks the current package and verdict. Terminal approvals are preserved. The Codex bootstrap instructs the claimed Socrates chat to present the exact preview, obtain a specific decision, and check readiness.

The agent assertion is not independent proof of the owner's identity; anyone able to invoke the command with an acceptable preview hash and chat reference can record it. This is the explicitly chosen temporary trust model. The passkey stage and its prerequisites are in `authorization-design.md`.
