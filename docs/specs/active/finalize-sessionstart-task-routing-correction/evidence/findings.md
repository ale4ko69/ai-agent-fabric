# SessionStart routing correction

The hook lists sanitized active-task metadata without restoring or starting a task.
Its prior instruction required a selection whenever active tasks existed, even if a
new request concerned unrelated authorized work. The corrected context directs a
restore only for a matching request, permits unrelated new work, and asks for a
choice when the request is ambiguous. The hook itself cannot determine user intent;
this is an instruction to the client, not a deterministic router.

Scope: `hooks/codex_session_start.py` and its focused lifecycle test. Metis,
Harness, help, other tasks, and project bindings are outside this correction.
