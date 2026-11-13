# Review and validation

Review: the hook continues to obtain active records through the read-only restore
picker, sanitizes metadata, and does not start or restore a task. Its instruction
now covers matching, unrelated, and ambiguous requests. No unrelated source files
were changed. This is a context instruction; actual client interpretation is not
proved by unit tests.

Validation: `PYTHONPATH=src python -m unittest discover -s tests -p
test_task_lifecycle_and_guards.py` passed 26 tests. `git diff --check` passed.
The initial test invocation omitted `PYTHONPATH` and could not import the source
package; sandboxed Git Bash then failed with MSYS access denied. The successful
test used the detected Git Bash outside the sandbox.
