# Model routing policy

The Fabric routes by two independent controls, not by one provider's model name:

1. **Capability floor** — the least reasoning capability that may perform the role.
2. **Cost policy** — whether the route minimizes cost, balances cost and quality, or
   prioritizes quality.

A target project maps these controls to model IDs available through its selected agent
client and provider. The router chooses the least expensive available model that meets
both the role's capability floor and cost policy. This keeps one policy portable
across clients and prevents universal access to the most expensive model.

| Tier | Suitable work | Cost policy |
|---|---|---|
| Economy | Narrow classification or formatting inside an approved role | Never a substitute for a role's floor |
| Standard | Orchestration, implementation, ordinary exploration and review | Default engineering tier |
| Deep | Planning, high-risk opposition, broad architecture, security-sensitive review | Explicitly limited to high-impact reasoning |

## Initial role policy

| Role | Capability floor | Cost policy | Permitted escalation |
|---|---|---|
| Orchestrator | Standard | Balanced | Deep for complex cross-cutting decisions |
| Explore | Standard | Minimize | Deep for broad architecture or high uncertainty |
| Plan | Deep | Quality-first | None; planned work is intentionally quality-weighted |
| Opponent (Kepler) | Standard | Minimize | Deep only for an explicitly marked high-risk decision |
| Dev | Standard | Balanced | Deep only when project policy marks complexity or security risk |
| Review | Standard | Minimize | Deep for security, concurrency, or architectural changes |
| Validation (Euclid) | Standard | Minimize | Deep for complex contract analysis |

Exact model IDs, model prices, effort settings, rate limits, and provider spend limits
are selected in the target project's client configuration. For example, a project can
map an OpenAI-family or Anthropic-family model to `standard + minimize`; the Fabric
does not hard-code either vendor's current catalogue. An adapter must reject an
unavailable model and fall back only to a tier explicitly allowed for that role; it
must never silently upgrade every role to Deep.
