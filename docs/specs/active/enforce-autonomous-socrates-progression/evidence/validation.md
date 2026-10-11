# Validation evidence

Executed from the repository root with `PYTHONPATH=src`:

```text
python -m unittest tests.test_task_lifecycle_and_guards
Ran 22 tests ... OK

python -m unittest tests.test_memory tests.test_task_specs
Ran 7 tests ... OK
```

The lifecycle coverage includes atomic internal continuation, explicit owner-approval
waiting with a recommended action, actionable final completion, actionable Guard block,
and schema-10 migration of a legacy pending internal successor.
