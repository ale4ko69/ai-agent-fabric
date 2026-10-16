# Plan evidence

The approved technical direction is an atomic successor transition in the project-local
SQLite lifecycle. It does not create a worker or client adapter dependency: it persists
the next internal action as in progress, or persists one of the three valid stopping
states (owner approval, Guard-derived blocker, completion).
