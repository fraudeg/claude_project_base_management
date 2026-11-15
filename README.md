# project-base

English · [Español](README.es.md)

A Claude Code plugin that gives a repository a lean, durable Claude setup: projects with durable memory, cheap focused agents, rules that load only when relevant, checkpoints that let another session pick up a task, and a way to measure what the work costs. Seed an empty repository with the whole structure in one command, or audit an existing one and get an adoption project that measures where it stands and what to change.

It packages one developer's way of working so anyone can adopt it. It ships templates and the procedures to write them, never filled-in knowledge of any product.

## Install

```text
/plugin marketplace add fraudeg/claude_project_base_management
/plugin install project-base@project-base
```

## Seed or audit

| | `/project-base:seed` | `/project-base:audit` |
|---|---|---|
| For | an empty or new repository | an existing repository |
| Does | writes the whole structure (below), asking only what it cannot infer: project name, purpose, language, test command | orients, measures the current Claude setup, finds what to change |
| Writes | `CLAUDE.md`, `.claude/`, `docs/`, a first project `docs/projects/<date>-bootstrap/` | only `docs/projects/<date>-adopt-project-base/`: README, decisions, log with the baseline, plan with one small task per change |
| Never | overwrites: it stops if `CLAUDE.md`, `.claude/agents/` or `docs/projects/` exists, and points to audit | edits, reformats or moves your `CLAUDE.md`, docs, code, `.claude/` or settings |

An audit reads an existing graphify graph (`graphify-out/`) when there is one, never builds one, and does not need it. It asks you to paste `/usage` and `/context` (Claude cannot run them) and records them as the baseline. Executing the plan is ordinary project work: one task at a time through the agents, with your approval. The adoption is the repository's first project, so you learn the system by running it.

## Checkpoint and measure

- `/project-base:checkpoint` writes or updates `docs/projects/<project>/tasks/NNN-<slug>.md` for a task that outgrew one session: a `Status:` line (`in-progress`, `blocked`, `done`), goal, done so far, files touched, the exact next step, how to verify, open questions. A fresh session or agent resumes from that file alone. Small tasks stay a line in `plan.md`.
- A hook lists open tasks when the context is compacted (the summary tells the resumed session to update them) and when the session ends (shown to you).
- `/project-base:measure` takes a new `/usage` and `/context` paste, stores it verbatim in the project's `log.md` and writes a short before/after table against the baseline.

## What gets installed

The plugin itself carries the skills, the hooks and the agent sources. Seed copies the rest into your repository, where you own and edit it:

- `CLAUDE.md`: a short skeleton (under 200 lines) with the commands, conventions, criticality gate and rules for working with agents.
- `.claude/agents/`: `explorer`, `implementer`, `test-runner`, `reviewer`. All use `model: sonnet`; `explorer` and `test-runner` skip `CLAUDE.md`.
- `.claude/rules/`: one example rule showing `paths:` and a README on when to add one.
- `.claude/settings.json`: `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`, plus superpowers, ponytail and this plugin recommended to every collaborator. Merged by adding keys only, after showing you the diff.
- `docs/`: the map, the project workflow, ADRs and topic cards with their templates.
- `.claude/project-base.json`, read by the hooks and the agents:

  | Key | Meaning |
  |---|---|
  | `test_command` | the project's test command, used by `test-runner` |
  | `test_command_patterns` | regexes the trim hook matches against a Bash command. **Update it whenever you change the test command**, or trimming silently stops |
  | `docs_root` | where the docs live, default `docs` |

Hooks, shipped by the plugin:

- **Test-output trim** (PreToolUse on Bash): when the command matches `test_command_patterns` (defaults cover common runners when there is no config file), it keeps the last 100 lines and the exit code.
- **Checkpoint reminder** (PreCompact and SessionEnd): lists every task file with `Status: in-progress`. On PreCompact the list goes into the compaction summary; on SessionEnd it is shown to you, since Claude can no longer act.

Knowledge skills load on demand: `project-workflow`, `write-adr`, `write-topic-card`, `write-rule`, `criticality-gate`, `harness-ops`.

## Why: a case study

The method comes from a production harness on a large backend repository. There the weekly usage limit was being exhausted mostly by two things:

- subagents inheriting the most expensive model: 61% of usage;
- a 67 KB `CLAUDE.md` reloaded by every agent.

The harness cut the always-loaded instructions from 67 KB to 16 KB and moved subagents to a cheaper model with near-equal benchmarks. This plugin is that setup without the product: percentages and sizes are all that remain of the original.

## Recommended companions

Seed recommends two plugins to every collaborator of the repository. Credit to their authors: this plugin complements them and does not replace them.

- [superpowers](https://github.com/obra/superpowers) by Jesse Vincent: the process skills (brainstorming, plans, test-driven development, subagent-driven execution, review). The seeded `CLAUDE.md` tells its subagent skills to dispatch the project's agents instead of `general-purpose`.
- [ponytail](https://github.com/DietrichGebert/ponytail) by Dietrich Gebert: keeps code small, with the standard library first and no speculative abstractions.

## Known limits

- The trim hook keeps the last 100 lines, so a failure early in a very long test run can be cut from the output. The model sees only the tail: in a live check it noticed the cut and offered to rerun with the output saved to a file, which is a redirect and is never trimmed.
- Chained or compound commands (`a && b`, pipes, redirects, `;`, backticks, `$(...)`) are never trimmed; only a single simple invocation is rewritten.
- A seeded `test_command_patterns` replaces the default patterns: only the exact seeded command form (with any arguments after it) is trimmed. Add a pattern for each variant you run, for example `pytest ...` next to `python3 -m pytest ...`.
- Checked live on 2026-11-15 (Claude Code 2.1.325, `sonnet`): the rewrite applied both in `--permission-mode auto` and in the default mode with `Bash` allowed. In each run the model saw 100 lines of a 216-line failing run and the exit code (1) was kept. Other permission modes were not checked.
- The hook rewrites the test command (it adds `tail` and `pipefail`). A rewritten command may not match a permission allowlist entry written for the original.
- `docs_root` other than `docs` is honored only by the hooks and the agents. Seed writes under `docs/` and the skills use that path.
- Maintainers: `python3 scripts/check_neutral.py .` checks the tree for names that must not appear. The names go in a git-ignored `.neutral-denylist` at the repository root (one per line, `#` comments allowed) and are never committed; with no terms the check only warns and exits 0.
- The unit tests run anywhere (`python3 -m unittest discover -s tests`). The smoke tests (`tests/smoke_seed.sh`, `tests/smoke_audit.sh`) call `claude` and need an account that can run `--permission-mode auto`; they are paid runs.

## Contributing

Issues and comments are welcome; pull requests are limited to collaborators. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, copyright FraudEG.
