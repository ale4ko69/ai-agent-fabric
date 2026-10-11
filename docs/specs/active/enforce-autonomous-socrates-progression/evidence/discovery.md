# Discovery evidence

`src/ai_agent_fabric/memory.py` currently updates only the closing row in
`advance_task_step`, then `_next_task_action` selects the next pending row. The runtime
therefore has no durable distinction between a valid owner-approval wait and an
abandoned internal successor. The claimed-chat and closure-evidence guards already
provide the necessary safe write boundary.
