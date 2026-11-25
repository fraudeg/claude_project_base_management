import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "worktree_hook.py"
ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
}


def git(repo, *args):
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(repo), *args],
                          capture_output=True, text=True, env=ENV)


class TestWorktreeHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "project-base.json").write_text(
            json.dumps({"parallel": {"worktrees_dir": "../wt"}}))
        (self.repo / ".worktreeinclude").write_text(".env\n")
        (self.repo / ".gitignore").write_text(".env\n")
        (self.repo / ".env").write_text("SECRET=1\n")
        git(self.repo, "add", ".claude", ".worktreeinclude", ".gitignore")
        git(self.repo, "commit", "-qm", "init")

    def run_hook(self, mode, **payload):
        payload.setdefault("cwd", str(self.repo))
        return subprocess.run([sys.executable, str(SCRIPT), mode], input=json.dumps(payload),
                              capture_output=True, text=True, env=ENV, cwd=self.base)

    def create(self, name="feat"):
        return self.run_hook("create", name=name)

    def test_create(self):
        r = self.create()
        self.assertEqual(r.returncode, 0, r.stderr)
        target = self.base / "wt" / "feat"
        self.assertEqual(r.stdout.strip().splitlines()[-1], str(target))
        self.assertEqual(git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "worktree-feat")
        self.assertEqual((target / ".env").read_text(), "SECRET=1\n")

    def test_worktrees_dir_at_or_above_root_falls_back(self):
        for bad in (".", "..", "/"):
            (self.repo / ".claude" / "project-base.json").write_text(
                json.dumps({"parallel": {"worktrees_dir": bad}}))
            r = self.create()
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip().splitlines()[-1], str(self.repo / ".claude" / "worktrees" / "feat"), bad)
            git(self.repo, "worktree", "remove", "--force", str(self.repo / ".claude" / "worktrees" / "feat"))
            git(self.repo, "branch", "-D", "worktree-feat")

    def test_create_twice_prints_same_path(self):
        a, b = self.create(), self.create()
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(a.stdout.strip().splitlines()[-1], b.stdout.strip().splitlines()[-1])

    def test_create_from_inside_worktree_cwd(self):
        self.create()
        r = self.run_hook("create", name="two", cwd=str(self.base / "wt" / "feat"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.base / "wt" / "two").is_dir())

    def test_bad_name(self):
        for name in ("../x", "a/b", ".", "..", "", "a b"):
            r = self.create(name)
            self.assertEqual(r.returncode, 1, name)
        self.assertFalse((self.base / "wt").exists())

    def test_remove_merged(self):
        self.create()
        target = self.base / "wt" / "feat"
        r = self.run_hook("remove", worktree_path=str(target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(target.exists())
        self.assertNotIn("worktree-feat", git(self.repo, "branch").stdout)

    def test_remove_dirty_keeps_dir(self):
        self.create()
        target = self.base / "wt" / "feat"
        (target / "new.txt").write_text("x")
        r = self.run_hook("remove", worktree_path=str(target))
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(target.exists())

    def test_remove_unmerged_keeps_branch(self):
        self.create()
        target = self.base / "wt" / "feat"
        (target / "f.txt").write_text("x")
        git(target, "add", "f.txt")
        git(target, "commit", "-qm", "work")
        r = self.run_hook("remove", worktree_path=str(target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(target.exists())
        self.assertIn("worktree-feat", git(self.repo, "branch").stdout)

    def test_symlink_copied_as_symlink(self):
        outside = self.base / "outside.txt"
        outside.write_text("private")
        (self.repo / ".worktreeinclude").write_text(".env\nlink\n")
        (self.repo / ".gitignore").write_text(".env\nlink\n")
        (self.repo / "link").symlink_to(outside)
        r = self.create()
        self.assertEqual(r.returncode, 0, r.stderr)
        link = self.base / "wt" / "feat" / "link"
        self.assertTrue(link.is_symlink())

    def test_create_after_unmerged_remove_resumes_branch(self):
        self.create()
        target = self.base / "wt" / "feat"
        (target / "f.txt").write_text("x")
        git(target, "add", "f.txt")
        git(target, "commit", "-qm", "work")
        self.run_hook("remove", worktree_path=str(target))
        r = self.create()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((target / "f.txt").exists())

    def test_create_after_dir_deleted(self):
        import shutil
        self.create()
        target = self.base / "wt" / "feat"
        shutil.rmtree(target)
        r = self.create()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(target.is_dir())

    def test_copy_failure_is_warning(self):
        (self.repo / ".env").chmod(0)
        self.addCleanup((self.repo / ".env").chmod, 0o644)
        r = self.create()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], str(self.base / "wt" / "feat"))
        self.assertIn("could not copy", r.stderr)


if __name__ == "__main__":
    unittest.main()
