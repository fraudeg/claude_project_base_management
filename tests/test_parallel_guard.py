import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import parallel_config as pc  # noqa: E402
import parallel_guard as g  # noqa: E402

ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def git(cwd, *args):
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(cwd), *args],
                   check=True, capture_output=True, text=True, env=ENV)


def ctx(out):
    return out["hookSpecificOutput"]


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")
        self.wt = self.base / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "topic", str(self.wt))
        self.config()

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, **par):
        par.setdefault("shared", ["CLAUDE.md", "docs/shared/"])
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "project-base.json").write_text(json.dumps({"parallel": par}))

    def board(self, sid, claims, name="other", branch="topic-b", age=0):
        d = pc.board_dir(self.repo)
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{sid}.json"
        f.write_text(json.dumps({"cwd": "/x", "branch": branch, "started": "t", "name": name, "claims": claims}))
        if age:
            t = time.time() - age
            os.utime(f, (t, t))
        return f

    def edit(self, path, tool="Edit", sid="me", cwd=None):
        return g.decide({"session_id": sid, "cwd": str(cwd or self.repo), "tool_name": tool,
                         "tool_input": {"file_path": str(path)}})

    def bash(self, cmd, cwd=None):
        return g.decide({"session_id": "me", "cwd": str(cwd or self.repo), "tool_name": "Bash",
                         "tool_input": {"command": cmd}})

    def test_edit_in_main_denied(self):
        o = ctx(self.edit(self.repo / "a.py"))
        self.assertEqual(o["permissionDecision"], "deny")
        self.assertEqual(o["hookEventName"], "PreToolUse")
        self.assertIn("claude -w <topic> -n <topic>", o["permissionDecisionReason"])

    def test_edit_in_main_warn(self):
        self.config(main_checkout="warn")
        o = ctx(self.edit(self.repo / "a.py"))
        self.assertNotIn("permissionDecision", o)
        self.assertIn("main checkout", o["additionalContext"])

    def test_edit_in_main_off(self):
        self.config(main_checkout="off")
        self.assertIsNone(self.edit(self.repo / "a.py"))

    def test_edit_in_worktree_ok_and_notebook(self):
        self.assertIsNone(self.edit(self.wt / "a.py"))
        d = g.decide({"session_id": "me", "cwd": str(self.repo), "tool_name": "NotebookEdit",
                      "tool_input": {"notebook_path": str(self.repo / "n.ipynb")}})
        self.assertEqual(ctx(d)["permissionDecision"], "deny")

    def test_relative_path_resolves_against_cwd(self):
        d = g.decide({"session_id": "me", "cwd": str(self.wt), "tool_name": "Edit",
                      "tool_input": {"file_path": "a.py"}})
        self.assertIsNone(d)

    def test_bad_paths_none(self):
        for ti in ({}, {"file_path": 5}, {"file_path": ""}):
            self.assertIsNone(g.decide({"session_id": "me", "cwd": str(self.repo),
                                        "tool_name": "Edit", "tool_input": ti}))

    def test_bash_git_writes_denied_in_main(self):
        for cmd in ("git commit -m x", "git add x && git commit -m y", "FOO=1 git commit -m x",
                    "git -C . commit -m x", "git --no-pager -c a=b reset --hard", "true; git merge x",
                    "git checkout -b n", "git switch x", "git rebase main", "git cherry-pick abc",
                    "echo hi\ngit commit -m z"):
            self.assertEqual(ctx(self.bash(cmd))["permissionDecision"], "deny", cmd)

    def test_bash_reads_pass(self):
        for cmd in ("git status", "git log --oneline", "git diff", "git show HEAD",
                    "git checkout file.txt", "echo git commit", "git add x"):
            self.assertIsNone(self.bash(cmd), cmd)

    def test_bash_commit_in_worktree_ok(self):
        self.assertIsNone(self.bash("git commit -m x", cwd=self.wt))

    def test_bash_warn_and_off(self):
        self.config(main_checkout="warn")
        o = ctx(self.bash("git commit -m x"))
        self.assertNotIn("permissionDecision", o)
        self.config(main_checkout="off")
        self.assertIsNone(self.bash("git commit -m x"))

    def test_no_parallel_key(self):
        (self.repo / ".claude" / "project-base.json").write_text("{}")
        self.assertIsNone(self.edit(self.repo / "a.py"))
        self.assertIsNone(self.bash("git commit -m x"))

    def test_shared_claimed_by_other_denied(self):
        self.board("s2", ["CLAUDE.md"], name="alice", branch="topic-b")
        o = ctx(self.edit(self.wt / "CLAUDE.md"))
        self.assertEqual(o["permissionDecision"], "deny")
        r = o["permissionDecisionReason"]
        for s in ("alice", "topic-b", "SendMessage"):
            self.assertIn(s, r)
        self.assertNotIn("stale", r)

    def test_shared_prefix_claim_and_session_id_fallback(self):
        f = self.board("s2", ["docs/shared/"], name="")
        o = ctx(self.edit(self.wt / "docs" / "shared" / "x.md"))
        self.assertIn("s2", o["permissionDecisionReason"])
        f.unlink()

    def test_stale_claim_names_file(self):
        f = self.board("s2", ["CLAUDE.md"], age=25 * 3600)
        r = ctx(self.edit(self.wt / "CLAUDE.md"))["permissionDecisionReason"]
        self.assertIn("stale", r)
        self.assertIn(str(f), r)

    def test_shared_unclaimed_reminder(self):
        o = ctx(self.edit(self.wt / "CLAUDE.md"))
        self.assertNotIn("permissionDecision", o)
        self.assertIn("/project-base:claim CLAUDE.md", o["additionalContext"])

    def test_shared_own_claim_none(self):
        self.board("me", ["CLAUDE.md"])
        self.assertIsNone(self.edit(self.wt / "CLAUDE.md"))

    def test_malformed_board_skipped(self):
        d = pc.board_dir(self.repo)
        d.mkdir(parents=True)
        (d / "bad.json").write_text("{nope")
        (d / "bad2.json").write_text("[]")
        o = ctx(self.edit(self.wt / "CLAUDE.md"))
        self.assertIn("additionalContext", o)

    def test_deny_wins_when_main_and_shared(self):
        self.board("s2", ["CLAUDE.md"])
        o = ctx(self.edit(self.repo / "CLAUDE.md"))
        self.assertEqual(o["permissionDecision"], "deny")
        self.assertIn("main checkout", o["permissionDecisionReason"])

    def test_shared_applies_with_main_off(self):
        self.config(main_checkout="off")
        self.board("s2", ["CLAUDE.md"])
        self.assertEqual(ctx(self.edit(self.repo / "CLAUDE.md"))["permissionDecision"], "deny")

    def test_quotes_and_heredocs_do_not_false_deny(self):
        for cmd in ('echo "done; git commit later"', "echo 'a && git reset x'",
                    "cat <<EOF > notes.md\ngit reset notes\nEOF",
                    "cat <<'EOF' > n.md\ngit commit\nEOF\ngit status", 'echo "unbalanced; git commit'):
            self.assertIsNone(self.bash(cmd), cmd)

    def test_more_forms_denied(self):
        for cmd in ("(git commit -m x)", "echo $(git commit -m x)", "a & git commit -m x",
                    'git -c user.name="A B" commit -m x', 'FOO="a b" git commit -m x',
                    "if true; then git commit -m x; fi", "sudo git commit -m x", "env X=1 git reset --hard",
                    "! git merge x", "time git commit -m x"):
            self.assertEqual(ctx(self.bash(cmd))["permissionDecision"], "deny", cmd)

    def test_cd_into_worktree_then_commit_ok(self):
        nested = self.repo / ".claude" / "worktrees" / "x"
        git(self.repo, "worktree", "add", "-q", "-b", "nx", str(nested))
        self.assertIsNone(self.bash("cd .claude/worktrees/x && git commit -m y"))
        self.assertIsNone(self.bash(f"cd {self.wt} && git commit -m y"))
        self.assertEqual(ctx(self.bash(f"cd {self.wt} && cd {self.repo} && git commit -m y"))["permissionDecision"], "deny")
        self.assertIsNone(self.bash("cd && git commit -m y"))

    def test_nested_worktree_not_main(self):
        nested = self.repo / ".claude" / "worktrees" / "x"
        git(self.repo, "worktree", "add", "-q", "-b", "nx", str(nested))
        self.assertIsNone(self.edit(nested / "a.py", cwd=nested))
        self.assertIsNone(self.bash("git commit -m x", cwd=nested))

    def test_own_claim_beats_other_claim_and_bad_session_id(self):
        self.board("me", ["CLAUDE.md"])
        self.board("s2", ["CLAUDE.md"])
        self.assertIsNone(self.edit(self.wt / "CLAUDE.md"))
        for sid in (None, 5):
            d = g.decide({"session_id": sid, "cwd": str(self.wt), "tool_name": "Edit",
                          "tool_input": {"file_path": str(self.wt / "CLAUDE.md")}})
            self.assertIsNone(d)

    def other_repo(self, par=None):
        o = self.base / "other"
        o.mkdir()
        git(o, "init", "-q")
        git(o, "commit", "-q", "--allow-empty", "-m", "init")
        if par is not None:
            (o / ".claude").mkdir()
            (o / ".claude" / "project-base.json").write_text(json.dumps({"parallel": par}))
        return o

    def test_cd_to_repo_with_own_config(self):
        o = self.other_repo()
        self.assertIsNone(self.bash(f"cd {o} && git commit -m x"))
        o2 = self.base / "other"
        (o2 / ".claude").mkdir()
        (o2 / ".claude" / "project-base.json").write_text(json.dumps({"parallel": {"main_checkout": "block"}}))
        self.assertEqual(ctx(self.bash(f"cd {o} && git commit -m x"))["permissionDecision"], "deny")
        (o2 / ".claude" / "project-base.json").write_text(json.dumps({"parallel": {"main_checkout": "warn"}}))
        out = ctx(self.bash(f"cd {o} && git commit -m x"))
        self.assertNotIn("permissionDecision", out)
        self.assertIn("main checkout", out["additionalContext"])

    def test_deny_wins_over_earlier_warn_target(self):
        o = self.other_repo({"main_checkout": "warn"})
        out = ctx(self.bash(f"cd {o} && git commit -m x; cd {self.repo} && git commit -m y"))
        self.assertEqual(out["permissionDecision"], "deny")

    def test_checkout_flags_before_branch(self):
        git(self.repo, "branch", "feat")
        for cmd in ("git checkout -f feat", "git checkout -q feat", "git checkout -f -q feat"):
            self.assertEqual(ctx(self.bash(cmd))["permissionDecision"], "deny", cmd)
        for cmd in ("git checkout -f file.txt", "git checkout -f -- feat", "git checkout -f"):
            self.assertIsNone(self.bash(cmd), cmd)

    def test_cd_to_repo_off_but_session_repo_blocks(self):
        o = self.other_repo({"main_checkout": "off"})
        self.assertIsNone(self.bash(f"cd {o} && git commit -m x"))

    def test_git_dash_C_judged_by_target(self):
        nested = self.repo / ".claude" / "worktrees" / "x"
        git(self.repo, "worktree", "add", "-q", "-b", "nx", str(nested))
        self.assertIsNone(self.bash("git -C .claude/worktrees/x commit -m x"))
        self.assertIsNone(self.bash(f"git -C {self.wt} commit -m x"))
        self.assertEqual(ctx(self.bash(f"git -C {self.repo} commit -m x", cwd=self.wt))["permissionDecision"], "deny")
        self.assertEqual(ctx(self.bash("git -C . commit -m x"))["permissionDecision"], "deny")
        self.assertEqual(ctx(self.bash(f"git -C {self.wt} -C {self.repo} commit -m x"))["permissionDecision"], "deny")
        self.assertIsNone(self.bash("git -C $X commit -m x"))
        self.assertIsNone(self.bash("git -C ~/x commit -m x"))

    def test_no_git_text_spawns_no_process(self):
        with mock.patch.object(pc.subprocess, "run", side_effect=AssertionError("spawned")) as m:
            self.assertIsNone(self.bash("ls -la && echo hi"))
        m.assert_not_called()

    def test_main_msg_tells_not_to_use_bash(self):
        self.assertTrue(g.MAIN_MSG.endswith("Do not make this change through Bash instead."))
        self.assertTrue(g.MAIN_MSG.startswith("This is the main checkout. Start a worktree: claude -w <topic> -n <topic>"))
        self.assertIn("EnterWorktree", g.MAIN_MSG)

    def test_checkout_branch_switch_denied_files_pass(self):
        git(self.repo, "branch", "other-b")
        for cmd in ("git checkout other-b", "git checkout -", "git checkout --detach",
                    "git checkout --detach HEAD", f"git -C {self.repo} checkout topic"):
            self.assertEqual(ctx(self.bash(cmd, cwd=self.wt if "-C" in cmd else None))["permissionDecision"],
                             "deny", cmd)
        (self.repo / "file.txt").write_text("x")
        for cmd in ("git checkout file.txt", "git checkout -- other-b", "git checkout .", "git checkout nobranch",
                    "git checkout"):
            self.assertIsNone(self.bash(cmd), cmd)

    def test_garbage_stdin_exits_zero_silent(self):
        for s in ("", "not json", "[]", '{"cwd": 5}', '{"cwd": "/nonexistent", "tool_name": "Edit"}'):
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "parallel_guard.py")],
                               input=s, capture_output=True, text=True, env=ENV)
            self.assertEqual((r.returncode, r.stdout), (0, ""), s)

    def test_main_prints_json(self):
        inp = {"session_id": "me", "cwd": str(self.repo), "tool_name": "Edit",
               "tool_input": {"file_path": str(self.repo / "a.py")}}
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "parallel_guard.py")],
                           input=json.dumps(inp), capture_output=True, text=True, env=ENV)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
