# Topic cards

A topic card answers the questions people and agents keep asking about one area, so nobody re-reads twenty files to
learn the same thing. It links the rules and ADRs that apply instead of repeating them. One card per area,
`docs/topics/<slug>.md`.

Write a card when the same question has been asked twice, or when an area cannot be understood from one file. The
`write-topic-card` skill of the `project-base` plugin fills the template below.

```markdown
# Topic: name of the area

What this area is and why it exists, in two or three sentences.

## Questions this answers

- A question people keep asking? The short answer. See `path/to/file:line`.

## Key files

- `path/to/file`: what it holds.

## Rules and decisions

- Rule: `.claude/rules/name.md`
- Decision: `docs/adr/NNN-slug.md`

## Gotchas

- What surprised someone once.
```

## Index

None yet. Add one line per card: `- [slug](slug.md): the area it covers`.
