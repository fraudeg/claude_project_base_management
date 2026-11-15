---
name: write-topic-card
description: Use when the same question about an area has been asked twice, or an area cannot be understood from one file. Writes a topic card in docs/topics/ that answers the questions and links the rules and ADRs.
---

# Write a topic card

Template: `${CLAUDE_PLUGIN_ROOT}/templates/topic-card.md`.

## The bar

A card answers the questions people and agents keep asking about one area, so nobody re-reads many files to learn the same thing. One card per area. If nobody has asked twice, do not write it yet.

## Steps

1. Read the area first. Check `docs/topics/` for a card to extend instead.
2. Write `docs/topics/<slug>.md` from the template:
   - **Questions this answers**: the real questions, each with a short answer and `path/to/file:line`.
   - **Key files**: path and what it holds.
   - **Rules and decisions**: link `.claude/rules/<name>.md` and `docs/adr/NNN-slug.md`. Link them, never repeat them.
   - **Gotchas**: what surprised someone once.
3. Open every path you cite and confirm it exists and says what the card claims.
4. Add `- [slug](slug.md): the area it covers` to the Index in `docs/topics/README.md`.

A card is not a tutorial or a copy of the code. When it grows past one area, split it.
