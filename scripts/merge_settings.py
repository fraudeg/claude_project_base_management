#!/usr/bin/env python3
"""Add the keys of a settings fragment to a settings file without changing any existing value.

Usage: merge_settings.py FRAGMENT TARGET [--apply]

Prints a unified diff of TARGET (an absent TARGET counts as empty), then one line per key kept because TARGET
already has a different value. TARGET is written only with --apply. Exits 1 if either file is not a JSON object.
"""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path


def merge(have: dict, add: dict, where: str = "") -> list[str]:
    """Add to `have` every key of `add` it lacks, recursing into dicts. Returns the dotted keys kept as they were."""
    kept = []
    for key, value in add.items():
        if key not in have:
            have[key] = value
        elif isinstance(have[key], dict) and isinstance(value, dict):
            kept += merge(have[key], value, f"{where}{key}.")
        elif have[key] != value:
            kept.append(f"{where}{key}")
    return kept


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    return data


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    args = [a for a in argv if a != "--apply"]
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    fragment, target = Path(args[0]), Path(args[1])
    try:
        add = load(fragment)
        have = load(target) if target.exists() else {}
        before = target.read_text(encoding="utf-8") if target.exists() else ""
    except (OSError, ValueError) as e:  # JSONDecodeError is a ValueError
        print(f"cannot merge, nothing written: {e}", file=sys.stderr)
        return 1
    kept = merge(have, add)
    after = json.dumps(have, indent=2, ensure_ascii=False) + "\n"
    diff = difflib.unified_diff(before.splitlines(True), after.splitlines(True), str(target), f"{target} (merged)")
    print("".join(diff) or "no change")
    for key in kept:
        print(f"kept your value: {key}")
    if apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(after, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
