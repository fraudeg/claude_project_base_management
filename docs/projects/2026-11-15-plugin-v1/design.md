# Design: project-base plugin v1

## Intent

A public Claude Code plugin that packages one developer's way of working with Claude Code so anyone can adopt it:
projects with durable memory, cheap focused agents, rules that load only when relevant, checkpoints that let another
session pick up a task, and measurement of what the work costs. It comes from a production harness built on a large
backend repo, published by the FraudEG organization, and carries none of that product's domain.

Why: the author wants to share the method. The method's value showed in numbers on the source repo: the weekly limit
was being exhausted mostly by subagents inheriting the most expensive model (61% of usage) and by a 67 KB CLAUDE.md
reloaded by every agent; the harness cut the always-loaded instructions to 16 KB and moved subagents to a cheaper
model with near-equal benchmarks.

## Users

A developer working with Claude Code, usually on a large existing repository, sometimes on a new one.

## Goals

1. **Seed** an empty or new repository with the whole structure in one command.
2. **Audit** an existing repository: understand it, measure its current Claude setup, and write an adoption project
   (baseline, findings, plan) without changing anything else.
3. The adoption is itself the repository's first project, so the user learns the system by running it.
4. **Checkpoints**: a task that outgrows one session leaves a file another session or agent resumes from.
5. Recommend superpowers and ponytail to every collaborator of the seeded repository.

## Non-goals

- No domain content: no rules, ADRs or skills of any product. The plugin ships templates and the procedures to write
  them, never filled-in knowledge.
- No graph-memory server, no external agent runner, no dependency on a specific language or framework.
- Not a replacement for superpowers' process skills; it complements them.

## Anti-goals (failure even if it technically works)

- The audit rewrites a user's CLAUDE.md or docs without being asked.
- Anything that names FraudEG's product, clients, vendors, data or numbers beyond the anonymised case study above.
- The plugin's own always-loaded footprint grows the context it promises to shrink (its skill and agent descriptions
  must stay short).
- Agents that silently inherit the session's most expensive model.

## Constraints

- Distributed as a Claude Code plugin whose repository is also its own marketplace:
  `/plugin marketplace add fraudeg/claude_project_base_management`.
- License MIT, copyright FraudEG. Everything in English.
- Plugin facts that shape the design (Claude Code plugin reference):
  - A plugin can ship skills, commands, agents, hooks and workflows; a `CLAUDE.md` at the plugin root is not loaded
    and path-scoped rules are not a plugin component. So the project's own CLAUDE.md, rules and agents must be
    written into the user's repository by the seed, where the user owns and edits them.
  - Plugin components are namespaced (`project-base:reviewer`); the seed copies agents into `.claude/agents/` so the
    project's names are plain and editable.
  - A plugin name must not start with `claude-` or read as Anthropic's.
  - `plugin.json` has a `dependencies` field; project settings take `extraKnownMarketplaces` and `enabledPlugins`.
- Subagent model: `CLAUDE_CODE_SUBAGENT_MODEL` changes subagents without a model of their own, not forks or the
  built-in Explore and Plan agents.

## Approaches

1. **Claude Code plugin + own marketplace (chosen).** One install, updates itself, carries skills, agents and hooks;
   the same way superpowers and ponytail ship.
2. GitHub template repository. Simplest for an empty repo, but cannot audit an existing one (the main case) and each
   copy freezes at creation.
3. Loose skills (`npx skills add`). Portable to other agents, but cannot carry agents or hooks, and checkpoints depend
   on a hook.

Chosen 1 with the owner: 2 misses the audit, 3 loses what keeps the system running by itself.

## What the user gets

### Commands (skills invoked as slash commands)

- **`/project-base:seed`**: for an empty or new repository. Asks only what it cannot infer (project name, primary
  language, test command). Writes:
  - `CLAUDE.md` (short skeleton: what the project does, commands, tests, conventions, package map, criticality gate,
    working with agents, where documents go) under 200 lines by construction.
  - `.claude/rules/` with one example rule showing `paths:` and a README on when to add one.
  - `.claude/agents/`: `explorer`, `implementer`, `test-runner`, `reviewer`, all `model: sonnet`; prompts take the
    test command and doc locations from the seed's answers.
  - `.claude/settings.json`: `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`, the plugin's hooks are active through the plugin
    itself, and superpowers and ponytail recommended through `extraKnownMarketplaces` + `enabledPlugins`.
  - `docs/README.md` (the map), `docs/projects/README.md` (the project workflow), `docs/adr/README.md` with the ADR
    template, `docs/topics/README.md` with the topic-card template.
  - A first project `docs/projects/<date>-bootstrap/` recording the seed and the measurement to take after a week.
- **`/project-base:audit`**: for an existing repository. Read-only except for the adoption project it writes:
  1. Orient: use graphify when it is installed (`graphify-out/` or the CLI), else the repo layout, manifests, test
     config and docs; dispatch `explorer` agents for breadth.
  2. Measure: CLAUDE.md files and their sizes, auto-memory size, existing `.claude/` agents, rules, skills, hooks,
     settings, plugins; ask the user to paste `/usage` and `/context` (Claude cannot run them) and record them as the
     baseline.
  3. Find: oversized CLAUDE.md sections and the paths they belong to, procedures that should be skills, checklists
     that fail silently, decisions buried in docs or comments that deserve ADRs, areas that need topic cards,
     subagents without a model, missing test-output trimming.
  4. Write `docs/projects/<date>-adopt-project-base/` (README with status line, decisions, log with the baseline,
     plan with one task per change, each small enough for one `implementer` run) and stop.
  Executing the plan is ordinary project work: one task at a time through the agents, with the user's approval.
- **`/project-base:checkpoint`**: writes or updates the checkpoint of the task in progress (see below).
- **`/project-base:measure`**: compares a new `/usage` + `/context` paste against the project's baseline and appends
  the result to its log.

### Skills (loaded on demand)

- `project-workflow`: how a project folder works (README with one dated status line, decisions DEC-nnn, log,
  plan with handoff, tasks, deferred with triggers) and how to close one.
- `write-adr`, `write-topic-card`, `write-rule`: templates and the bar for each (one decision per ADR; a topic card
  answers questions and links rules; a rule is one line, path-scoped).
- `criticality-gate`: the generic 1-10 scale (1-3 instrumentation, 4-6 consistency with an approved pattern, 7-8
  observable and reversible, 9-10 policy or irreversible: stop for a decision), with the project defining what counts
  as policy.
- `harness-ops`: model choice (main session on the strongest model at medium effort, subagents on the cheaper one,
  no max effort routinely), session discipline (one task per session, handoff, `/clear`), and reading `/usage`.

### Agents (copied into the project by seed or by an audit task)

`explorer` (read-only, skips CLAUDE.md, returns locations), `implementer` (one task, test first, stages, never
commits), `test-runner` (runs the project's test command, returns failures only, skips CLAUDE.md), `reviewer`
(fresh context, reads the matching rules and topic cards itself, returns findings with failure scenarios).

### Hooks (shipped by the plugin)

- Test-output trim: PreToolUse on Bash; when the command is the project's test command (configured with
  `userConfig`, default patterns for common runners), keep the last 100 lines and the exit code.
- Checkpoint reminder: on PreCompact and SessionEnd, when the working tree has an open task (a task file with status
  `in-progress`), remind Claude to update it before context is lost.

### Checkpoints

A task listed in a project's `plan.md` gets its own file only when it outgrows one session:
`docs/projects/<project>/tasks/NNN-<slug>.md`, committed with the project. Sections: Status
(`in-progress`, `blocked`, `done`), Goal, Done so far, Files touched, Next step (exact), How to verify, Open
questions. A fresh session or agent resumes from the file alone, never from the old conversation. Small tasks stay a
line in `plan.md`.

## Repository layout

```text
.claude-plugin/
  marketplace.json        this repo as a marketplace with one plugin
  plugin.json             name project-base, MIT, dependencies or recommendations (see builder notes)
skills/                   seed, audit, checkpoint, measure, project-workflow, write-adr, write-topic-card,
                          write-rule, criticality-gate, harness-ops
agents/                   the four agents (source of what seed copies)
hooks/hooks.json          trim and checkpoint reminder
scripts/                  hook scripts (Python 3 stdlib only)
templates/                CLAUDE.md, rule, ADR, topic card, project files, task file, settings fragment
docs/                     this repository's own projects, ADRs and topic cards (it dogfoods the system)
README.md                 what it is, install, the two paths (seed, audit), the case study
LICENSE                   MIT
```

## Decided with the owner

- Audience: one developer, usually a large existing repo.
- Two entry points, seed and audit; audit writes the adoption project and stops.
- graphify is used when present, never required.
- Checkpoint files per task, in git, with a reminder hook.
- superpowers and ponytail recommended for every collaborator.
- Plugin + own marketplace; MIT; English.

## Calls made by the designer (owner may override)

- Plugin name `project-base` (the repo name stays); commands namespaced `/project-base:*`.
- superpowers' subagent-driven execution is told, in the seeded CLAUDE.md, to dispatch the project agents instead
  of `general-purpose`.
- Hook scripts in Python 3 standard library, so no install step.
- The case study in the README uses percentages and sizes only, no product facts.

## Settled after the builder check

- **Project config file.** The seed (or an audit task) writes `.claude/project-base.json`, committed:
  `test_command`, `test_command_patterns`, `docs_root`. The trim hook and the agents read it; no `userConfig`, since
  the value belongs to the project, not the user. With no file, the hook uses default patterns for common runners.
- **Filling templates.** Claude writes each file from `templates/`, which use `{{placeholder}}` markers; a script
  (`scripts/check_seeded.py`, stdlib) then fails if any marker is left or a required file is missing. No substitution
  engine.
- **Existing files.** Seed never overwrites. If `CLAUDE.md`, `.claude/agents/` or `docs/projects/` already exist it
  stops and points to audit. `.claude/settings.json` is merged by adding keys only, after showing the diff.
- **Open task detection.** The reminder lists every task file with `Status: in-progress` under `docs/projects/*/tasks/`.
  A stale one keeps showing up until someone closes it, which is the intended nudge.
- **Checkpoint command.** One in-progress task: update it. Several: ask which. None: create one for the `plan.md`
  task the user names, numbered next in that project.
- **Measure.** The pasted `/usage` and `/context` are stored verbatim in the log, plus the few numbers Claude reads off
  them (weekly %, top attribution rows, context categories); the comparison is Claude's, written as a short table.
- `model: sonnet` is a valid agent frontmatter value (sub-agents reference).

## Settled during the build

- **Companions.** superpowers and ponytail are project-settings recommendations (`extraKnownMarketplaces` +
  `enabledPlugins`: `superpowers@claude-plugins-official`, `ponytail@ponytail`), not `dependencies`.
- **Trim hook.** Default patterns cover `pytest`, `python -m pytest`, `npm|pnpm|yarn test`, `go test`, `cargo test`,
  `mvn test`, `gradle test`, `./gradlew test`. Compound commands are never rewritten. `updatedInput` copies the whole
  tool input and sets no `permissionDecision`, so the user's permissions still apply. Seed writes
  `test_command_patterns` from the test command, which replaces the defaults.
- **Reminder output.** PreCompact prints to stdout, which goes into the compaction summary. SessionEnd prints to stderr
  with exit 2, which only the user sees: Claude can no longer act at that point.
- **Settings merge.** `scripts/merge_settings.py` (stdlib, tested) prints the diff, then adds missing keys only with
  `--apply`.
- **Seed checker scope.** `check_seeded.py` looks for markers only in the files seed writes and under `docs/projects/`,
  so it never flags or edits a user's own `{{ }}` (CI files, for example).
- **Audit.** It reads an existing graphify graph and never builds one. Plan tasks name plugin files as `<plugin>/...`
  and never use a machine path.
- **Neutrality.** `scripts/check_neutral.py` reads the terms from a git-ignored `.neutral-denylist`. A list kept in the
  committed script would publish the names it guards.
- **Validation.** `claude plugin validate . --strict` passes. `tests/smoke_seed.sh` and `tests/smoke_audit.sh` run the
  real CLI in temporary repositories with `--permission-mode auto`. `acceptEdits` cannot write under `.claude/` in
  `-p`, and the smoke tests never use bypass.
