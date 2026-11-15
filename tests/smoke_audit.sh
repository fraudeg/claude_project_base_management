#!/usr/bin/env bash
# Smoke test for /project-base:audit. It calls the real `claude` CLI twice (the second run is a cheap refusal), so it costs a little.
# Runs on a throwaway sample repo only, never on a real one. Run: bash tests/smoke_audit.sh   (exit 0 = every check passed)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLE="$(mktemp -d)"   # sample repo with a CLAUDE.md, a manifest, a test and an agent without `model:`
OUT_AUDIT="$(mktemp)"; OUT_AGAIN="$(mktemp)"  # what claude printed in each run
# SMOKE_KEEP=1 keeps the sample so you can read what the model wrote.
trap 'if [ -n "${SMOKE_KEEP:-}" ]; then echo "kept: $SAMPLE"; else rm -rf "$SAMPLE"; fi; rm -f "$OUT_AUDIT" "$OUT_AGAIN"' EXIT

FAILED=0
check() { # check "name" command args...
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS: $name"; else echo "FAIL: $name"; FAILED=1; fi
}

# run_audit OUTFILE: runs the skill in the sample, saves what claude printed in OUTFILE, sets RC to its exit code.
# Same flags as smoke_seed.sh: auto mode (a classifier decides; bypassPermissions is never used), Bash limited to the listed commands.
run_audit() {
  RC=0
  (cd "$SAMPLE" && claude --plugin-dir "$REPO" --model sonnet --strict-mcp-config --setting-sources project,local \
    --permission-mode auto --max-budget-usd 3 --no-session-persistence \
    --allowedTools "Bash(python3:*),Bash(mkdir:*),Bash(cp:*),Bash(ls:*),Bash(cat:*),Bash(date:*),Bash(find:*),Bash(wc:*),Bash(grep:*),Bash(head:*),Bash(git status:*),Bash(git ls-files:*),Read(/$REPO/**)" \
    -p "/project-base:audit" </dev/null) >"$1" 2>&1 || RC=$?
}

# --- sample repo: committed, so any later change shows in git status ---
git -C "$SAMPLE" init -q
mkdir -p "$SAMPLE/src" "$SAMPLE/test" "$SAMPLE/.claude/agents" "$SAMPLE/docs"
cat >"$SAMPLE/CLAUDE.md" <<'EOF'
# Sample

Small CLI that adds numbers.

## Commands

- Test: `npm test`

## Release

1. Bump the version in `package.json`.
2. Run `npm test`.
3. Tag the commit and push the tag.
4. Always remember to update the changelog before tagging.
EOF
cat >"$SAMPLE/package.json" <<'EOF'
{ "name": "sample", "version": "1.0.0", "scripts": { "test": "node --test" } }
EOF
printf 'exports.add = (a, b) => a + b;\n' >"$SAMPLE/src/index.js"
printf "const test = require('node:test');\nconst assert = require('node:assert');\nconst { add } = require('../src');\ntest('add', () => assert.strictEqual(add(1, 2), 3));\n" >"$SAMPLE/test/index.test.js"
printf -- '---\nname: foo\ndescription: Sample agent without a model.\n---\n\nYou help.\n' >"$SAMPLE/.claude/agents/foo.md"
printf '# Notes\n\nWe decided to keep the adder pure because callers cache its result. Do not change that.\n' >"$SAMPLE/docs/notes.md"
git -C "$SAMPLE" add -A
git -C "$SAMPLE" -c user.name=smoke -c user.email=smoke@example.invalid -c commit.gpgsign=false commit -q -m "sample"
before_files() { (cd "$SAMPLE" && git ls-files | xargs shasum -a 256); }
BEFORE="$(before_files)"

# --- 1. audit writes only the adoption folder ---
run_audit "$OUT_AUDIT"
ADOPT="$(ls -d "$SAMPLE"/docs/projects/*-adopt-project-base 2>/dev/null | head -1 || true)"
ADOPT="${ADOPT:-$SAMPLE/docs/projects/MISSING-adopt-project-base}"  # absent: the checks below fail

check "claude exited 0 (audit run)" test "$RC" -eq 0
check "git status shows only the adoption folder" bash -c '
  [ -n "$(git -C "$1" status --porcelain)" ] &&
  ! git -C "$1" status --porcelain --untracked-files=all | grep -qvE "^\?\? docs/projects/[0-9]{4}-[0-9]{2}-[0-9]{2}-adopt-project-base/"' _ "$SAMPLE"
check "tracked files unchanged" bash -c '[ "$(cd "$1" && git ls-files | xargs shasum -a 256)" = "$2" ]' _ "$SAMPLE" "$BEFORE"
check "nothing staged" bash -c '[ -z "$(git -C "$1" diff --cached --name-only)" ]' _ "$SAMPLE"
check "adoption folder has the four project files" bash -c 'for f in README decisions log plan; do [ -f "$1/$f.md" ] || exit 1; done' _ "$ADOPT"
check "no {{marker}} left in the folder" bash -c '[ -d "$1" ] && ! grep -rq "{{" "$1"' _ "$ADOPT"
check "README has a dated status line" grep -qE '^Status \([0-9]{4}-[0-9]{2}-[0-9]{2}\):' "$ADOPT/README.md"
check "log records the baseline as pending" grep -q "baseline pending" "$ADOPT/log.md"
check "plan has task lines" grep -qE '^- \[ \] 1\.' "$ADOPT/plan.md"
check "plan names the agent without a model" grep -qw foo "$ADOPT/plan.md"
# plugin files are named `<plugin>/...`: an absolute path is machine- and version-specific (the plugin dir here is $REPO)
ABS_PLUGIN='(^|[^A-Za-z0-9_.<>-])/[A-Za-z0-9_.~/-]+/(scripts|templates|agents)/'  # any absolute path into scripts/, templates/ or agents/
check "no absolute plugin path in the folder" bash -c '[ -d "$1" ] && ! grep -rqF "$2" "$1" && ! grep -rqE "$3" "$1"' _ "$ADOPT" "$REPO" "$ABS_PLUGIN"

# --- 2. a second run finds the folder and stops ---
folder_hash() { (cd "$ADOPT" && find . -type f | sort | xargs shasum -a 256) 2>/dev/null || true; }
status_count() { git -C "$SAMPLE" status --porcelain --untracked-files=all | wc -l | tr -d ' '; }
AFTER_AUDIT="$(folder_hash)"; STATUS_COUNT="$(status_count)"
if [ -d "$ADOPT" ]; then  # without the folder the second run would be a full audit, not a refusal
  run_audit "$OUT_AGAIN"
  check "claude exited 0 (second run)" test "$RC" -eq 0
  check "second run says the project already exists" grep -qi "already" "$OUT_AGAIN"
  check "second run changed nothing" test "$(folder_hash)|$(status_count)" = "$AFTER_AUDIT|$STATUS_COUNT"
else
  echo "FAIL: no adoption folder, second run skipped"; FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then echo "--- claude output (audit run) ---"; cat "$OUT_AUDIT"; echo "--- claude output (second run) ---"; cat "$OUT_AGAIN"; fi
exit "$FAILED"
