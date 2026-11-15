# project-base plugin v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `project-base` Claude Code plugin (seed, audit, checkpoint, measure) from this repository, which is also its own marketplace.

**Architecture:** Markdown skills and agents carry the method; Claude fills templates from `templates/`; two stdlib Python hook scripts and one checker script are the only code, each with unit tests. The repo dogfoods the system it ships (`docs/projects/`).

**Tech Stack:** Claude Code plugin format, Markdown, Python 3 standard library (`unittest`), `claude plugin validate`.

**Spec:** `docs/projects/2026-11-15-plugin-v1/design.md`

## Global Constraints

- Plugin name `project-base`; repository `fraudeg/claude_project_base_management`; license MIT, copyright FraudEG.
- Everything in English.
- Scripts: Python 3 standard library only; tests run with `python3 -m unittest discover -s tests`.
- No domain content of any product: no product, client, vendor, data or figure of the source repo; the README case study uses percentages and sizes only.
- Seeded `CLAUDE.md` stays under 200 lines; every skill and agent `description` stays under 250 characters.
- Agents use `model: sonnet`; `explorer` and `test-runner` set `omitClaudeMd: true`.
- Seed never overwrites: it stops if `CLAUDE.md`, `.claude/agents/` or `docs/projects/` exists; `.claude/settings.json` is merged by adding keys only, after showing the diff.
- Project config file `.claude/project-base.json`: `{"test_command": str, "test_command_patterns": [regex str], "docs_root": "docs"}`.
- Task files: `docs/projects/<project>/tasks/NNN-<slug>.md` with a line `Status: in-progress|blocked|done`.
- Stage only (`git add`); the owner commits.

## Review Focus

1. A test command chained with `|`, `;`, `&&` or a redirect must not be rewritten by the trim hook (Task 2).
2. Missing or malformed `.claude/project-base.json` must fall back to default patterns, never crash the hook (Task 2).
3. A task file without a `Status:` line or with an unknown status is ignored by the reminder, not reported as open (Task 2).
4. Seeding a repo that already has `CLAUDE.md` stops before writing anything (Task 6).
5. A leftover `{{placeholder}}` anywhere in seeded files fails `check_seeded.py` (Task 3).

---

### Task 1: Plugin skeleton and marketplace

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `LICENSE`, `README.md` (stub: one paragraph + install line), `.gitignore`
- Create: `docs/projects/2026-11-15-plugin-v1/README.md` (status line `Status (2026-11-15): in progress — plugin skeleton`), `docs/README.md` (map of this repo's docs)

**Interfaces:**
- Produces: plugin root = repo root; marketplace entry `{"name": "project-base", "source": "./"}`.

- [ ] **Step 1:** Write `plugin.json`: `name` `project-base`, `displayName` `Project Base`, `version` `0.1.0`, `description`, `author {name: "FraudEG"}`, `license` `MIT`, `repository` the GitHub URL, `keywords`.
- [ ] **Step 2:** Write `marketplace.json` per the marketplace reference, owner FraudEG, one plugin entry with source `./`.
- [ ] **Step 3:** Verify: `claude plugin validate . --strict` → `Validation passed`.
- [ ] **Step 4:** `git add` the files.

### Task 2: Hook scripts

**Files:**
- Create: `scripts/trim_test_output.py`, `scripts/checkpoint_reminder.py`, `hooks/hooks.json`
- Test: `tests/test_trim_test_output.py`, `tests/test_checkpoint_reminder.py`

**Interfaces:**
- Produces: `trim_test_output.rewrite(command: str, patterns: list[str]) -> str | None` (None = leave untouched); `trim_test_output.load_patterns(project_dir: Path) -> list[str]`; `DEFAULT_PATTERNS` covering `pytest`, `python -m pytest`, `npm test`, `pnpm test`, `yarn test`, `go test`, `cargo test`, `mvn test`, `gradle test`, `./gradlew test`; `TAIL_LINES = 100`.
- Produces: `checkpoint_reminder.open_tasks(project_dir: Path) -> list[Path]`; `main()` prints a reminder listing them, prints nothing when empty.

- [ ] **Step 1: failing tests**
  - `test_rewrites_matching_command`: `rewrite("pytest -q", DEFAULT_PATTERNS) == "set -o pipefail; pytest -q 2>&1 | tail -n 100"`
  - `test_leaves_chained_command`: for each of `"pytest | head"`, `"pytest; ls"`, `"pytest && ls"`, `"pytest > out"` → `None`
  - `test_leaves_other_command`: `rewrite("ls", DEFAULT_PATTERNS) is None`
  - `test_config_patterns_used`: tmp dir with `.claude/project-base.json` `{"test_command_patterns": ["^make check$"]}` → `load_patterns` returns `["^make check$"]`
  - `test_bad_config_falls_back`: invalid JSON → `DEFAULT_PATTERNS`
  - `test_open_tasks_lists_in_progress`: tmp `docs/projects/p/tasks/001-a.md` with `Status: in-progress` and `002-b.md` with `Status: done` → `[001-a.md]`
  - `test_task_without_status_ignored`: file with no `Status:` line → `[]`
- [ ] **Step 2:** Run `python3 -m unittest discover -s tests -v` → FAIL (modules missing).
- [ ] **Step 3:** Implement both modules. `trim_test_output.py` reads the PreToolUse JSON on stdin, prints `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {...command}}}` or `{}`. `docs_root` comes from the config, default `docs`.
- [ ] **Step 4:** `hooks/hooks.json`: PreToolUse matcher `Bash` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/trim_test_output.py"`; PreCompact and SessionEnd → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/checkpoint_reminder.py"`.
- [ ] **Step 5:** Tests PASS; `claude plugin validate . --strict` passes; `git add`.

### Task 3: Templates and the seed checker

**Files:**
- Create: `templates/CLAUDE.md`, `templates/rules/example.md`, `templates/rules/README.md`, `templates/adr.md`, `templates/adr-README.md`, `templates/topic-card.md`, `templates/topics-README.md`, `templates/docs-README.md`, `templates/projects-README.md`, `templates/project/{README,decisions,log,plan}.md`, `templates/task.md`, `templates/settings.fragment.json`, `templates/project-base.json`
- Create: `scripts/check_seeded.py`; Test: `tests/test_check_seeded.py`

**Interfaces:**
- Produces: placeholders `{{project_name}}`, `{{one_line_purpose}}`, `{{language}}`, `{{test_command}}`, `{{date}}`; `REQUIRED_FILES` list (CLAUDE.md, .claude/project-base.json, .claude/settings.json, the four agents, docs/README.md, docs/projects/README.md, docs/adr/README.md, docs/topics/README.md); `check_seeded.problems(root: Path) -> list[str]`; CLI exits 1 when non-empty.

- [ ] **Step 1: failing tests**: `test_complete_tree_passes` (fixture with all `REQUIRED_FILES`, no markers → `[]`); `test_leftover_marker_reported` (`{{date}}` in one file → one problem naming the file); `test_missing_file_reported`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `check_seeded.py`; write the templates. `CLAUDE.md` sections: What this project does, Commands, Tests, Conventions, Package map, Criticality gate (pointer to skill), Working with agents (agents by name, never bare `general-purpose`; superpowers' subagent execution dispatches these), Where documents go. Template ≤ 120 lines. Settings fragment: `env.CLAUDE_CODE_SUBAGENT_MODEL = "sonnet"`, `extraKnownMarketplaces` for superpowers and ponytail, `enabledPlugins` for both plus `project-base`.
- [ ] **Step 4:** Tests PASS; `wc -l templates/CLAUDE.md` ≤ 120; `git add`.

### Task 4: Agents

**Files:** Create `agents/explorer.md`, `agents/implementer.md`, `agents/test-runner.md`, `agents/reviewer.md`

**Interfaces:** Consumes `.claude/project-base.json` (`test_command`, `docs_root`). Seed copies these files verbatim into `.claude/agents/`.

- [ ] **Step 1:** Port the four agents from the design with no product terms: explorer (read-only, topic cards first, `path:line` answers); implementer (one task, criticality-gate skill, test first, `git add` only, report files/test/undone); test-runner (runs `test_command` from the config or the one given, failures only); reviewer (reads matching `.claude/rules/*.md` and topic cards itself, findings with failure scenarios).
- [ ] **Step 2:** Verify frontmatter: `model: sonnet`, `effort`, `omitClaudeMd` on explorer and test-runner, descriptions < 250 chars; `claude plugin validate . --strict` passes; `git add`.

### Task 5: Knowledge skills

**Files:** Create `skills/{project-workflow,write-adr,write-topic-card,write-rule,criticality-gate,harness-ops}/SKILL.md`

- [ ] **Step 1:** Write each from the design's "Skills" section, pointing to `templates/` via `${CLAUDE_PLUGIN_ROOT}`. `project-workflow` includes the task-file rule (a file only when a task outgrows one session) and closing a project. `harness-ops` includes reading `/usage` and the model/effort policy.
- [ ] **Step 2:** Validate passes; descriptions < 250 chars; `git add`.

### Task 6: seed

**Files:** Create `skills/seed/SKILL.md`; Test: `tests/smoke_seed.sh`

- [ ] **Step 1:** Write the skill: refuse when `CLAUDE.md`, `.claude/agents/` or `docs/projects/` exists (point to audit); ask project name, purpose, language, test command; write every `REQUIRED_FILES` entry from templates; merge settings by adding keys after showing the diff; create `docs/projects/<date>-bootstrap/`; run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_seeded.py" .` and fix until clean.
- [ ] **Step 2:** `tests/smoke_seed.sh`: makes a temp git repo, runs `claude --plugin-dir "$REPO" -p "/project-base:seed name=demo purpose='demo app' language=python test_command='pytest -q'"`, then `check_seeded.py` must exit 0; a second temp repo with an existing `CLAUDE.md` must end with `CLAUDE.md` unchanged (checksum).
- [ ] **Step 3:** Run the smoke test → PASS; `git add`.

### Task 7: audit

**Files:** Create `skills/audit/SKILL.md`

- [ ] **Step 1:** Write the skill per the design's four stages: orient (graphify when `graphify-out/` or the CLI exists, else layout/manifests/tests/docs, `explorer` agents for breadth); measure (CLAUDE.md sizes, memory, `.claude/` contents, ask the user to paste `/usage` and `/context`); find (the design's list); write `docs/projects/<date>-adopt-project-base/` from the project templates with one plan task per change, then stop. It writes nothing outside that folder.
- [ ] **Step 2:** Manual check on this repo's sibling or any sample repo with `claude --plugin-dir`: only the adoption folder appears in `git status`. Record the result in this project's log; `git add`.

### Task 8: checkpoint and measure

**Files:** Create `skills/checkpoint/SKILL.md`, `skills/measure/SKILL.md`

- [ ] **Step 1:** checkpoint: one in-progress task → update; several → ask; none → create the next-numbered file for the `plan.md` task the user names, from `templates/task.md`.
- [ ] **Step 2:** measure: store the pasted text verbatim in the project log, extract weekly %, top attribution rows and context categories, append a before/after table against the baseline.
- [ ] **Step 3:** Validate passes; `git add`.

### Task 9: README, neutrality guard, release

**Files:** Modify `README.md`; Create `scripts/check_neutral.py`, `tests/test_check_neutral.py`, `docs/projects/2026-11-15-plugin-v1/log.md`

**Interfaces:** `check_neutral.problems(root: Path, denylist: list[str]) -> list[str]`; the denylist lives in the script and matches case-insensitively, skipping `LICENSE` and the author lines of `plugin.json` and `marketplace.json`.

- [ ] **Step 1: failing tests**: a file containing a denylisted term is reported; `LICENSE` is skipped.
- [ ] **Step 2:** Implement; the owner supplies the denylist terms at review (product, client and vendor names of the source repo).
- [ ] **Step 3:** README: what it is, install (`/plugin marketplace add fraudeg/claude_project_base_management`, `/plugin install project-base@...`), seed vs audit, checkpoints, the case study (61% subagent share, 67 KB → 16 KB instructions), credits to superpowers and ponytail.
- [ ] **Step 4:** All unit tests PASS, `check_neutral.py .` clean, `claude plugin validate . --strict` passes, smoke seed passes; status line → `delivered` once the owner commits and pushes; `git add`.

## Handoff

- 2026-11-15: design and plan approved by the owner.
- 2026-11-15: all nine tasks built subagent-driven (implementer and reviewer on `sonnet`), each reviewed for spec and
  quality, then a whole-plugin review and one fix wave. 81 unit tests pass on Python 3.9 and 3.14; `claude plugin
  validate . --strict` passes; both smoke tests pass (seed 14/14, audit 14/14); the trim hook was checked live. The
  owner verified the denylist terms. Deviations from this plan are recorded in `log.md` and `design.md` ("Settled
  during the build"). Committed and pushed as v0.1.0. Next: install from the marketplace on a real repository, run
  `/project-base:audit`, and record the first measure.
