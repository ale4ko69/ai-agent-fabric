# Client-adapter evidence

**Reviewed:** 2026-10-10. This record captures the client facts used by the
release manifests. It is an input to adapter decisions, not an installation guide.
Each future adapter or hook implementation must re-check the linked vendor document
against the selected client version.

| Client runtime | Verified instruction behaviour | Hook decision in baseline |
|---|---|---|
| Codex local runtime | Codex reads user instructions below `~/.codex` and applicable repository instructions root-to-leaf; later repository layers refine the global layer. | No Fabric hook is installed. Codex desktop plugin hooks are a different packaging surface and need a separate reviewed adapter. |
| Copilot CLI | User, repository, and applicable path/agent instructions are combined; GitHub documents no general precedence rule. The user entry point is `~/.copilot/copilot-instructions.md`. | Copilot has native user-level and repository-level hook surfaces, but this baseline installs none. A future hook adapter must declare exact native event names, client version, a per-host command strategy, ownership, rollback, and uninstall. |
| Claude Code | User and project `CLAUDE.md` files are additive; project layers appear after user layers. `@path` imports are supported, including a user-level import into the Fabric bootstrap. | No Fabric hook is installed. Claude hooks remain a separate concrete adapter decision because their lifecycle and configuration format are client-specific. |

## Source links

- [OpenAI Codex prompting guide — AGENTS loading](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [GitHub Copilot CLI instruction loading](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)
- [GitHub Copilot CLI hook configuration](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks)
- [Claude Code memory and instruction loading](https://code.claude.com/docs/en/memory)

## Baseline rule

`hooks.mode: "unsupported"` means **this Fabric adapter has no installed or managed
hook implementation**. It does not claim that the vendor client lacks a hook API. Model
routing never enables a hook. A model selection changes the role's allowed model only;
the selected client, its installed version, host, and adapter manifest decide whether a
specific hook can be installed.
