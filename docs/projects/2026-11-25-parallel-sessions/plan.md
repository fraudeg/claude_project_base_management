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

- [ ] Failing tests: main checkout true; a worktree under `.claude/worktrees/` false; a worktree outside the tree
  false; non-git dir → None/False; missing and malformed JSON → None; defaults filled.
- [ ] Implement with `subprocess.run(["git", "-C", ..., "rev-parse", ...])`, comparing resolved absolute paths.
- [ ] Tests pass; `git add`.

### Task 2: Guard hook

**Files:** Create `scripts/parallel_guard.py`; Test `tests/test_parallel_guard.py`; Modify `hooks/hooks.json`
(PreToolUse matcher `Edit|Write|NotebookEdit|Bash`).

**Produces:** `decide(hook_input: dict) -> dict | None` (None = say nothing; else the PreToolUse JSON output with
`permissionDecision` `deny` or `allow` plus reason/context); `GIT_WRITES` tuple; `main()` reads stdin, prints
`decide`'s output, exits 0 on any exception.

- [ ] Failing tests for each design rule: edit in main with block/warn/off; edit in a worktree; Bash `git commit` and
  `git add x && git commit -m y` in main denied; `git status`, `git log` allowed; shared path claimed by another board
  file denied naming its branch; unclaimed shared path → reminder; own claim → None; no `parallel` key → None;
  garbage stdin → exit 0.
- [ ] Implement; read the PreToolUse output format from the Claude Code hooks docs, not from memory.
- [ ] Tests pass; `claude plugin validate . --strict`; `git add`.

### Task 3: Board hook

**Files:** Create `scripts/session_board.py`; Test `tests/test_session_board.py`; Modify `hooks/hooks.json`
(SessionStart `start`, SessionEnd `end`, keeping `checkpoint_reminder.py`).

**Produces:** `start(hook_input) -> str` (context text), `end(hook_input) -> None`; `STALE_HOURS = 24`,
`PRUNE_DAYS = 7`.

- [ ] Failing tests: start writes the file with branch and cwd; a second start (resume) keeps `name` and `claims`;
  output lists other sessions with age and `stale`, plus `git worktree list`, plus the own file path; files older than
  `PRUNE_DAYS` deleted; end deletes the own file; no `parallel` key → no file, no output.
- [ ] Implement; check the SessionStart output format (additional context) in the hooks docs.
- [ ] Tests pass; `git add`.

### Task 4: `claim` skill

**Files:** Create `skills/claim/SKILL.md`; Modify `tests/test_skills.py` if it lists skills.

- [ ] Write the skill per design §3 (check, message the holder with `SendMessage`, write the claim, `release`).
- [ ] `python3 -m unittest discover -s tests`; `git add`.

### Task 5: Setup questions in `seed` and `audit`

**Files:** Create `skills/seed/parallel.md`; Modify `skills/seed/SKILL.md` (step 2 asks question 1, then reads
`parallel.md`), `skills/audit/SKILL.md` (finding kind 8 and its standard plan task), `templates/CLAUDE.md` (the
worktree and claim line, only when parallel is on: a marked block seed keeps or drops), `scripts/check_seeded.py`
(`worktrees_dir` gitignored when `parallel` exists) with its test.

- [ ] Write `parallel.md`: the five questions, the defaults, what each answer writes (`parallel` key via Python
  `json` adding the key only, `.worktreeinclude` never overwritten, `.gitignore` line, CLAUDE.md line).
- [ ] Update `seed` and `audit`; keep `audit` read-only (it only plans the task).
- [ ] `bash tests/smoke_seed.sh` and `tests/smoke_audit.sh` with stub binaries; unit tests; `git add`.

### Task 6: Custom worktree location (optional path)

**Files:** Create `scripts/worktree_hook.py`; Test `tests/test_worktree_hook.py`; Modify `skills/seed/parallel.md`
(copy the script to `.claude/hooks/` and merge the `WorktreeCreate`/`WorktreeRemove` entries when `worktrees_dir` is
not the default).

- [ ] Read the `WorktreeCreate`/`WorktreeRemove` input and output contract in the Claude Code hooks docs. If it does
  not settle what the hook returns, stop and record it in Deferred.
- [ ] Failing tests on a throwaway repo: create makes `<dir>/<name>` on `worktree-<name>` and copies
  `.worktreeinclude` matches; remove removes it.
- [ ] Implement; tests pass; `git add`.

### Task 7: Docs and release

**Files:** Modify `README.md`, `README.es.md` (a "Parallel sessions" section: what the setup asks, `claude -w -n`,
the board, `claim`, messaging, when to consider MCP Agent Mail), `.claude-plugin/plugin.json` (version `0.2.0`),
`docs/README.md` (map line for this project), this project's `README.md` status and `log.md`.

- [ ] Write the docs; `python3 scripts/check_neutral.py`; `claude plugin validate . --strict`; all tests.
- [ ] Manual check on a throwaway repo with `--plugin-dir`: two sessions, one in main (edit denied), one with `-w`
  (edit allowed), each sees the other on start; record it in `log.md`.
- [ ] `git add`; tell the owner it is ready to commit, tag `v0.2.0` and push.

## Handoff

Planned on 2026-11-25. Next: Task 1, in a fresh session in this repository, subagent-driven with model sonnet.

After release, phase 2 (outside this repository): in each repository that uses the plugin, `/plugin update
project-base`, then answer the parallel questions (through `/project-base:audit`'s plan task, or by following
`skills/seed/parallel.md` directly in a repository that already has an adoption project). Do not move existing
worktrees; new ones go to `worktrees_dir`, old ones close when their work merges.

## Deferred

- Advisory reservations that expire on their own (MCP Agent Mail style): revive if sessions still collide on the same
  files after a few weeks of the board.
- Agent teams integration: revive when teams can run each teammate in its own worktree.
