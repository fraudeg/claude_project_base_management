# Parallel sessions: the setup questions

Used by `seed` (in its step 8; question 1 comes from its `parallel` argument or its final-message offer) and by the `audit` plan task "Answer the parallel-session questions". Ask the questions below; each has its default (a non-interactive run takes the defaults). Write only what an answer says.

Precondition: `.claude/project-base.json` exists. If not, stop and say to create it first (`seed` creates it in its step 5; the `audit` plan has that task: order this one after it).

1. **Will several sessions work on this repository at the same time?** No: write nothing more, stop.
2. **Where should worktrees live?** Default `.claude/worktrees` (recommended: native `claude -w`, nothing to maintain). Take the default. Any other directory needs the hook in "Custom worktree location" below.
   **Which branch does a new worktree start from?** Ask only for the default directory, and only when they differ: `git symbolic-ref --short refs/remotes/origin/HEAD` (the remote's default branch; no output: skip) against `git branch --show-current` in the main checkout. Native `claude -w` starts from the remote's default branch (`worktree.baseRef: "fresh"`), which is wrong when work integrates into another branch (e.g. a `develop`). Default: the main checkout's branch, written as `worktree.baseRef: "head"` (Claude Code takes no branch name). Tell the user it starts from the main checkout's local HEAD, so they run `git pull --ff-only` there before `claude -w` (the guard does not block `pull`).
3. **Which gitignored files must every worktree have (`.env`, local config)?** Default: none. Each goes on a line in `.worktreeinclude`.
4. **Main checkout: block, warn, or off?** What the guard does for edits in the main checkout. Default `block`.
5. **Which shared resources must be claimed before editing?** Repository-relative paths or prefixes (a migrations folder, `CLAUDE.md`, `.claude/rules/`, a lockfile). Propose the candidates you see; default `[]` unless the user gives a list.

## What the answers write

Write the `parallel` key LAST, after every other write below (`worktree.baseRef`, `.worktreeinclude`, `.gitignore`, the `CLAUDE.md` line, the custom-location steps): once it is there, the guard denies edits in the main checkout, including this setup's own.

- **`parallel` key** (last) in `.claude/project-base.json`, with Python `json`: load, check it is an object, add the key only if absent, never change an existing value. Pass the answers as one JSON argument (here answers 2, 4, 5):

```bash
python3 -c '
import json, sys
f = ".claude/project-base.json"
d = json.load(open(f))
p = json.loads(sys.argv[1])
assert isinstance(d, dict) and isinstance(p, dict)
if "parallel" not in d:
    d["parallel"] = p
    open(f, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
' '{"worktrees_dir": ".claude/worktrees", "main_checkout": "block", "shared": ["CLAUDE.md"]}'
```

  This is allowed on an existing `.claude/project-base.json` (the one exception to the KEEP rule in `seed`): it adds the key only.

  After writing it: if `git check-ignore -q .claude/project-base.json` exits 0, the config is gitignored, so the guard and the board work only on this machine. Say so, and offer the fix the user commits: append `!.claude/project-base.json` to `.gitignore` (it works when the ignore rule is `.claude/*`, not `.claude/`). Do not apply it unasked.

- **`worktree.baseRef`** (answer 2, when it is `head`): add it to `.claude/settings.json` with the same add-only Python as the `parallel` key (file `.claude/settings.json`, an absent file is `{}`, nested key `worktree.baseRef`; an existing different value is kept and reported). Before the `parallel` key.
- **`.worktreeinclude`** (answer 3): never overwrite. If it exists, show the lines that would be added and let the user add them.
- **`.gitignore`**: add a line for `worktrees_dir` (e.g. `/.claude/worktrees/`), appending, and creating the file if absent, only if `git check-ignore -q <worktrees_dir>/x` exits 1 (not ignored). Any other non-zero exit (e.g. 128, not a git repo): skip.
- **`CLAUDE.md`**: add, if absent, under "Working with agents", the line "Edit only from a worktree: start with `claude -w <topic> -n <topic>`, or, in a session already open (an IDE), run `git pull --ff-only` in the main checkout and call the EnterWorktree tool with a short name for the task before the first edit. Claim a shared resource with `/project-base:claim` before editing it." (`seed` keeps it from the template; in `audit` it is part of the plan task).

## Custom worktree location

Only when the answer to question 2 is not `.claude/worktrees`.

1. `mkdir -p .claude/hooks`. If `.claude/hooks/worktree_hook.py` exists, compare: `diff .claude/hooks/worktree_hook.py "${CLAUDE_PLUGIN_ROOT}/scripts/worktree_hook.py"`. Identical: skip the copy and continue. Different: show the diff and stop (never overwrite).
2. If it does not exist: `cp "${CLAUDE_PLUGIN_ROOT}/scripts/worktree_hook.py" .claude/hooks/`.
3. Merge the hook entries. First without `--apply`, and show the diff to the user:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/merge_settings.py" "${CLAUDE_PLUGIN_ROOT}/templates/worktree-hooks.fragment.json" .claude/settings.json`
   Then, as a separate step, the same command with `--apply`.
4. Make sure the chosen directory is gitignored (same `.gitignore` rule as above).

Tell the user:

- The hook replaces Claude Code's own worktree logic (`WorktreeCreate`/`WorktreeRemove`).
- `.worktreeinclude` is handled by the script (gitignored files matching it are copied into a new worktree).
- The base is the main checkout's HEAD.
- Worktrees created by Bash (`git worktree add`) do not run the hook.
