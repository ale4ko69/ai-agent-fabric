# Migration policy

Every candidate rule is classified before it is copied:

| Classification | Destination | Criterion |
|---|---|---|
| Core | Fabric source | true for every project and every supported environment |
| Profile | target repository | depends on one project's process, tools, or delivery rules |
| Adapter | optional integration package | depends on one external system or agent client |
| Retire | archive, then delete after review | duplicate, obsolete, or unsupported |

Migration is one rule at a time. A rule is copied only after its inputs, outputs,
dependencies, environment assumptions, and validation path are explicit.
