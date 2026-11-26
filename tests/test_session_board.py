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
import session_board as sb  # noqa: E402

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


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve() / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "project-base.json").write_text('{"parallel": {}}')
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")
        self.wt = Path(self.tmp.name).resolve() / "wt"
        git(self.repo, "worktree", "add", "-q", "-b", "feat", str(self.wt))
        self.bd = pc.board_dir(self.repo)

    def inp(self, sid="s1", cwd=None):
        return {"session_id": sid, "cwd": str(cwd or self.wt)}

    def file(self, sid="s1"):
        return self.bd / f"{sid}.json"

    def test_start_writes_file(self):
        out = sb.start(self.inp())
        b = json.loads(self.file().read_text())
        self.assertEqual((b["cwd"], b["branch"], b["name"], b["claims"]),
                         (str(self.wt), "feat", None, []))
        self.assertIn(str(self.file()), out)
        self.assertIn("/project-base:claim", out)

    def test_restart_keeps_name_claims_started(self):
        sb.start(self.inp())
        b = json.loads(self.file().read_text())
        b.update(name="me", claims=["a/"], started="2000-01-01T00:00:00Z")
        self.file().write_text(json.dumps(b))
        sb.start(self.inp(cwd=self.repo))
        n = json.loads(self.file().read_text())
        self.assertEqual((n["name"], n["claims"], n["started"]), ("me", ["a/"], "2000-01-01T00:00:00Z"))
        self.assertEqual((n["cwd"], n["branch"]), (str(self.repo), "main"))

    def test_claims_do_not_survive_end(self):
        sb.start(self.inp())
        b = json.loads(self.file().read_text())
        b["claims"] = ["a/"]
        self.file().write_text(json.dumps(b))
        sb.end(self.inp())
        sb.start(self.inp())
        self.assertEqual(json.loads(self.file().read_text())["claims"], [])

    def test_badly_typed_own_fields_sanitized(self):
        self.bd.mkdir(parents=True)
        self.file().write_text(json.dumps({"claims": "docs/", "name": 5, "started": "t"}))
        sb.start(self.inp())
        b = json.loads(self.file().read_text())
        self.assertEqual((b["claims"], b["name"], b["started"]), ([], None, "t"))

    def test_session_title_names_unnamed_session(self):
        sb.start({**self.inp(), "session_title": "w1"})
        self.assertEqual(json.loads(self.file().read_text())["name"], "w1")
        sb.start({**self.inp("s2"), "session_title": ""})
        self.assertIsNone(json.loads(self.file("s2").read_text())["name"])
        sb.start(self.inp("s3"))
        self.assertIsNone(json.loads(self.file("s3").read_text())["name"])

    def test_session_title_keeps_existing_name(self):
        sb.start(self.inp())
        b = json.loads(self.file().read_text())
        b["name"] = "mine"
        self.file().write_text(json.dumps(b))
        sb.start({**self.inp(), "session_title": "w1"})
        self.assertEqual(json.loads(self.file().read_text())["name"], "mine")

    def test_malformed_own_file_starts_fresh(self):
        self.bd.mkdir(parents=True)
        self.file().write_text("{nope")
        sb.start(self.inp())
        self.assertEqual(json.loads(self.file().read_text())["claims"], [])

    def test_lists_others_with_age_stale_and_worktrees(self):
        self.bd.mkdir(parents=True)
        (self.bd / "o1.json").write_text(json.dumps(
            {"cwd": "/x", "branch": "bx", "name": "alice", "claims": ["docs/"]}))
        (self.bd / "o2.json").write_text(json.dumps(
            {"cwd": "/y", "branch": "by", "name": None, "claims": []}))
        (self.bd / "bad.json").write_text("garbage")
        old = time.time() - 3 * 86400
        os.utime(self.bd / "o2.json", (old, old))
        out = sb.start(self.inp())
        self.assertIn("alice", out)
        self.assertIn("bx", out)
        self.assertIn("docs/", out)
        self.assertIn("o2", out)
        self.assertIn("3d", out)
        self.assertIn("stale", out)
        self.assertNotIn("bad", out)
        self.assertIn(str(self.wt), out)  # from git worktree list
        self.assertEqual(out.count("stale"), 1)
        self.assertIn("SendMessage", out)

    def test_alone_no_messaging_hint(self):
        self.assertNotIn("SendMessage", sb.start(self.inp()))

    def test_prunes_old_other_files_not_own(self):
        self.bd.mkdir(parents=True)
        old = time.time() - (sb.PRUNE_DAYS + 1) * 86400
        (self.bd / "dead.json").write_text("{}")
        os.utime(self.bd / "dead.json", (old, old))
        sb.start(self.inp())
        os.utime(self.file(), (old, old))
        sb.start(self.inp())
        self.assertFalse((self.bd / "dead.json").exists())
        self.assertTrue(self.file().exists())

    def test_end_deletes_own_file_only(self):
        sb.start(self.inp())
        sb.start(self.inp("s2"))
        self.assertIsNone(sb.end(self.inp()))
        self.assertFalse(self.file().exists())
        self.assertTrue(self.file("s2").exists())
        sb.end(self.inp())  # already gone: no error

    def test_end_falls_back_to_project_dir_when_worktree_gone(self):
        sb.start(self.inp())
        gone = Path(self.tmp.name).resolve() / "gone"  # not a repo, not existing
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}):
            sb.end(self.inp(cwd=gone))
        self.assertFalse(self.file().exists())
        sb.start(self.inp("s2"))
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.repo)}):
            sb.end(self.inp("s1", cwd=gone))
        self.assertTrue(self.file("s2").exists())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
            sb.end(self.inp("s2", cwd=gone))  # no env: silent no-op
        self.assertTrue(self.file("s2").exists())

    def test_no_parallel_key_nothing(self):
        (self.repo / ".claude" / "project-base.json").write_text("{}")
        self.assertEqual(sb.start(self.inp()), "")
        self.assertFalse(self.bd.exists())

    def test_bad_input_nothing(self):
        for bad in ({}, {"session_id": 5, "cwd": str(self.wt)}, {"session_id": "s"},
                    {"session_id": "s", "cwd": 3},
                    {"session_id": "s", "cwd": self.tmp.name},
                    {"session_id": "../x", "cwd": str(self.wt)},
                    {"session_id": "a/b", "cwd": str(self.wt)},
                    {"session_id": "..", "cwd": str(self.wt)}):
            self.assertEqual(sb.start(bad), "", bad)
            self.assertIsNone(sb.end(bad))
        self.assertFalse(self.bd.exists())
        self.assertFalse((self.bd.parent / "x.json").exists())

    def run_main(self, arg, stdin):
        args = [sys.executable, str(ROOT / "scripts" / "session_board.py")] + ([arg] if arg else [])
        return subprocess.run(args, input=stdin, capture_output=True, text=True, env=ENV, cwd=self.tmp.name)

    def test_main_cli(self):
        r = self.run_main("start", json.dumps(self.inp()))
        self.assertEqual(r.returncode, 0)
        self.assertIn(str(self.file()), r.stdout)
        r = self.run_main("end", json.dumps(self.inp()))
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertFalse(self.file().exists())

    def test_main_garbage(self):
        for arg in ("start", "end", "bogus", None):
            for stdin in ("not json", "", "[]", "null"):
                r = self.run_main(arg, stdin)
                self.assertEqual((r.returncode, r.stdout), (0, ""), (arg, stdin))


if __name__ == "__main__":
    unittest.main()
