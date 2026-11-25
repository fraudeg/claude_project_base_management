# {{project_name}}

## What this project does

{{one_line_purpose}}

Primary language: {{language}}.

## Commands

- Test: `{{test_command}}`

<!-- Add the build, lint and run commands that are actually used, one line each. -->

## Tests

- Run `{{test_command}}` before saying a task is done, and read the failures, not only the exit code.
- Write the failing test first when fixing a bug or adding behavior.
- For a long run, dispatch the `test-runner` agent: it returns failures only.
- The command is also in `.claude/project-base.json`: `test_command` (read by the agents) and `test_command_patterns`
  (a regex for the command, read by the test-output trim hook). Change the command here, `test_command` and
  `test_command_patterns` together, or trimming silently stops.

## Conventions

- Follow the style of the surrounding code. Do not reformat files you did not change.
- One task per change; keep diffs small enough to review.
- Ask before adding a dependency.
- The `implementer` agent stages changes and never commits. Commit only when asked.
- A rule for one area goes in `.claude/rules/` (path-scoped, loaded only there), not in this file. This file is
  loaded in every session, so keep it short.

## Package map

<!-- One line per top-level directory: what it holds and what depends on it. Keep it current. -->

- `path/`: what lives here

## Criticality gate

Before editing, rate the change 1-10 with the `project-base:criticality-gate` skill: 1-3 instrumentation, 4-6
consistency with an approved pattern, 7-8 observable and reversible, 9-10 policy or irreversible (stop and ask for a
decision).

What counts as policy in this project:

<!-- List the areas where a wrong change cannot be undone or breaks a promise to users. -->

## Working with agents

Dispatch the project agents in `.claude/agents/` by name. Never use a bare `general-purpose` agent.

- `explorer`: find code or answers; read-only; returns `path:line`.
- `implementer`: do one planned task, test first; stages, never commits.
- `test-runner`: run the test command; returns failures only.
- `reviewer`: review a change in a fresh context; returns findings with failure scenarios.

When a superpowers skill (`subagent-driven-development`, `dispatching-parallel-agents`) says to dispatch an
implementer or a reviewer, dispatch `implementer` or `reviewer` instead of `general-purpose`. Subagents run on
`sonnet` (`CLAUDE_CODE_SUBAGENT_MODEL` in `.claude/settings.json`).

<!-- parallel:start -->
Edit only from a worktree: `claude -w <topic> -n <topic>`. Claim a shared resource with `/project-base:claim` before editing it.
<!-- parallel:end -->

## Where documents go

- `docs/README.md`: the map of all documents. Start there.
- `docs/projects/<date>-<slug>/`: work that spans sessions. README with one dated status line, decisions, log, plan.
- `docs/projects/<project>/tasks/NNN-<slug>.md`: checkpoint of a task that outgrew one session. Resume from this file
  alone and update it before the session ends (`/project-base:checkpoint`).
- `docs/adr/`: one decision per file, when a choice needs its reason kept.
- `docs/topics/`: topic cards that answer recurring questions about one area.
- `.claude/rules/`: one-line, path-scoped rules.
