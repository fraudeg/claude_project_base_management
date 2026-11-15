---
name: write-adr
description: Use when a decision is costly to reverse or someone will later ask why it is like this, to record it as an ADR in docs/adr/. One decision per ADR; never rewrite an accepted one.
---

# Write an ADR

Template: `${CLAUDE_PLUGIN_ROOT}/templates/adr.md`.

## The bar

Write one when the choice is costly to reverse, or when someone is likely to ask "why is it like this?". A choice that only matters inside one project goes in that project's `decisions.md` (DEC-nnn). A standing instruction goes in a rule (`project-base:write-rule`).

## Steps

1. List `docs/adr/` and take the next number NNN.
2. Write `docs/adr/NNN-<slug>.md` from the template. Set Status (`proposed` or `accepted`) and today's date.
3. Fill it in:
   - **Context**: the facts and forces. No solutions.
   - **Decision**: one decision, in a sentence or two. Two decisions means two ADRs.
   - **Consequences**: what gets easier, what gets harder, what must now stay true.
   - **Alternatives considered**: each option and why it lost.
4. Add `- [ADR-NNN: title](NNN-slug.md)` to the Index in `docs/adr/README.md`.

## Changing a decision

Never rewrite an accepted ADR. Write a new one that supersedes it, then set the old status to `superseded by ADR-NNN`. That status line is the only edit an accepted ADR gets.
