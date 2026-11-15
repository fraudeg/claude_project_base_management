---
name: harness-ops
description: Use when choosing a model or effort, setting subagent models, planning sessions, or reading /usage and /context. Covers model policy, one task per session, handoff and /clear. Claude cannot run /usage.
---

# Harness operations

## Model and effort

- **Main session**: the strongest model at medium effort. Raise effort for one hard step, then lower it. No max effort routinely.
- **Subagents**: the cheaper model. Set `CLAUDE_CODE_SUBAGENT_MODEL` in the `env` of `.claude/settings.json`, and `model:` in each agent's frontmatter. A subagent with neither inherits the session's model.
- **Coverage**: `CLAUDE_CODE_SUBAGENT_MODEL` changes subagents that have no model of their own. It does not cover forks or the built-in Explore and Plan agents. When the model matters, dispatch a project agent by name.

## Session discipline

- One task per session. Finish, verify, stage.
- Before ending, write the handoff: rewrite Handoff in `plan.md`, and update any in-progress task file (`project-base:project-workflow`). The next session starts from those files, not from this conversation.
- `/clear` between unrelated tasks. A long conversation is carried into every request.

## Reading /usage and /context

Claude cannot run either command. Ask the user to run them and paste the output. Store the paste verbatim in the project's `log.md` with the date, then read off the few numbers that matter.

- **`/usage`**: the plan usage bars, and the attribution breakdown (share of usage per skill, subagent, plugin, MCP server). Check the subagents' share and any recommendations.
- **`/context`**: what fills the context window, by category. Check how much is always-loaded: `CLAUDE.md`, memory, skill and agent descriptions, MCP.

To cut always-loaded context, move area-specific instructions to path-scoped rules (`project-base:write-rule`) or skills. Compare a later paste against the baseline with `/project-base:measure`.
