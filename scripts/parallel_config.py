"""Shared helpers for the parallel-sessions hooks. Every function returns None/False on any error."""
import json
import subprocess
from pathlib import Path



def _defaults():
    return {"worktrees_dir": ".claude/worktrees", "main_checkout": "block", "shared": []}


def _safe(fallback):
    """Public boundary: any exception (bad input, symlink loop, deep JSON) -> fallback."""
    def deco(fn):
        def wrapper(*a, **k):
            try:
                return fn(*a, **k)
            except Exception:
                return fallback
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    return deco


def _git(start, *args):
    """Run git from the nearest existing directory at or above start; stdout or None."""
    try:
        d = Path(start).resolve()
        while not d.is_dir():
            if d.parent == d:
                return None
            d = d.parent
        r = subprocess.run(["git", "-C", str(d), "rev-parse", *args],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError):
        return None


def _dirs(start):
    """(git dir, common dir) as resolved Paths, or None."""
    g = _git(start, "--absolute-git-dir")
    c = _git(start, "--path-format=absolute", "--git-common-dir")
    return (Path(g).resolve(), Path(c).resolve()) if g and c else None


@_safe(None)
def main_root(start):
    # ponytail: bare repos (common dir not named .git) -> None
    d = _dirs(start)
    return d[1].parent if d and d[1].name == ".git" else None


@_safe(None)
def board_dir(start):
    d = _dirs(start)
    return d[1] / "project-base-board" if d else None


@_safe(None)
def load_parallel(start):
    root = main_root(start)
    if root is None:
        return None
    try:
        par = json.loads((root / ".claude" / "project-base.json").read_text()).get("parallel")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(par, dict):
        return None
    out = _defaults()
    w = par.get("worktrees_dir")
    # a dir that is the root or above it would make the whole checkout "a worktree": keep the default
    if isinstance(w, str) and w and not root.is_relative_to((root / w).resolve()):
        out["worktrees_dir"] = w
    if par.get("main_checkout") in ("block", "warn", "off"):
        out["main_checkout"] = par["main_checkout"]
    s = par.get("shared")
    if isinstance(s, list) and all(isinstance(x, str) for x in s):
        out["shared"] = s
    return out


@_safe(False)
def is_main_checkout(path):
    d = _dirs(path)
    root = main_root(path)
    if not d or d[0] != d[1] or root is None:
        return False
    wt = (load_parallel(path) or _defaults())["worktrees_dir"]
    p = Path(path).resolve()
    try:
        p.relative_to((root / wt).resolve())
        return False
    except ValueError:
        return True
