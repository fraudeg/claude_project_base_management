import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import trim_test_output as t  # noqa: E402

SCRIPT = ROOT / "scripts" / "trim_test_output.py"


def run_hook(stdin, project_dir):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)}
    p = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


class RewriteTests(unittest.TestCase):
    def test_rewrites_matching_command(self):
        self.assertEqual(
            t.rewrite("pytest -q", t.DEFAULT_PATTERNS),
            "set -o pipefail; pytest -q 2>&1 | tail -n 100",
        )

    def test_default_patterns_cover_common_runners(self):
        for cmd in ["pytest", "python -m pytest -x", "python3 -m pytest", "npm test", "pnpm test", "yarn test",
                    "go test ./...", "cargo test", "mvn test", "gradle test", "./gradlew test"]:
            self.assertIsNotNone(t.rewrite(cmd, t.DEFAULT_PATTERNS), cmd)

    def test_leaves_chained_command(self):
        for cmd in ["pytest | head", "pytest; ls", "pytest && ls", "pytest > out", "pytest || true", "pytest < in",
                    "pytest `ls`", "pytest $(ls)", "pytest &", "pytest\nls", "pytest 2>&1"]:
            self.assertIsNone(t.rewrite(cmd, t.DEFAULT_PATTERNS), cmd)

    def test_leaves_other_command(self):
        self.assertIsNone(t.rewrite("ls", t.DEFAULT_PATTERNS))
        self.assertIsNone(t.rewrite("pytest-watch", t.DEFAULT_PATTERNS))
        self.assertIsNone(t.rewrite("echo pytest", t.DEFAULT_PATTERNS))

    def test_invalid_regex_pattern_is_skipped(self):
        self.assertIsNone(t.rewrite("make check", ["("]))
        self.assertIsNotNone(t.rewrite("make check", ["(", "^make check$"]))


class LoadPatternsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / ".claude").mkdir()
        self.cfg = self.dir / ".claude" / "project-base.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_patterns_used(self):
        self.cfg.write_text(json.dumps({"test_command_patterns": ["^make check$"]}))
        self.assertEqual(t.load_patterns(self.dir), ["^make check$"])

    def test_missing_config_falls_back(self):
        self.assertEqual(t.load_patterns(self.dir), t.DEFAULT_PATTERNS)

    def test_bad_config_falls_back(self):
        self.cfg.write_text("{not json")
        self.assertEqual(t.load_patterns(self.dir), t.DEFAULT_PATTERNS)

    def test_non_list_config_falls_back(self):
        for value in ['{"test_command_patterns": "^make$"}', '{"test_command_patterns": [1]}', "[1]", "null"]:
            self.cfg.write_text(value)
            self.assertEqual(t.load_patterns(self.dir), t.DEFAULT_PATTERNS, value)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_outputs_updated_input_keeping_other_fields(self):
        tool_input = {"command": "pytest -q", "description": "run tests", "timeout": 5000}
        code, out = run_hook(json.dumps({"tool_name": "Bash", "tool_input": tool_input}), self.tmp.name)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {**tool_input, "command": "set -o pipefail; pytest -q 2>&1 | tail -n 100"},
        }})

    def test_untouched_command_prints_empty_object(self):
        code, out = run_hook(json.dumps({"tool_input": {"command": "ls"}}), self.tmp.name)
        self.assertEqual((code, json.loads(out)), (0, {}))

    def test_malformed_stdin_prints_empty_object(self):
        for stdin in ["", "not json", "[]", "null", '{"tool_input": "x"}', '{"tool_input": {"command": 3}}']:
            code, out = run_hook(stdin, self.tmp.name)
            self.assertEqual((code, json.loads(out)), (0, {}), stdin)

    def test_non_str_cwd_does_not_crash(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        payload = json.dumps({"cwd": 5, "tool_input": {"command": "pytest -q"}})
        p = subprocess.run([sys.executable, str(SCRIPT)], input=payload, capture_output=True, text=True, env=env,
                           cwd=self.tmp.name)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["updatedInput"]["command"],
                         "set -o pipefail; pytest -q 2>&1 | tail -n 100")

    def test_project_dir_falls_back_to_cwd_field(self):
        (Path(self.tmp.name) / ".claude").mkdir()
        (Path(self.tmp.name) / ".claude" / "project-base.json").write_text('{"test_command_patterns": ["^make check$"]}')
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        payload = json.dumps({"cwd": self.tmp.name, "tool_input": {"command": "make check"}})
        p = subprocess.run([sys.executable, str(SCRIPT)], input=payload, capture_output=True, text=True, env=env)
        self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["updatedInput"]["command"],
                         "set -o pipefail; make check 2>&1 | tail -n 100")


if __name__ == "__main__":
    unittest.main()
