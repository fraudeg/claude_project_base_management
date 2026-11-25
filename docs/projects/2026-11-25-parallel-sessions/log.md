# Log

Dated entries, oldest first. Record what happened, what was measured and what was learned.

## 2026-11-25

- Project created from a research pass on running Claude Code sessions in parallel: the Claude Code docs (worktrees,
  cross-session messaging, agent teams), Anthropic's engineering posts on long-running harnesses (state lives in
  progress files, not in a session's memory), and community coordination servers (coordinationhub, agent-board,
  MCP Agent Mail).
- Evidence from a source repository: one `git commit` in the shared main checkout swept in another session's staged
  files; over twenty worktrees spread across four parent directories; sessions with generated names that say nothing
  of their work.
- Coordination servers set aside: two had zero or one star; MCP Agent Mail is mature but adds a server and tool context
  to every session, and its only feature missing from Claude Code is expiring file reservations (deferred).
- Owner decisions: no separate command, the question belongs to the setup (`seed` asks, `audit` offers); build the
  plugin first, apply it to existing repositories after their in-progress work ends; the setup asks where worktrees
  live.
