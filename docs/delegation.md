# Delegation contract

Only a claimed, separate Socrates chat creates a delegation request inside the current project's local memory
database. It is idempotent and contains identifiers and artifact references, not a
copied prompt, secret, tracker payload, or another project's context.

```text
claimed Socrates submits request -> pending request
claimed Socrates dispatches      -> specialist reads scope and inputs
specialist submits result        -> pending result in project-local outbox
claimed Socrates acknowledges    -> durable memory record and task evidence
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

## Exchange a result

Use the launcher for the project's pinned release. Examples use
`<launcher>` for that selected entry point and a single JSON argument wherever
`--request` or `--result` appears. For a project-only installation, run the
pinned local launcher from the verified project root.

1. Claimed Socrates defines the objective, scope and required evidence in the
   task package. It submits the request and dispatches it by request key.

   ```json
   {
     "idempotency_key": "checklist-discovery",
     "session_id": "offline-checklist",
     "agent": "explore",
     "task_id": "offline-checklist",
     "scope_artifact": "docs/specs/active/offline-checklist/spec.md",
     "input_artifacts": ["docs/specs/active/offline-checklist/spec.md"],
     "required_outputs": ["docs/specs/active/offline-checklist/evidence/discovery.md"]
   }
   ```

   ```text
   <launcher> socrates submit-request <project> --session offline-checklist --thread-id <claimed-thread-id> --request <request-json> --json
   <launcher> socrates dispatch-request <project> --session offline-checklist --thread-id <claimed-thread-id> --key checklist-discovery --json
   ```

2. The selected specialist reviews the declared inputs and returns the requested
   evidence within its role. For example, a read-only explorer returns findings
   for the coordinator to record in the declared evidence file before the
   explorer submits its result. Use the same technical role, session and request
   key, and a distinct result key.

   ```json
   {
     "idempotency_key": "checklist-discovery-result",
     "request_id": "checklist-discovery",
     "session_id": "offline-checklist",
     "agent": "explore",
     "summary": "Mapped the local persistence options and recorded the constraints.",
     "artifacts": [{"path": "docs/specs/active/offline-checklist/evidence/discovery.md"}],
     "findings": [],
     "decisions": []
   }
   ```

   ```text
   <launcher> memory submit-result <project> --result <result-json> --json
   ```

3. Socrates checks the returned evidence and acknowledges the result by **result**
   key. The acknowledgment persists the result in project-local memory and
   updates the session. Use `memory pending-requests`, `memory pending-results`
   or `restore` to inspect interrupted work before retrying. Advance a step
   only when its actual evidence is present.

   ```text
   <launcher> socrates acknowledge-result <project> --session offline-checklist --thread-id <claimed-thread-id> --key checklist-discovery-result --json
   ```

## Verify artifact contributions

The path-only example is compatible with releases such as `0.1.31`, whose
validator accepts only the `path` field on artifacts. Record an independently
checked digest in task evidence when using such a release. This gives the
reviewer a reproducible file identity. Releases with project-journal attribution
also accept a lowercase SHA-256 in the artifact's `sha256` field and verify
contributions through the lifecycle.

For journal attribution, declare a concrete project-relative output in
`required_outputs`. Use distinct outputs when multiple requests affect the
same main file. The current journal implementation captures the output's
initial digest or absence at first dispatch. On acknowledgment it checks that
the digest matches the artifact on disk, differs from the baseline, and that
the resolved output is distinct from the request's inputs and scope. Completion
checks the proof again. Multiple requests claiming the same output bytes,
including through aliases, do not establish distinct contributions. See
[project journal and release notes](cli.md#project-journal-and-release-notes).

Every agent authorized to edit files inspects their current state before an edit and
preserves the owner's and other agents' changes. When the intended edit conflicts with
the current file, stop on that file, report the conflict and agree on its resolution;
do not silently overwrite or revert another person's work. This operational contract
does not claim a universal atomic guarantee against all concurrent processes.
