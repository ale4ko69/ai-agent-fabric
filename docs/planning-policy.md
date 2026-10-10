# Planning policy

## Triage

The Orchestrator classifies a task before assigning agents.

- **Local correction:** a known, isolated text or styling correction with no behavior,
  contract, data, dependency, or scope impact. It does not require a written plan.
- **Small bug:** a narrow, reproducible defect with an already-understood correction
  and a proportionate verification path. It uses `tasks.md` and execution evidence,
  but not `spec.md` or `plan.md`.
- **Planned work:** every new feature, reproducible bug, or feature rework. It requires
  a written plan and an independent opposition verdict before implementation.

If a defect is not proven to be narrow and understood, classify it as planned work.

## Plan lifecycle

```text
evidence -> plan -> KEPLER verdict -> approval gate -> implementation
                  └-> revise plan -> fresh KEPLER verdict
```

The Plan role authors the proposal; it cannot approve its own plan. KEPLER reviews
scope, alternatives, risks, validation, and evidence, then returns `advice`,
`challenge`, or `block`. A target-project policy selects whether a human approval is
also required. Implementation is blocked until challenges are resolved, blocks are
lifted by new evidence, and the required approval is present.

## Scope lock

KEPLER does not expand a spec. A finding outside the approved scope has exactly one
of these outcomes:

1. record it as a backlog proposal for later work; or
2. ask the human owner whether to amend the current spec.

It may return `block` when an out-of-scope concern makes the approved work unsafe or
invalid, but it still may not add implementation steps. Only an explicit spec amendment
followed by a revised plan and fresh KEPLER verdict authorizes expanded work.
