import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import checkpoint_reminder as c  # noqa: E402

SCRIPT = ROOT / "scripts" / "checkpoint_reminder.py"


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def task(self, name, text, docs="docs", project="p"):
        f = self.dir / docs / "projects" / project / "tasks" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        return f

    def run_hook(self, event):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.dir)}
        return subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"hook_event_name": event}),
                              capture_output=True, text=True, env=env)

    def test_open_tasks_lists_in_progress(self):
        a = self.task("001-a.md", "# A\n\nStatus: in-progress\n")
        self.task("002-b.md", "# B\n\nStatus: done\n")
        self.assertEqual(c.open_tasks(self.dir), [a])

    def test_task_without_status_ignored(self):
        self.task("001-a.md", "# A\n\nno status here\n")
        self.assertEqual(c.open_tasks(self.dir), [])

    def test_unknown_status_ignored(self):
        self.task("001-a.md", "Status: paused\n")
        self.task("002-b.md", "Status: in-progress|blocked|done\n")
        self.task("003-c.md", "see Status: in-progress later\n")
        self.assertEqual(c.open_tasks(self.dir), [])

    def test_docs_root_from_config(self):
        (self.dir / ".claude").mkdir()
        (self.dir / ".claude" / "project-base.json").write_text('{"docs_root": "handbook"}')
        self.task("001-a.md", "Status: in-progress\n", docs="docs")
        b = self.task("001-b.md", "Status: in-progress\n", docs="handbook")
        self.assertEqual(c.open_tasks(self.dir), [b])

    def test_absolute_docs_root_does_not_crash(self):
        (self.dir / ".claude").mkdir()
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        (self.dir / ".claude" / "project-base.json").write_text(json.dumps({"docs_root": other.name}))
        f = Path(other.name) / "projects" / "p" / "tasks" / "001-a.md"
        f.parent.mkdir(parents=True)
        f.write_text("Status: in-progress\n")
        p = self.run_hook("PreCompact")
        self.assertEqual(p.returncode, 0)
        self.assertIn("001-a.md", p.stdout)

    def test_bad_stdin_or_cwd_or_docs_root_never_crashes(self):
        self.task("001-a.md", "Status: in-progress\n")
        for stdin in ["", "not json", "[]", "null", '{"cwd": 5}', '{"cwd": ["x"], "hook_event_name": "SessionEnd"}']:
            env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.dir)}
            p = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True, env=env)
            self.assertIn(p.returncode, (0, 2), stdin)
            self.assertNotIn("Traceback", p.stderr, stdin)
        # no env var: a non-str cwd falls through to os.getcwd() instead of raising
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        p = subprocess.run([sys.executable, str(SCRIPT)], input='{"cwd": 5}', capture_output=True, text=True,
                           env=env, cwd=self.dir)
        self.assertEqual(p.returncode, 0)
        self.assertIn("001-a.md", p.stdout)
        (self.dir / ".claude").mkdir()
        (self.dir / ".claude" / "project-base.json").write_text('{"docs_root": "a\\u0000b"}')
        self.assertEqual(c.open_tasks(self.dir), [])

    def test_no_docs_dir(self):
        self.assertEqual(c.open_tasks(self.dir), [])

    def test_precompact_prints_reminder_to_stdout(self):
        self.task("001-a.md", "Status: in-progress\n")
        p = self.run_hook("PreCompact")
        self.assertEqual(p.returncode, 0)
        self.assertIn("docs/projects/p/tasks/001-a.md", p.stdout)
        self.assertEqual(p.stderr, "")

    def test_sessionend_prints_reminder_to_stderr_exit_2(self):
        self.task("001-a.md", "Status: in-progress\n")
        p = self.run_hook("SessionEnd")
        self.assertEqual(p.returncode, 2)
        self.assertIn("docs/projects/p/tasks/001-a.md", p.stderr)
        self.assertEqual(p.stdout, "")

    def test_nothing_printed_without_open_tasks(self):
        self.task("001-a.md", "Status: done\n")
        for event in ("PreCompact", "SessionEnd"):
            p = self.run_hook(event)
            self.assertEqual((p.returncode, p.stdout, p.stderr), (0, "", ""), event)


if __name__ == "__main__":
    unittest.main()
