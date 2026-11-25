#!/usr/bin/env python3
"""SessionStart/SessionEnd hook: keep one board file per session. Usage: session_board.py start|end.
Fails open: any error -> exit 0, no output."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from parallel_config import board_dir, load_parallel

STALE_HOURS = 24
PRUNE_DAYS = 7


def _git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _target(inp):
    """(board dir, session id, cwd) or None when the hook must do nothing."""
    sid, cwd = inp.get("session_id"), inp.get("cwd")
    if not (isinstance(sid, str) and sid and isinstance(cwd, str) and cwd):
        return None
    if "/" in sid or "\\" in sid or ".." in sid or "\0" in sid:
        return None
    bd = board_dir(cwd)
    return (bd, sid, cwd) if bd else None


def _age(secs):
    h = secs / 3600
    return f"{int(h // 24)}d" if h >= 24 else f"{int(h)}h"


def start(inp) -> str:
    t = _target(inp)
    if not t or load_parallel(t[2]) is None:
        return ""
    bd, sid, cwd = t
    own = bd / f"{sid}.json"
    bd.mkdir(parents=True, exist_ok=True)
    try:
        old = json.loads(own.read_text())
        cl, nm, st = old.get("claims"), old.get("name"), old.get("started")
        board = {"name": nm if isinstance(nm, str) else None,
                 "claims": cl if isinstance(cl, list) and all(isinstance(c, str) for c in cl) else [],
                 "started": st if isinstance(st, str) else None}
        if board["started"] is None:
            raise ValueError
    except (OSError, ValueError, AttributeError):
        board = {"name": None, "claims": [],
                 "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    title = inp.get("session_title")
    if board["name"] is None and isinstance(title, str) and title:
        board["name"] = title
    board = {"cwd": cwd, "branch": _git(cwd, "rev-parse", "--abbrev-ref", "HEAD"), **board}
    fd, tmp = tempfile.mkstemp(dir=bd, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(board, f)
        os.replace(tmp, own)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

    # ponytail: age/prune use mtime; a live session idle >PRUNE_DAYS without start/claim is pruned. Upgrade: heartbeat.
    now, lines = time.time(), []
    for f in sorted(bd.glob("*.json")):
        if f == own:
            continue
        try:
            secs = now - f.stat().st_mtime
            if secs > PRUNE_DAYS * 86400:
                f.unlink()
                continue
            b = json.loads(f.read_text())
            claims = [c for c in b.get("claims", []) if isinstance(c, str)]
            lines.append(f"- {b.get('name') or f.stem} | branch {b.get('branch')} | {b.get('cwd')} | "
                         f"claims: {', '.join(claims) or 'none'} | {_age(secs)}"
                         + (" stale" if secs > STALE_HOURS * 3600 else ""))
        except (OSError, ValueError, AttributeError, TypeError):
            continue
    out = [f"Session board file: {own}", "Record claims there via /project-base:claim; claims last until this session ends, is cleared (/clear) or resumed; claim again after those.",
           "Other sessions:" if lines else "No other sessions.", *lines]
    wl = _git(cwd, "worktree", "list")
    if wl:
        out += ["Worktrees:", wl]
    return "\n".join(out)


def end(inp) -> None:
    # ponytail: claims do not survive an exit; re-claim after --resume (a dead session must not hold claims).
    t = _target(inp)
    if t:
        (t[0] / f"{t[1]}.json").unlink(missing_ok=True)
        return
    # ponytail: a custom worktrees_dir may already be gone at SessionEnd, so cwd finds no repo. The env var
    # is the main root and is used only to locate the board for unlinking this session's own file.
    sid, pd = inp.get("session_id"), os.environ.get("CLAUDE_PROJECT_DIR")
    if pd and isinstance(sid, str) and sid and not any(c in sid for c in ("/", "\\", "..", "\0")):
        bd = board_dir(pd)
        if bd:
            (bd / f"{sid}.json").unlink(missing_ok=True)


def main() -> int:
    try:
        fn = {"start": start, "end": end}.get(sys.argv[1] if len(sys.argv) > 1 else "")
        if fn:
            inp = json.load(sys.stdin)
            out = fn(inp) if isinstance(inp, dict) else ""
            if out:
                print(out)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
