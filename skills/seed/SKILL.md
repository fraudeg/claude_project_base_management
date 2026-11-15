---
name: seed
description: Seed an empty or new repository with project-base (CLAUDE.md, agents, rules, settings, docs map, bootstrap project). Never overwrites; stops if CLAUDE.md, .claude/agents/ or docs/projects/ exists.
disable-model-invocation: true
argument-hint: name=... purpose=... language=... test_command=...
---

# Seed a repository

Arguments: `$ARGUMENTS` (`name=… purpose=… language=… test_command=…`, values may be quoted).

Work in the current directory (the repository root). Templates are in `${CLAUDE_PLUGIN_ROOT}/templates/`, agents in `${CLAUDE_PLUGIN_ROOT}/agents/`. Never overwrite a file, never commit, never stage.

## 1. Check first (writes nothing)

```bash
python3 - <<'EOF'
import os
hard = [p for p in ("CLAUDE.md", ".claude/agents", "docs/projects") if os.path.exists(p)]
kept = [p for p in (".claude/project-base.json", "docs/README.md", "docs/adr/README.md", "docs/topics/README.md") if os.path.exists(p)]
print("REFUSE:", hard)
print("KEEP:", kept)
EOF
```

- If `REFUSE` lists anything: stop. Write nothing. Tell the user this repository already has a setup and to run `/project-base:audit` instead.
- Files in `KEEP` stay as they are: skip writing them and say so at the end.

## 2. Inputs

Take `project_name`, `one_line_purpose`, `language`, `test_command` from the arguments (`name`, `purpose`, `language`, `test_command`). For one that is missing, infer it when the repo shows it (name: the directory name; language and test command: the manifest, e.g. `pyproject.toml` means python and `pytest`, `package.json` its `scripts.test`) and say what you inferred. Ask only for what is still unknown. If you cannot ask (non-interactive run), stop and name the missing argument. Never invent a test command.

Get today's date with `date +%Y-%m-%d`; it is `date` below.

## 3. Copy the files that need no filling

```bash
mkdir -p .claude/agents .claude/rules docs/adr docs/topics
cp "${CLAUDE_PLUGIN_ROOT}/agents/"*.md .claude/agents/
cp -n "${CLAUDE_PLUGIN_ROOT}/templates/rules/example.md" "${CLAUDE_PLUGIN_ROOT}/templates/rules/README.md" .claude/rules/
cp -n "${CLAUDE_PLUGIN_ROOT}/templates/adr-README.md" docs/adr/README.md
cp -n "${CLAUDE_PLUGIN_ROOT}/templates/topics-README.md" docs/topics/README.md
```

## 4. `.claude/settings.json`

Merge by adding keys only; an existing value is never changed. Run the script once: it prints the diff (and the keys it kept) and writes nothing. Show the diff to the user, then run it again with `--apply`. If it exits 1 (the file is not a JSON object), stop and report; do not rewrite the file. An absent file is simply created.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/merge_settings.py" "${CLAUDE_PLUGIN_ROOT}/templates/settings.fragment.json" .claude/settings.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/merge_settings.py" "${CLAUDE_PLUGIN_ROOT}/templates/settings.fragment.json" .claude/settings.json --apply
```

## 5. `.claude/project-base.json`

Skip it if `.claude/project-base.json` is in `KEEP`. Otherwise generate it with Python so the regex and the JSON escaping are right; never write the regex by hand. The file is opened with mode `"x"`, so it can never overwrite. Pass the test command as one quoted argument:

```bash
python3 -c 'import json, re, sys; c = sys.argv[1]; json.dump({"test_command": c, "test_command_patterns": ["^" + re.escape(c) + r"(\s|$)"], "docs_root": "docs"}, open(".claude/project-base.json", "x"), indent=2)' 'THE TEST COMMAND'
```

Same shape as `${CLAUDE_PLUGIN_ROOT}/templates/project-base.json`; do not fill that template by hand.

## 6. Fill the templates

Read each template, then write the target with the text reproduced exactly, changing only what is listed. A target that is in `KEEP` is skipped, never rewritten. Replace every `{{marker}}`: `{{project_name}}`, `{{one_line_purpose}}`, `{{language}}`, `{{test_command}}` (the plain command, as given), `{{date}}`, `{{project_title}}`.

| Target | Template | Also change | If it exists (`KEEP`) |
|---|---|---|---|
| `CLAUDE.md` | `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md` | the two placeholders below | cannot exist, step 1 refused |
| `docs/README.md` | `${CLAUDE_PLUGIN_ROOT}/templates/docs-README.md` | nothing | skip |
| `docs/projects/README.md` | `${CLAUDE_PLUGIN_ROOT}/templates/projects-README.md` | the Index line below | cannot exist, step 1 refused |

`CLAUDE.md` has two placeholders that are not markers. Fill them from what you can see (`ls` of the top level); otherwise leave an explicit TODO, never a made-up path:

- Package map: replace the line ``- `path/`: what lives here`` with one line per top-level directory you can see (skip hidden ones, `docs`, `node_modules`, build output), saying what it holds. If you cannot tell what one holds, write ``- `dir/`: TODO describe``. If there are no directories yet, write `- TODO: list the top-level directories once the project has some.`
- What counts as policy: after the line "What counts as policy in this project:", add `- TODO: name the areas where a wrong change cannot be undone or breaks a promise to users.` (add real areas only if the repo makes them obvious).

`docs/projects/README.md`: replace the whole line starting `None yet.` with:

```markdown
One line per project: `- [YYYY-MM-DD-slug](./YYYY-MM-DD-slug/): current state`.

- [<date>-bootstrap](./<date>-bootstrap/): in progress: seeded, baseline pending
```

## 7. Bootstrap project

Create `docs/projects/<date>-bootstrap/` from `${CLAUDE_PLUGIN_ROOT}/templates/project/`:

- `README.md`: `{{project_title}}` is `Bootstrap project-base`; status line `Status (<date>): in progress: seeded, baseline pending`. Goal: seed this repository with project-base and take a baseline so the effect can be measured. Done when: a `/usage` and `/context` baseline is in `log.md` and a second measurement a week later has been compared with it. Keep the Files list.
- `decisions.md`: copy unchanged (`cp`).
- `log.md`: keep the template, then under `## <date>` add what was seeded (list the files written and any kept) and the test command.
- `plan.md`: replace the placeholder task with these, and write the Handoff as "Seeded on <date>. Next: task 1." and Deferred as "None yet.":
  1. Paste `/usage` and `/context` into `log.md` as the baseline (Claude cannot run them).
  2. After a week of normal work, paste both again and run `/project-base:measure`.
  3. Replace the TODO lines in `CLAUDE.md` (only if any were left).

## 8. Check and finish

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_seeded.py" .
```

It lists a missing required file or a `{{marker}}` left behind. Fix the files this seed wrote, then run it again, until nothing is listed or every remaining line is about a file in `KEEP`. Do not edit a `KEEP` file: report its lines to the user instead (they are the user's file). Then run `git status --short` and tell the user: the files written, the files kept (and any check lines about them), the TODO lines still to fill, that nothing is committed, and to review and commit.
