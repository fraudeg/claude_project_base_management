---
name: project-workflow
description: Use when starting, resuming, updating or closing a multi-session project in docs/projects/, or when deciding whether a task needs its own checkpoint file. Covers status line, decisions, log, plan, tasks.
---

# Project workflow

A project is a goal that takes more than one session. It lives in `docs/projects/<YYYY-MM-DD>-<slug>/` (use `docs_root` from `.claude/project-base.json` if it is not `docs`).

Templates: `${CLAUDE_PLUGIN_ROOT}/templates/project/` (`README.md`, `decisions.md`, `log.md`, `plan.md`) and `${CLAUDE_PLUGIN_ROOT}/templates/task.md`.

## Start

1. Write the four project files from the templates and replace every `{{placeholder}}`.
2. In `README.md` state the goal, when it is done, and the status line `Status (YYYY-MM-DD): state`.
3. Add one line to the Index in `docs/projects/README.md`.

## While working

- **Status line**: one line, rewritten with a new date whenever the state changes. Never appended to.
- **decisions.md**: one entry per decision, `DEC-001`, `DEC-002`. Never edit an old entry: add a new one that supersedes it and name it in both.
- **log.md**: dated entries, oldest first. Paste raw measurements verbatim.
- **plan.md**: one line per task, small enough for one `implementer` run. Rewrite Handoff at the end of every session. Park items under Deferred with the trigger that revives each.

## Task files

A task stays a line in `plan.md`. Give it a file only when it will not finish in one session: `tasks/NNN-<slug>.md` from `${CLAUDE_PLUGIN_ROOT}/templates/task.md`, NNN the next number in that project.

- The line `Status: in-progress|blocked|done` is what the reminder hook reads. Set `done` only once verified.
- Before the session ends, update Done so far, Files touched and Next step (the exact action). Resume from the file alone, never from the old conversation.
- `/project-base:checkpoint` writes or updates it.

## Close

1. Every task is `done`, or moved to Deferred with a trigger. No task file stays `in-progress`: set `done`, or `blocked` with the reason under Open questions.
2. Decisions that outlive the project become ADRs (`project-base:write-adr`), areas worth explaining become topic cards (`project-base:write-topic-card`), repeated corrections become rules (`project-base:write-rule`).
3. Set the status line to `delivered`, or `abandoned` with the reason, and today's date. Update the project's line in the Index.
