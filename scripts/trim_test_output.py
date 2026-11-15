#!/usr/bin/env python3
"""PreToolUse hook (matcher Bash): keep only the tail of a test command's output.

Reads the hook JSON on stdin. Prints a `updatedInput` rewrite when the command is a
plain test command, otherwise `{}`. Never raises: on any problem the command is left alone.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TAIL_LINES = 100

DEFAULT_PATTERNS = [
    r"^(python3?\s+-m\s+)?pytest(\s|$)",
    r"^(npm|pnpm|yarn)\s+test(\s|$)",
    r"^go\s+test(\s|$)",
    r"^cargo\s+test(\s|$)",
    r"^mvn\s+test(\s|$)",
    r"^(\./)?gradlew?\s+test(\s|$)",
]

# Anything that makes the command more than one simple invocation: pipes, lists, redirects,
# background, substitution, newlines. Those are left untouched (a rewrite could change meaning).
COMPOUND = re.compile(r"[|;&<>`\n\r]|\$\(")


def load_config(project_dir: Path) -> dict:
    try:
        cfg = json.loads((Path(project_dir) / ".claude" / "project-base.json").read_text())
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def project_dir_from(data: dict) -> Path:
    """CLAUDE_PROJECT_DIR, else the hook input's `cwd` (if a string), else the process cwd."""
    cwd = data.get("cwd")
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or (cwd if isinstance(cwd, str) else "") or os.getcwd())


def load_patterns(project_dir: Path) -> list[str]:
    patterns = load_config(project_dir).get("test_command_patterns")
    if isinstance(patterns, list) and all(isinstance(p, str) for p in patterns):
        return patterns
    return DEFAULT_PATTERNS


def rewrite(command: str, patterns: list[str]) -> str | None:
    """Return the trimmed command, or None to leave it untouched."""
    command = command.strip()
    if not command or COMPOUND.search(command):
        return None
    for pattern in patterns:
        try:
            matched = re.search(pattern, command)
        except re.error:
            continue  # a bad user pattern must not break the hook
        if matched:
            return f"set -o pipefail; {command} 2>&1 | tail -n {TAIL_LINES}"
    return None


def main() -> None:
    out = {}
    try:
        data = json.load(sys.stdin)
        tool_input = data["tool_input"]
        command = tool_input["command"]
        if isinstance(command, str):
            new = rewrite(command, load_patterns(project_dir_from(data)))
            if new:
                # updatedInput replaces the whole input: keep every other field.
                out = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                              "updatedInput": {**tool_input, "command": new}}}
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        out = {}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
