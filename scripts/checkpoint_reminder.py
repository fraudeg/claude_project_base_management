#!/usr/bin/env python3
"""PreCompact / SessionEnd hook: remind about task files still `Status: in-progress`.

Prints nothing when no task is open. Output channel depends on the event, because Claude Code
discards `systemMessage` on both and only these two paths surface:
- PreCompact: plain stdout becomes instructions for the compaction summary.
- SessionEnd: only stderr with exit 2 is shown (to the user; Claude cannot act any more).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from trim_test_output import load_config, project_dir_from

IN_PROGRESS = re.compile(r"^Status:[ \t]*in-progress[ \t]*$", re.MULTILINE)


def open_tasks(project_dir: Path) -> list[Path]:
    project_dir = Path(project_dir)
    docs_root = load_config(project_dir).get("docs_root")
    if not isinstance(docs_root, str) or not docs_root:
        docs_root = "docs"
    try:
        tasks = sorted((project_dir / docs_root / "projects").glob("*/tasks/*.md"))
    except (OSError, ValueError):  # nonsense docs_root (e.g. embedded NUL)
        return []
    found = []
    for task in tasks:
        try:
            if IN_PROGRESS.search(task.read_text(errors="replace")):
                found.append(task)
        except OSError:
            continue
    return found


def reminder(project_dir: Path, tasks: list[Path], event: str) -> str:
    lines = "\n".join(f"- {os.path.relpath(t, project_dir)}" for t in tasks)
    if event == "SessionEnd":
        return f"Open task checkpoints (Status: in-progress); update before closing:\n{lines}"
    return ("Open task checkpoints (Status: in-progress). In the summary, name these files and tell the "
            "resumed session to update each (Done so far, Files touched, Next step) before continuing:\n" + lines)


def main() -> int:
    try:
        data = json.load(sys.stdin)
        data = data if isinstance(data, dict) else {}
    except ValueError:
        data = {}
    project_dir = project_dir_from(data)
    tasks = open_tasks(project_dir)
    if not tasks:
        return 0
    event = data.get("hook_event_name")
    text = reminder(project_dir, tasks, event)
    if event == "SessionEnd":
        print(text, file=sys.stderr)
        return 2
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
