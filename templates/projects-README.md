# Projects

A project is a goal that takes more than one session. Each lives in `docs/projects/<date>-<slug>/`:

- `README.md`: one status line, `Status (YYYY-MM-DD): state`, rewritten with a new date whenever the state changes;
  then the goal and when it is done.
- `decisions.md`: the choices made, numbered DEC-001, DEC-002, one each. Never edit an old one: add a new one that
  supersedes it.
- `log.md`: dated notes and measurements, oldest first.
- `plan.md`: the tasks, the handoff for the next session, and deferred items with the trigger that revives each.
- `tasks/`: a checkpoint file per task, only for a task that outgrows one session.

## Tasks and checkpoints

A task is a line in `plan.md`, small enough for one `implementer` run. Only a task that will not finish in one
session gets a file, `tasks/NNN-<slug>.md`, committed with the project. Its sections: Status, Goal, Done so far,
Files touched, Next step (exact), How to verify, Open questions. Its `Status:` line is `in-progress`, `blocked` or
`done`.

A fresh session or agent resumes from that file alone, never from the old conversation. While a task is
`in-progress`, a hook reminds Claude to update it before the context is compacted or the session ends. The
`/project-base:checkpoint` command writes or updates it.

## Closing a project

1. Every task is done, or moved to Deferred with a trigger.
2. Decisions that outlive the project become ADRs in `docs/adr/`; areas worth explaining become topic cards.
3. Set the status line to `delivered` (or `abandoned`, with the reason) and today's date.

## Index

None yet. Add one line per project: `- [YYYY-MM-DD-slug](./YYYY-MM-DD-slug/): current state`.
