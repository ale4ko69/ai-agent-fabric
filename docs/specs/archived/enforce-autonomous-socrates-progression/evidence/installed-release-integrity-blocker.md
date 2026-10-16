# Installed release integrity blocker

After the implementation approval was recorded, the global launcher rejected
Fabric-managed writes for this project. Its read-only `project status` response was:

```text
status: invalid
error: Fabric release file set does not match its manifest
```

The task implementation and local test validation do not require modifying the global
release. Repairing or replacing that release was not authorized, so durable lifecycle
close-out through the launcher remains blocked pending owner direction.
