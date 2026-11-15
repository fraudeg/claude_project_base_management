---
name: write-rule
description: Use when the same correction has been made twice and it applies to a clear set of paths. Writes a one-line, path-scoped rule in .claude/rules/ instead of growing CLAUDE.md.
---

# Write a rule

Example: `${CLAUDE_PLUGIN_ROOT}/templates/rules/example.md`.

A rule is a short instruction in `.claude/rules/<name>.md`. Its `paths:` frontmatter decides when it loads: only when Claude touches a matching file, so it costs nothing elsewhere.

## The bar

Write one when the same correction has been made twice and it applies to a clear set of paths. One line per rule.

## Steps

1. Read `.claude/rules/`. If a rule already covers the area, add the line there.
2. Write `.claude/rules/<area>.md`:

   ```markdown
   ---
   paths:
     - "src/area/**"
   ---

   - The instruction, in one line.
   ```

3. Check the globs match the files you mean, and no others.

## Where it does not belong

- A rule that applies to every file goes in `CLAUDE.md`, and only if it is short.
- The reason behind it goes in an ADR (`project-base:write-adr`). The rule only says what to do.
- Never repeat a rule in `CLAUDE.md`.
- A rule without `paths:` loads in every session. Add `paths:` unless that is the intent.
