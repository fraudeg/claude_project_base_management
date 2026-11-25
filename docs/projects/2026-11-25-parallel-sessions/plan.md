# Parallel sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship project-base 0.2.0: the setup asks about parallel work, a guard keeps edits out of the main checkout, a
board shows every session what the others hold.

**Architecture:** Two stdlib Python hook scripts (guard, board), one optional worktree hook script, one skill (`claim`),
one shared reference file read by `seed` and `audit`. All behaviour is gated on the `parallel` key of
`.claude/project-base.json`.

**Tech Stack:** Claude Code plugin format, Markdown, Python 3 standard library (`unittest`), `claude plugin validate`.

**Spec:** `docs/projects/2026-11-25-parallel-sessions/design.md`

## Global Constraints

- Everything in English. Python 3 standard library only; tests: `python3 -m unittest discover -s tests`.
- No domain content of any product (`scripts/check_neutral.py` with `.neutral-denylist` must pass).
- Every skill `description` under 250 characters.
- Hooks fail open: any error → exit 0, no output. Without the `parallel` key → exit 0, no output.
- Scripts find the worktree from the hook input `cwd`, never from `CLAUDE_PROJECT_DIR`.
- Tests build throwaway git repositories (`tempfile`, `git init`, `git worktree add`); never touch a real repository.
- Stage only (`git add`); the owner commits.

## Review Focus

See design.md, "Review focus".

---

### Task 1: Shared config loader and main-checkout detection

**Files:** Create `scripts/parallel_config.py`; Test `tests/test_parallel_config.py`.

**Produces:** `load_parallel(start: Path) -> dict | None` (finds the main checkout from `start`, reads
`.claude/project-base.json`, returns the `parallel` dict with defaults filled, or None when absent, malformed or not
git); `main_root(start: Path) -> Path | None`; `is_main_checkout(path: Path) -> bool`; `board_dir(start: Path) -> Path
| None` (`<git common dir>/project-base-board`).

- [x] Failing tests: main checkout true; a worktree under `.claude/worktrees/` false; a worktree outside the tree
  false; non-git dir → None/False; missing and malformed JSON → None; defaults filled.
- [x] Implement with `subprocess.run(["git", "-C", ..., "rev-parse", ...])`, comparing resolved absolute paths.
- [x] Tests pass; `git add`.

### Task 2: Guard hook

**Files:** Create `scripts/parallel_guard.py`; Test `tests/test_parallel_guard.py`; Modify `hooks/hooks.json`
(PreToolUse matcher `Edit|Write|NotebookEdit|Bash`).

**Produces:** `decide(hook_input: dict) -> dict | None` (None = say nothing; else the PreToolUse JSON output with
`permissionDecision` `deny` or `allow` plus reason/context); `GIT_WRITES` tuple; `main()` reads stdin, prints
`decide`'s output, exits 0 on any exception.

- [x] Failing tests for each design rule: edit in main with block/warn/off; edit in a worktree; Bash `git commit` and
  `git add x && git commit -m y` in main denied; `git status`, `git log` allowed; shared path claimed by another board
  file denied naming its branch; unclaimed shared path → reminder; own claim → None; no `parallel` key → None;
  garbage stdin → exit 0.
- [x] Implement; read the PreToolUse output format from the Claude Code hooks docs, not from memory.
- [x] Tests pass; `claude plugin validate . --strict`; `git add`.

### Task 3: Board hook

**Files:** Create `scripts/session_board.py`; Test `tests/test_session_board.py`; Modify `hooks/hooks.json`
(SessionStart `start`, SessionEnd `end`, keeping `checkpoint_reminder.py`).

**Produces:** `start(hook_input) -> str` (context text), `end(hook_input) -> None`; `STALE_HOURS = 24`,
`PRUNE_DAYS = 7`.

- [x] Failing tests: start writes the file with branch and cwd; a second start (resume) keeps `name` and `claims`;
  output lists other sessions with age and `stale`, plus `git worktree list`, plus the own file path; files older than
  `PRUNE_DAYS` deleted; end deletes the own file; no `parallel` key → no file, no output.
- [x] Implement; check the SessionStart output format (additional context) in the hooks docs.
- [x] Tests pass; `git add`.

### Task 4: `claim` skill

**Files:** Create `skills/claim/SKILL.md`; Modify `tests/test_skills.py` if it lists skills.

- [x] Write the skill per design §3 (check, message the holder with `SendMessage`, write the claim, `release`).
- [x] `python3 -m unittest discover -s tests`; `git add`.

### Task 5: Setup questions in `seed` and `audit`

**Files:** Create `skills/seed/parallel.md`; Modify `skills/seed/SKILL.md` (step 2 asks question 1, then reads
`parallel.md`), `skills/audit/SKILL.md` (finding kind 8 and its standard plan task), `templates/CLAUDE.md` (the
worktree and claim line, only when parallel is on: a marked block seed keeps or drops), `scripts/check_seeded.py`
(`worktrees_dir` gitignored when `parallel` exists) with its test.

- [x] Write `parallel.md`: the five questions, the defaults, what each answer writes (`parallel` key via Python
  `json` adding the key only, `.worktreeinclude` never overwritten, `.gitignore` line, CLAUDE.md line).
- [x] Update `seed` and `audit`; keep `audit` read-only (it only plans the task).
- [x] `bash tests/smoke_seed.sh` and `tests/smoke_audit.sh` with stub binaries; unit tests; `git add`.

### Task 6: Custom worktree location (optional path)

**Files:** Create `scripts/worktree_hook.py`; Test `tests/test_worktree_hook.py`; Modify `skills/seed/parallel.md`
(copy the script to `.claude/hooks/` and merge the `WorktreeCreate`/`WorktreeRemove` entries when `worktrees_dir` is
not the default).

- [x] Read the `WorktreeCreate`/`WorktreeRemove` input and output contract in the Claude Code hooks docs. If it does
  not settle what the hook returns, stop and record it in Deferred.
- [x] Failing tests on a throwaway repo: create makes `<dir>/<name>` on `worktree-<name>` and copies
  `.worktreeinclude` matches; remove removes it.
- [x] Implement; tests pass; `git add`.

### Task 7: Docs and release

**Files:** Modify `README.md`, `README.es.md` (a "Parallel sessions" section: what the setup asks, `claude -w -n`,
the board, `claim`, messaging, when to consider MCP Agent Mail), `.claude-plugin/plugin.json` (version `0.2.0`),
`docs/README.md` (map line for this project), this project's `README.md` status and `log.md`.

- [x] Write the docs; `python3 scripts/check_neutral.py`; `claude plugin validate . --strict`; all tests.
- [x] Manual check on a throwaway repo with `--plugin-dir`: two sessions, one in main (edit denied), one with `-w`
  (edit allowed), each sees the other on start; record it in `log.md`.
- [x] `git add`; tell the owner it is ready to commit, tag `v0.2.0` and push.

## Handoff

Planned on 2026-11-25. Execution started 2026-11-25, subagent-driven (implementer and reviewer on sonnet), staged
only, nothing committed.

- Task 1 done: `scripts/parallel_config.py` (`load_parallel`, `main_root`, `is_main_checkout`, `board_dir`; every
  function returns None/False on any error). Reviewed, two fixes applied.
- Task 2 done: `scripts/parallel_guard.py` and a new PreToolUse group in `hooks/hooks.json`. Ruling: it never returns
  `permissionDecision: "allow"` (the docs say allow skips the user's permission prompt); warn mode and the shared
  reminder return `additionalContext` only. Bash parsing is quote- and heredoc-aware and follows `cd`; rare shell
  forms (subshell `cd`, `git -C`, `|&`, `if git commit`) fail open.
- Task 3 done: `scripts/session_board.py start|end`, SessionStart group and a second SessionEnd command in
  `hooks/hooks.json`. Claims do not survive an exit (`end` deletes the file, per design §3); they survive compact and
  other SessionStart re-fires within a live session.
- Task 4 done: `skills/claim/SKILL.md`. It changes the board file with an inline `python3` command through Bash,
  because the board sits in `.git/` of the main checkout, where the guard denies Edit and Write.
- Task 5 done: `skills/seed/parallel.md` (the five questions; answers passed as one JSON argument), `seed` takes
  question 1 from `parallel=yes|no` (without it: no, and it offers the question in its final message), `audit`
  finding kind 8 and its plan task,
  `templates/CLAUDE.md` marked block, `check_seeded.py` checks `worktrees_dir` is gitignored. Smoke: seed 16 PASS,
  audit 14 PASS (no smoke run covers `parallel=yes`). Seed may add the `parallel` key to an existing
  `project-base.json`, the one exception to its keep rule.
- Task 6 done (not deferred: the docs settle the contract, the path is the last non-empty stdout line):
  `scripts/worktree_hook.py create|remove` (self-contained, copied into the project), `templates/worktree-hooks.fragment.json`,
  and a "Custom worktree location" section in `parallel.md`. The hook input has no base ref, so the base is the main
  checkout's HEAD. Remove never forces and deletes the branch only with `git branch -d`.

- Task 7 done: both READMEs ("Parallel sessions", hooks, known limits), version 0.2.0, this project's status and
  log. `.neutral-denylist` filled with owner-approved terms (gitignored); `check_neutral.py` passes.
- Manual check, live (Claude Code 2.1.332, sonnet, `--plugin-dir`, throwaway repo): see `log.md`. The main checkout
  denied Write and `git commit`; `-w` sessions could write; overlapping sessions saw each other at start; a claim held
  by one session denied another's edit; the custom `WorktreeCreate` hook created `trees/feat` and copied `.env`.
- Final whole-change review fixed: setup writes the `parallel` key last (it was blocking its own writes), claims are
  documented as dropped on `/clear` and `/resume`, `worktrees_dir` covering the repo root falls back to the default,
  the claim skill refuses paths with `'`. Tests 151 OK, validate passes, smoke seed 21/21, smoke audit 14/14.

- After an independent review of these decisions: per-repository judgment of `cd`/`git -C` targets, `git checkout
  <branch>` denied in the main checkout, `design.md` amended. See `log.md`.

Released as `v0.2.0` on 2026-11-25 (tag and GitHub release). Next: phase 2 below. Not run live:
`warn` mode and the seed offer path (a "yes" after the final message).

After release, phase 2 (outside this repository): in each repository that uses the plugin, `/plugin update
project-base`, then answer the parallel questions (through `/project-base:audit`'s plan task, or by following
`skills/seed/parallel.md` directly in a repository that already has an adoption project). Do not move existing
worktrees; new ones go to `worktrees_dir`, old ones close when their work merges.

## Deferred

- Advisory reservations that expire on their own (MCP Agent Mail style): revive if sessions still collide on the same
  files after a few weeks of the board.
- Agent teams integration: revive when teams can run each teammate in its own worktree.
