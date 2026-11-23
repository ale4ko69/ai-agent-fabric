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

For project journal attribution, declare a concrete project-relative output in
`required_outputs` and cite it in the result's `artifacts` array with its lowercase
SHA-256 as `sha256`. Use a separate evidence file when multiple requests will edit
the same main output. Fabric records the output's initial digest or absence on the
first dispatch. On acknowledgement it checks that the digest matches the current
file and differs from the baseline, and that the output is distinct from the
request's input and scope files. It checks that proof again on task completion.
If multiple requests claim the same output and bytes, including through aliases
of the same file, that evidence does not establish which request made the
contribution. Use distinct outputs to establish each contribution.
Existing result envelopes with path-only artifacts are still supported.

Use the pinned launcher to run `memory submit-result` for a specialist response.
Socrates uses `socrates submit-request`, `socrates dispatch-request` and
`socrates acknowledge-result` with the task session and its claimed thread ID.
See [CLI operations](cli.md#memory-guards-and-harness).

Every agent authorized to edit files inspects their current state before an edit and
preserves the owner's and other agents' changes. When the intended edit conflicts with
the current file, stop on that file, report the conflict and agree on its resolution;
do not silently overwrite or revert another person's work. This operational contract
does not claim a universal atomic guarantee against all concurrent processes.
