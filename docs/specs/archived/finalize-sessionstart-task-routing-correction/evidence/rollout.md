# Rollout evidence

- Task commit: `8bb027dacd911b73c76814a64a3202f5636331aa`.
- PR: https://github.com/ale4ko69/ai-agent-fabric/pull/6; merged as
  `78f5342716e6e79aec5f40a3c3c2915f96b49002`.
- `distribution install-release` previewed and installed version `0.1.28`.
- The installed release and local marketplace hook contain the corrected guidance.
- The project remained bound to `0.1.27` after installation; `project status`
  reported `current_release: 0.1.28` and `update_available: true`. No project
  binding update was performed.
- The test establishes emitted context, not a live Codex interpretation.
