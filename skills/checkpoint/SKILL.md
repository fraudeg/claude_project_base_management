---
name: checkpoint
description: Write or update the checkpoint file of the task in progress (docs/projects/<project>/tasks/NNN-<slug>.md) so a fresh session can resume from it alone. Creates it from the plan.md task you name.
disable-model-invocation: true
argument-hint: "[task from plan.md]"
---

# Checkpoint a task

Arguments: `$ARGUMENTS` (the `plan.md` task to checkpoint, by number or title; only used when no task is in progress).

Work in the repository root. The format and the rules for task files are in `project-base:project-workflow`. Do not stage or commit.

## 1. Find the open tasks

The same test the reminder hook uses: a whole line `Status: in-progress` in a task file.

```bash
find docs/projects -mindepth 3 -maxdepth 3 -path '*/tasks/*.md' -type f -exec grep -lE '^Status:[[:blank:]]*in-progress[[:blank:]]*$' {} + 2>/dev/null | sort
```

- **One**: update it (step 2).
- **Several**: ask which. In a non-interactive run (`-p`), list them and stop.
- **None**: create one (step 3).

## 2. Update the task file

Edit the file in place; keep its headings.

- **Status**: `in-progress`, `blocked` (give the reason under Open questions) or `done`. Set `done` only after running How to verify and seeing it pass.
- **Done so far**: bring it up to date: what is finished, and the decisions taken on the way.
- **Files touched**: the files this task changed, from `git status --short`, `git diff --stat` and `git diff --cached --stat` (implementers stage and never commit), each with what changed. Leave out files that belong to other work.
- **Next step**: the exact next action: the file to open, the command to run, the test to write first.
- **How to verify**: the command and the result that shows the task is done.
- **Open questions**: what needs the owner's decision; empty if none.

## 3. Create the task file

1. Find the `plan.md` task: the one `$ARGUMENTS` names, searched in `docs/projects/*/plan.md`. If no task is named, or it matches none or more than one, ask (in `-p`: say so and stop).
2. In that project, the next number: one more than the highest `NNN` in `docs/projects/<project>/tasks/` (`001` if there is none), zero-padded to 3 digits. The slug is the task title in lowercase words joined by `-`, at most five words.
3. `mkdir -p docs/projects/<project>/tasks`, copy `${CLAUDE_PLUGIN_ROOT}/templates/task.md` to `docs/projects/<project>/tasks/NNN-<slug>.md` (`cp -n`; never overwrite), then replace every placeholder: the title (`NNN: <task title>`), Goal from the plan task (name the project and its `plan.md`), and the sections as in step 2. Status is `in-progress`.

## 4. Check and finish

Read the file as a session that has never seen this conversation: every path starts at the repository root, nothing says "as discussed" or "above", Next step can be run as written, no template placeholder is left (`grep -n 'path/to/file\|Task title' <file>`). Fix it until it holds.

Tell the user the file written or updated, its Status and the Next step. Nothing is staged or committed; the task file is committed with the project.
