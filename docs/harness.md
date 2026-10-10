# Project Harness and retrospective learning

Harness is a project-local quality loop, not merely a health check. It preserves the
useful operational idea from the source Fabric: recurring behavioural failures become
evidenced, bounded proposals for improving instructions, gates, profiles, or workflow.
It never changes any of them automatically.

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
ai-agent-fabric harness signal <project> \
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

## Promotion to Fabric

A local lesson may become a Fabric improvement only through a separate, anonymized
release change. It must be stripped of project facts, task content, tracker data, and
secrets, reviewed as a normal Fabric change, and shipped in a new versioned release.
This preserves reuse without turning user-level Fabric into cross-project memory.
