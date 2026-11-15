---
name: criticality-gate
description: Use when about to edit code, to rate the change 1-10 (instrumentation up to irreversible policy). At 9-10 stop and ask for a decision. What counts as policy is defined in the project's CLAUDE.md.
---

# Criticality gate

Rate the change before you edit.

| Rating | Kind of change | Action |
| --- | --- | --- |
| 1-3 | Instrumentation | Proceed |
| 4-6 | Consistency with an approved pattern | Proceed, follow the pattern |
| 7-8 | Observable and reversible | Proceed, know how you would see it fail and undo it |
| 9-10 | Policy, or irreversible | **Stop for a decision** |

## Steps

1. Read the "Criticality gate" section of the project's `CLAUDE.md`. Its "What counts as policy" list says which areas are 9-10 here. If the list is empty or only a TODO line, judge by the scale alone and say so.
2. Rate the whole change at the highest band any part of it reaches. Between two bands, take the higher.
3. State it in one line: `Criticality: N, reason`.
4. At 9-10 make no edits. Report the decision that is needed: the question, the options, and why it rates 9-10. Stop there. The owner's answer is recorded as a `DEC-nnn` in the project's `decisions.md`, or as an ADR (`project-base:write-adr`) if it outlives the project.
