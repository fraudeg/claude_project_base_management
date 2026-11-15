---
name: measure
description: Compare a new /usage and /context paste with the project's baseline and append the result to its log.md. Stores the paste verbatim, with a short before/after table. The paste becomes the baseline if none exists.
disable-model-invocation: true
argument-hint: "[pasted /usage and /context output]"
---

# Measure against the baseline

Arguments: `$ARGUMENTS` (the pasted `/usage` and `/context` output).

Work in the repository root. This skill appends to one file, the project's `log.md`. It never edits earlier text, and never stages or commits. Claude cannot run `/usage` or `/context`.

## 1. The paste

Take it from `$ARGUMENTS` or from the user's message. If there is none, ask the user to run `/usage` and `/context` and paste both, and **write nothing**. In a non-interactive run (`-p`), say what to paste and stop. If only one of the two is pasted, record it and compare only that part.

## 2. The project

The project is the one whose `log.md` holds the baseline.

```bash
grep -il baseline docs/projects/*/log.md 2>/dev/null
find docs/projects -maxdepth 1 -type d \( -name '*-adopt-project-base' -o -name '*-bootstrap' \) | sed 's|.*/||' | sort | tail -1
```

If the first command lists one file, use that project. Otherwise use the newest project from the second command. If there is none, ask which project (in `-p`: stop). Read its `log.md`.

## 3. Baseline or after

The baseline is the earliest `/usage` or `/context` paste in that `log.md`.

- Found: this paste is an **after**; compare it with the baseline.
- Not found (the log says `baseline pending`, or has no paste): this paste **is the baseline**. The old `baseline pending` line stays; the log is append-only. No table.

## 4. Read off the numbers

Only what the paste shows; write `n/a` for anything it does not.

- **Weekly usage**: the weekly percentage.
- **Attribution**: the top rows of the `/usage` breakdown (skills, subagents, plugins, MCP servers) with their shares.
- **Context**: each `/context` category with its tokens or share, and the total. Mark the always-loaded ones: memory files and `CLAUDE.md`, skills, agents, MCP tools, system prompt.

## 5. Append

Get today's date with `date +%Y-%m-%d`. Append to `log.md` with `>>` and a quoted heredoc (`<<'EOF'`, whose delimiter line appears nowhere in the paste), or with the Edit tool. Never an unquoted heredoc: the shell would expand `$` and backticks in the paste. Start with a blank line:

````markdown
## <date>: measure (baseline | after)

Pasted `/usage` and `/context`, verbatim:

<fence>
<the paste, unchanged>
<fence>

Read off: weekly <n>%; top attribution <row> <n>%, ...; context <category> <n>, ...
````

- `<fence>` is a run of backticks longer than any run inside the paste (at least three).
- For an **after**, add `Compared with the baseline of <baseline date>:` and a table of at most ten rows: weekly %, the top attribution rows by name, the context total and the always-loaded categories. Columns `Metric | Baseline | Now | Change`. Then one or two lines: what moved, and a caveat when the weeks' workloads differ (weekly % is not like for like).

## 6. Finish

Tell the user the log file appended to, whether this was the baseline or an after, and the table's main finding. Nothing is staged or committed.
