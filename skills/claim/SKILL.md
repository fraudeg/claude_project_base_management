---
name: claim
description: Use before editing a path listed in parallel.shared, or when the parallel-sessions guard asks for it. Claims the path on the session board so other sessions see it; `release` drops the claim.
argument-hint: "<path> [release]"
---

# Claim a shared path

Arguments: `$ARGUMENTS` (a path, then optionally `release`).

Claims live in this session's board file. That file is inside `.git/` of the main checkout, where the guard denies Edit and Write. Change it only with the `python3` command below, through Bash.

## 1. Find your board file and the path

- Own file: the path in "Session board file: ..." printed at session start. If it is not in context, the board dir is `$(git rev-parse --path-format=absolute --git-common-dir)/project-base-board`, but you cannot tell which file is yours from the directory alone. If you cannot identify your own file, stop and tell the user to restart the session. Never use another session's file.
- Path: make it relative to the root of this checkout (`git rev-parse --show-toplevel`), with no leading `./`. Keep a trailing `/` for a directory or prefix.

## 2. The command

If the path or the name contains `'`, a newline or a backslash, stop and tell the user; do not run the command (the values go inside single quotes in a shell command).

Replace the quoted `BOARD` and `P` values and set `MODE` to `check`, `claim`, `release` or `name`. Run each mode as its own Bash call, exactly in this form. Never loop, chain (`&&`, `;`) or combine modes. If Claude Code refuses a call as too complex, run it again as one plain call.

```bash
MODE=check BOARD='<own board file>' P='<path>' python3 - <<'PY'
import json, os, sys, time, glob
own, p, mode = os.environ["BOARD"], os.environ["P"], os.environ["MODE"]
cov = lambda c, t: c == t or t.startswith(c.rstrip("/") + "/") or (c.endswith("/") and t.startswith(c))
def holders():
    for f in glob.glob(os.path.join(os.path.dirname(own), "*.json")):
        if f == own: continue
        try:
            b = json.load(open(f))
            hit = [c for c in b["claims"] if isinstance(c, str) and (cov(c, p) or cov(p, c))]
        except Exception: continue
        if hit: yield f, b, hit
n = 0
for f, b, hit in holders():
    n += 1
    print(b.get("name") or os.path.basename(f)[:-5], b.get("branch"), b.get("cwd"), "age %dm" % ((time.time() - os.path.getmtime(f)) / 60), hit, "file", f)
if mode == "check": sys.exit(0)
if mode == "claim" and n: sys.exit("refused: overlaps a claim above")
b = json.load(open(own))
if mode == "claim":
    if p not in b["claims"]: b["claims"].append(p)
elif mode == "release":
    k = [c for c in b["claims"] if c != p]
    if len(k) == len(b["claims"]): print("nothing released: no claim equals", repr(p))
    b["claims"] = k
elif mode == "name":
    b["name"] = p
tmp = own + ".tmp"
json.dump(b, open(tmp, "w"))
os.replace(tmp, own)
PY
```

## 3. Check for a conflict

Run `MODE=check`. It reads every other `*.json` in the board dir (malformed files are skipped) and prints each session whose claims overlap yours: the same path, or one is a prefix of the other on a `/` boundary. No output: no conflict, go to step 4.

On a conflict: stop. Tell the user the holder (name, or session id), its branch, cwd, the overlapping claims and the age. Message the holder with `SendMessage` using its board `name`; if `name` is null, ask the user who it is (`ListAgents` can help). Do not claim and do not edit until it releases or the user decides.

If the holder is older than 24h it is probably dead. Tell the user which board file (printed after `file`) to delete. Never delete it yourself.

## 4. Claim

Run `MODE=claim`. It checks again and refuses (exit 1) if another session overlaps, so a claim made in the meantime wins. Then edit.

`name` is set at session start from `claude -n <name>`. Only if it is still null, run `MODE=name` with `P='<your name from ListAgents, the row for this session>'`.

## Release

`/project-base:claim <path> release`: run `MODE=release` with the exact string you claimed. If it prints "nothing released", the string did not match; check the claims in your board file and retry. Claims also vanish when the session ends, is cleared (`/clear`) or resumed (`--resume` or in-process `/resume`): claim again after those.
