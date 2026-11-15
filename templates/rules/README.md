---
paths:
  - ".claude/rules/**"
---

# Rules

A rule is a short instruction scoped to the files it applies to, in `.claude/rules/<name>.md`. The `paths:` list in its
frontmatter decides when it loads: only when Claude touches a matching file, so it costs nothing elsewhere. See
`example.md`.

Add a rule when the same correction has been made twice and it applies to a clear set of paths. One line per rule.

- A rule that applies to every file belongs in `CLAUDE.md`, but only if it is short.
- The reason behind a choice belongs in an ADR (`docs/adr/`); the rule just states what to do.
- Do not repeat a rule in `CLAUDE.md`.
- A rule without `paths:` loads in every session. Give it `paths:` unless that is what you want.
