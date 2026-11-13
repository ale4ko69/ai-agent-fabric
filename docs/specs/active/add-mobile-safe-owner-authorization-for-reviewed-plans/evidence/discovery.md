# Discovery and blocking dependency

`src/ai_agent_fabric/task_specs.py` validates schema version 1 approvals with the `interactive-terminal` method and checks current planning artifact hashes and the exact Kepler verdict hash. `src/ai_agent_fabric/__main__.py` requires an interactive TTY for the approval command. Existing research prefix handling permits complete-line runtime appends while protecting the reviewed prefix. The declared schema is `schemas/task-approval.schema.json`.

The available Codex desktop `read_thread` capability returns conversation summaries to the agent; its documented interface provides no signed owner message or runtime-verifiable attestation. No host approval or attestation tool was exposed in the available tool inventory. An agent-written evidence file, an unsigned command argument, or an agent assertion naming a chat message can be fabricated by the same agent that seeks approval. Hashing that assertion binds content, but does not establish owner provenance. Therefore no available mechanism satisfies the requested independently verifiable chat authorization without changing the trust boundary.

Required path:

```text
Kepler advice + exact reviewed package -> owner sees exact package in chat
  -> host-authenticated owner decision bound to task, artifact hashes, verdict and expiry
  -> Fabric verifies trusted attestation and current package -> implementation gate
  -> changed material, expired or invalid attestation -> fail closed and request fresh decision
```

Existing `interactive-terminal` approvals must remain readable. A possible implementation requires a host-provided authenticated attestation and verifier, or an explicitly selected external identity/signing integration. Neither is currently available in the documented desktop capability surface; the latter would introduce a new credential or trust mechanism beyond the activation packet's stop boundary. A signed payload must include project/task identity, artifact digests, Kepler verdict hash, decision, issue/expiry times, audience and replay protection; verifier trust roots and lifecycle must be established independently of agent-controlled task artifacts. Task identity and current package must be checked again at use time. Exact message-to-package presentation and failure handling also need end-to-end validation.

At the time of this discovery, no implementation, approval, test, release or modification of another task had been performed. Subsequent owner direction deferred passkey integration and requested the work currently possible; see `authorization-design.md` and `partial-validation.md`. The task remains at implementation pending a trusted mechanism.
