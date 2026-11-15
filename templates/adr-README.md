# Architecture decision records

An ADR keeps the reason behind one decision, so it is not rediscovered or reversed by accident. One decision per file,
`docs/adr/NNN-slug.md`, numbered in order. Never rewrite an accepted ADR: add a new one that supersedes it and update
the old one's status.

Write an ADR when a choice is costly to reverse, or when someone is likely to ask "why is it like this?". The
`write-adr` skill of the `project-base` plugin fills the template below.

```markdown
# ADR-NNN: Title of the decision

- Status: proposed | accepted | superseded by ADR-NNN
- Date: YYYY-MM-DD

## Context

The facts and forces that make a decision necessary. No solutions here.

## Decision

The one decision, in a sentence or two. One decision per ADR.

## Consequences

What becomes easier, what becomes harder, what must now stay true.

## Alternatives considered

Each option and the reason it lost.
```

## Index

None yet. Add one line per ADR: `- [ADR-001: title](001-slug.md)`.
