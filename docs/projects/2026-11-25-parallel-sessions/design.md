# Design: parallel sessions

## Intent

A developer runs several Claude Code sessions on one repository at once (one per feature, fix or investigation). Today
they share the main checkout and its git index, so one session's `git commit` can sweep in files another session staged,
a branch switch carries someone else's changes along, and two sessions can take the same shared resource (the next
migration number, the project `CLAUDE.md`, a rules file) without either knowing. The sessions also cannot see each
other: each starts blind to what the others hold.

Make the safe way the default way: every session that edits works in its own worktree, the main checkout refuses edits
and commits, and every session sees on start who else is working, on which branch, and what they have claimed.

## What Claude Code already gives (do not rebuild)

Checked against the docs (code.claude.com, 2026-11-25):

- `claude -w <name>` / `--worktree`: creates `.claude/worktrees/<name>/` on branch `worktree-<name>` and, for that
  session, blocks edits, Bash and git aimed at the main checkout. `worktree.baseRef` (`fresh` default, or `head`).
- `.worktreeinclude` (gitignore syntax, project root): gitignored files to copy into each new worktree (`.env`).
- `claude -n <name>` / `/rename`: the session's display name, which is also its address for messages.
- Cross-session messaging (`ListAgents`, `SendMessage`, `/peers`, `notify_when_idle`): plain text over a local socket;
  inbound controlled by `crossSessionInbound` (`accept`, `hold`, `refuse`).
- Agent teams (experimental): one lead with teammates and a shared task list. Teammates share the working directory,
  so they are not the answer to isolation. Out of scope here.

What is missing, and what this project adds:

1. A session started **without** `-w` can still edit and commit in the main checkout. Nothing stops it.
2. No session knows what the others are working on or what shared resources they hold.
3. Nothing asks, when a repository is set up, whether it will be worked on in parallel.

## Decisions

- **No new command.** The question "will several sessions work on this repository at the same time?" is part of the
  setup: `seed` asks it for a new repository; `audit` reports its absence as a finding and its plan has a task that asks
  it. Both read the same questions from one reference file, `skills/seed/parallel.md`.
- **Opt-in by configuration.** Everything is driven by a `parallel` key in `.claude/project-base.json`. Without it every
  new hook exits 0 and prints nothing, so updating the plugin changes nothing in a repository that did not opt in.
- **No server, no MCP.** The board is plain files inside the git common directory. Advisory file reservations with
  expiry (as in MCP Agent Mail) are deferred until the plain board proves insufficient.
- **One board file per session**, so no two sessions ever write the same file and there are no write races.

## Configuration

`.claude/project-base.json` gains an optional key:

```json
{
  "parallel": {
    "worktrees_dir": ".claude/worktrees",
    "main_checkout": "block",
    "shared": ["CLAUDE.md", ".claude/rules/"]
  }
}
```

- `worktrees_dir`: where worktrees live, relative to the main checkout root. Default `.claude/worktrees` (native
  `claude -w`, no code). Any other value makes the setup install a `WorktreeCreate`/`WorktreeRemove` hook (below).
- `main_checkout`: `block` (default), `warn` or `off`. What the guard does in the main checkout.
- `shared`: repository-relative paths or prefixes that a session claims before editing. The setup proposes candidates
  it sees (a migrations folder, `CLAUDE.md`, `.claude/rules/`, a lockfile) and the user picks.

## The setup questions (`skills/seed/parallel.md`)

1. Will several sessions work on this repository at the same time? No: write nothing more, stop.
2. Where should worktrees live? Default `.claude/worktrees` (recommended: native, nothing to maintain).
3. Which gitignored files must every worktree have (`.env`, local config)? Writes `.worktreeinclude`, never
   overwriting an existing one (show what would be added instead).
4. Main checkout: block, warn, or off?
5. Which shared resources must be claimed before editing? Propose candidates from the repository; the user edits the
   list.

Then: write the `parallel` key (adding the key only; never change an existing value), make sure the worktrees
directory is gitignored (add a line to `.gitignore` if not), add to `CLAUDE.md` one line under its working section:
"Edit only from a worktree: `claude -w <topic> -n <topic>`. Claim a shared resource with `/project-base:claim` before
editing it." (in `seed` the template carries it; in `audit` it is a plan task).

## Components

### 1. Guard: `scripts/parallel_guard.py` (PreToolUse, matcher `Edit|Write|NotebookEdit|Bash`)

Reads the hook input (`cwd`, `session_id`, `tool_name`, `tool_input`) from stdin. Finds the repository of the target
(the file's directory for edits, `cwd` for Bash), loads `parallel` from that repository's main checkout
`.claude/project-base.json`; absent → exit 0.

- **Main checkout detection**: a directory is in the main checkout when `git rev-parse --git-dir` and
  `git rev-parse --git-common-dir` resolve to the same absolute path. A path under `worktrees_dir` is never main.
  Not a git repository → exit 0.
- **Edits in the main checkout** (`Edit`, `Write`, `NotebookEdit` whose file is in the main checkout): `block` → deny
  with the reason "This is the main checkout. Start a worktree: claude -w <topic> -n <topic>"; `warn` → allow with that
  text as context; `off` → nothing.
- **Bash in the main checkout**: the same treatment for `git commit`, `git checkout -b`, `git switch`, `git merge`,
  `git rebase`, `git cherry-pick`, `git reset` (the commands that move the shared index or HEAD). Read-only git and
  everything else pass. Matching is on the command text, after splitting on `&&`, `;`, `|`.
- **Shared resources** (any checkout): an edit to a path under a `shared` entry that another live session's board file
  claims → deny, naming that session and its branch, and say to message it with `SendMessage`. Not claimed by anyone →
  allow with a reminder to claim it. Claimed by this session → allow silently.
- Never crashes the tool call: any unexpected error → exit 0 with nothing printed (fail open; the guard is a safety
  net, not a lock).

### 2. Board: `scripts/session_board.py start|end` (SessionStart and SessionEnd)

Board directory: `<git common dir>/project-base-board/`. It is shared by every worktree of the repository, never
tracked by git, and needs no configuration.

- `start`: with `parallel` configured, write `<session_id>.json` = `{"cwd", "branch", "started", "name": null,
  "claims": []}` (keep `name` and `claims` if the file exists: resume and compact fire SessionStart again). Print, as
  context for the session: its own board file path; each other session's file (name or session id, branch, cwd,
  claims, age from mtime, marked `stale` when older than `STALE_HOURS` = 24); and `git worktree list`. Delete files
  older than `PRUNE_DAYS` = 7.
- `end`: delete `<session_id>.json`.

### 3. Skill `claim` (`/project-base:claim <path> [release]`)

1. Read the board directory. If another session claims the path (or a prefix of it): stop, name it, and message it with
   `SendMessage` (by its board `name`, else ask the user who it is). Do not edit until it releases or the user decides.
2. Otherwise add the path to this session's board file (the path printed at start), and set `name` from `ListAgents`
   ("This session is …").
3. `release`: remove the path. Claims also vanish when the session ends.

### 4. Custom worktree location (only when `worktrees_dir` is not the default)

`WorktreeCreate` replaces Claude Code's git logic and disables `.worktreeinclude`, so it applies only when the user
picked another directory. The setup copies `scripts/worktree_hook.py` into the project's `.claude/hooks/` (a project
settings file cannot reference the plugin's install path) and adds the `WorktreeCreate`/`WorktreeRemove` entries to
`.claude/settings.json` with `merge_settings.py`. The script runs `git worktree add <worktrees_dir>/<name> -b
worktree-<name> <base>` and copies the `.worktreeinclude` matches itself. The hook input and output contract must be
read from the Claude Code hooks docs before writing it; if the docs do not settle it, stop and report.

### 5. `audit` and `seed`

- `audit`: finding kind 8, "parallel sessions without isolation": no `parallel` key, and evidence that sessions run in
  parallel (more than one `git worktree list` entry, or a `.claude/worktrees/` directory). The plan task: "Answer the
  parallel-session questions (`<plugin>/skills/seed/parallel.md`) and apply them".
- `seed`: step 2 asks question 1; on yes it runs the rest of `parallel.md`.
- `check_seeded.py`: if `parallel` is present, `worktrees_dir` must be gitignored.

## Non-goals

- No lock that survives a crash or expires on its own; no server; no MCP tools in every session's context.
- No coordination of sessions across machines or containers (messaging does not reach them either).
- No moving of existing worktrees: `git worktree move` breaks a session running inside one.

## Anti-goals

- Updating the plugin changes behaviour in a repository that never answered the questions.
- The guard blocks work because of its own bug (it must fail open).
- A hook that prints on every tool call (the guard prints only when it denies or reminds).

## Review focus

1. A worktree under `.claude/worktrees/` sits inside the main checkout's directory tree: it must not be treated as the
   main checkout.
2. `git commit` inside a chained command (`git add x && git commit -m y`) is caught; `git log` and `git status` are not.
3. Missing or malformed `project-base.json`, a non-git directory, or a broken board file: exit 0, no output.
4. SessionStart on `resume` keeps the session's claims.
5. Hook paths: `${CLAUDE_PROJECT_DIR}` stays at the main root; scripts use the input `cwd`, never the env var, to find
   the worktree.
