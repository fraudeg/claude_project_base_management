#!/usr/bin/env python3
"""WorktreeCreate / WorktreeRemove hook for a custom worktrees_dir. Self-contained, stdlib only.

Usage: worktree_hook.py create|remove  (hook JSON on stdin). Non-zero exit = the operation fails.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_DIR = ".claude/worktrees"


def err(msg):
    print(msg, file=sys.stderr)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.stderr:
        err(r.stderr.rstrip())
    if check and r.returncode:
        raise SystemExit(1)
    return r


def main_root(cwd):
    out = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    return Path(out).parent  # ponytail: non-bare repos only


def worktrees_dir(root):
    try:
        v = json.loads((root / ".claude" / "project-base.json").read_text())["parallel"]["worktrees_dir"]
    except (OSError, ValueError, KeyError, TypeError):
        v = None
    d = (root / v).resolve() if isinstance(v, str) and v else None
    # root or an ancestor of it is invalid: fall back to the default
    return d if d and not root.resolve().is_relative_to(d) else (root / DEFAULT_DIR).resolve()


def git_z(root, *args):
    out = git(root, "ls-files", "-z", "--others", "--ignored", *args).stdout
    return {p for p in out.split("\0") if p}


def copy_includes(root, wt_dir, target):
    inc = root / ".worktreeinclude"
    if not inc.is_file():
        return
    for rel in sorted(git_z(root, "--exclude-from=.worktreeinclude") & git_z(root, "--exclude-standard")):
        src, dst = root / rel, target / rel
        if (root / rel).parent.resolve().is_relative_to(wt_dir):
            continue
        if (src.is_symlink() or src.is_file()) and not (dst.exists() or dst.is_symlink()):
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst, follow_symlinks=False)  # symlinks stay symlinks
            except OSError as e:
                err(f"worktree_hook: could not copy {rel}: {e}")


def create(data):
    name = data.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", name) or name in (".", ".."):
        err(f"worktree_hook: invalid worktree name: {name!r}")
        return 1
    root = main_root(data["cwd"])
    wt_dir = worktrees_dir(root)
    target = (wt_dir / name).resolve()
    git(root, "worktree", "prune", check=False)
    registered = {Path(l[9:]).resolve() for l in
                  git(root, "worktree", "list", "--porcelain").stdout.splitlines() if l.startswith("worktree ")}
    if not (target in registered and target.is_dir()):
        branch = f"worktree-{name}"
        if git(root, "rev-parse", "--verify", "-q", f"refs/heads/{branch}", check=False).returncode == 0:
            git(root, "worktree", "add", str(target), branch)  # resume kept branch
        else:
            base = git(root, "rev-parse", "HEAD").stdout.strip()
            git(root, "worktree", "add", "-b", branch, str(target), base)
        copy_includes(root, wt_dir, target)
    print(target)
    return 0


def remove(data):
    path = data["worktree_path"]
    root = main_root(path)
    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    git(root, "worktree", "remove", path)  # no --force: a dirty worktree stays on disk
    if branch.startswith("worktree-") and git(root, "branch", "-d", branch, check=False).returncode:
        err(f"worktree_hook: kept unmerged branch {branch}")
    return 0


if __name__ == "__main__":
    try:
        mode = sys.argv[1]
        data = json.load(sys.stdin)
        sys.exit({"create": create, "remove": remove}[mode](data))
    except SystemExit:
        raise
    except Exception as e:  # any failure fails the operation, which is the correct mode here
        err(f"worktree_hook: {e!r}")
        sys.exit(1)
