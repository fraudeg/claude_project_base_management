---
name: audit
description: Audit an existing repository for project-base. Orients, measures the current Claude setup, finds what to change, and writes only the adoption project docs/projects/<date>-adopt-project-base/. Changes nothing else.
disable-model-invocation: true
argument-hint: "[pasted /usage and /context output]"
---

# Audit a repository

Arguments: `$ARGUMENTS` (optional: pasted `/usage` and `/context` output, the baseline).

Work in the current directory (the repository root). This skill reads the repository and writes **only** `docs/projects/<date>-adopt-project-base/`. It never edits, overwrites, reformats or moves `CLAUDE.md`, docs, code, `.claude/` or settings. It never stages or commits, and never runs the tests, a build or a graph build (they write files). A change to any of those files is a plan task the user approves later, one at a time.

Templates are in `${CLAUDE_PLUGIN_ROOT}/templates/project/`. Get today's date with `date +%Y-%m-%d`; it is `date` below.

## 1. Check first (writes nothing)

```bash
find docs/projects -maxdepth 1 -type d -name '*-adopt-project-base' 2>/dev/null
```

If it lists anything: stop. Write nothing. Say the adoption project already exists (name the folder) and that the user can continue it, or remove it to audit again.

## 2. Orient

Establish the project name, languages, **test command** (from the manifest, Makefile or CI; never invent one, write "unknown" if none), the top-level areas and what each holds, where tests and docs live.

- If `graphify-out/` exists, read `graphify-out/GRAPH_REPORT.md` and, when the `graphify` CLI is on PATH (`command -v graphify`), use `graphify query "<question>"` and `graphify explain "<node>"` (read-only).
- If only the CLI exists, do not build a graph (that writes `graphify-out/`). Note in the log that `/graphify` can build one later.
- With neither: the layout (`ls`, `git ls-files`), manifests, test config, README and docs.
- For breadth (more than a handful of top-level areas), dispatch `explorer` agents in parallel, one per area, each with one narrow question (what the area holds, where its tests are, which files record a decision). Use `explorer` if `.claude/agents/explorer.md` exists, else `project-base:explorer`. Spot-check the `path:line` answers you rely on. A small repository needs no agents.

## 3. Measure

Numbers, not opinions. Read-only commands only (`find`, `wc`, `ls`, `grep`, `head`, `git worktree list`).

- **CLAUDE.md files**: every `CLAUDE.md`, `CLAUDE.local.md` and `.claude/CLAUDE.md` in the repository (skip `node_modules`, `.git`, build output), and `~/.claude/CLAUDE.md` (size only): path, lines (`wc -l`), bytes (`wc -c`). Follow `@path` imports and count them. The total is what every session and agent loads. For a file over 200 lines, list its `##` headings with their line counts.
- **Auto-memory**: `~/.claude/projects/<this path, every non-alphanumeric character replaced by "-">/memory/`: file count and bytes, no content. If you cannot find it, write "not found".
- **`.claude/`**: each agent (name, `model:` set or not), rules (count, with or without `paths:`), skills (name), hooks, `settings.json` and `settings.local.json` (key names), `enabledPlugins`, `.mcp.json` server names, whether `.claude/project-base.json` exists and has a `parallel` key, and whether `env.CLAUDE_CODE_SUBAGENT_MODEL` is set. Record key names only; never copy a value from a settings or MCP file (they can hold secrets).
- **Usage baseline**: use the paste in `$ARGUMENTS` if there is one. Otherwise ask the user to run `/usage` and `/context` and paste both (Claude cannot run them). If nothing is pasted, or the session is non-interactive, do not wait: the baseline is `baseline pending — paste with /project-base:measure`.

## 4. Find

Look for exactly these. Each finding has its evidence (`path:line` or a size), the change, and the skill that makes it:

1. **Oversized CLAUDE.md sections**: a file over 200 lines, or a section that matters only under some paths. Name the section, its size, and where it belongs: a path-scoped rule (`project-base:write-rule`), a topic card, or a skill.
2. **Procedures that should be skills**: step-by-step how-tos (release, migration, setup) in CLAUDE.md or docs, used only now and then.
3. **Checklists that fail silently**: "remember to…" or "always X before Y" that nothing enforces. Name the check that would fail loudly (a hook, a test, a script).
4. **Decisions that deserve ADRs**: choices buried in docs or comments (`grep -rniE "we decided|decided to|do not change" --exclude-dir=node_modules --exclude-dir=.git . | head -50`), costly to reverse or likely to be asked about (`project-base:write-adr`).
5. **Areas that need topic cards**: areas that cannot be understood from one file, or that CLAUDE.md spends many lines on (`project-base:write-topic-card`).
6. **Subagents without a model**: each `.claude/agents/*.md` with no `model:`. They inherit the session's most expensive model; say whether `env.CLAUDE_CODE_SUBAGENT_MODEL` covers them.
7. **Missing test-output trimming**: no `.claude/project-base.json`, so the trim hook falls back to default patterns.
8. **Parallel sessions without isolation**: no `parallel` key in `.claude/project-base.json`, and evidence of parallel sessions: more than one `git worktree list` entry, or a `.claude/worktrees/` directory.

Keep at most five of kind 4 and five of kind 5, best evidenced first. A finding below the bar is not a task: park it under Deferred with the trigger that revives it.

## 5. Write the adoption project

`mkdir -p docs/projects/<date>-adopt-project-base`, then write four files from the templates, keeping their headings. Replace every `{{marker}}`. Never paste text containing `{{` from the repository into these files; describe it instead.

- `README.md`: `{{project_title}}` is `Adopt project-base`; status line `Status (<date>): in progress: audit done, plan awaiting approval`. Goal: bring this repository to the project-base way of working (subagents on a cheaper model, short always-loaded instructions, rules and topic cards loaded on demand, checkpoints, measured) through the plan, one approved task at a time. Done when: every task is done or deferred and a second `/usage` and `/context` has been compared with the baseline. Keep the Files list.
- `decisions.md`: keep the template, then add DEC-001: the audit changed nothing outside this folder, and each change is a plan task run one at a time with the user's approval. Add one more entry for the order of the plan and for anything proposed but left out, with why.
- `log.md`: under `## <date>` write Orientation (project, language, test command, areas, whether a graph was used), Measurements (the step 3 numbers; the `/usage` and `/context` paste verbatim, or `baseline pending — paste with /project-base:measure`), and Findings (the eight kinds in order, each with evidence; "none" where there is none).
- `plan.md`: replace the placeholder task with one line per change, `- [ ] N. <verb> <what> (<paths>): done when <check>`. Each is small enough for one `implementer` run: split a large CLAUDE.md move into one task per section or path group; the same small edit over a few files is one task. Name the skill or agent that does it. Order: the baseline paste first when pending, then by size of the saving, the follow-up measurement last. Standard tasks, only when they apply:
  - the paste of `/usage` and `/context` into `log.md`, when pending;
  - `.claude/project-base.json` for the test command found (or "ask the owner for the test command first" when unknown): the keys `test_command` (the command), `test_command_patterns` (`["^" + re.escape(command) + r"(\s|$)"]`) and `docs_root` (`"docs"`), the same shape as `<plugin>/templates/project-base.json`; generate it with Python `json.dump`, opened with mode `"x"`;
  - `model: sonnet` for the agents without a model;
  - merge the settings fragment into `.claude/settings.json`: `python3 "<plugin>/scripts/merge_settings.py" "<plugin>/templates/settings.fragment.json" .claude/settings.json`, show the diff, then rerun with `--apply`;
  - copy the plugin's `explorer`, `implementer`, `test-runner` and `reviewer` from `<plugin>/agents/` into `.claude/agents/`, skipping any name that exists;
  - `docs/projects/README.md`: add this project's index line, creating the file from `<plugin>/templates/projects-README.md` if absent;
  - answer the parallel-session questions (`<plugin>/skills/seed/parallel.md`) and apply them (finding 8; after the `.claude/project-base.json` task, which it needs, and after every task that edits files in the main checkout, because it writes the `parallel` key last and the guard then denies such edits): done when `.claude/project-base.json` has a `parallel` key or the owner answered no;
  - after a week of normal work, paste both again and run `/project-base:measure`.

  Plan tasks name plugin files as `<plugin>/…`, literally, and quote the path in every command. Never write the resolved plugin path into a project file: it is specific to a machine, a user and a plugin version. Write the Handoff as "Audited on <date>. Next: task 1, after the user approves the plan." plus the line "`<plugin>` is the project-base install directory: the `installPath` of the enabled `project-base@project-base` entry in `claude plugin list --json` (for a session started with `--plugin-dir`, that directory)." Write Deferred as the parked findings, or "None yet.".

## 6. Check and finish

```bash
grep -rn '{{' "docs/projects/<date>-adopt-project-base/"
git status --short
```

The grep must print nothing; fix the files and run it again until it does. In `git status --short` the only entry from this run is the new folder. Then stop: do not start the plan. Tell the user the folder written, whether the baseline is pasted or pending, the number of findings and tasks, that nothing outside the folder changed and nothing is staged or committed, and the next step: review the folder and commit it, then work the plan one task at a time through the `implementer` agent, approving each.
