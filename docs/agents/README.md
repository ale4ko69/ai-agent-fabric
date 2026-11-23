# Agent profiles

Each profile below is the readable companion to `core/agent-profiles.json` in a pinned
Fabric release. The JSON file is the canonical machine-readable authority; client
adapters must render from it and may not define a competing role contract.

| Role | Persona | Profile |
|---|---|---|
| Orchestrator | Socrates | [socrates.md](socrates.md) |
| Explore | Aristotle | [aristotle.md](aristotle.md) |
| Plan | Plato | [plato.md](plato.md) |
| Opponent | Kepler | [kepler.md](kepler.md) |
| Dev | Heracles | [heracles.md](heracles.md) |
| Review | Athena | [athena.md](athena.md) |
| Validation | Euclid | [euclid.md](euclid.md) |
| Maintenance (optional) | Metis | [metis.md](metis.md) |

The Metis profile in this source tree supports candidate inspection and a narrow
approved text-edit action. An installed release exposes only the profiles in its own
pinned registry.

The request envelope uses the lowercase technical role ID from each profile. Root
handles entry and recovery, and the claimed Socrates chat owns lifecycle transitions,
delegation and result acknowledgment. The human owner approves the reviewed plan
and, in New Product, the separate MVP contract. See the
[portable workflow](../workflow.md) and [delegation contract](../delegation.md).
