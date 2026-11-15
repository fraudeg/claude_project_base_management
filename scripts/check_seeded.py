#!/usr/bin/env python3
"""Check a seeded repository: every required file exists and no `{{marker}}` is left in the files seed wrote.

Only those files are scanned (see seeded_files); the rest of the repository is never read.

Usage: check_seeded.py [ROOT]   (default: current directory)
Prints each problem and exits 1 if there is any.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Markers the templates use; the seed replaces every one of them.
PLACEHOLDERS = (
    "{{project_name}}",
    "{{one_line_purpose}}",
    "{{language}}",
    "{{test_command}}",
    "{{test_command_regex}}",
    "{{date}}",
    "{{project_title}}",
)

REQUIRED_FILES = (
    "CLAUDE.md",
    ".claude/project-base.json",
    ".claude/settings.json",
    ".claude/agents/explorer.md",
    ".claude/agents/implementer.md",
    ".claude/agents/test-runner.md",
    ".claude/agents/reviewer.md",
    "docs/README.md",
    "docs/projects/README.md",
    "docs/adr/README.md",
    "docs/topics/README.md",
)

# Any `{{...}}`, not only the known names: a typo or a new marker must not slip through.
MARKER = re.compile(r"\{\{[^{}]+\}\}")


def seeded_files(root: Path) -> list[Path]:
    """The files seed writes: each existing REQUIRED_FILES entry and everything under docs/projects/
    (seed refuses when that folder exists). The user's other files are never read."""
    files = {root / rel for rel in REQUIRED_FILES if (root / rel).is_file()}
    for dirpath, _, names in os.walk(root / "docs" / "projects"):
        files.update(Path(dirpath) / name for name in names)
    return sorted(files)


def problems(root: Path) -> list[str]:
    root = Path(root)
    found = [f"missing required file: {rel}" for rel in REQUIRED_FILES if not (root / rel).is_file()]
    for path in seeded_files(root):
        try:
            markers = MARKER.findall(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):  # not UTF-8 text (binary), unreadable, or a dangling symlink
            continue
        if markers:
            rel = path.relative_to(root).as_posix()
            found.append(f"{rel}: unfilled marker(s) {', '.join(sorted(set(markers)))}")
    return found


def main(argv: list[str]) -> int:
    found = problems(Path(argv[0] if argv else "."))
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
