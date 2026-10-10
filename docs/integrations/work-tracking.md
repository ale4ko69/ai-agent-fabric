# Work-tracking configuration

Each target repository may opt into a work-tracking provider through
`.agent-fabric/config/work-tracking.json`. The configuration controls writing policy;
it does not contain authentication material and does not itself make network calls.

```json
{
  "schema_version": 1,
  "provider": "project-adapter",
  "adapter": {
    "id": "project-owned"
  },
  "enabled": true,
  "write_policy": {
    "require_user_approval": true,
    "allowed_actions": ["read", "comment", "transition"]
  },
  "content": {
    "description_template": "templates/work-item-description.md",
    "comment_template": "templates/work-item-comment.md",
    "format": "provider-native"
  },
  "workflow": {
    "allowed_transitions": []
  }
}
```

The foundation knows only `none` and `project-adapter`. The adapter identifier belongs
to the project and is not interpreted by Fabric. A project adapter translates generic
actions and templates into the chosen external system's requests. It must obtain
credentials through the target project's approved mechanism, never from this file.
