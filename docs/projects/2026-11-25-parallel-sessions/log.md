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

## 2026-11-25: build

Built and staged (not committed); the manual two-session check is pending.

- Task 1: shared config helpers (`scripts/parallel_config.py`): read the `parallel` key, find the main checkout and the board directory.
- Task 2: the guard (`scripts/parallel_guard.py`): main-checkout block/warn/off for edits and git writes, shared-path claims.
- Task 3: the session board (`scripts/session_board.py`) on SessionStart and SessionEnd, and `hooks/hooks.json`.
- Task 4: the `claim` skill.
- Task 5: the setup questions (`skills/seed/parallel.md`), with the `seed` and `audit` changes, the `CLAUDE.md` template line and `check_seeded.py`.
- Task 6: the optional custom worktree location (`scripts/worktree_hook.py`, `templates/worktree-hooks.fragment.json`).
- Task 7: README.md and README.es.md, version 0.2.0, this project's status and map line.

Rulings that changed the plan:

- The guard never returns `permissionDecision: "allow"`: per the docs it skips the permission prompt. It denies, or adds context only.
- `WorktreeCreate` was not deferred: the docs settle the contract (the hook prints the worktree path; the base is the main checkout's HEAD).
- Claims do not survive an exit: the board file is deleted at SessionEnd, so after `--resume` a session claims again.

## 2026-11-25: manual check

Claude Code 2.1.332, model sonnet, `--plugin-dir`, a throwaway repository with `parallel` {block, shared [CLAUDE.md]}.

- Run 1, three overlapping `-p` sessions (w1 with `-w`, main1 in the main checkout, w2 with `-w`): main1's Write was denied with "This is the main checkout. Start a worktree: claude -w <topic> -n <topic>"; w1's and w2's Writes were allowed; main1 saw w1 at start; w2 saw main1 and w1, with branch, cwd and claims; the board files were gone after all ended.
- Earlier attempts did not overlap because Claude Code blocks `sleep N` and `sleep N && echo` in Bash; an until-loop on a flag file kept the sessions alive.
- Run 2: an Edit of unclaimed CLAUDE.md in a worktree was allowed and the reminder arrived as context after the edit; session a claimed CLAUDE.md with the skill; session b's Edit of CLAUDE.md was denied ("CLAUDE.md is claimed by a (branch worktree-a). Message it with SendMessage."); `git commit --allow-empty` in the main checkout was denied.
- Fixed after the check: the board takes the `-n` name from `session_title`; the claim skill says to run one plain command per step (native isolation refused a combined loop).
- Custom worktree location, live: `worktrees_dir` "trees", `worktree_hook.py` copied to `.claude/hooks/`, the
  fragment merged with `merge_settings.py`. `claude -w feat` ran in `trees/feat` on branch `worktree-feat`, with the
  gitignored `.env` copied through `.worktreeinclude`, and its Write was allowed. `WorktreeRemove` was not run live.
- Final checks after the whole-change review fixes: 151 unit tests OK, `claude plugin validate . --strict` passes,
  `check_neutral.py` passes, smoke seed 21/21 (including a `parallel=yes` run), smoke audit 14/14.
- Independent review of the final decisions, then fixes: a `cd` or `git -C` target is judged by its own repository's
  config (the guard had denied a commit in a repository that never opted in), and deny wins over warn across
  targets; `git checkout <branch>` is denied in the main checkout like `git switch`; Bash calls without "git" spawn no
  git process; the board deletes its own file even when a custom worktree directory is already gone; `design.md`
  gained an Amendments section for every deviation. `WorktreeRemove` script checked on worktrees made by Claude Code:
  a clean one was removed with its merged branch, a dirty one was refused and kept (a `-p` session never fires the
  hook, so it was run with the documented input). 160 unit tests OK, smoke seed 21/21.

## 2026-11-26: first adoption, 0.2.1

Applied to a large existing repository through `/project-base:audit` (headless, in a worktree) and its plan task.
The audit wrote only its folder and found the missing `parallel` key. Three gaps came out of it, fixed in 0.2.1:

- `worktree.baseRef`: the remote's default branch (`main`) was not the integration branch (`develop`), so native
  `claude -w` would have started from the wrong branch. `parallel.md` now compares them and writes `head`.
- The config was gitignored by a `.claude/*` rule, so the guard would have worked on one machine only. `parallel.md`
  now checks and offers the `.gitignore` negation.
- The repository had its own trim hook for its test command; the audit now plans which hook stays, and documents
  `"test_command_patterns": []` to turn the plugin's off.

## 2026-11-26: 0.2.2

- The board showed each session the others but never told it to talk to them, so sessions saw each other and still
  worked blind. When other sessions exist, the start context now says to coordinate through `SendMessage` by name
  (before touching another session's branch or claims, and when finishing work others wait on). The README says to
  start sessions with `-n`, since the name is the address.
