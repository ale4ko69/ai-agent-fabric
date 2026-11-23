# Release history

Entries summarize changes in the repository by the version declared in
`pyproject.toml`. A source entry records code history. Use
`project context <project> --json` to check the version a particular project runs.

## Unreleased

- Project-only installation and the optional Codex adapter plan local Git
  exclusions for generated artifacts. Compatible tracked contracts retain their
  bytes. Existing installations can preview a Git cleanup and keep their release,
  memory, tasks and binding.
- Setup and update documentation distinguishes user-level distribution from
  project-only installation. The standalone [New Product guide](docs/new-product.md)
  describes both Codex launch paths and their approval boundaries.

## 0.1.31 source

- Added project-local delegation CLI operations for Socrates to submit, dispatch and
  acknowledge requests and results, and for specialists to submit outbox results.
  Source revision `f74cc63`.
- Added completed-task journal entries from close-out facts and local versioned
  release notes assembled from explicitly selected tasks. Source revision `bab6745`.
  See [project journal and release notes](docs/cli.md#project-journal-and-release-notes).

## 0.1.30 source

- Added bounded project-local maintenance and declarative source inventories for
  the versioned release installer. Source revision `37a096b`.
- Added isolated project-only installation with a pinned launcher and a separate
  optional local Codex adapter. Source revision `76be905`.
- Integrated New Product discovery into the local Codex project adapter with a
  separate Socrates chat and explicit MVP approval. Source revision `1bb518e`.

## 0.1.29 source

- Added agent-attested chat approval for the exact Kepler-reviewed implementation
  plan as an alternative to terminal confirmation. Source revision `eb3f780`.
