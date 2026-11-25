import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import parallel_config as p  # noqa: E402

ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}
DEFAULTS = {"worktrees_dir": ".claude/worktrees", "main_checkout": "block", "shared": []}


def git(cwd, *args):
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(cwd), *args],
                   check=True, capture_output=True, text=True, env=ENV)


class ParallelConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "init")
        self.inside = self.repo / ".claude" / "worktrees" / "a"
        self.outside = self.base / "wt-out"
        git(self.repo, "worktree", "add", "-q", "-b", "a", str(self.inside))
        git(self.repo, "worktree", "add", "-q", "-b", "b", str(self.outside))

    def tearDown(self):
        self.tmp.cleanup()

    def cfg(self, data):
        d = self.repo / ".claude"
        d.mkdir(exist_ok=True)
        (d / "project-base.json").write_text(data if isinstance(data, str) else json.dumps(data))

    def test_is_main_checkout(self):
        self.assertTrue(p.is_main_checkout(self.repo))
        self.assertTrue(p.is_main_checkout(self.repo / "new" / "dir" / "f.txt"))
        self.assertFalse(p.is_main_checkout(self.inside))
        self.assertFalse(p.is_main_checkout(self.inside / "x" / "f.txt"))
        self.assertFalse(p.is_main_checkout(self.outside))

    def test_custom_worktrees_dir_is_never_main(self):
        self.cfg({"parallel": {"worktrees_dir": "trees"}})
        (self.repo / "trees" / "q").mkdir(parents=True)
        self.assertFalse(p.is_main_checkout(self.repo / "trees" / "q"))
        self.assertTrue(p.is_main_checkout(self.repo))

    def test_worktrees_dir_at_or_above_root_is_invalid(self):
        for bad in (".", "..", "/", "a/.."):
            self.cfg({"parallel": {"worktrees_dir": bad}})
            self.assertEqual(p.load_parallel(self.repo)["worktrees_dir"], ".claude/worktrees", bad)
            self.assertTrue(p.is_main_checkout(self.repo), bad)

    def test_non_git(self):
        d = self.base / "plain"
        d.mkdir()
        self.assertFalse(p.is_main_checkout(d))
        self.assertIsNone(p.main_root(d))
        self.assertIsNone(p.board_dir(d))
        self.assertIsNone(p.load_parallel(d))
        self.assertFalse(p.is_main_checkout(self.base / "nope" / "f"))

    def test_main_root_from_worktree(self):
        for s in (self.repo, self.inside, self.outside):
            self.assertEqual(p.main_root(s).resolve(), self.repo)

    def test_board_dir(self):
        want = self.repo / ".git" / "project-base-board"
        for s in (self.repo, self.inside, self.outside):
            self.assertEqual(p.board_dir(s).resolve(), want)
        self.assertFalse(want.exists())

    def test_load_missing_and_malformed(self):
        self.assertIsNone(p.load_parallel(self.repo))
        self.cfg("{not json")
        self.assertIsNone(p.load_parallel(self.repo))
        self.cfg({"other": 1})
        self.assertIsNone(p.load_parallel(self.repo))
        self.cfg({"parallel": "yes"})
        self.assertIsNone(p.load_parallel(self.repo))

    def test_load_defaults_and_worktree_start(self):
        self.cfg({"parallel": {}})
        self.assertEqual(p.load_parallel(self.repo), DEFAULTS)
        self.cfg({"parallel": {"main_checkout": "warn", "shared": ["CLAUDE.md"]}})
        want = {**DEFAULTS, "main_checkout": "warn", "shared": ["CLAUDE.md"]}
        self.assertEqual(p.load_parallel(self.repo), want)
        # config lives in the main checkout; a worktree start finds it
        self.assertEqual(p.load_parallel(self.outside), want)

    def test_load_wrong_types_fall_back(self):
        self.cfg({"parallel": {"main_checkout": "maybe", "shared": "CLAUDE.md", "worktrees_dir": 3}})
        self.assertEqual(p.load_parallel(self.repo), DEFAULTS)
        self.cfg({"parallel": {"shared": ["a", 1]}})
        self.assertEqual(p.load_parallel(self.repo), DEFAULTS)

    def test_never_raises(self):
        for bad in (None, 5, b"x"):
            self.assertIsNone(p.main_root(bad))
            self.assertIsNone(p.board_dir(bad))
            self.assertIsNone(p.load_parallel(bad))
            self.assertFalse(p.is_main_checkout(bad))
        self.cfg("[" * 100000)
        self.assertIsNone(p.load_parallel(self.repo))
        loop = self.base / "loop"
        loop.symlink_to(loop)
        self.assertIsNone(p.load_parallel(loop))
        self.assertFalse(p.is_main_checkout(loop))

    def test_returned_defaults_are_fresh(self):
        self.cfg({"parallel": {}})
        p.load_parallel(self.repo)["shared"].append("x")
        self.assertEqual(p.load_parallel(self.repo), DEFAULTS)
        self.assertEqual(p._defaults()["shared"], [])


if __name__ == "__main__":
    unittest.main()
