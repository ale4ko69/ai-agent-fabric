# Project Harness and retrospective learning

Harness is a project-local quality loop, not merely a health check. It preserves the
useful operational idea from the source Fabric: recurring behavioural failures become
evidenced, bounded proposals for improving instructions, gates, profiles, or workflow.
The retrospective review does not change them. The separate maintenance action below
can apply only a specifically approved, narrowly typed project-local candidate.

The source-tree maintenance candidate preview described below is an inspection step;
it does not itself enable or apply maintenance. A project running an earlier pinned
release has only the commands in that release.

## Boundary and cadence

Every project stores its Harness state below `.agent-fabric/harness/`:

```text
harness/
  trace.jsonl                 # typed gate/checkpoint audit events
  signals.jsonl               # minimal behavioural signals; no conversation text
  retrospective-state.json    # immutable byte-watermark of the last approved run
```

The immutable signal-log watermark, not a daily or weekly calendar, defines the analysis
window. A project can be inactive for any length of time: `harness retrospective-input`
returns both signals after that project's latest approved watermark and the exact next
snapshot offsets and SHA-256 digest. `close-retrospective` must receive that unchanged
snapshot descriptor, so a signal recorded while the report is being reviewed remains
for the following run rather than being lost.
One project's cursor, signals,
reports, and local memory are never read by another project or by the global release.

## Signals are pointers, not transcripts

During a Fabric-mediated session, Socrates may record one of these categories when the
user corrects behaviour or the system observes a relevant failure:

- `user-correction`
- `agent-drift`
- `missed-instruction`
- `scope-violation`
- `memory-gap`
- `repeated-failure`
- `security-concern`
- `friction`

Each signal contains only its category, optional task identifier, optional
project-relative artifact reference, and generated timestamp. It must not copy raw
chat text, user frustration, commands, credentials, or tokens. A signal is a prompt to
investigate, not proof of a failure. Evidence belongs in the relevant local task package
or other declared project artifact.

## Retrospective protocol

```text
signals since local cursor
        -> Socrates builds an evidence-backed retrospective report
        -> Kepler checks evidence, scope, and unintended expansion
        -> human accepts, rejects, or defers each proposal
        -> only then close the run and advance the local cursor
```

The report must distinguish observed failure pattern and concrete evidence, root cause
or uncertainty, one bounded proposal per target, its validation evidence, and findings
outside the existing scope. Kepler records out-of-scope findings as deferred; it never
sends them to implementation without a human amendment.

## Client hooks and fallback

The global release defines the event vocabulary and safety requirements, not a universal
hook implementation. A selected client adapter may connect supported lifecycle hooks to
record signals, restore context, or offer checkpoints only after it has declared the
supported client version or version range, hook point, delivery method, and rollback
record. Client hooks must use the current project's binding and may access only that
project's local state.

If a selected Fabric adapter has no installed hook, the same protocol remains available
through the Fabric launcher commands. Fabric does not claim automatic capture from a
client's private chat history or invent a hook for an unconfigured adapter.

## Commands

All state-changing commands require a bound project and work only in that project.
`harness resume` and `harness health` are deliberately read-only diagnostics: they may
describe an unbound or incomplete project but never create or alter Fabric state.

```bash
ai-agent-fabric socrates signal <project> \
  --category user-correction --task-id <task-id> \
  --artifact docs/specs/active/<task-id>/evidence/feedback.md

ai-agent-fabric harness retrospective-input <project> --json

ai-agent-fabric harness close-retrospective <project> \
  --report-artifact docs/specs/active/<task-id>/harness-retrospective.md \
  --kepler-verdict-artifact docs/specs/active/<task-id>/kepler.md \
  --human-decision-artifact docs/specs/active/<task-id>/evidence/harness-decision.md \
  --snapshot-start-offset <value-returned-by-retrospective-input> \
  --watermark <value-returned-by-retrospective-input> \
  --snapshot-digest <value-returned-by-retrospective-input> \
  --reviewer opponent --human-approved
```

`retrospective-input` is read-only. `close-retrospective` requires project-local report,
Kepler-verdict, and human-decision artifacts, all below the project root, plus the
unchanged snapshot descriptor. It validates that the byte window is complete and still
has the supplied digest, as well as the durable references and declared approval; the
human-decision artifact is the auditable decision record. It advances the cursor only
after those conditions are supplied; it does not apply any proposed change.

### Maintenance candidate preview

The optional Metis profile can inspect a project-local candidate for an already
approved task. The project's `maintenance` capability must be enabled; a missing or
disabled `.agent-fabric/config/maintenance-policy.json` denies the preview. The policy
lists exact paths, command argument arrays and delivery
actions; it is project-owned data, not a sandbox. Candidate and policy schemas ship in
`schemas/maintenance-candidate.schema.json` and `schemas/maintenance-policy.schema.json`.
When maintenance is enabled, `harness review` includes signal categories, available
evidence references and the snapshot digest as candidate input. These pointers do not prove a failure and are not
an authorized change; Metis and Socrates must still establish evidence and scope.

For example, a project that explicitly opts into the `maintenance` capability can
restrict its policy to the one supported configuration path:

```json
{
  "schema_version": 1,
  "enabled": true,
  "paths": [".agent-fabric/config/harness/retrospective.json"],
  "commands": [],
  "delivery": []
}
```

The target must already exist. Its supported values are, for example,
`{"schema_version":1,"minimum_signal_count":2,"summary_style":"brief"}`.
Enabling the capability or changing policy is a separate project-owner decision;
upgrading a binding neither enables maintenance nor overwrites existing configuration.

```bash
ai-agent-fabric harness maintenance-preview /path/to/project \
  --task-id <task-id> --candidate <project-relative-candidate.json> --json
```

This command reads the candidate, checks the current task approval and policy, and
returns a digest and `preview-only` status. It does not execute commands, modify files,
or confirm that command effects are bounded. It is not evidence of an applied
improvement or an external delivery.

`harness maintenance-apply` accepts the same candidate only when its digest occurs on
its own `maintenance-candidate-sha256: <digest>` line in the currently approved task
specification. It requires the claimed Socrates lifecycle to be at implementation,
the existing `.agent-fabric/config/harness/retrospective.json`, an exact preimage hash,
an enabled policy and the `json-object` evaluation. Only `schema_version`,
`minimum_signal_count` and `summary_style` are accepted; the latter two change the
threshold and presentation hint returned by retrospective input. Optional evaluations
include `nonempty-utf8` and `no-conflict-markers`. These checks do not replace
task-specific regression tests. It refuses external commands and delivery.
It checks the current file before writing and reports a conflict rather than knowingly
overwriting another edit; it cannot guarantee atomic comparison against every race.
It saves the preimage under `.agent-fabric/backups/maintenance/preimages/`. Replacement
may alter file metadata such as ACLs; no universal metadata-preservation guarantee is
made. It does not roll back other work or claim that a local edit is a release.
The action also writes a prepared operation journal. After interruption or a conflict,
`harness maintenance-inspect <project> --candidate-sha256 <digest> --json` compares the
target with the preimage and candidate hashes. It reports `unchanged`,
`candidate-present` or `conflict` without automatically restoring or retrying.
Neither `unchanged` nor `candidate-present` proves whether an earlier write completed
or who changed the file afterwards. A pre-existing journal prevents automatic reuse
of that candidate. Inspect the evidence and agree on a resolution; preserve the file
and journal. A changed candidate requires the ordinary task scope and review checks.

To prepare an actionable candidate, include one `edit` with its exact `path`, the
SHA-256 of the existing file as `before_sha256`, and the full proposed UTF-8 `content`;
include `"evaluations":["json-object"]`, evidence paths, and empty `commands` and
`delivery` arrays. Before seeking approval, run `harness maintenance-digest <project>
--candidate <file> --json` to get the digest without asserting authority. The reviewed task
specification must contain the exact line `maintenance-candidate-sha256: <digest>`
before it is approved; changing the candidate, spec or review requires fresh scope
checking. After review and owner decision, run `maintenance-preview` to check current
policy and approval before `maintenance-apply`; allowlisted paths alone are not approval.

## Promotion to Fabric

A local lesson may become a Fabric improvement only through a separate, anonymized
release change. It must be stripped of project facts, task content, tracker data, and
secrets, reviewed as a normal Fabric change, and shipped in a new versioned release.
This preserves reuse without turning user-level Fabric into cross-project memory.
