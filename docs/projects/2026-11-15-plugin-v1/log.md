# Log

Dated entries, oldest first. Record what happened, what was measured and what was learned. Paste raw measurements
verbatim.

## 2026-11-15

- Project created.
- Task 7 (audit skill) manual check, 2026-11-15, on a throwaway sample repo in a temp directory (a committed
  `CLAUDE.md`, `package.json`, a test, an agent without `model:`, a note holding a buried decision). Never on a real repo.
  - Command: `SMOKE_KEEP=1 bash tests/smoke_audit.sh`, which runs
    `claude --plugin-dir <repo> --model sonnet --strict-mcp-config --setting-sources project,local --permission-mode auto --max-budget-usd 3 --no-session-persistence -p "/project-base:audit"`
    in the sample, then a second time in the same sample. Two `claude` runs in total.
  - Result: 13 of 13 checks passed. `git status --porcelain --untracked-files=all` in the sample listed only
    `docs/projects/2026-11-15-adopt-project-base/{README,decisions,log,plan}.md`; tracked files unchanged, nothing
    staged, no `{{marker}}` left, baseline recorded as pending (non-interactive). The plan named `foo.md` (no `model:`),
    the Release procedure (skill), the silent changelog checklist, the buried decision (ADR), and the missing
    `.claude/project-base.json`. The second run said the project already exists and changed nothing.
  - The checks were first run against stub `claude` binaries: a well-behaved stub passed all, one that also edited
    `CLAUDE.md` and wrote `.claude/x` failed the status and tracked-file checks, one that wrote nothing failed eight.
  - Not exercised: `explorer` dispatch (the sample is too small to need it), an existing `graphify-out/`.
- Task 7 fix round 1: the run above wrote the resolved plugin path into `plan.md` (machine- and version-specific). The
  skill now has plan tasks name plugin files as `<plugin>/…` (paths quoted) and the Handoff say how to resolve
  `<plugin>`: the `installPath` of the enabled `project-base@project-base` entry in `claude plugin list --json`
  (checked on 2026-11-15 with another installed plugin, since this plugin is only loaded with `--plugin-dir` here).
  `tests/smoke_audit.sh` gained a check for absolute plugin paths in the folder. It was verified with stub `claude`
  binaries only (relative form passes, `--plugin-dir` path and a cache path both fail); the paid run was not repeated,
  so the real model's output after this change is unchecked.
- Task 9 (README, neutrality guard, release checks), 2026-11-15. The plugin is built and staged; nothing is committed.
  - Built across nine tasks: manifests, the test-output trim and checkpoint-reminder hooks, `check_seeded.py` and
    `merge_settings.py`, templates, four agents, `seed`, `audit`, `checkpoint` and `measure` plus six knowledge skills,
    unit tests and the two smoke scripts.
  - Added `scripts/check_neutral.py` (`problems(root, denylist)`; skips `.git`, `.superpowers`, `__pycache__`, the
    root `LICENSE`, itself, binaries and the author/owner values of the two manifests) and its tests. The module
    `DENYLIST` is empty and stays generic; the owner supplies the source repo's product, client and vendor names at
    review in the git-ignored `.neutral-denylist` (see fix round 1). With no terms the CLI warns on stderr and exits 0,
    so the neutrality check below says nothing yet.
  - README rewritten: install, seed vs audit, checkpoint and measure, what gets installed, the case study (61%, 67 KB
    to 16 KB), credits, known limits.
  - Checks: `python3 -m unittest discover -s tests` OK, 69 tests, on `/usr/bin/python3` (3.9.6) and `python3`
    (3.14.7). `python3 scripts/check_neutral.py .` exit 0 with the empty-denylist warning.
    `claude plugin validate . --strict` passed (exit 0; the informational `ICON_MISSING` plugin-directory warning
    remains). The paid smoke tests were not run by this task; the controller runs them in final verification.
  - Open for the owner: put the names in `.neutral-denylist` (never committed), re-run the check, review, commit and push. The status line becomes
    `delivered` only after the push.
- Task 9 fix round 1, 2026-11-15, after review.
  - README: the checkpoint hook was described as reminding Claude on both events. Now stated as it works: on PreCompact
    the open tasks go into the compaction summary (the resumed session is told to update them); on SessionEnd they are
    shown to the user only, since Claude cannot act any more.
  - Neutrality guard, fail-open on the list: a filled `DENYLIST` in the committed script would publish the names it
    guards and ship them to every user. `DENYLIST` stays `[]` for generic terms; the CLI also reads `.neutral-denylist`
    at ROOT (one term per line, blank lines and `#` comment lines ignored), which is in `.gitignore` and skipped by the
    scan. The owner puts the product, client and vendor names there; they are never committed. An unreadable file exits
    2 instead of passing. README Known limits says so.
  - Neutrality guard, fail-open on the root: a missing or non-directory ROOT returned no problems and exited 0. The CLI
    now prints `error: <root> is not a directory` and exits 2.
  - Both were test-first: 9 of the 29 tests in `tests/test_check_neutral.py` failed before the change. Afterwards,
    `python3 -m unittest discover -s tests` OK, 80 tests, on `/usr/bin/python3` (3.9.6) and `python3` (3.14.7);
    `python3 scripts/check_neutral.py .` exit 0 with the empty warning; a bad root exits 2; a temp tree with a
    `.neutral-denylist` term exits 1 and does not report the list file; `claude plugin validate . --strict` passed.
- Final review fix wave, 2026-11-15: live check of the test-output trim hook (never exercised in a real session before).
  - Setup: a throwaway git repo in a temp directory with `tests/test_noisy.py` (one failing test that prints 200 lines;
    run directly, `python3 -m pytest -q` prints 216 lines and exits 1) and `.claude/project-base.json` with
    `test_command` `python3 -m pytest -q` and the seeded pattern `^python3\ \-m\ pytest\ \-q(\s|$)`. Claude Code 2.1.325.
  - Command, one run per mode (two `claude` runs in total, never `bypassPermissions`):
    `claude --plugin-dir <repo> --model sonnet -p "Run the test command python3 -m pytest -q exactly as given and report the last line of its output and how many lines you saw" --max-budget-usd 1 --strict-mcp-config --setting-sources project,local --no-session-persistence --output-format stream-json --verbose`
    plus (a) `--permission-mode auto`, (b) `--allowedTools "Bash"` with the default mode. `stream-json` was added only to read
    the raw tool result.
  - (a) auto mode: init reported `permissionMode: auto`; no permission denials. The Bash tool result was `Exit code 1`
    followed by 100 lines (`noise line 103` to `noise line 199`, the summary header, the `FAILED` line, `1 failed in 0.01s`).
    The rewrite applied: 100 lines instead of 216, exit code 1 kept. The model reported the last line and "100 lines",
    and noticed the output started at `noise line 103`.
  - (b) default mode with `Bash` allowed: init reported `permissionMode: default`; no permission denials. Same tool result
    (`Exit code 1` plus the same 100 lines). The rewrite applied; exit code kept. Same report from the model.
  - The stream shows the command as the model sent it (`python3 -m pytest -q`), not the rewritten one; the trimmed result is
    the evidence that the hook's `updatedInput` was applied.
  - Not exercised: other permission modes, a command that does not match the patterns (covered by the unit tests), the
    allowlist-mismatch case of the README's Known limits. README Known limits now records the above.
- Final review fix wave, other items: `measure` says how to append the paste verbatim (quoted heredoc or Edit, never an
  unquoted heredoc); the `audit` plan task for `.claude/project-base.json` states its three keys; README graphify wording
  and Known limits (compound commands, seeded patterns replace the defaults, the live check); `docs/README.md` lists all
  four files of this folder; `checkpoint` lists `git diff --cached --stat`; `criticality-gate` treats a TODO-only list as
  empty; new test that every `<plugin>/...` path in `skills/` exists and every hook command points at an existing script.

## 2026-11-15 — release v0.1.0

- The owner verified the neutrality terms manually. `design.md` and `plan.md` were updated: English status lines,
  Handoff, and a "Settled during the build" section that replaces "Left to the builder".
- Added `CONTRIBUTING.md` and issue templates (bug, question; blank issues off). Repository settings: issues on;
  pull requests restricted to collaborators; wiki and projects off; discussions on; a ruleset on `main` that blocks
  deletion, force-push and pushes from anyone without the admin bypass.
- Committed as one commit and pushed to `main`.
