#!/usr/bin/env bash
# Smoke test for /project-base:seed. It calls the real `claude` CLI, so it costs a little.
# Run: bash tests/smoke_seed.sh   (exit 0 = every check passed)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEED="$(mktemp -d)"      # empty repo: seed must fill it
EXISTING="$(mktemp -d)"  # repo with a CLAUDE.md: seed must refuse
PAR="$(mktemp -d)"       # empty repo, parallel=yes: the guard must not block seed's own writes
OUT_SEED="$(mktemp)"; OUT_EXISTING="$(mktemp)"; OUT_PAR="$(mktemp)"  # what claude printed in each run
# SMOKE_KEEP=1 keeps the two repos so you can read what the model wrote.
trap 'if [ -n "${SMOKE_KEEP:-}" ]; then echo "kept: $SEED $EXISTING $PAR"; else rm -rf "$SEED" "$EXISTING" "$PAR"; fi; rm -f "$OUT_SEED" "$OUT_EXISTING" "$OUT_PAR"' EXIT

FAILED=0
check() { # check "name" command args...
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS: $name"; else echo "FAIL: $name"; FAILED=1; fi
}

# run_seed DIR OUTFILE [EXTRA]: runs the skill in DIR (EXTRA is appended to the arguments), saves what claude printed in OUTFILE, sets RC to its exit code.
# `.claude/` is a protected path: acceptEdits (and allow rules) still prompt for it, and `-p` cannot answer, so use
# auto mode (a classifier decides; bypassPermissions is never used). Bash is limited to the listed commands.
run_seed() {
  RC=0
  (cd "$1" && claude --plugin-dir "$REPO" --model sonnet --strict-mcp-config --setting-sources project,local \
    --permission-mode auto --max-budget-usd 3 --no-session-persistence \
    --allowedTools "Bash(python3:*),Bash(mkdir:*),Bash(cp:*),Bash(ls:*),Bash(cat:*),Bash(date:*),Bash(git status:*),Bash(git check-ignore:*),Read(/$REPO/**)" \
    -p "/project-base:seed name=demo purpose='demo app' language=python test_command='pytest -q' ${3:-}" </dev/null) >"$2" 2>&1 || RC=$?
}

# --- 1. empty repo gets seeded ---
git -C "$SEED" init -q
run_seed "$SEED" "$OUT_SEED"

check "claude exited 0 (seed run)" test "$RC" -eq 0
check "seeded repo passes check_seeded.py" python3 "$REPO/scripts/check_seeded.py" "$SEED"
check "project-base.json is valid and its pattern matches the test command" python3 -c '
import json, re, sys
d = json.load(open(sys.argv[1] + "/.claude/project-base.json"))
assert d["test_command"] == "pytest -q" and d["docs_root"] == "docs"
p = d["test_command_patterns"][0]
assert re.search(p, "pytest -q") and re.search(p, "pytest -q tests/x") and not re.search(p, "pytest -qq")
' "$SEED"
check "settings.json has the fragment" python3 -c '
import json, sys
d = json.load(open(sys.argv[1] + "/.claude/settings.json"))
assert d["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "sonnet" and d["enabledPlugins"]["project-base@project-base"] is True
' "$SEED"
check "agents copied verbatim" diff -r "$REPO/agents" "$SEED/.claude/agents"
check "bootstrap project exists" bash -c 'ls -d "$1"/docs/projects/*-bootstrap/README.md' _ "$SEED"
check "CLAUDE.md has no fake package path" bash -c '! grep -q "what lives here" "$1/CLAUDE.md"' _ "$SEED"
check "no parallel key without parallel=yes" bash -c '! grep -q "\"parallel\"" "$1/.claude/project-base.json"' _ "$SEED"
check "no parallel marker in CLAUDE.md without parallel=yes" bash -c '! grep -q "<!-- parallel:" "$1/CLAUDE.md"' _ "$SEED"
check "nothing staged" bash -c '[ -z "$(git -C "$1" diff --cached --name-only)" ]' _ "$SEED"

# --- 2. repo with CLAUDE.md is left alone ---
git -C "$EXISTING" init -q
printf '# mine\nkeep this exactly\n' >"$EXISTING/CLAUDE.md"
BEFORE="$(shasum -a 256 "$EXISTING/CLAUDE.md")"
run_seed "$EXISTING" "$OUT_EXISTING"

check "claude exited 0 (refusal run)" test "$RC" -eq 0
check "refusal points to /project-base:audit" grep -q "/project-base:audit" "$OUT_EXISTING"
check "existing CLAUDE.md unchanged" bash -c '[ "$(shasum -a 256 "$1/CLAUDE.md")" = "$2" ]' _ "$EXISTING" "$BEFORE"
check "no .claude/agents created" bash -c '! test -e "$1/.claude/agents"' _ "$EXISTING"
check "no docs/projects created" bash -c '! test -e "$1/docs/projects"' _ "$EXISTING"
check "nothing else written" bash -c '[ "$(cd "$1" && find . -path ./.git -prune -o -type f -print)" = "./CLAUDE.md" ]' _ "$EXISTING"

# --- 3. parallel=yes: the main-checkout guard must not block seed's own writes ---
git -C "$PAR" init -q
run_seed "$PAR" "$OUT_PAR" "parallel=yes"

check "claude exited 0 (parallel run)" test "$RC" -eq 0
check "parallel key written" bash -c 'grep -q "\"parallel\"" "$1/.claude/project-base.json"' _ "$PAR"
check "CLAUDE.md has the worktree line, no parallel marker" bash -c 'grep -q "claude -w" "$1/CLAUDE.md" && ! grep -q "<!-- parallel:" "$1/CLAUDE.md"' _ "$PAR"
check ".gitignore ignores .claude/worktrees/" bash -c 'git -C "$1" check-ignore -q .claude/worktrees/x' _ "$PAR"
check "bootstrap plan.md exists (guard did not block seed)" bash -c 'ls -d "$1"/docs/projects/*-bootstrap/plan.md' _ "$PAR"

if [ "$FAILED" -ne 0 ]; then echo "--- claude output (seed run) ---"; cat "$OUT_SEED"; echo "--- claude output (parallel run) ---"; cat "$OUT_PAR"; echo "--- claude output (refusal run) ---"; cat "$OUT_EXISTING"; fi
exit "$FAILED"
