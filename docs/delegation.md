# Delegation contract

Only a claimed, separate Socrates chat creates a delegation request inside the current project's local memory
database. It is idempotent and contains identifiers and artifact references, not a
copied prompt, secret, tracker payload, or another project's context.

```text
Socrates -> delegation_requests (project-local, pending)
        -> selected specialist reads declared task artifacts
        -> result_outbox (project-local, pending)
        -> Socrates acknowledges result into durable memory
```

## Request envelope

`delegation-request.schema.json` requires:

- an idempotency key and session ID;
- one non-orchestrator target role;
- a task ID and one scope artifact;
- project-relative input-artifact references;
- required output identifiers.

The request deliberately does not carry natural-language task content. The task package
is the durable source for that content, so a retry cannot silently diverge from the
approved scope. Only Socrates may submit a request or mark its hand-off as dispatched;
neither action alters the immutable request payload.

Artifact references are normalized identifiers with no absolute path or `..` segment.

## Result envelope

`delegation-result.schema.json` binds its target role, session, and `request_id` to one
dispatched request, then records a concise summary and typed
references to artifacts, findings, and decisions. A specialist may submit it to the
local outbox, but only Socrates can acknowledge it into the memory record. Both
envelopes reject secret-like keys and common credential formats before persistence.
