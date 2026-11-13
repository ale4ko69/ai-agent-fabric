# Partial work validation

During the explicitly requested validation phase, `PYTHONPATH=src python -m unittest discover -s tests -p test_task_specs.py -v` completed successfully: 9 tests passed on the current Windows host using detected Git Bash. The new regression cases check that a fabricated `owner-chat` approval method is rejected and that changing an otherwise valid Kepler verdict invalidates an existing terminal approval. The existing research-prefix test checks preserved terminal approval behavior and invalidation of reviewed-prefix edits.

This is local regression evidence only. It does not validate mobile authorization, a WebAuthn implementation, a trusted verifier, or a release. The feature's implementation, independent review and end-to-end acceptance remain incomplete; no release is justified by these tests.
