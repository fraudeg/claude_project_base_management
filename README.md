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
- `/project-base:claim <path> [release]` claims a shared path for parallel sessions (see below).
- `/project-base:measure` takes a new `/usage` and `/context` paste, stores it verbatim in the project's `log.md` and writes a short before/after table against the baseline.

## Parallel sessions

Several Claude Code sessions can work on one repository without overwriting each other. There is no separate command: `seed` takes question 1 from `parallel=yes|no` (without it, seed proceeds as no and offers it in its final message), runs the rest after the bootstrap project so the `parallel` key is written last, and `audit` flags a repository that shows parallel work with no `parallel` key and adds a plan task to answer the same questions (`skills/seed/parallel.md`). The questions: will several sessions work here at once (`parallel=yes|no`; no writes nothing more), where worktrees live (default `.claude/worktrees`), which gitignored files every worktree needs (`.worktreeinclude`), main checkout `block`, `warn` or `off` (default `block`), and which shared paths must be claimed before editing (default none). The answers go in the `parallel` key of `.claude/project-base.json`, never overwriting an existing one.

Start each session in its own worktree, named for its work: `claude -w <topic> -n <topic>`. **From an IDE extension** (no command line), open the session as usual: it starts in the main checkout, can read freely, and before its first edit runs `git pull --ff-only` and calls the `EnterWorktree` tool with a name for the task (the `CLAUDE.md` line tells it to; if it forgets, the guard's denial says so). An IDE session keeps its generated name, which is still its `SendMessage` address.

**Integration branch other than the remote default** (e.g. work goes to `develop` while `origin/HEAD` is `main`): native `claude -w` starts from the remote default, so the setup asks and writes `worktree.baseRef: "head"` to `.claude/settings.json`; a worktree then starts from the main checkout's HEAD, so run `git pull --ff-only` there first. **Config ignored by git**: if `.claude/project-base.json` is gitignored (a `.claude/*` rule), the guard and the board work only on your machine; the setup says so and offers `!.claude/project-base.json` for `.gitignore`.

- **Guard** (PreToolUse on Edit, Write, NotebookEdit and Bash). It checks the Edit, Write and NotebookEdit tools and the git commands below; other Bash (redirects, `sed -i`, other git commands) is not checked. In the main checkout it denies edits and these git commands: `commit`, `merge`, `rebase`, `cherry-pick`, `reset`, `switch`, `checkout -b`, `checkout -B` and a branch switch with `checkout` (`checkout -`, `checkout --detach` or `checkout <existing local branch>`; `checkout <file>`, `checkout -- <path>` and `checkout .` pass) (also inside `a && b`; `git log` and `git status` pass). `warn` only adds context; `off` disables this main-checkout rule. Any linked worktree is not the main checkout, and nothing under `worktrees_dir` is. The claim rule is separate and does not depend on `main_checkout`: for a path covered by `parallel.shared`, an edit is denied in any mode when another session claims it (the message names the holder, its branch and says to use `SendMessage`) and gets a reminder to claim it when nobody does.
- **Board** (SessionStart and SessionEnd). Each session has a file in the main checkout's `.git/project-base-board/`. At start a session sees the others (name, branch, directory, claims, age, `stale` after 24 hours) and the worktree list, and, when there are others, is told to coordinate with them through `SendMessage` (before touching their branch or claims, and when it finishes work they wait on). Start sessions with `-n <topic>`: the name is the address. Files of sessions idle more than 7 days are pruned. A session's file is deleted when it ends, so **claims last until the session ends, is cleared (`/clear`) or resumed; claim again after those**.
- **Landing work while the main checkout is blocked.** Commit in the worktree, then merge from outside Claude (a terminal); or push the worktree branch and open a PR; or set `main_checkout` to `warn`.
- `/project-base:claim <path> [release]` records a claim on the board after checking that no other session holds an overlapping one. On a conflict it stops and points to the holder.
- Messaging: sessions talk through `SendMessage` (the board shows each session's `name`, set at start from `claude -n <name>`; `/project-base:claim` sets it only if it is still empty) and `ListAgents`. Nothing else is needed.
- **Custom worktree location.** If `worktrees_dir` is not `.claude/worktrees`, seed copies `scripts/worktree_hook.py` to `.claude/hooks/` and merges `WorktreeCreate` and `WorktreeRemove` entries into `.claude/settings.json` after showing you the diff. The hook branches from the main checkout's HEAD, copies the files `.worktreeinclude` lists, and on removal keeps a dirty worktree and an unmerged branch. It replaces Claude Code's own worktree logic, and `git worktree add` from Bash does not run it.

MCP Agent Mail is not needed. Consider it if, after a few weeks of the board, sessions still collide on the same files: its one missing piece here is reservations that expire on their own.

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
  | `parallel` | set by the parallel-sessions questions: `worktrees_dir`, `main_checkout` (`block`, `warn`, `off`), `shared` (paths to claim). Absent: the hooks do nothing |

Hooks, shipped by the plugin:

- **Test-output trim** (PreToolUse on Bash): when the command matches `test_command_patterns` (defaults cover common runners when there is no config file), it keeps the last 100 lines and the exit code.
- **Checkpoint reminder** (PreCompact and SessionEnd): lists every task file with `Status: in-progress`. On PreCompact the list goes into the compaction summary; on SessionEnd it is shown to you, since Claude can no longer act.
- **Parallel guard** (PreToolUse on Edit, Write, NotebookEdit and Bash): with a `parallel` key, denies edits and git writes in the main checkout and edits to a shared path someone else claims. Without the key it does nothing.
- **Session board** (SessionStart and SessionEnd): writes and removes the session's board file, and at start lists the other sessions and the worktrees.

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
- Parallel guard: Bash is judged by the session's directory, following `cd` and `git -C <dir>` (relative to the current directory; several `-C` compose), each in its own repository with that repository's `parallel` config. Only `--git-dir`/`--work-tree` and some shell forms (unbalanced quotes, `cd $VAR`, `cd ~`, `-C $VAR`) are not caught: it fails open. `git pull`, `stash`, `revert` and `am` are not checked.
- The guard never approves anything: it only denies or adds context (`warn` mode, the claim reminder), so the normal permission prompt still applies. A claim conflict on a shared path is denied whatever `main_checkout` says.
- The reminder for an unclaimed shared path reaches Claude alongside the tool result, after that first edit has been made. It prompts a claim for later edits and does not stop the first one. A claim held by another session does deny.
- Claude Code's own worktree isolation refuses complex Bash that touches `.git` from inside a worktree, so the claim skill runs one plain command per step.
- Claims do not survive an exit followed by `--resume`: claim again. Age and staleness come from the board file's modification time, so a live session idle for more than 7 days without a start or claim is pruned.
- The unit tests run anywhere (`python3 -m unittest discover -s tests`). The smoke tests (`tests/smoke_seed.sh`, `tests/smoke_audit.sh`) call `claude` and need an account that can run `--permission-mode auto`; they are paid runs.

## Contributing

Issues and comments are welcome; pull requests are limited to collaborators. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, copyright FraudEG.
