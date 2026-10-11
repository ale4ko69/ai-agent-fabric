# Implementation evidence

The committed separate-Socrates-chat lifecycle is present on the task branch:

- `start_task` and `restore_task` return the same `socrates_chat_request` shape.
- The request instructs Root to create or reopen the named separate Socrates chat.
- `socrates claim` binds that chat before lifecycle steps may advance.
- `socrates_chats` preserves the claimed thread identity and rejects a different claimant.

This completion pass adds explicit recovery-only wording for chat creation and
activation-packet delivery failures, plus regression coverage for the generated Codex
bootstrap and the shared start/restore packet.
