#!/usr/bin/env python3
"""PreToolUse hook: keep edits and index-moving git commands out of the main checkout,
and enforce claims on shared resources. Fails open: any error -> exit 0, no output."""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from parallel_config import _git, board_dir, is_main_checkout, load_parallel

GIT_WRITES = ("commit", "merge", "rebase", "cherry-pick", "reset", "switch",
              "checkout -b", "checkout -B")
MAIN_MSG = ("This is the main checkout. Start a worktree: claude -w <topic> -n <topic>; in a session already open "
            "(an IDE), run git pull --ff-only here, call the EnterWorktree tool with a short name for this task, and "
            "make the change there. Do not make this change through Bash instead.")
STALE_SECS = 24 * 3600

_SEPS = {";", "&", "|", "&&", "||", "(", ")"}
_SKIP = {"then", "do", "else", "env", "command", "sudo", "time", "!"}
_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)(\w+)\1")


def _tokens(command: str):
    lines, end = [], None
    for ln in command.split("\n"):
        if end is not None:
            end = None if ln.strip() == end else end
            continue
        lines.append(ln)
        m = _HEREDOC.search(ln)
        end = m.group(2) if m else None
    lex = shlex.shlex(" ; ".join(lines), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _branch_switch(d: str, sub: list[str]) -> bool:
    """`git checkout <x>` where x is `-`, `--detach` or an existing local branch."""
    if sub[0] != "checkout" or len(sub) < 2:
        return False
    x = next((a for a in sub[1:] if a in ("-", "--", "--detach", "-b", "-B") or not a.startswith("-")), None)
    if x in ("-", "--detach"):
        return True
    if x is None or x.startswith("-"):
        return False
    r = subprocess.run(["git", "-C", d, "show-ref", "--verify", "--quiet", f"refs/heads/{x}"],
                       capture_output=True)
    return r.returncode == 0


def git_write_dirs(command: str, cwd: str) -> list[str]:
    """Directories (tracking `cd`) in which the command runs a GIT_WRITES subcommand."""
    # ponytail: `-C` and `cd` are followed; `--git-dir` / `--work-tree` are still judged by the tracked cwd
    try:
        toks = _tokens(command)
    except ValueError:
        return []  # unbalanced quotes: fail open
    segs = [[]]
    for t in toks:
        if t in _SEPS:
            segs.append([])
        else:
            segs[-1].append(t)
    out, here = [], cwd
    for w in segs:
        while w and (w[0] in _SKIP or re.match(r"\w+=", w[0])):
            w = w[1:]
        if not w:
            continue
        if w[0] == "cd":
            arg = w[1] if len(w) > 1 else None
            here = None if not here or not arg or arg == "-" or arg[0] in "$~" \
                else str((Path(here) / arg).resolve())
        elif w[0] == "git" and here:
            i, at = 1, here
            while i < len(w) and w[i].startswith("-"):
                if w[i] == "-C" and i + 1 < len(w):
                    a = w[i + 1]
                    at = None if not at or a[:1] in "$~" else str((Path(at) / a).resolve())
                i += 2 if w[i] in ("-C", "-c") else 1
            sub = w[i:]
            if at and sub and (sub[0] in GIT_WRITES or " ".join(sub[:2]) in GIT_WRITES
                               or _branch_switch(at, sub)):
                out.append(at)
    return out


def covers(entry: str, rel: str) -> bool:
    return rel == entry or rel.startswith(entry if entry.endswith("/") else entry + "/")


def target_path(inp: dict, cwd: str):
    ti = inp.get("tool_input")
    if not isinstance(ti, dict):
        return None
    keys = ("notebook_path", "file_path") if inp.get("tool_name") == "NotebookEdit" else ("file_path",)
    for k in keys:
        v = ti.get(k)
        if isinstance(v, str) and v:
            p = Path(v)
            return (p if p.is_absolute() else Path(cwd) / p).resolve()
    return None


def shared_check(cfg, target: Path, sid: str):
    """(deny reason | None, context | None) for a target covered by a `shared` entry."""
    top = _git(target.parent, "--show-toplevel")
    if not top:
        return None, None
    try:
        rel = target.relative_to(Path(top).resolve()).as_posix()
    except ValueError:
        return None, None
    if not any(covers(s, rel) for s in cfg["shared"]):
        return None, None
    bd = board_dir(target.parent)
    files = sorted(bd.glob("*.json")) if bd and bd.is_dir() else []
    own = bd / f"{sid}.json" if files else None
    for f in ([own] if own in files else []) + [f for f in files if f != own]:
        try:
            b = json.loads(f.read_text())
            if not any(covers(c, rel) for c in b["claims"] if isinstance(c, str)):
                continue
            if f == own:
                return None, None
            who = b.get("name") or f.stem
            msg = f"{rel} is claimed by {who} (branch {b.get('branch')}). Message it with SendMessage."
            if time.time() - f.stat().st_mtime > STALE_SECS:
                msg += f" That claim looks stale (board file older than 24h); delete {f} if it is dead."
            return msg, None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return None, f"{rel} is a shared resource and nobody claims it. Run /project-base:claim {rel} first."


def decide(inp: dict):
    cwd = inp["cwd"]
    tool = inp.get("tool_name")
    denies, ctxs = [], []
    if tool == "Bash":
        cmd = (inp.get("tool_input") or {}).get("command")
        if not isinstance(cmd, str) or "git" not in cmd:
            return None
        for d in dict.fromkeys(git_write_dirs(cmd, cwd)):
            cfg = load_parallel(d)  # each target is judged by its own repository's config
            if cfg and cfg["main_checkout"] != "off" and is_main_checkout(d):
                if cfg["main_checkout"] == "block":
                    denies.append(MAIN_MSG)
                    break  # deny wins; a warn keeps scanning for a later block target
                ctxs.append(MAIN_MSG)
    else:
        t = target_path(inp, cwd)
        cfg = load_parallel(t) if t else None
        if not cfg:
            return None
        if cfg["main_checkout"] != "off" and is_main_checkout(t.parent):
            (denies if cfg["main_checkout"] == "block" else ctxs).append(MAIN_MSG)
        sid = inp.get("session_id")
        if isinstance(sid, str) and sid:
            d, c = shared_check(cfg, t, sid)
            denies += [d] if d else []
            ctxs += [c] if c else []
    if denies:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": " ".join(denies)}}
    if ctxs:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "additionalContext": " ".join(ctxs)}}
    return None


def main() -> int:
    try:
        out = decide(json.load(sys.stdin))
        if out:
            print(json.dumps(out))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
