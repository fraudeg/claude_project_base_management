#!/usr/bin/env python3
"""Release check: no product, client or vendor name of the source repository may appear in this repository.

Walks every text file under ROOT and reports each line that contains a denied term (case-insensitive
substring), as `path:line: ...`. The terms are DENYLIST plus those in the git-ignored file `.neutral-denylist` at
ROOT (one per line; blank lines and lines starting with `#` are ignored). Skipped: the directories .git,
.superpowers and __pycache__, the root LICENSE, the root `.neutral-denylist`, this script, binary files, and the
author/owner values in the two plugin manifests (the publisher's name is not a denied term).

Usage: check_neutral.py [ROOT]   (default: current directory)
Prints each problem and exits 1 if there is any; exits 2 if ROOT is not a directory or the denylist file cannot
be read. No terms at all: warns on stderr and exits 0.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ponytail: generic terms only. The source repo's product, client and vendor names go in the git-ignored
# `.neutral-denylist`, never here: a committed name would publish the very thing this check guards.
DENYLIST: list[str] = []
DENYLIST_FILE = ".neutral-denylist"

SKIP_DIRS = {".git", ".superpowers", "__pycache__"}
SELF = Path(__file__).resolve()
MANIFESTS = {".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"}

# `"author": {...}` / `"owner": "..."` in a manifest: the value is blanked, newlines kept so line numbers hold.
PUBLISHER = re.compile(r'("(?:author|owner)"\s*:\s*)(\{[^{}]*\}|"[^"]*")')


def read_denylist_file(root: Path) -> list[str]:
    """Terms from ROOT/.neutral-denylist; none if the file is absent. Raises on an unreadable file."""
    path = Path(root) / DENYLIST_FILE
    if not path.is_file():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def blank_publisher(text: str) -> str:
    return PUBLISHER.sub(lambda m: m.group(1) + re.sub(r"[^\n]", " ", m.group(2)), text)


def problems(root: Path, denylist: list[str]) -> list[str]:
    root = Path(root)
    terms = [t for t in denylist if t.strip()]
    found: list[str] = []
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(names):
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if rel in ("LICENSE", DENYLIST_FILE) or path.resolve() == SELF:
                continue
            try:
                data = path.read_bytes()
                text = data.decode("utf-8") if b"\0" not in data else None
            except (OSError, UnicodeDecodeError):  # unreadable, dangling symlink, or binary
                continue
            if text is None:
                continue
            if rel in MANIFESTS:
                text = blank_publisher(text)
            for number, line in enumerate(text.splitlines(), 1):
                lowered = line.lower()
                found += [f"{rel}:{number}: denied term {t!r}" for t in terms if t.lower() in lowered]
    return found


def main(argv: list[str]) -> int:
    root = Path(argv[0] if argv else ".")
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    try:
        terms = DENYLIST + read_denylist_file(root)
    except (OSError, UnicodeDecodeError) as e:  # a denylist that cannot be read must not pass as "clean"
        print(f"error: cannot read {root / DENYLIST_FILE}: {e}", file=sys.stderr)
        return 2
    if not terms:
        print(f"warning: denylist empty — check is not meaningful (put terms in {DENYLIST_FILE}, never committed)",
              file=sys.stderr)
    found = problems(root, terms)
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
